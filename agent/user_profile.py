# -*- coding: utf-8 -*-
"""
医疗智能助手 - 用户画像
存储和管理用户医疗相关信息
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class Gender(Enum):
    """性别"""
    UNKNOWN = "unknown"
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


@dataclass
class UserProfile:
    """
    用户画像
    存储用户的医疗相关信息
    """
    user_id: str                           # 用户ID
    created_at: str                        # 创建时间
    updated_at: str = ""                   # 更新时间

    # 基本信息
    basic_info: Dict[str, Any] = field(default_factory=dict)
    # 可能包含: age, gender, location, language等

    # 医疗信息
    medical_history: List[str] = field(default_factory=list)      # 既往病史
    allergies: List[str] = field(default_factory=list)            # 过敏史
    current_medications: Dict[str, Any] = field(default_factory=dict)  # 当前用药
    # 格式: {"drug_name": {"dose": ..., "frequency": ..., "started": ...}}

    chronic_conditions: List[str] = field(default_factory=list)   # 慢性病

    # 偏好设置
    preferences: Dict[str, Any] = field(default_factory=dict)
    # 可能包含: language, notification_settings, privacy_settings等

    # 统计信息
    stats: Dict[str, Any] = field(default_factory=dict)
    # 可能包含: total_sessions, total_turns, last_visit等

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def get_age(self) -> Optional[int]:
        """获取年龄"""
        if not self.basic_info:
            return None
        return self.basic_info.get('age')

    def set_age(self, age: int):
        """设置年龄"""
        self.basic_info['age'] = age
        self._touch()

    def get_gender(self) -> Gender:
        """获取性别"""
        gender_str = self.basic_info.get('gender', 'unknown')
        try:
            return Gender(gender_str)
        except ValueError:
            return Gender.UNKNOWN

    def set_gender(self, gender: Gender):
        """设置性别"""
        self.basic_info['gender'] = gender.value if isinstance(gender, Gender) else gender
        self._touch()

    def add_medical_history(self, condition: str):
        """添加病史"""
        if condition and condition not in self.medical_history:
            self.medical_history.append(condition)
            self._touch()

    def add_allergy(self, allergen: str):
        """添加过敏"""
        if allergen and allergen not in self.allergies:
            self.allergies.append(allergen)
            self._touch()

    def remove_allergy(self, allergen: str) -> bool:
        """移除过敏"""
        if allergen in self.allergies:
            self.allergies.remove(allergen)
            self._touch()
            return True
        return False

    def add_medication(self, drug_name: str, dosage: str = None, frequency: str = None):
        """添加当前用药"""
        med_info = {}
        if dosage:
            med_info['dosage'] = dosage
        if frequency:
            med_info['frequency'] = frequency
        med_info['started'] = datetime.now().isoformat()

        self.current_medications[drug_name] = med_info
        self._touch()

    def remove_medication(self, drug_name: str) -> bool:
        """移除当前用药"""
        if drug_name in self.current_medications:
            del self.current_medications[drug_name]
            self._touch()
            return True
        return False

    def add_chronic_condition(self, condition: str):
        """添加慢性病"""
        if condition and condition not in self.chronic_conditions:
            self.chronic_conditions.append(condition)
            self._touch()

    def has_allergy(self, allergen: str) -> bool:
        """检查是否有过敏"""
        return allergen in self.allergies

    def has_condition(self, condition: str) -> bool:
        """检查是否有某种疾病/病史"""
        return condition in self.medical_history or condition in self.chronic_conditions

    def is_taking_medication(self, drug_name: str) -> bool:
        """检查是否正在使用某种药物"""
        return drug_name in self.current_medications

    def get_medication_dose(self, drug_name: str) -> Optional[str]:
        """获取药物剂量"""
        med_info = self.current_medications.get(drug_name)
        if med_info:
            return med_info.get('dosage')
        return None

    def set_preference(self, key: str, value: Any):
        """设置偏好"""
        self.preferences[key] = value
        self._touch()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """获取偏好"""
        return self.preferences.get(key, default)

    def update_stats(self, key: str, value: Any):
        """更新统计信息"""
        self.stats[key] = value
        self._touch()

    def increment_session_count(self):
        """增加会话计数"""
        self.stats['total_sessions'] = self.stats.get('total_sessions', 0) + 1
        self.stats['last_visit'] = datetime.now().isoformat()
        self._touch()

    def increment_turn_count(self):
        """增加对话轮次计数"""
        self.stats['total_turns'] = self.stats.get('total_turns', 0) + 1
        self._touch()

    def _touch(self):
        """更新时间戳"""
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """从字典创建"""
        return cls(**data)

    def get_risk_factors(self) -> List[str]:
        """获取风险因素列表"""
        risk_factors = []
        risk_factors.extend(self.chronic_conditions)
        risk_factors.extend(self.allergies)
        # 正在使用的药物也可能有风险
        risk_factors.extend(self.current_medications.keys())
        return risk_factors

    def get_summary(self) -> str:
        """获取用户画像摘要"""
        parts = []

        if self.get_age():
            parts.append(f"{self.get_age()}岁")

        gender = self.get_gender()
        if gender != Gender.UNKNOWN:
            gender_cn = {"male": "男", "female": "女"}.get(gender.value, "")
            if gender_cn:
                parts.append(gender_cn)

        if self.chronic_conditions:
            parts.append(f"有{len(self.chronic_conditions)}种慢性病")

        if self.allergies:
            parts.append(f"有{len(self.allergies)}种过敏")

        if self.current_medications:
            parts.append(f"正在使用{len(self.current_medications)}种药物")

        return "、".join(parts) if parts else "用户"

    def anonymize(self) -> Dict[str, Any]:
        """返回匿名化的数据（用于分析）"""
        return {
            'age_range': self._get_age_range(),
            'gender': self.get_gender().value,
            'chronic_conditions_count': len(self.chronic_conditions),
            'allergies_count': len(self.allergies),
            'medications_count': len(self.current_medications),
            'sessions_count': self.stats.get('total_sessions', 0),
            'turns_count': self.stats.get('total_turns', 0),
        }

    def _get_age_range(self) -> str:
        """获取年龄范围"""
        age = self.get_age()
        if age is None:
            return "unknown"

        if age < 18:
            return "0-17"
        elif age < 30:
            return "18-29"
        elif age < 50:
            return "30-49"
        elif age < 65:
            return "50-64"
        else:
            return "65+"


@dataclass
class ProfileUpdate:
    """用户画像更新"""
    user_id: str
    update_type: str           # medical_history, allergy, medication, preference, etc.
    action: str                # add, remove, update
    data: Any
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "user"       # user, system, inference


class UserProfileBuilder:
    """用户画像构建器"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.basic_info = {}
        self.medical_history = []
        self.allergies = []
        self.current_medications = {}
        self.chronic_conditions = []
        self.preferences = {}
        self.stats = {}
        self.metadata = {}

    def with_age(self, age: int) -> 'UserProfileBuilder':
        """设置年龄"""
        self.basic_info['age'] = age
        return self

    def with_gender(self, gender: str) -> 'UserProfileBuilder':
        """设置性别"""
        self.basic_info['gender'] = gender
        return self

    def with_location(self, location: str) -> 'UserProfileBuilder':
        """设置位置"""
        self.basic_info['location'] = location
        return self

    def add_medical_history(self, condition: str) -> 'UserProfileBuilder':
        """添加病史"""
        if condition not in self.medical_history:
            self.medical_history.append(condition)
        return self

    def add_allergy(self, allergen: str) -> 'UserProfileBuilder':
        """添加过敏"""
        if allergen not in self.allergies:
            self.allergies.append(allergen)
        return self

    def add_medication(self, drug_name: str, dosage: str = None) -> 'UserProfileBuilder':
        """添加用药"""
        med_info = {'started': datetime.now().isoformat()}
        if dosage:
            med_info['dosage'] = dosage
        self.current_medications[drug_name] = med_info
        return self

    def add_chronic_condition(self, condition: str) -> 'UserProfileBuilder':
        """添加慢性病"""
        if condition not in self.chronic_conditions:
            self.chronic_conditions.append(condition)
        return self

    def with_preference(self, key: str, value: Any) -> 'UserProfileBuilder':
        """设置偏好"""
        self.preferences[key] = value
        return self

    def with_metadata(self, key: str, value: Any) -> 'UserProfileBuilder':
        """设置元数据"""
        self.metadata[key] = value
        return self

    def build(self) -> UserProfile:
        """构建用户画像"""
        return UserProfile(
            user_id=self.user_id,
            created_at=datetime.now().isoformat(),
            basic_info=self.basic_info,
            medical_history=self.medical_history,
            allergies=self.allergies,
            current_medications=self.current_medications,
            chronic_conditions=self.chronic_conditions,
            preferences=self.preferences,
            stats=self.stats,
            metadata=self.metadata
        )


# 工厂函数
def create_profile(user_id: str, **kwargs) -> UserProfile:
    """创建用户画像"""
    return UserProfile(
        user_id=user_id,
        created_at=datetime.now().isoformat(),
        **kwargs
)


def create_default_profile(user_id: str) -> UserProfile:
    """创建默认用户画像"""
    return UserProfile(
        user_id=user_id,
        created_at=datetime.now().isoformat(),
        basic_info={},
        medical_history=[],
        allergies=[],
        current_medications={},
        chronic_conditions=[],
        preferences={
            'language': 'zh-CN',
            'timezone': 'Asia/Shanghai',
        },
        stats={
            'total_sessions': 0,
            'total_turns': 0,
        }
    )


if __name__ == "__main__":
    # 测试用户画像
    print("用户画像测试")
    print("=" * 60)

    # 使用构建器创建画像
    profile = (UserProfileBuilder("user_123")
               .with_age(35)
               .with_gender("male")
               .add_medical_history("高血压")
               .add_allergy("青霉素")
               .add_medication("硝苯地平", "10mg 每日2次")
               .add_chronic_condition("高血压")
               .build())

    print("\n用户画像:")
    print(f"  用户ID: {profile.user_id}")
    print(f"  年龄: {profile.get_age()}")
    print(f"  性别: {profile.get_gender().value}")
    print(f"  慢性病: {profile.chronic_conditions}")
    print(f"  过敏: {profile.allergies}")
    print(f"  当前用药: {list(profile.current_medications.keys())}")

    print(f"\n摘要: {profile.get_summary()}")

    print(f"\n风险因素: {profile.get_risk_factors()}")

    print("\n匿名化数据:")
    import json
    print(json.dumps(profile.anonymize(), indent=2, ensure_ascii=False))
