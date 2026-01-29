# -*- coding: utf-8 -*-
"""
医疗智能助手 - 配置管理
使用Pydantic进行配置验证和环境变量管理
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

# 尝试导入pydantic，如果不可用则使用dataclass
try:
    from pydantic import BaseModel, Field, validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # 定义简单的Field和validator替代品
    def Field(default=None, **kwargs):
        return default

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"


if PYDANTIC_AVAILABLE:
    class DatabaseConfig(BaseModel):
        """数据库配置"""
        path: str = Field(default=str(DATA_DIR / "sessions.db"), description="SQLite数据库路径")
        pool_size: int = Field(default=5, ge=1, le=20, description="连接池大小")
        timeout: int = Field(default=30, ge=5, description="查询超时时间(秒)")

    class CacheConfig(BaseModel):
        """缓存配置"""
        enabled: bool = Field(default=True, description="是否启用缓存")
        intent_ttl: int = Field(default=300, ge=0, description="意图分类缓存TTL(秒)")
        kb_ttl: int = Field(default=3600, ge=0, description="知识库缓存TTL(秒)")
        profile_ttl: int = Field(default=1800, ge=0, description="用户画像缓存TTL(秒)")
        max_size: int = Field(default=1000, ge=100, description="缓存最大条目数")

    class MonitoringConfig(BaseModel):
        """监控配置"""
        enabled: bool = Field(default=True, description="是否启用监控")
        metrics_port: int = Field(default=9090, ge=1024, le=65535, description="Prometheus指标端口")
        log_level: str = Field(default="INFO", description="日志级别")
        log_format: str = Field(default="json", description="日志格式: json或text")
        trace_enabled: bool = Field(default=False, description="是否启用链路追踪")

    class SafetyConfig(BaseModel):
        """安全检查配置"""
        strict_mode: bool = Field(default=True, description="严格模式 - 所有安全检查都强制执行")
        emergency_detection_enabled: bool = Field(default=True, description="启用紧急症状检测")
        drug_interaction_check: bool = Field(default=True, description="启用药物相互作用检查")
        allergy_check: bool = Field(default=True, description="启用过敏检查")
        dose_check: bool = Field(default=True, description="启用剂量检查")

    class IntentConfig(BaseModel):
        """意图分类配置"""
        confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="置信度阈值")
        fallback_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="兜底阈值")
        enable_jieba: bool = Field(default=True, description="启用jieba分词")
        enable_fuzzy_match: bool = Field(default=True, description="启用模糊匹配")
        enable_context_boost: bool = Field(default=True, description="启用上下文增强")
        max_history_turns: int = Field(default=5, ge=1, le=20, description="最大历史轮次")

    class SessionConfig(BaseModel):
        """会话配置"""
        persist_enabled: bool = Field(default=True, description="启用会话持久化")
        session_ttl: int = Field(default=86400, ge=0, description="会话TTL(秒)，默认24小时")
        max_history_length: int = Field(default=50, ge=10, description="最大历史记录长度")
        auto_save: bool = Field(default=True, description="自动保存会话")

    class KnowledgeConfig(BaseModel):
        """知识库配置"""
        external_enabled: bool = Field(default=True, description="启用外部知识库")
        kb_path: str = Field(default=str(DATA_DIR / "knowledge_base.json"), description="知识库文件路径")
        auto_reload: bool = Field(default=False, description="自动重新加载")
        reload_interval: int = Field(default=300, ge=60, description="重载间隔(秒)")

    class MCPConfig(BaseModel):
        """MCP配置"""
        host: str = Field(default="localhost", description="MCP主机地址")
        port: int = Field(default=50051, ge=1024, le=65535, description="MCP端口")
        protocol: str = Field(default="grpc", description="协议类型: grpc或http")
        timeout: int = Field(default=30, ge=5, description="请求超时(秒)")

    class Settings(BaseModel):
        """应用主配置"""
        app_name: str = Field(default="Medical AI Assistant", description="应用名称")
        version: str = Field(default="1.0.0", description="版本号")
        debug: bool = Field(default=False, description="调试模式")
        environment: str = Field(default="development", description="运行环境")

        # 子配置
        database: DatabaseConfig = Field(default_factory=DatabaseConfig)
        cache: CacheConfig = Field(default_factory=CacheConfig)
        monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
        safety: SafetyConfig = Field(default_factory=SafetyConfig)
        intent: IntentConfig = Field(default_factory=IntentConfig)
        session: SessionConfig = Field(default_factory=SessionConfig)
        knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
        mcp: MCPConfig = Field(default_factory=MCPConfig)

        @validator('environment')
        def validate_environment(cls, v):
            valid_envs = ['development', 'staging', 'production']
            if v not in valid_envs:
                raise ValueError(f'Invalid environment. Must be one of {valid_envs}')
            return v

        @classmethod
        def from_env(cls) -> 'Settings':
            """从环境变量加载配置"""
            return cls()

        @classmethod
        def from_file(cls, config_path: str) -> 'Settings':
            """从配置文件加载"""
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls(**data)

        def to_file(self, config_path: str):
            """保存配置到文件"""
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.dict(), f, indent=2, ensure_ascii=False)

else:
    # Pydantic不可用时的简单版本
    @dataclass
    class DatabaseConfig:
        path: str = str(DATA_DIR / "sessions.db")
        pool_size: int = 5
        timeout: int = 30

    @dataclass
    class CacheConfig:
        enabled: bool = True
        intent_ttl: int = 300
        kb_ttl: int = 3600
        profile_ttl: int = 1800
        max_size: int = 1000

    @dataclass
    class MonitoringConfig:
        enabled: bool = True
        metrics_port: int = 9090
        log_level: str = "INFO"
        log_format: str = "json"
        trace_enabled: bool = False

    @dataclass
    class SafetyConfig:
        strict_mode: bool = True
        emergency_detection_enabled: bool = True
        drug_interaction_check: bool = True
        allergy_check: bool = True
        dose_check: bool = True

    @dataclass
    class IntentConfig:
        confidence_threshold: float = 0.6
        fallback_threshold: float = 0.3
        enable_jieba: bool = True
        enable_fuzzy_match: bool = True
        enable_context_boost: bool = True
        max_history_turns: int = 5

    @dataclass
    class SessionConfig:
        persist_enabled: bool = True
        session_ttl: int = 86400
        max_history_length: int = 50
        auto_save: bool = True

    @dataclass
    class KnowledgeConfig:
        external_enabled: bool = True
        kb_path: str = str(DATA_DIR / "knowledge_base.json")
        auto_reload: bool = False
        reload_interval: int = 300

    @dataclass
    class MCPConfig:
        host: str = "localhost"
        port: int = 50051
        protocol: str = "grpc"
        timeout: int = 30

    @dataclass
    class Settings:
        app_name: str = "Medical AI Assistant"
        version: str = "1.0.0"
        debug: bool = False
        environment: str = "development"

        database: DatabaseConfig = field(default_factory=DatabaseConfig)
        cache: CacheConfig = field(default_factory=CacheConfig)
        monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
        safety: SafetyConfig = field(default_factory=SafetyConfig)
        intent: IntentConfig = field(default_factory=IntentConfig)
        session: SessionConfig = field(default_factory=SessionConfig)
        knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
        mcp: MCPConfig = field(default_factory=MCPConfig)

        @classmethod
        def from_env(cls) -> 'Settings':
            """从环境变量加载配置"""
            return cls(
                debug=os.getenv('DEBUG', '').lower() == 'true',
                environment=os.getenv('ENVIRONMENT', 'development'),
                database=DatabaseConfig(
                    path=os.getenv('DB_PATH', str(DATA_DIR / "sessions.db"))
                ),
                monitoring=MonitoringConfig(
                    log_level=os.getenv('LOG_LEVEL', 'INFO')
                )
            )

        @classmethod
        def from_file(cls, config_path: str) -> 'Settings':
            """从配置文件加载"""
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 递归构建配置对象
            db_data = data.pop('database', {})
            cache_data = data.pop('cache', {})
            monitoring_data = data.pop('monitoring', {})
            safety_data = data.pop('safety', {})
            intent_data = data.pop('intent', {})
            session_data = data.pop('session', {})
            knowledge_data = data.pop('knowledge', {})
            mcp_data = data.pop('mcp', {})

            return cls(
                database=DatabaseConfig(**db_data),
                cache=CacheConfig(**cache_data),
                monitoring=MonitoringConfig(**monitoring_data),
                safety=SafetyConfig(**safety_data),
                intent=IntentConfig(**intent_data),
                session=SessionConfig(**session_data),
                knowledge=KnowledgeConfig(**knowledge_data),
                mcp=MCPConfig(**mcp_data),
                **data
            )

        def to_file(self, config_path: str):
            """保存配置到文件"""
            import dataclasses

            def _to_dict(obj):
                if dataclasses.is_dataclass(obj):
                    return dataclasses.asdict(obj)
                return obj

            data = {
                'app_name': self.app_name,
                'version': self.version,
                'debug': self.debug,
                'environment': self.environment,
                'database': _to_dict(self.database),
                'cache': _to_dict(self.cache),
                'monitoring': _to_dict(self.monitoring),
                'safety': _to_dict(self.safety),
                'intent': _to_dict(self.intent),
                'session': _to_dict(self.session),
                'knowledge': _to_dict(self.knowledge),
                'mcp': _to_dict(self.mcp),
            }

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================
# 全局配置实例
# ============================================================

# 全局配置对象
_settings: Optional[Settings] = None


def get_settings(reload: bool = False) -> Settings:
    """
    获取全局配置实例

    Args:
        reload: 是否重新加载配置

    Returns:
        Settings: 配置对象
    """
    global _settings

    if _settings is None or reload:
        # 尝试从环境变量加载
        _settings = Settings.from_env()

        # 如果存在配置文件，则覆盖
        config_file = PROJECT_ROOT / "config.json"
        if config_file.exists():
            try:
                _settings = Settings.from_file(str(config_file))
            except Exception as e:
                import warnings
                warnings.warn(f"Failed to load config file: {e}")

        # 尝试加载.env文件
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)
            # 重新从环境变量加载
            _settings = Settings.from_env()

    return _settings


def reload_settings():
    """重新加载配置"""
    return get_settings(reload=True)


# ============================================================
# 配置验证和默认值
# ============================================================

DEFAULT_CONFIG = {
    "app_name": "Medical AI Assistant",
    "version": "1.0.0",
    "debug": False,
    "environment": "development",
    "database": {
        "path": "data/sessions.db",
        "pool_size": 5,
        "timeout": 30
    },
    "cache": {
        "enabled": True,
        "intent_ttl": 300,
        "kb_ttl": 3600,
        "profile_ttl": 1800,
        "max_size": 1000
    },
    "monitoring": {
        "enabled": True,
        "metrics_port": 9090,
        "log_level": "INFO",
        "log_format": "json"
    },
    "safety": {
        "strict_mode": True,
        "emergency_detection_enabled": True,
        "drug_interaction_check": True,
        "allergy_check": True,
        "dose_check": True
    },
    "intent": {
        "confidence_threshold": 0.6,
        "fallback_threshold": 0.3,
        "enable_jieba": True,
        "enable_fuzzy_match": True,
        "enable_context_boost": True,
        "max_history_turns": 5
    },
    "session": {
        "persist_enabled": True,
        "session_ttl": 86400,
        "max_history_length": 50,
        "auto_save": True
    },
    "knowledge": {
        "external_enabled": True,
        "kb_path": "data/knowledge_base.json",
        "auto_reload": False,
        "reload_interval": 300
    },
    "mcp": {
        "host": "localhost",
        "port": 50051,
        "protocol": "grpc",
        "timeout": 30
    }
}


def save_default_config(path: str = None):
    """保存默认配置到文件"""
    if path is None:
        path = PROJECT_ROOT / "config.json"

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # 测试配置加载
    settings = get_settings()
    print(f"Application: {settings.app_name} v{settings.version}")
    print(f"Database: {settings.database.path}")
    print(f"Cache TTL: {settings.cache.intent_ttl}s")
    print(f"Safety Mode: {settings.safety.strict_mode}")
