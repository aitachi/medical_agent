# -*- coding: utf-8 -*-
"""
医疗智能助手 - 缓存管理器
使用TTL缓存提高系统性能
"""

import asyncio
import hashlib
import pickle
import time
import threading
from typing import Any, Optional, Dict, Callable, TypeVar, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
import functools

# 尝试导入cachetools
try:
    from cachetools import TTLCache
    CACHETOOLS_AVAILABLE = True
except ImportError:
    CACHETOOLS_AVAILABLE = False


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    hits: int = 0
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def ttl(self) -> Optional[float]:
        """获取剩余TTL（秒）"""
        if self.expires_at is None:
            return None
        remaining = (self.expires_at - datetime.now()).total_seconds()
        return max(0, remaining) if remaining > 0 else 0


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    total_size_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0


class LRUCache:
    """简单的LRU缓存实现（当cachetools不可用时）"""

    def __init__(self, maxsize: int = 128, ttl: int = 300):
        self.maxsize = maxsize
        self.ttl = ttl  # TTL in seconds
        self._data: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """获取值"""
        with self._lock:
            if key not in self._data:
                self._stats.misses += 1
                return None

            entry = self._data[key]

            # 检查过期
            if entry.is_expired():
                del self._data[key]
                self._stats.misses += 1
                self._stats.size -= 1
                return None

            # 移到末尾（最近使用）
            self._data.move_to_end(key)
            entry.hits += 1
            self._stats.hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置值"""
        with self._lock:
            # 计算过期时间
            expires_at = None
            if ttl is not None:
                expires_at = datetime.now() + timedelta(seconds=ttl)
            elif self.ttl > 0:
                expires_at = datetime.now() + timedelta(seconds=self.ttl)

            # 计算大小
            size_bytes = len(pickle.dumps(value))

            # 如果已存在，更新
            if key in self._data:
                old_entry = self._data[key]
                self._stats.total_size_bytes -= old_entry.size_bytes

            entry = CacheEntry(
                key=key,
                value=value,
                expires_at=expires_at,
                size_bytes=size_bytes
            )

            # 检查容量
            if len(self._data) >= self.maxsize and key not in self._data:
                # 移除最旧的
                self._data.popitem(last=False)
                self._stats.evictions += 1

            self._data[key] = entry
            self._data.move_to_end(key)
            self._stats.size = len(self._data)
            self._stats.total_size_bytes += size_bytes

    def delete(self, key: str) -> bool:
        """删除条目"""
        with self._lock:
            if key in self._data:
                entry = self._data.pop(key)
                self._stats.size -= 1
                self._stats.total_size_bytes -= entry.size_bytes
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._data.clear()
            self._stats.size = 0
            self._stats.total_size_bytes = 0

    def cleanup_expired(self):
        """清理过期条目"""
        with self._lock:
            expired_keys = [k for k, v in self._data.items() if v.is_expired()]
            for key in expired_keys:
                entry = self._data.pop(key)
                self._stats.size -= 1
                self._stats.total_size_bytes -= entry.size_bytes

    def get_stats(self) -> CacheStats:
        """获取统计信息"""
        with self._lock:
            self._stats.size = len(self._data)
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size=self._stats.size,
                total_size_bytes=self._stats.total_size_bytes
            )

    def __len__(self):
        return len(self._data)

    def __contains__(self, key: str):
        return key in self._data


class CacheManager:
    """
    缓存管理器
    管理多个缓存实例，提供统一的缓存访问接口
    """

    def __init__(
        self,
        intent_cache_size: int = 1000,
        intent_ttl: int = 300,
        kb_cache_size: int = 500,
        kb_ttl: int = 3600,
        profile_cache_size: int = 200,
        profile_ttl: int = 1800
    ):
        """
        初始化缓存管理器

        Args:
            intent_cache_size: 意图分类缓存大小
            intent_ttl: 意图分类缓存TTL（秒）
            kb_cache_size: 知识库缓存大小
            kb_ttl: 知识库缓存TTL（秒）
            profile_cache_size: 用户画像缓存大小
            profile_ttl: 用户画像缓存TTL（秒）
        """
        self.locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = threading.RLock()

        # 创建各种缓存
        self.intent_cache = self._create_cache(intent_cache_size, intent_ttl, "intent")
        self.kb_cache = self._create_cache(kb_cache_size, kb_ttl, "kb")
        self.profile_cache = self._create_cache(profile_cache_size, profile_ttl, "profile")

    def _create_cache(self, maxsize: int, ttl: int, name: str):
        """创建缓存实例"""
        if CACHETOOLS_AVAILABLE:
            cache = TTLCache(maxsize=maxsize, ttl=ttl)
        else:
            cache = LRUCache(maxsize=maxsize, ttl=ttl)

        # 创建对应的异步锁
        with self._global_lock:
            self.locks[name] = asyncio.Lock()

        return cache

    def _make_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        # 将参数序列化为字符串
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        key_str = ":".join(key_parts)

        # 使用哈希缩短键名
        if len(key_str) > 100:
            return hashlib.md5(key_str.encode()).hexdigest()
        return key_str

    def _get_lock(self, cache_name: str) -> asyncio.Lock:
        """获取缓存的锁"""
        if cache_name not in self.locks:
            with self._global_lock:
                self.locks[cache_name] = asyncio.Lock()
        return self.locks[cache_name]

    async def get_or_compute(
        self,
        cache,
        cache_name: str,
        key: str,
        compute_fn: Callable,
        *args,
        ttl: Optional[int] = None
    ) -> Any:
        """
        获取或计算缓存值（带双重检查锁定）

        Args:
            cache: 缓存实例
            cache_name: 缓存名称
            key: 缓存键
            compute_fn: 计算函数
            *args: 传递给计算函数的参数
            ttl: 自定义TTL

        Returns:
            Any: 缓存值或计算结果
        """
        # 第一次检查（无锁）
        value = self._get_from_cache(cache, key)
        if value is not None:
            return value

        # 获取锁并双重检查
        lock = self._get_lock(cache_name)
        async with lock:
            # 第二次检查（有锁）
            value = self._get_from_cache(cache, key)
            if value is not None:
                return value

            # 计算值
            if asyncio.iscoroutinefunction(compute_fn):
                value = await compute_fn(*args)
            else:
                value = compute_fn(*args)

            # 存入缓存
            self._set_to_cache(cache, key, value, ttl)
            return value

    def _get_from_cache(self, cache, key: str) -> Optional[Any]:
        """从缓存获取值"""
        if CACHETOOLS_AVAILABLE:
            return cache.get(key, None)
        else:
            return cache.get(key)

    def _set_to_cache(self, cache, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存值"""
        if CACHETOOLS_AVAILABLE:
            cache[key] = value
        else:
            cache.set(key, value, ttl)

    # ========== 意图分类缓存 ==========

    async def get_or_classify(
        self,
        text: str,
        classifier: Callable,
        context: Any,
        ttl: Optional[int] = None
    ) -> Any:
        """
        获取或进行意图分类

        Args:
            text: 输入文本
            classifier: 分类器函数
            context: 对话上下文
            ttl: 自定义TTL

        Returns:
            Any: 分类结果
        """
        # 生成缓存键（包含上下文信息）
        context_key = self._get_context_key(context)
        key = self._make_key("intent", text, context_key)

        return await self.get_or_compute(
            self.intent_cache,
            "intent",
            key,
            classifier,
            text,
            context,
            ttl=ttl
        )

    def _get_context_key(self, context: Any) -> str:
        """从上下文提取缓存键"""
        if context is None:
            return ""
        if hasattr(context, 'current_intent'):
            intent = context.current_intent
            if intent:
                return intent.intent.value if hasattr(intent, 'intent') else str(intent)
        return ""

    # ========== 知识库缓存 ==========

    async def get_or_query_kb(
        self,
        category: str,
        keyword: str,
        query_fn: Callable,
        ttl: Optional[int] = None
    ) -> Any:
        """
        获取或查询知识库

        Args:
            category: 查询类别
            keyword: 关键词
            query_fn: 查询函数
            ttl: 自定义TTL

        Returns:
            Any: 查询结果
        """
        key = self._make_key("kb", category, keyword)

        return await self.get_or_compute(
            self.kb_cache,
            "kb",
            key,
            query_fn,
            category,
            keyword,
            ttl=ttl
        )

    # ========== 用户画像缓存 ==========

    async def get_or_load_profile(
        self,
        user_id: str,
        load_fn: Callable,
        ttl: Optional[int] = None
    ) -> Any:
        """
        获取或加载用户画像

        Args:
            user_id: 用户ID
            load_fn: 加载函数
            ttl: 自定义TTL

        Returns:
            Any: 用户画像
        """
        key = self._make_key("profile", user_id)

        return await self.get_or_compute(
            self.profile_cache,
            "profile",
            key,
            load_fn,
            user_id,
            ttl=ttl
        )

    # ========== 通用缓存操作 ==========

    def invalidate(self, cache_name: str, key: Optional[str] = None):
        """
        使缓存失效

        Args:
            cache_name: 缓存名称
            key: 缓存键，如果为None则清空整个缓存
        """
        cache = getattr(self, f"{cache_name}_cache", None)
        if cache is None:
            return

        if key is None:
            # 清空整个缓存
            if CACHETOOLS_AVAILABLE:
                cache.clear()
            else:
                cache.clear()
        else:
            # 删除特定键
            if CACHETOOLS_AVAILABLE:
                cache.pop(key, None)
            else:
                cache.delete(key)

    def warm_up(self, cache_name: str, data: Dict[str, Any]):
        """
        预热缓存

        Args:
            cache_name: 缓存名称
            data: 预热数据
        """
        cache = getattr(self, f"{cache_name}_cache", None)
        if cache is None:
            return

        for key, value in data.items():
            self._set_to_cache(cache, key, value)

    # ========== 统计信息 ==========

    def get_cache_stats(self, cache_name: str) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Args:
            cache_name: 缓存名称

        Returns:
            Dict: 统计信息
        """
        cache = getattr(self, f"{cache_name}_cache", None)
        if cache is None:
            return {}

        if CACHETOOLS_AVAILABLE:
            return {
                "size": len(cache),
                "maxsize": cache.maxsize,
                "ttl": cache.ttl
            }
        else:
            stats = cache.get_stats()
            return {
                "size": stats.size,
                "hits": stats.hits,
                "misses": stats.misses,
                "hit_rate": stats.hit_rate,
                "evictions": stats.evictions,
                "total_size_bytes": stats.total_size_bytes
            }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓存统计信息"""
        return {
            "intent": self.get_cache_stats("intent"),
            "kb": self.get_cache_stats("kb"),
            "profile": self.get_cache_stats("profile"),
        }

    def cleanup_expired_all(self):
        """清理所有缓存的过期条目"""
        if not CACHETOOLS_AVAILABLE:
            for cache_name in ["intent", "kb", "profile"]:
                cache = getattr(self, f"{cache_name}_cache", None)
                if cache and hasattr(cache, 'cleanup_expired'):
                    cache.cleanup_expired()

    # ========== 装饰器 ==========

    def cached(
        self,
        cache_name: str = "intent",
        ttl: Optional[int] = None,
        key_fn: Optional[Callable] = None
    ):
        """
        缓存装饰器

        Args:
            cache_name: 缓存名称
            ttl: 自定义TTL
            key_fn: 自定义键生成函数
        """
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                cache = getattr(self, f"{cache_name}_cache", None)
                if cache is None:
                    return await func(*args, **kwargs)

                # 生成键
                if key_fn:
                    key = key_fn(*args, **kwargs)
                else:
                    # 使用函数名和参数生成键
                    key = self._make_key(func.__name__, *args, **kwargs)

                # 尝试获取缓存
                value = self._get_from_cache(cache, key)
                if value is not None:
                    return value

                # 计算并缓存
                result = await func(*args, **kwargs)
                self._set_to_cache(cache, key, result, ttl)
                return result

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                cache = getattr(self, f"{cache_name}_cache", None)
                if cache is None:
                    return func(*args, **kwargs)

                # 生成键
                if key_fn:
                    key = key_fn(*args, **kwargs)
                else:
                    key = self._make_key(func.__name__, *args, **kwargs)

                # 尝试获取缓存
                value = self._get_from_cache(cache, key)
                if value is not None:
                    return value

                # 计算并缓存
                result = func(*args, **kwargs)
                self._set_to_cache(cache, key, result, ttl)
                return result

            # 根据函数类型返回对应的包装器
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator


# ============================================================
# 全局缓存管理器实例
# ============================================================

_global_cache_manager: Optional[CacheManager] = None


def get_cache_manager(**kwargs) -> CacheManager:
    """获取全局缓存管理器"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager(**kwargs)
    return _global_cache_manager


def reset_cache_manager():
    """重置全局缓存管理器"""
    global _global_cache_manager
    _global_cache_manager = None


# ============================================================
# 测试代码
# ============================================================

if __name__ == "__main__":
    import asyncio

    async def test():
        print("缓存管理器测试")
        print("=" * 60)

        # 创建缓存管理器
        cache_mgr = CacheManager(
            intent_cache_size=10,
            intent_ttl=5,  # 5秒TTL用于测试
        )

        # 测试意图分类缓存
        async def mock_classify(text, context):
            print(f"  -> 执行分类: {text}")
            await asyncio.sleep(0.1)  # 模拟耗时
            return {"intent": "symptom_inquiry", "confidence": 0.85}

        # 第一次调用 - 会执行分类
        print("\n1. 第一次调用（应该执行分类）:")
        result1 = await cache_mgr.get_or_classify("我头痛", mock_classify, None)

        # 第二次调用 - 应该从缓存获取
        print("\n2. 第二次调用（应该从缓存获取）:")
        result2 = await cache_mgr.get_or_classify("我头痛", mock_classify, None)

        # 不同文本 - 会执行分类
        print("\n3. 不同文本（应该执行分类）:")
        result3 = await cache_mgr.get_or_classify("我发烧", mock_classify, None)

        # 打印统计
        print("\n4. 缓存统计:")
        stats = cache_mgr.get_all_stats()
        for cache_name, cache_stats in stats.items():
            print(f"  {cache_name}: {cache_stats}")

        # 等待过期后再次调用
        print("\n5. 等待6秒后（缓存已过期）:")
        await asyncio.sleep(6)
        result4 = await cache_mgr.get_or_classify("我头痛", mock_classify, None)

        # 最终统计
        print("\n6. 最终缓存统计:")
        stats = cache_mgr.get_all_stats()
        for cache_name, cache_stats in stats.items():
            print(f"  {cache_name}: {cache_stats}")

    asyncio.run(test())
