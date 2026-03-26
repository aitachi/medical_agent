# -*- coding: utf-8 -*-
"""
医疗智能助手 - 偏好数据服务
提供用户偏好数据，辅助推荐系统
"""

import json
import sqlite3
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from collections import Counter

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False


@dataclass
class UserPreference:
    """用户偏好数据"""
    user_id: str
    frequent_hospitals: List[str] = field(default_factory=list)
    preferred_doctors: List[str] = field(default_factory=list)
    frequent_departments: List[str] = field(default_factory=list)
    preferred_time_slots: List[str] = field(default_factory=list)
    consultation_type: str = "text"  # text, video, phone
    language: str = "zh-CN"
    notification_enabled: bool = True
    notification_time: Optional[str] = None
    reminder_enabled: bool = True
    auto_renew_prescription: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "frequent_hospitals": self.frequent_hospitals,
            "preferred_doctors": self.preferred_doctors,
            "frequent_departments": self.frequent_departments,
            "preferred_time_slots": self.preferred_time_slots,
            "consultation_type": self.consultation_type,
            "language": self.language,
            "notification_enabled": self.notification_enabled,
            "notification_time": self.notification_time,
            "reminder_enabled": self.reminder_enabled,
            "auto_renew_prescription": self.auto_renew_prescription,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPreference":
        """从字典创建"""
        return cls(**data)


@dataclass
class HospitalPreference:
    """医院偏好记录"""
    user_id: str
    hospital_name: str
    visit_count: int = 0
    last_visit: Optional[str] = None
    rating: Optional[float] = None
    departments_visited: List[str] = field(default_factory=list)


@dataclass
class DoctorPreference:
    """医生偏好记录"""
    user_id: str
    doctor_id: str
    doctor_name: str
    department: str
    hospital: Optional[str] = None
    consult_count: int = 0
    last_consult: Optional[str] = None
    rating: Optional[float] = None
    is_favorite: bool = False


class PreferenceService:
    """
    偏好数据服务
    提供用户偏好数据，辅助推荐系统
    """

    def __init__(self, db_path: str = "data/preferences.db"):
        """
        初始化偏好服务

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._initialized = False
        self._cache: Dict[str, UserPreference] = {}

        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_schema_statements(self) -> List[str]:
        """获取数据库表结构SQL语句"""
        return [
            """CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                frequent_hospitals TEXT NOT NULL DEFAULT '[]',
                preferred_doctors TEXT NOT NULL DEFAULT '[]',
                frequent_departments TEXT NOT NULL DEFAULT '[]',
                preferred_time_slots TEXT NOT NULL DEFAULT '[]',
                consultation_type TEXT NOT NULL DEFAULT 'text',
                language TEXT NOT NULL DEFAULT 'zh-CN',
                notification_enabled INTEGER NOT NULL DEFAULT 1,
                notification_time TEXT,
                reminder_enabled INTEGER NOT NULL DEFAULT 1,
                auto_renew_prescription INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS hospital_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                hospital_name TEXT NOT NULL,
                visit_count INTEGER NOT NULL DEFAULT 0,
                last_visit TEXT,
                rating REAL,
                departments_visited TEXT NOT NULL DEFAULT '[]',
                UNIQUE(user_id, hospital_name)
            )""",
            """CREATE TABLE IF NOT EXISTS doctor_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                doctor_id TEXT NOT NULL,
                doctor_name TEXT NOT NULL,
                department TEXT NOT NULL,
                hospital TEXT,
                consult_count INTEGER NOT NULL DEFAULT 0,
                last_consult TEXT,
                rating REAL,
                is_favorite INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, doctor_id)
            )""",
            """CREATE INDEX IF NOT EXISTS idx_hospital_prefs_user_id
                ON hospital_preferences (user_id)""",
            """CREATE INDEX IF NOT EXISTS idx_doctor_prefs_user_id
                ON doctor_preferences (user_id)""",
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

    async def _save_preference(self, pref: UserPreference) -> None:
        """保存偏好到数据库"""
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO user_preferences
                    (user_id, frequent_hospitals, preferred_doctors,
                     frequent_departments, preferred_time_slots,
                     consultation_type, language, notification_enabled,
                     notification_time, reminder_enabled, auto_renew_prescription,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pref.user_id,
                    json.dumps(pref.frequent_hospitals, ensure_ascii=False),
                    json.dumps(pref.preferred_doctors, ensure_ascii=False),
                    json.dumps(pref.frequent_departments, ensure_ascii=False),
                    json.dumps(pref.preferred_time_slots, ensure_ascii=False),
                    pref.consultation_type,
                    pref.language,
                    1 if pref.notification_enabled else 0,
                    pref.notification_time,
                    1 if pref.reminder_enabled else 0,
                    1 if pref.auto_renew_prescription else 0,
                    pref.created_at,
                    pref.updated_at
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT OR REPLACE INTO user_preferences
                    (user_id, frequent_hospitals, preferred_doctors,
                     frequent_departments, preferred_time_slots,
                     consultation_type, language, notification_enabled,
                     notification_time, reminder_enabled, auto_renew_prescription,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pref.user_id,
                    json.dumps(pref.frequent_hospitals, ensure_ascii=False),
                    json.dumps(pref.preferred_doctors, ensure_ascii=False),
                    json.dumps(pref.frequent_departments, ensure_ascii=False),
                    json.dumps(pref.preferred_time_slots, ensure_ascii=False),
                    pref.consultation_type,
                    pref.language,
                    1 if pref.notification_enabled else 0,
                    pref.notification_time,
                    1 if pref.reminder_enabled else 0,
                    1 if pref.auto_renew_prescription else 0,
                    pref.created_at,
                    pref.updated_at
                ))
                db.commit()

    def _load_preference_from_row(self, row: tuple) -> UserPreference:
        """从数据库行加载偏好"""
        return UserPreference(
            user_id=row[0],
            frequent_hospitals=json.loads(row[1]) if row[1] else [],
            preferred_doctors=json.loads(row[2]) if row[2] else [],
            frequent_departments=json.loads(row[3]) if row[3] else [],
            preferred_time_slots=json.loads(row[4]) if row[4] else [],
            consultation_type=row[5],
            language=row[6],
            notification_enabled=bool(row[7]),
            notification_time=row[8],
            reminder_enabled=bool(row[9]),
            auto_renew_prescription=bool(row[10]),
            created_at=row[11],
            updated_at=row[12]
        )

    # ========== CRUD 操作 ==========

    async def get_preference(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户偏好

        Args:
            user_id: 用户ID

        Returns:
            Dict: 用户偏好数据，如果不存在返回None
        """
        await self.initialize()

        # 先检查缓存
        if user_id in self._cache:
            return self._cache[user_id].to_dict()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM user_preferences WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT * FROM user_preferences WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()

        if not row:
            return None

        pref = self._load_preference_from_row(row)
        self._cache[user_id] = pref

        return pref.to_dict()

    async def get_or_create_preference(self, user_id: str) -> Dict[str, Any]:
        """
        获取或创建用户偏好

        Args:
            user_id: 用户ID

        Returns:
            Dict: 用户偏好数据
        """
        pref = await self.get_preference(user_id)
        if not pref:
            pref = await self.create_preference(user_id)
        return pref

    async def create_preference(self, user_id: str) -> Dict[str, Any]:
        """
        创建用户偏好

        Args:
            user_id: 用户ID

        Returns:
            Dict: 创建的用户偏好
        """
        await self.initialize()

        now = datetime.now().isoformat()
        pref = UserPreference(user_id=user_id, created_at=now, updated_at=now)

        await self._save_preference(pref)
        self._cache[user_id] = pref

        return pref.to_dict()

    async def update_preference(
        self,
        user_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        更新用户偏好

        Args:
            user_id: 用户ID
            data: 更新数据

        Returns:
            bool: 是否更新成功
        """
        pref = await self.get_preference(user_id)
        if not pref:
            return False

        # 更新允许的字段
        updatable_fields = [
            "consultation_type", "language", "notification_enabled",
            "notification_time", "reminder_enabled", "auto_renew_prescription"
        ]

        for field in updatable_fields:
            if field in data:
                pref[field] = data[field]

        # 更新列表字段
        if "frequent_hospitals" in data:
            pref["frequent_hospitals"] = list(set(data["frequent_hospitals"]))
        if "preferred_doctors" in data:
            pref["preferred_doctors"] = list(set(data["preferred_doctors"]))
        if "frequent_departments" in data:
            pref["frequent_departments"] = list(set(data["frequent_departments"]))
        if "preferred_time_slots" in data:
            pref["preferred_time_slots"] = list(set(data["preferred_time_slots"]))

        pref["updated_at"] = datetime.now().isoformat()

        await self._save_preference(UserPreference.from_dict(pref))

        # 更新缓存
        if user_id in self._cache:
            self._cache[user_id] = UserPreference.from_dict(pref)

        return True

    # ========== 医院偏好操作 ==========

    async def add_frequent_hospital(
        self,
        user_id: str,
        hospital_name: str,
        department: Optional[str] = None
    ) -> bool:
        """
        添加常去医院

        Args:
            user_id: 用户ID
            hospital_name: 医院名称
            department: 科室（可选）

        Returns:
            bool: 是否添加成功
        """
        await self.initialize()

        now = datetime.now().isoformat()

        # 更新医院偏好表
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                # 先查询是否存在
                cursor = await db.execute(
                    "SELECT visit_count, departments_visited FROM hospital_preferences WHERE user_id = ? AND hospital_name = ?",
                    (user_id, hospital_name)
                )
                row = await cursor.fetchone()

                if row:
                    # 更新
                    visit_count = row[0] + 1
                    departments = json.loads(row[1]) if row[1] else []
                    if department and department not in departments:
                        departments.append(department)

                    await db.execute("""
                        UPDATE hospital_preferences
                        SET visit_count = ?, last_visit = ?, departments_visited = ?
                        WHERE user_id = ? AND hospital_name = ?
                    """, (visit_count, now, json.dumps(departments, ensure_ascii=False), user_id, hospital_name))
                else:
                    # 插入
                    await db.execute("""
                        INSERT INTO hospital_preferences
                        (user_id, hospital_name, visit_count, last_visit, departments_visited)
                        VALUES (?, ?, 1, ?, ?)
                    """, (user_id, hospital_name, now, json.dumps([department] if department else [], ensure_ascii=False)))

                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT visit_count, departments_visited FROM hospital_preferences WHERE user_id = ? AND hospital_name = ?",
                    (user_id, hospital_name)
                )
                row = cursor.fetchone()

                if row:
                    visit_count = row[0] + 1
                    departments = json.loads(row[1]) if row[1] else []
                    if department and department not in departments:
                        departments.append(department)

                    db.execute("""
                        UPDATE hospital_preferences
                        SET visit_count = ?, last_visit = ?, departments_visited = ?
                        WHERE user_id = ? AND hospital_name = ?
                    """, (visit_count, now, json.dumps(departments, ensure_ascii=False), user_id, hospital_name))
                else:
                    db.execute("""
                        INSERT INTO hospital_preferences
                        (user_id, hospital_name, visit_count, last_visit, departments_visited)
                        VALUES (?, ?, 1, ?, ?)
                    """, (user_id, hospital_name, now, json.dumps([department] if department else [], ensure_ascii=False)))

                db.commit()

        # 更新用户偏好
        pref = await self.get_or_create_preference(user_id)
        if hospital_name not in pref["frequent_hospitals"]:
            pref["frequent_hospitals"].append(hospital_name)
            # 最多保留10个
            if len(pref["frequent_hospitals"]) > 10:
                pref["frequent_hospitals"] = pref["frequent_hospitals"][-10:]

            pref["updated_at"] = datetime.now().isoformat()
            await self._save_preference(UserPreference.from_dict(pref))
            self._cache[user_id] = UserPreference.from_dict(pref)

        return True

    async def get_hospital_preferences(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取医院偏好列表

        Args:
            user_id: 用户ID

        Returns:
            List[Dict]: 医院偏好列表
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """SELECT * FROM hospital_preferences
                       WHERE user_id = ?
                       ORDER BY visit_count DESC, last_visit DESC""",
                    (user_id,)
                )
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    """SELECT * FROM hospital_preferences
                       WHERE user_id = ?
                       ORDER BY visit_count DESC, last_visit DESC""",
                    (user_id,)
                )
                rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "hospital_name": row[2],
                "visit_count": row[3],
                "last_visit": row[4],
                "rating": row[5],
                "departments_visited": json.loads(row[6]) if row[6] else []
            }
            for row in rows
        ]

    async def rate_hospital(
        self,
        user_id: str,
        hospital_name: str,
        rating: float
    ) -> bool:
        """
        给医院评分

        Args:
            user_id: 用户ID
            hospital_name: 医院名称
            rating: 评分（1-5）

        Returns:
            bool: 是否评分成功
        """
        if not 1 <= rating <= 5:
            return False

        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE hospital_preferences
                    SET rating = ?
                    WHERE user_id = ? AND hospital_name = ?
                """, (rating, user_id, hospital_name))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    UPDATE hospital_preferences
                    SET rating = ?
                    WHERE user_id = ? AND hospital_name = ?
                """, (rating, user_id, hospital_name))
                db.commit()

        return True

    # ========== 医生偏好操作 ==========

    async def add_preferred_doctor(
        self,
        user_id: str,
        doctor_id: str,
        doctor_name: str,
        department: str,
        hospital: Optional[str] = None
    ) -> bool:
        """
        添加偏好医生

        Args:
            user_id: 用户ID
            doctor_id: 医生ID
            doctor_name: 医生姓名
            department: 科室
            hospital: 医院（可选）

        Returns:
            bool: 是否添加成功
        """
        await self.initialize()

        now = datetime.now().isoformat()

        # 更新医生偏好表
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT consult_count FROM doctor_preferences WHERE user_id = ? AND doctor_id = ?",
                    (user_id, doctor_id)
                )
                row = await cursor.fetchone()

                if row:
                    await db.execute("""
                        UPDATE doctor_preferences
                        SET consult_count = consult_count + 1, last_consult = ?
                        WHERE user_id = ? AND doctor_id = ?
                    """, (now, user_id, doctor_id))
                else:
                    await db.execute("""
                        INSERT INTO doctor_preferences
                        (user_id, doctor_id, doctor_name, department, hospital, consult_count, last_consult)
                        VALUES (?, ?, ?, ?, ?, 1, ?)
                    """, (user_id, doctor_id, doctor_name, department, hospital, now))

                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT consult_count FROM doctor_preferences WHERE user_id = ? AND doctor_id = ?",
                    (user_id, doctor_id)
                )
                row = cursor.fetchone()

                if row:
                    db.execute("""
                        UPDATE doctor_preferences
                        SET consult_count = consult_count + 1, last_consult = ?
                        WHERE user_id = ? AND doctor_id = ?
                    """, (now, user_id, doctor_id))
                else:
                    db.execute("""
                        INSERT INTO doctor_preferences
                        (user_id, doctor_id, doctor_name, department, hospital, consult_count, last_consult)
                        VALUES (?, ?, ?, ?, ?, 1, ?)
                    """, (user_id, doctor_id, doctor_name, department, hospital, now))

                db.commit()

        # 更新用户偏好
        pref = await self.get_or_create_preference(user_id)
        doctor_key = f"{doctor_id}:{doctor_name}"
        if doctor_key not in pref["preferred_doctors"]:
            pref["preferred_doctors"].append(doctor_key)
            # 最多保留10个
            if len(pref["preferred_doctors"]) > 10:
                pref["preferred_doctors"] = pref["preferred_doctors"][-10:]

            pref["updated_at"] = datetime.now().isoformat()
            await self._save_preference(UserPreference.from_dict(pref))
            self._cache[user_id] = UserPreference.from_dict(pref)

        return True

    async def get_doctor_preferences(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取医生偏好列表

        Args:
            user_id: 用户ID

        Returns:
            List[Dict]: 医生偏好列表
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """SELECT * FROM doctor_preferences
                       WHERE user_id = ?
                       ORDER BY is_favorite DESC, consult_count DESC, last_consult DESC""",
                    (user_id,)
                )
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    """SELECT * FROM doctor_preferences
                       WHERE user_id = ?
                       ORDER BY is_favorite DESC, consult_count DESC, last_consult DESC""",
                    (user_id,)
                )
                rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "doctor_id": row[2],
                "doctor_name": row[3],
                "department": row[4],
                "hospital": row[5],
                "consult_count": row[6],
                "last_consult": row[7],
                "rating": row[8],
                "is_favorite": bool(row[9])
            }
            for row in rows
        ]

    async def set_favorite_doctor(
        self,
        user_id: str,
        doctor_id: str,
        is_favorite: bool = True
    ) -> bool:
        """
        设置收藏医生

        Args:
            user_id: 用户ID
            doctor_id: 医生ID
            is_favorite: 是否收藏

        Returns:
            bool: 是否设置成功
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE doctor_preferences
                    SET is_favorite = ?
                    WHERE user_id = ? AND doctor_id = ?
                """, (1 if is_favorite else 0, user_id, doctor_id))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    UPDATE doctor_preferences
                    SET is_favorite = ?
                    WHERE user_id = ? AND doctor_id = ?
                """, (1 if is_favorite else 0, user_id, doctor_id))
                db.commit()

        return True

    async def rate_doctor(
        self,
        user_id: str,
        doctor_id: str,
        rating: float
    ) -> bool:
        """
        给医生评分

        Args:
            user_id: 用户ID
            doctor_id: 医生ID
            rating: 评分（1-5）

        Returns:
            bool: 是否评分成功
        """
        if not 1 <= rating <= 5:
            return False

        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE doctor_preferences
                    SET rating = ?
                    WHERE user_id = ? AND doctor_id = ?
                """, (rating, user_id, doctor_id))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    UPDATE doctor_preferences
                    SET rating = ?
                    WHERE user_id = ? AND doctor_id = ?
                """, (rating, user_id, doctor_id))
                db.commit()

        return True

    # ========== 科室偏好操作 ==========

    async def add_frequent_department(
        self,
        user_id: str,
        department: str
    ) -> bool:
        """
        添加常去科室

        Args:
            user_id: 用户ID
            department: 科室名称

        Returns:
            bool: 是否添加成功
        """
        pref = await self.get_or_create_preference(user_id)

        if department not in pref["frequent_departments"]:
            pref["frequent_departments"].append(department)
            # 最多保留10个
            if len(pref["frequent_departments"]) > 10:
                pref["frequent_departments"] = pref["frequent_departments"][-10:]

            pref["updated_at"] = datetime.now().isoformat()
            await self._save_preference(UserPreference.from_dict(pref))
            self._cache[user_id] = UserPreference.from_dict(pref)

        return True

    # ========== 时间段偏好操作 ==========

    async def add_preferred_time_slot(
        self,
        user_id: str,
        time_slot: str
    ) -> bool:
        """
        添加偏好时间段

        Args:
            user_id: 用户ID
            time_slot: 时间段（如 "morning", "afternoon", "evening"）

        Returns:
            bool: 是否添加成功
        """
        pref = await self.get_or_create_preference(user_id)

        if time_slot not in pref["preferred_time_slots"]:
            pref["preferred_time_slots"].append(time_slot)

            pref["updated_at"] = datetime.now().isoformat()
            await self._save_preference(UserPreference.from_dict(pref))
            self._cache[user_id] = UserPreference.from_dict(pref)

        return True

    # ========== 设置操作 ==========

    async def set_consultation_type(
        self,
        user_id: str,
        consultation_type: str
    ) -> bool:
        """
        设置问诊类型偏好

        Args:
            user_id: 用户ID
            consultation_type: 问诊类型（text/video/phone）

        Returns:
            bool: 是否设置成功
        """
        if consultation_type not in ("text", "video", "phone"):
            return False

        pref = await self.get_or_create_preference(user_id)
        pref["consultation_type"] = consultation_type
        pref["updated_at"] = datetime.now().isoformat()

        await self._save_preference(UserPreference.from_dict(pref))
        self._cache[user_id] = UserPreference.from_dict(pref)

        return True

    async def set_language(
        self,
        user_id: str,
        language: str
    ) -> bool:
        """
        设置语言偏好

        Args:
            user_id: 用户ID
            language: 语言代码（zh-CN, en-US等）

        Returns:
            bool: 是否设置成功
        """
        pref = await self.get_or_create_preference(user_id)
        pref["language"] = language
        pref["updated_at"] = datetime.now().isoformat()

        await self._save_preference(UserPreference.from_dict(pref))
        self._cache[user_id] = UserPreference.from_dict(pref)

        return True

    async def set_notification(
        self,
        user_id: str,
        enabled: bool,
        notification_time: Optional[str] = None
    ) -> bool:
        """
        设置通知偏好

        Args:
            user_id: 用户ID
            enabled: 是否启用
            notification_time: 通知时间（可选）

        Returns:
            bool: 是否设置成功
        """
        pref = await self.get_or_create_preference(user_id)
        pref["notification_enabled"] = enabled
        if notification_time:
            pref["notification_time"] = notification_time
        pref["updated_at"] = datetime.now().isoformat()

        await self._save_preference(UserPreference.from_dict(pref))
        self._cache[user_id] = UserPreference.from_dict(pref)

        return True

    # ========== 统计信息 ==========

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取服务统计信息

        Returns:
            Dict: 统计信息
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM user_preferences")
                total_users = (await cursor.fetchone())[0]

                cursor = await db.execute("SELECT COUNT(*) FROM hospital_preferences")
                total_hospital_prefs = (await cursor.fetchone())[0]

                cursor = await db.execute("SELECT COUNT(*) FROM doctor_preferences")
                total_doctor_prefs = (await cursor.fetchone())[0]
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("SELECT COUNT(*) FROM user_preferences")
                total_users = cursor.fetchone()[0]

                cursor = db.execute("SELECT COUNT(*) FROM hospital_preferences")
                total_hospital_prefs = cursor.fetchone()[0]

                cursor = db.execute("SELECT COUNT(*) FROM doctor_preferences")
                total_doctor_prefs = cursor.fetchone()[0]

        return {
            "total_users": total_users,
            "total_hospital_prefs": total_hospital_prefs,
            "total_doctor_prefs": total_doctor_prefs,
            "cache_size": len(self._cache),
        }


# ============================================================
# 全局服务实例
# ============================================================

_global_preference_service: Optional[PreferenceService] = None


def get_preference_service(
    db_path: str = "data/preferences.db"
) -> PreferenceService:
    """获取全局偏好服务"""
    global _global_preference_service
    if _global_preference_service is None:
        _global_preference_service = PreferenceService(db_path)
    return _global_preference_service


def reset_preference_service():
    """重置全局偏好服务"""
    global _global_preference_service
    _global_preference_service = None
