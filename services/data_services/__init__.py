# -*- coding: utf-8 -*-
"""
医疗智能助手 - 数据服务层
提供用户数据支撑服务
"""

from .user_profile_service import (
    UserProfileService,
    UserProfile,
    get_user_profile_service,
    reset_user_profile_service
)

from .health_records_service import (
    HealthRecordsService,
    HealthRecord,
    get_health_records_service,
    reset_health_records_service
)

from .chronic_disease_service import (
    ChronicDiseaseService,
    ChronicRecord,
    TrendAnalysis,
    get_chronic_disease_service,
    reset_chronic_disease_service
)

from .preference_service import (
    PreferenceService,
    UserPreference,
    get_preference_service,
    reset_preference_service
)

from .behavior_log_service import (
    BehaviorLogService,
    BehaviorLog,
    SessionLog,
    ActionType,
    get_behavior_log_service,
    reset_behavior_log_service
)

from .reminder_service import (
    ReminderDataService,
    Reminder,
    ReminderType,
    get_reminder_service,
    reset_reminder_service
)

from .payment_service import (
    PaymentService,
    Order,
    Coupon,
    get_payment_service,
    reset_payment_service
)

from .location_service import (
    LocationService,
    Location,
    get_location_service,
    reset_location_service
)

__all__ = [
    # User Profile Service
    'UserProfileService',
    'UserProfile',
    'get_user_profile_service',
    'reset_user_profile_service',

    # Health Records Service
    'HealthRecordsService',
    'HealthRecord',
    'get_health_records_service',
    'reset_health_records_service',

    # Chronic Disease Service
    'ChronicDiseaseService',
    'ChronicRecord',
    'TrendAnalysis',
    'get_chronic_disease_service',
    'reset_chronic_disease_service',

    # Preference Service
    'PreferenceService',
    'UserPreference',
    'get_preference_service',
    'reset_preference_service',

    # Behavior Log Service
    'BehaviorLogService',
    'BehaviorLog',
    'SessionLog',
    'ActionType',
    'get_behavior_log_service',
    'reset_behavior_log_service',

    # Reminder Service
    'ReminderDataService',
    'Reminder',
    'ReminderType',
    'get_reminder_service',
    'reset_reminder_service',

    # Payment Service
    'PaymentService',
    'Order',
    'Coupon',
    'get_payment_service',
    'reset_payment_service',

    # Location Service
    'LocationService',
    'Location',
    'get_location_service',
    'reset_location_service',
]
