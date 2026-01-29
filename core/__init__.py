# -*- coding: utf-8 -*-
"""
Core 模块
包含核心功能：意图分类、安全检查、紧急检测、缓存、会话存储
"""

from .emergency_detector import (
    EmergencyDetector,
    EmergencyLevel,
    EmergencyAction,
    EmergencyResult,
    detect_emergency,
    is_emergency
)

from .safety_checker import (
    DrugSafetyChecker,
    SafetyReport,
    SafetyWarning,
    SafetySeverity,
    check_drug_safety
)

from .cache_manager import (
    CacheManager,
    get_cache_manager,
    reset_cache_manager
)

from .session_store import (
    SessionStore,
    SessionRecord,
    TurnRecord,
    get_session_store,
    reset_session_store
)

__all__ = [
    # Emergency
    'EmergencyDetector',
    'EmergencyLevel',
    'EmergencyAction',
    'EmergencyResult',
    'detect_emergency',
    'is_emergency',
    # Safety
    'DrugSafetyChecker',
    'SafetyReport',
    'SafetyWarning',
    'SafetySeverity',
    'check_drug_safety',
    # Cache
    'CacheManager',
    'get_cache_manager',
    'reset_cache_manager',
    # Session
    'SessionStore',
    'SessionRecord',
    'TurnRecord',
    'get_session_store',
    'reset_session_store',
]
