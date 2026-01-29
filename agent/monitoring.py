# -*- coding: utf-8 -*-
"""
医疗智能助手 - 监控指标
使用Prometheus风格的指标收集
"""

import time
import asyncio
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps
import threading
import logging

logger = logging.getLogger(__name__)


# ============================================================
# 指标数据结构
# ============================================================

@dataclass
class MetricValue:
    """指标值"""
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HistogramBucket:
    """直方图桶"""
    le: float  # 小于等于
    count: int = 0


class MetricType:
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


# ============================================================
# 指标基类
# ============================================================

class Metric:
    """指标基类"""

    def __init__(
        self,
        name: str,
        description: str,
        metric_type: str,
        label_names: List[str] = None
    ):
        self.name = name
        self.description = description
        self.metric_type = metric_type
        self.label_names = label_names or []
        self._data: Dict[tuple, MetricValue] = {}
        self._lock = threading.RLock()

    def _make_key(self, labels: Dict[str, str]) -> tuple:
        """创建标签键"""
        return tuple(labels.get(name, "") for name in self.label_names)

    def _validate_labels(self, labels: Dict[str, str]):
        """验证标签"""
        if set(labels.keys()) != set(self.label_names):
            raise ValueError(f"Invalid labels. Expected {self.label_names}, got {list(labels.keys())}")

    def get_value(self, labels: Dict[str, str] = None) -> float:
        """获取指标值"""
        labels = labels or {}
        key = self._make_key(labels)
        with self._lock:
            metric_value = self._data.get(key)
            return metric_value.value if metric_value else 0

    def get_total_count(self) -> float:
        """获取总计数（所有label组合的总和）"""
        with self._lock:
            return sum(v.value for v in self._data.values())

    def get_all_values(self) -> Dict[tuple, MetricValue]:
        """获取所有值"""
        with self._lock:
            return dict(self._data)

    def reset(self):
        """重置指标"""
        with self._lock:
            self._data.clear()

    def export_prometheus(self) -> str:
        """导出为Prometheus格式"""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} {self.metric_type}"
        ]
        lines.extend(self._format_prometheus_values())
        return "\n".join(lines)

    def _format_prometheus_values(self) -> List[str]:
        """格式化Prometheus值"""
        raise NotImplementedError


class Counter(Metric):
    """计数器 - 只增不减"""

    def __init__(
        self,
        name: str,
        description: str,
        label_names: List[str] = None
    ):
        super().__init__(name, description, MetricType.COUNTER, label_names)

    def inc(self, value: float = 1.0, labels: Dict[str, str] = None):
        """增加计数"""
        if value < 0:
            raise ValueError("Counter can only increase")
        labels = labels or {}
        key = self._make_key(labels)

        with self._lock:
            if key in self._data:
                self._data[key].value += value
                self._data[key].timestamp = datetime.now()
            else:
                self._data[key] = MetricValue(value=value, labels=labels)

    def _format_prometheus_values(self) -> List[str]:
        lines = []
        for key, metric_value in self._data.items():
            label_str = self._format_labels(metric_value.labels)
            lines.append(f"{self.name}{label_str} {metric_value.value}")
        return lines

    def _format_labels(self, labels: Dict[str, str]) -> str:
        if not labels:
            return ""
        pairs = [f'{k}="{v}"' for k, v in labels.items()]
        return "{" + ",".join(pairs) + "}"


class Gauge(Metric):
    """仪表 - 可增可减"""

    def __init__(
        self,
        name: str,
        description: str,
        label_names: List[str] = None
    ):
        super().__init__(name, description, MetricType.GAUGE, label_names)

    def set(self, value: float, labels: Dict[str, str] = None):
        """设置值"""
        labels = labels or {}
        key = self._make_key(labels)

        with self._lock:
            if key in self._data:
                self._data[key].value = value
                self._data[key].timestamp = datetime.now()
            else:
                self._data[key] = MetricValue(value=value, labels=labels)

    def inc(self, value: float = 1.0, labels: Dict[str, str] = None):
        """增加"""
        labels = labels or {}
        current = self.get_value(labels)
        self.set(current + value, labels)

    def dec(self, value: float = 1.0, labels: Dict[str, str] = None):
        """减少"""
        labels = labels or {}
        current = self.get_value(labels)
        self.set(current - value, labels)

    def _format_prometheus_values(self) -> List[str]:
        lines = []
        for key, metric_value in self._data.items():
            label_str = self._format_labels(metric_value.labels)
            lines.append(f"{self.name}{label_str} {metric_value.value}")
        return lines

    def _format_labels(self, labels: Dict[str, str]) -> str:
        if not labels:
            return ""
        pairs = [f'{k}="{v}"' for k, v in labels.items()]
        return "{" + ",".join(pairs) + "}"


class Histogram(Metric):
    """直方图 - 分布统计"""

    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]

    def __init__(
        self,
        name: str,
        description: str,
        label_names: List[str] = None,
        buckets: List[float] = None
    ):
        super().__init__(name, description, MetricType.HISTOGRAM, label_names)
        self.buckets = buckets or self.DEFAULT_BUCKETS.copy()
        self._counts: Dict[tuple, Dict[float, int]] = defaultdict(lambda: {b: 0 for b in self.buckets})
        self._sums: Dict[tuple, float] = defaultdict(float)
        self._counts_raw: Dict[tuple, int] = defaultdict(int)

    def observe(self, value: float, labels: Dict[str, str] = None):
        """观察一个值"""
        labels = labels or {}
        key = self._make_key(labels)

        with self._lock:
            # 更新计数
            for bucket in self.buckets:
                if value <= bucket:
                    self._counts[key][bucket] += 1

            # 更新总和和计数
            self._sums[key] += value
            self._counts_raw[key] += 1

            # 更新基本数据（用于get_value）
            if key not in self._data:
                self._data[key] = MetricValue(value=0, labels=labels)
            self._data[key].timestamp = datetime.now()

    def get_sum(self, labels: Dict[str, str] = None) -> float:
        """获取总和"""
        labels = labels or {}
        key = self._make_key(labels)
        return self._sums.get(key, 0)

    def get_count(self, labels: Dict[str, str] = None) -> int:
        """获取观察次数"""
        labels = labels or {}
        key = self._make_key(labels)
        return self._counts_raw.get(key, 0)

    def get_average(self, labels: Dict[str, str] = None) -> float:
        """获取平均值"""
        count = self.get_count(labels)
        if count == 0:
            return 0
        return self.get_sum(labels) / count

    def get_bucket_values(self, labels: Dict[str, str] = None) -> Dict[float, int]:
        """获取桶值"""
        labels = labels or {}
        key = self._make_key(labels)
        return dict(self._counts.get(key, {}))

    def _format_prometheus_values(self) -> List[str]:
        lines = []
        for key_tuple, counts in self._counts.items():
            labels = {name: key_tuple[i] for i, name in enumerate(self.label_names)}
            label_str = self._format_labels(labels)
            sum_val = self._sums.get(key_tuple, 0)
            count = self._counts_raw.get(key_tuple, 0)

            # 桶计数
            cumulative = 0
            for bucket in self.buckets:
                cumulative += counts.get(bucket, 0)
                lines.append(f"{self.name}_bucket{{le=\"{bucket}\",{label_str[1:-1]}}} {cumulative}")

            # +Inf桶
            lines.append(f"{self.name}_bucket{{le=\"+Inf\",{label_str[1:-1]}}} {count}")
            # 总和
            lines.append(f"{self.name}_sum{label_str} {sum_val}")
            # 计数
            lines.append(f"{self.name}_count{label_str} {count}")

        return lines

    def _format_labels(self, labels: Dict[str, str]) -> str:
        if not labels:
            return ""
        pairs = [f'{k}="{v}"' for k, v in labels.items()]
        return "{" + ",".join(pairs) + "}"

    def reset(self):
        """重置直方图"""
        with self._lock:
            super().reset()
            self._counts.clear()
            self._sums.clear()
            self._counts_raw.clear()


# ============================================================
# 指标收集器
# ============================================================

class MetricsCollector:
    """
    医疗助手指标收集器
    收集所有业务相关的监控指标
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.RLock()
        self._init_metrics()

    def _init_metrics(self):
        """初始化所有指标"""

        # ========== 意图分类指标 ==========
        self.intent_total = Counter(
            name="intent_classification_total",
            description="Total intent classifications",
            label_names=["intent", "result"]
        )

        self.intent_confidence = Histogram(
            name="intent_confidence",
            description="Intent confidence distribution",
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )

        self.intent_duration = Histogram(
            name="intent_classification_duration_seconds",
            description="Intent classification duration",
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
        )

        self.ambiguous_intent_total = Counter(
            name="ambiguous_intent_total",
            description="Total ambiguous intent detections",
            label_names=["resolved"]
        )

        # ========== Skill执行指标 ==========
        self.skill_total = Counter(
            name="skill_invocation_total",
            description="Total skill invocations",
            label_names=["skill", "result"]
        )

        self.skill_duration = Histogram(
            name="skill_execution_seconds",
            description="Skill execution time",
            label_names=["skill"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        )

        self.skill_errors = Counter(
            name="skill_errors_total",
            description="Skill errors",
            label_names=["skill", "error_type"]
        )

        self.skill_timeout_total = Counter(
            name="skill_timeout_total",
            description="Skill timeouts",
            label_names=["skill"]
        )

        # ========== 会话指标 ==========
        self.active_sessions = Gauge(
            name="active_sessions",
            description="Number of active sessions"
        )

        self.session_total = Counter(
            name="session_total",
            description="Total sessions created",
            label_names=["status"]
        )

        self.session_duration = Histogram(
            name="session_duration_seconds",
            description="Session duration",
            buckets=[10, 30, 60, 300, 600, 1800, 3600]
        )

        self.session_turns = Histogram(
            name="session_turns_total",
            description="Number of turns per session",
            buckets=[1, 2, 3, 5, 10, 20, 50]
        )

        # ========== 安全指标 ==========
        self.emergency_detected = Counter(
            name="emergency_detections_total",
            description="Emergency detections",
            label_names=["level"]
        )

        self.safety_warnings = Counter(
            name="safety_warnings_total",
            description="Safety warnings",
            label_names=["type", "severity"]
        )

        self.drug_interaction_detected = Counter(
            name="drug_interaction_detections_total",
            description="Drug interaction detections",
            label_names=["severity"]
        )

        self.allergy_risk_detected = Counter(
            name="allergy_risk_detections_total",
            description="Allergy risk detections"
        )

        # ========== 缓存指标 ==========
        self.cache_hits = Counter(
            name="cache_hits_total",
            description="Cache hits",
            label_names=["cache_type"]
        )

        self.cache_misses = Counter(
            name="cache_misses_total",
            description="Cache misses",
            label_names=["cache_type"]
        )

        self.cache_size = Gauge(
            name="cache_size",
            description="Current cache size",
            label_names=["cache_type"]
        )

        # ========== 知识库指标 ==========
        self.knowledge_query_total = Counter(
            name="knowledge_query_total",
            description="Knowledge base queries",
            label_names=["category", "result"]
        )

        self.knowledge_query_duration = Histogram(
            name="knowledge_query_duration_seconds",
            description="Knowledge query duration",
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
        )

        # ========== 用户画像指标 ==========
        self.profile_queries = Counter(
            name="profile_queries_total",
            description="User profile queries",
            label_names=["result"]
        )

        self.profile_updates = Counter(
            name="profile_updates_total",
            description="User profile updates",
            label_names=["field"]
        )

        # ========== MCP调用指标 ==========
        self.mcp_calls_total = Counter(
            name="mcp_calls_total",
            description="MCP tool calls",
            label_names=["tool", "result"]
        )

        self.mcp_duration = Histogram(
            name="mcp_call_duration_seconds",
            description="MCP call duration",
            label_names=["tool"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2]
        )

        # 注册所有指标
        self._register_all()

    def _register_all(self):
        """注册所有指标"""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, Metric):
                self._metrics[attr.name] = attr

    def get_metric(self, name: str) -> Optional[Metric]:
        """获取指标"""
        return self._metrics.get(name)

    def export_all(self) -> str:
        """导出所有指标为Prometheus格式"""
        if not self.enabled:
            return ""

        lines = []
        for metric in self._metrics.values():
            lines.append(metric.export_prometheus())
            lines.append("")  # 空行分隔

        return "\n".join(lines)

    def reset_all(self):
        """重置所有指标"""
        for metric in self._metrics.values():
            metric.reset()

    # ========== 便捷方法 ==========

    def record_intent_classification(
        self,
        intent: str,
        confidence: float,
        duration: float,
        success: bool = True
    ):
        """记录意图分类"""
        if not self.enabled:
            return

        result = "success" if success else "failure"
        self.intent_total.inc(labels={"intent": intent, "result": result})
        self.intent_confidence.observe(confidence)
        self.intent_duration.observe(duration)

    def record_skill_execution(
        self,
        skill: str,
        duration: float,
        success: bool = True,
        error_type: str = None
    ):
        """记录Skill执行"""
        if not self.enabled:
            return

        result = "success" if success else "failure"
        self.skill_total.inc(labels={"skill": skill, "result": result})
        self.skill_duration.observe(duration, labels={"skill": skill})

        if not success and error_type:
            self.skill_errors.inc(labels={"skill": skill, "error_type": error_type})

    def record_session_start(self):
        """记录会话开始"""
        if not self.enabled:
            return
        self.active_sessions.inc()
        self.session_total.inc(labels={"status": "started"})

    def record_session_end(self, duration: float, turn_count: int):
        """记录会话结束"""
        if not self.enabled:
            return
        self.active_sessions.dec()
        self.session_duration.observe(duration)
        self.session_turns.observe(turn_count)
        self.session_total.inc(labels={"status": "ended"})

    def record_emergency(self, level: str):
        """记录紧急情况检测"""
        if not self.enabled:
            return
        self.emergency_detected.inc(labels={"level": level})

    def record_safety_warning(self, warning_type: str, severity: str):
        """记录安全警告"""
        if not self.enabled:
            return
        self.safety_warnings.inc(labels={"type": warning_type, "severity": severity})

    def record_cache_hit(self, cache_type: str):
        """记录缓存命中"""
        if not self.enabled:
            return
        self.cache_hits.inc(labels={"cache_type": cache_type})

    def record_cache_miss(self, cache_type: str):
        """记录缓存未命中"""
        if not self.enabled:
            return
        self.cache_misses.inc(labels={"cache_type": cache_type})

    def set_cache_size(self, cache_type: str, size: int):
        """设置缓存大小"""
        if not self.enabled:
            return
        self.cache_size.set(size, labels={"cache_type": cache_type})

    def get_cache_hit_rate(self, cache_type: str) -> float:
        """获取缓存命中率"""
        hits = self.cache_hits.get_value(labels={"cache_type": cache_type})
        misses = self.cache_misses.get_value(labels={"cache_type": cache_type})
        total = hits + misses
        return hits / total if total > 0 else 0

    def record_mcp_call(self, tool: str, duration: float, success: bool = True):
        """记录MCP调用"""
        if not self.enabled:
            return

        result = "success" if success else "failure"
        self.mcp_calls_total.inc(labels={"tool": tool, "result": result})
        self.mcp_duration.observe(duration, labels={"tool": tool})

    def get_stats_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        if not self.enabled:
            return {}

        return {
            "intent_classifications": self.intent_total.get_total_count(),
            "skill_invocations": self.skill_total.get_total_count(),
            "active_sessions": self.active_sessions.get_value(),
            "emergency_detections": self.emergency_detected.get_total_count(),
            "safety_warnings": self.safety_warnings.get_total_count(),
            "mcp_calls": self.mcp_calls_total.get_total_count(),
            "cache_hit_rate": {
                "intent": self.get_cache_hit_rate("intent"),
                "kb": self.get_cache_hit_rate("kb"),
                "profile": self.get_cache_hit_rate("profile"),
            },
            "avg_intent_confidence": self.intent_confidence.get_average(),
            "avg_skill_duration": self.skill_duration.get_average(),
        }


# ============================================================
# 装饰器
# ============================================================

def track_time(collector: MetricsCollector, histogram: Histogram, labels: Dict[str, str] = None):
    """跟踪执行时间的装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                if labels:
                    histogram.observe(duration, labels)
                else:
                    histogram.observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start
                if labels:
                    histogram.observe(duration, labels)
                else:
                    histogram.observe(duration)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                if labels:
                    histogram.observe(duration, labels)
                else:
                    histogram.observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start
                if labels:
                    histogram.observe(duration, labels)
                else:
                    histogram.observe(duration)
                raise

        # 根据函数是否是协程返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_counter(collector: MetricsCollector, counter: Counter, labels: Dict[str, str] = None, success_only: bool = True):
    """跟踪计数的装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                if not success_only or result is not None:
                    counter.inc(labels=labels or {})
                return result
            except Exception:
                if not success_only:
                    counter.inc(labels={**(labels or {}), "result": "failure"})
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                if not success_only or result is not None:
                    counter.inc(labels=labels or {})
                return result
            except Exception:
                if not success_only:
                    counter.inc(labels={**(labels or {}), "result": "failure"})
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================
# 全局实例
# ============================================================

_global_collector: Optional[MetricsCollector] = None


def get_metrics_collector(enabled: bool = True) -> MetricsCollector:
    """获取全局指标收集器"""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector(enabled=enabled)
    return _global_collector


def reset_metrics():
    """重置全局指标"""
    global _global_collector
    if _global_collector:
        _global_collector.reset_all()


if __name__ == "__main__":
    # 测试
    collector = MetricsCollector()

    # 模拟一些指标
    collector.record_intent_classification("symptom_inquiry", 0.85, 0.05)
    collector.record_intent_classification("department_query", 0.72, 0.03)
    collector.record_skill_execution("symptom-analyzer", 0.15)
    collector.record_session_start()
    collector.record_cache_hit("intent")
    collector.record_cache_miss("kb")

    print(collector.export_all())
    print("\n=== Stats Summary ===")
    import json
    print(json.dumps(collector.get_stats_summary(), indent=2))
