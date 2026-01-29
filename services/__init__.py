# -*- coding: utf-8 -*-
"""
服务模块
"""

from .knowledge_service import (
    KnowledgeService,
    KnowledgeResult,
    get_knowledge_service,
    reset_knowledge_service
)

from .profile_service import (
    ProfileService,
    get_profile_service,
    reset_profile_service
)

__all__ = [
    'KnowledgeService',
    'KnowledgeResult',
    'get_knowledge_service',
    'reset_knowledge_service',
    'ProfileService',
    'get_profile_service',
    'reset_profile_service',
]
