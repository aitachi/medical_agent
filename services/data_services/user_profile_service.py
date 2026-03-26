# -*- coding: utf-8 -*-
"""
医疗智能助手 - 用户画像数据服务
提供用户基础画像数据，支撑个性化服务
"""

import json
import sqlite3
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False


@dataclass
class BasicInfo:
    """用户基础信息"""
    age: Optional[int] = None
    gender: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


@dataclass
class UserPreferences:
    """用户偏好设置"""
    frequent_hospitals: List[str] = field(default_factory=list)
    preferred_doctors: List[str] = field(default_factory=list)
    frequent_departments: List[str] = field(default_factory=list)
    preferred_time_slots: List[str] = field(default_factory=list)
    notification_enabled: bool = True
    language: str = "zh-CN"


@dataclass
class BehaviorStats:
    """用户行为统计"""
    total_consults: int = 0
    total_appointments: int = 0
    total_chronic_records: int = 0
    last_active_time: Optional[str] = None
    avg_session_duration: float = 0.0


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    basic_info: Dict[str, Any] = field(default_factory=dict)
    health_tags: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    behavior_stats: Dict[str, Any] = field(default_factory=dict)
    risk_level: str = "low"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "basic_info": self.basic_info,
            "health_tags": self.health_tags,
            "preferences": self.preferences,
            "behavior_stats": self.behavior_stats,
            "risk_level": self.risk_level,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """从字典创建"""
        return cls(**data)


class UserProfileService:
    """
    用户画像数据服务
    提供用户基础画像数据，支撑个性化服务
    """

    def __init__(self, db_path: str = "data/user_profiles.db"):
        """
        初始化用户画像服务

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._initialized = False
        self._cache: Dict[str, UserProfile] = {}

        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_schema_statements(self) -> List[str]:
        """获取数据库表结构SQL语句"""
        return [
            """CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                basic_info TEXT NOT NULL DEFAULT '{}',
                health_tags TEXT NOT NULL DEFAULT '[]',
                preferences TEXT NOT NULL DEFAULT '{}',
                behavior_stats TEXT NOT NULL DEFAULT '{}',
                risk_level TEXT NOT NULL DEFAULT 'low',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            """CREATE INDEX IF NOT EXISTS idx_user_profiles_risk_level
                ON user_profiles (risk_level)""",
            """CREATE INDEX IF NOT EXISTS idx_user_profiles_region
                ON user_profiles (user_id)""",
        ]

    async def initialize(self) -> None:
        """初始化数据库"""
        if self._initialized:
            return

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                for stmt in self._get_schema_statements():
                    await db.execute(stmt)
                await db.commit()
        else:
            self._initialize_sync()

        self._initialized = True

    def _initialize_sync(self) -> None:
        """同步初始化数据库"""
        with sqlite3.connect(self.db_path) as db:
            for stmt in self._get_schema_statements():
                db.execute(stmt)
            db.commit()
        self._initialized = True

    # ========== CRUD 操作 ==========

    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户画像

        Args:
            user_id: 用户ID

        Returns:
            Dict: 用户画像数据，如果不存在返回None
        """
        await self.initialize()

        # 先检查缓存
        if user_id in self._cache:
            return self._cache[user_id].to_dict()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM user_profiles WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT * FROM user_profiles WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()

        if not row:
            return None

        profile = {
            "user_id": row[0],
            "basic_info": json.loads(row[1]) if row[1] else {},
            "health_tags": json.loads(row[2]) if row[2] else [],
            "preferences": json.loads(row[3]) if row[3] else {},
            "behavior_stats": json.loads(row[4]) if row[4] else {},
            "risk_level": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }

        # 更新缓存
        self._cache[user_id] = UserProfile.from_dict(profile)

        return profile

    async def create_profile(
        self,
        user_id: str,
        basic_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建用户画像

        Args:
            user_id: 用户ID
            basic_info: 基础信息

        Returns:
            Dict: 创建的用户画像
        """
        await self.initialize()

        now = datetime.now().isoformat()
        profile = UserProfile(
            user_id=user_id,
            basic_info=basic_info or {},
            created_at=now,
            updated_at=now
        )

        await self._save_profile(profile)
        self._cache[user_id] = profile

        return profile.to_dict()

    async def update_profile(
        self,
        user_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        更新用户画像

        Args:
            user_id: 用户ID
            data: 更新数据

        Returns:
            bool: 是否更新成功
        """
        await self.initialize()

        profile = await self.get_profile(user_id)
        if not profile:
            return False

        # 更新字段
        if "basic_info" in data:
            profile["basic_info"].update(data["basic_info"])
        if "health_tags" in data:
            if isinstance(data["health_tags"], list):
                profile["health_tags"] = data["health_tags"]
        if "preferences" in data:
            profile["preferences"].update(data["preferences"])
        if "behavior_stats" in data:
            profile["behavior_stats"].update(data["behavior_stats"])
        if "risk_level" in data:
            profile["risk_level"] = data["risk_level"]

        profile["updated_at"] = datetime.now().isoformat()

        await self._save_profile(UserProfile.from_dict(profile))

        # 更新缓存
        if user_id in self._cache:
            self._cache[user_id] = UserProfile.from_dict(profile)

        return True

    async def delete_profile(self, user_id: str) -> bool:
        """
        删除用户画像

        Args:
            user_id: 用户ID

        Returns:
            bool: 是否删除成功
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM user_profiles WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()
                deleted = cursor.rowcount > 0
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "DELETE FROM user_profiles WHERE user_id = ?",
                    (user_id,)
                )
                db.commit()
                deleted = cursor.rowcount > 0

        if deleted and user_id in self._cache:
            del self._cache[user_id]

        return deleted

    async def _save_profile(self, profile: UserProfile) -> None:
        """保存用户画像到数据库"""
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO user_profiles
                    (user_id, basic_info, health_tags, preferences,
                     behavior_stats, risk_level, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    profile.user_id,
                    json.dumps(profile.basic_info, ensure_ascii=False),
                    json.dumps(profile.health_tags, ensure_ascii=False),
                    json.dumps(profile.preferences, ensure_ascii=False),
                    json.dumps(profile.behavior_stats, ensure_ascii=False),
                    profile.risk_level,
                    profile.created_at,
                    profile.updated_at
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT OR REPLACE INTO user_profiles
                    (user_id, basic_info, health_tags, preferences,
                     behavior_stats, risk_level, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    profile.user_id,
                    json.dumps(profile.basic_info, ensure_ascii=False),
                    json.dumps(profile.health_tags, ensure_ascii=False),
                    json.dumps(profile.preferences, ensure_ascii=False),
                    json.dumps(profile.behavior_stats, ensure_ascii=False),
                    profile.risk_level,
                    profile.created_at,
                    profile.updated_at
                ))
                db.commit()

    # ========== 健康标签操作 ==========

    async def get_tags(self, user_id: str) -> List[str]:
        """
        获取用户健康标签

        Args:
            user_id: 用户ID

        Returns:
            List[str]: 健康标签列表
        """
        profile = await self.get_profile(user_id)
        return profile["health_tags"] if profile else []

    async def add_tag(self, user_id: str, tag: str) -> bool:
        """
        添加健康标签

        Args:
            user_id: 用户ID
            tag: 标签

        Returns:
            bool: 是否添加成功
        """
        profile = await self.get_profile(user_id)
        if not profile:
            return False

        if tag not in profile["health_tags"]:
            profile["health_tags"].append(tag)
            profile["updated_at"] = datetime.now().isoformat()
            await self._save_profile(UserProfile.from_dict(profile))

            if user_id in self._cache:
                self._cache[user_id] = UserProfile.from_dict(profile)

        return True

    async def remove_tag(self, user_id: str, tag: str) -> bool:
        """
        移除健康标签

        Args:
            user_id: 用户ID
            tag: 标签

        Returns:
            bool: 是否移除成功
        """
        profile = await self.get_profile(user_id)
        if not profile:
            return False

        if tag in profile["health_tags"]:
            profile["health_tags"].remove(tag)
            profile["updated_at"] = datetime.now().isoformat()
            await self._save_profile(UserProfile.from_dict(profile))

            if user_id in self._cache:
                self._cache[user_id] = UserProfile.from_dict(profile)

        return True

    async def update_tags(self, user_id: str, tags: List[str]) -> bool:
        """
        批量更新健康标签

        Args:
            user_id: 用户ID
            tags: 标签列表

        Returns:
            bool: 是否更新成功
        """
        profile = await self.get_profile(user_id)
        if not profile:
            return False

        profile["health_tags"] = list(set(tags))
        profile["updated_at"] = datetime.now().isoformat()
        await self._save_profile(UserProfile.from_dict(profile))

        if user_id in self._cache:
            self._cache[user_id] = UserProfile.from_dict(profile)

        return True

    # ========== 偏好设置操作 ==========

    async def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户偏好

        Args:
            user_id: 用户ID

        Returns:
            Dict: 用户偏好
        """
        profile = await self.get_profile(user_id)
        return profile["preferences"] if profile else {}

    async def update_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> bool:
        """
        更新用户偏好

        Args:
            user_id: 用户ID
            preferences: 偏好数据

        Returns:
            bool: 是否更新成功
        """
        profile = await self.get_profile(user_id)
        if not profile:
            return False

        profile["preferences"].update(preferences)
        profile["updated_at"] = datetime.now().isoformat()
        await self._save_profile(UserProfile.from_dict(profile))

        if user_id in self._cache:
            self._cache[user_id] = UserProfile.from_dict(profile)

        return True

    async def add_frequent_hospital(self, user_id: str, hospital: str) -> bool:
        """
        添加常去医院

        Args:
            user_id: 用户ID
            hospital: 医院名称

        Returns:
            bool: 是否添加成功
        """
        profile = await self.get_profile(user_id)
        if not profile:
            return False

        frequent_hospitals = profile["preferences"].get("frequent_hospitals", [])
        if hospital not in frequent_hospitals:
            frequent_hospitals.append(hospital)
            # 最多保留10个
            if len(frequent_hospitals) > 10:
                frequent_hospitals = frequent_hospitals[-10:]
            profile["preferences"]["frequent_hospitals"] = frequent_hospitals
            profile["updated_at"] = datetime.now().isoformat()
            await self._save_profile(UserProfile.from_dict(profile))

            if user_id in self._cache:
                self._cache[user_id] = UserProfile.from_dict(profile)

        return True

    async def add_preferred_doctor(self, user_id: str, doctor: str) -> bool:
        """
        添加偏好医生

        Args:
            user_id: 用户ID
            doctor: 医生名称

        Returns:
            bool: 是否添加成功
        """
        profile = await self.get_profile(user_id)
        if not profile:
            return False

        preferred_doctors = profile["preferences"].get("preferred_doctors", [])
        if doctor not in preferred_doctors:
            preferred_doctors.append(doctor)
            # 最多保留10个
            if len(preferred_doctors) > 10:
                preferred_doctors = preferred_doctors[-10:]
            profile["preferences"]["preferred_doctors"] = preferred_doctors
            profile["updated_at"] = datetime.now().isoformat()
            await self._save_profile(UserProfile.from_dict(profile))

            if user_id in self._cache:
                self._cache[user_id] = UserProfile.from_dict(profile)

        return True

    # ========== 行为统计操作 ==========

    async def increment_behavior_count(
        self,
        user_id: str,
        field: str,
        count: int = 1
    ) -> bool:
        """
        增加行为统计计数

        Args:
            user_id: 用户ID
            field: 统计字段 (total_consults, total_appointments等)
            count: 增加数量

        Returns:
            bool: 是否更新成功
        """
        profile = await self.get_profile(user_id)
        if not profile:
            return False

        current = profile["behavior_stats"].get(field, 0)
        profile["behavior_stats"][field] = current + count
        profile["behavior_stats"]["last_active_time"] = datetime.now().isoformat()
        profile["updated_at"] = datetime.now().isoformat()
        await self._save_profile(UserProfile.from_dict(profile))

        if user_id in self._cache:
            self._cache[user_id] = UserProfile.from_dict(profile)

        return True

    async def get_behavior_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取行为统计

        Args:
            user_id: 用户ID

        Returns:
            Dict: 行为统计数据
        """
        profile = await self.get_profile(user_id)
        return profile["behavior_stats"] if profile else {}

    # ========== 风险等级操作 ==========

    async def get_risk_level(self, user_id: str) -> str:
        """
        获取用户风险等级

        Args:
            user_id: 用户ID

        Returns:
            str: 风险等级 (low/medium/high)
        """
        profile = await self.get_profile(user_id)
        return profile["risk_level"] if profile else "low"

    async def set_risk_level(self, user_id: str, risk_level: str) -> bool:
        """
        设置用户风险等级

        Args:
            user_id: 用户ID
            risk_level: 风险等级 (low/medium/high)

        Returns:
            bool: 是否设置成功
        """
        if risk_level not in ("low", "medium", "high"):
            return False

        profile = await self.get_profile(user_id)
        if not profile:
            return False

        profile["risk_level"] = risk_level
        profile["updated_at"] = datetime.now().isoformat()
        await self._save_profile(UserProfile.from_dict(profile))

        if user_id in self._cache:
            self._cache[user_id] = UserProfile.from_dict(profile)

        return True

    async def evaluate_risk_level(self, user_id: str) -> str:
        """
        评估用户风险等级

        Args:
            user_id: 用户ID

        Returns:
            str: 评估的风险等级
        """
        profile = await self.get_profile(user_id)
        if not profile:
            return "low"

        health_tags = profile.get("health_tags", [])
        basic_info = profile.get("basic_info", {})

        # 根据年龄和健康标签评估风险
        age = basic_info.get("age", 0)
        high_risk_tags = ["高血压", "糖尿病", "冠心病", "脑卒中", "癌症"]
        medium_risk_tags = ["高血脂", "肥胖", "脂肪肝", "痛风"]

        has_high_risk = any(tag in health_tags for tag in high_risk_tags)
        has_medium_risk = any(tag in health_tags for tag in medium_risk_tags)

        if has_high_risk or age >= 65:
            risk_level = "high"
        elif has_medium_risk or age >= 50:
            risk_level = "medium"
        else:
            risk_level = "low"

        await self.set_risk_level(user_id, risk_level)
        return risk_level

    # ========== 查询操作 ==========

    async def get_profiles_by_risk_level(
        self,
        risk_level: str
    ) -> List[Dict[str, Any]]:
        """
        按风险等级查询用户

        Args:
            risk_level: 风险等级

        Returns:
            List[Dict]: 用户画像列表
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM user_profiles WHERE risk_level = ?",
                    (risk_level,)
                )
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT * FROM user_profiles WHERE risk_level = ?",
                    (risk_level,)
                )
                rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                "user_id": row[0],
                "basic_info": json.loads(row[1]) if row[1] else {},
                "health_tags": json.loads(row[2]) if row[2] else [],
                "preferences": json.loads(row[3]) if row[3] else {},
                "behavior_stats": json.loads(row[4]) if row[4] else {},
                "risk_level": row[5],
                "created_at": row[6],
                "updated_at": row[7],
            })

        return results

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取服务统计信息

        Returns:
            Dict: 统计信息
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM user_profiles")
                total_users = (await cursor.fetchone())[0]

                cursor = await db.execute("""
                    SELECT risk_level, COUNT(*) as count
                    FROM user_profiles
                    GROUP BY risk_level
                """)
                risk_dist_rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("SELECT COUNT(*) FROM user_profiles")
                total_users = cursor.fetchone()[0]

                cursor = db.execute("""
                    SELECT risk_level, COUNT(*) as count
                    FROM user_profiles
                    GROUP BY risk_level
                """)
                risk_dist_rows = cursor.fetchall()

        risk_distribution = {row[0]: row[1] for row in risk_dist_rows}

        return {
            "total_users": total_users,
            "risk_distribution": risk_distribution,
            "cache_size": len(self._cache),
        }


# ============================================================
# 全局服务实例
# ============================================================

_global_user_profile_service: Optional[UserProfileService] = None


def get_user_profile_service(
    db_path: str = "data/user_profiles.db"
) -> UserProfileService:
    """获取全局用户画像服务"""
    global _global_user_profile_service
    if _global_user_profile_service is None:
        _global_user_profile_service = UserProfileService(db_path)
    return _global_user_profile_service


def reset_user_profile_service():
    """重置全局用户画像服务"""
    global _global_user_profile_service
    _global_user_profile_service = None
