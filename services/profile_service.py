# -*- coding: utf-8 -*-
"""
医疗智能助手 - 用户画像服务
管理用户画像的持久化和更新
"""

import json
import sqlite3
import asyncio
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime

# 尝试导入aiosqlite
try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False

try:
    from agent.user_profile import UserProfile, ProfileUpdate, create_default_profile
    USER_PROFILE_AVAILABLE = True
except ImportError:
    USER_PROFILE_AVAILABLE = False

    # 定义简化版本
    from dataclasses import dataclass, field

    @dataclass
    class UserProfile:
        user_id: str
        created_at: str
        updated_at: str = ""
        basic_info: Dict[str, Any] = field(default_factory=dict)
        medical_history: List[str] = field(default_factory=list)
        allergies: List[str] = field(default_factory=list)
        current_medications: Dict[str, Any] = field(default_factory=dict)
        chronic_conditions: List[str] = field(default_factory=list)
        preferences: Dict[str, Any] = field(default_factory=dict)
        stats: Dict[str, Any] = field(default_factory=dict)
        metadata: Dict[str, Any] = field(default_factory=dict)

    def create_default_profile(user_id: str) -> UserProfile:
        return UserProfile(user_id=user_id, created_at=datetime.now().isoformat())


class ProfileService:
    """
    用户画像服务
    管理用户画像的存储和更新
    """

    def __init__(self, db_path: str = "data/profiles.db"):
        """
        初始化用户画像服务

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._initialized = False

        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_schema_statements(self):
        """获取SQL语句"""
        return [
            """CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                profile_data TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS profile_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                update_type TEXT NOT NULL,
                action TEXT NOT NULL,
                data TEXT,
                source TEXT,
                timestamp TEXT,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )""",
            """CREATE INDEX IF NOT EXISTS idx_profile_updates_user_id ON profile_updates (user_id)""",
        ]

    async def initialize(self):
        """初始化数据库（异步）"""
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

    def _initialize_sync(self):
        """同步初始化"""
        with sqlite3.connect(self.db_path) as db:
            for stmt in self._get_schema_statements():
                db.execute(stmt)
            db.commit()
        self._initialized = True

    async def save_profile(self, profile: UserProfile) -> bool:
        """
        保存用户画像

        Args:
            profile: 用户画像

        Returns:
            bool: 是否保存成功
        """
        await self.initialize()

        # 序列化画像数据
        if hasattr(profile, 'to_dict'):
            profile_dict = profile.to_dict()
        else:
            profile_dict = {
                'user_id': profile.user_id,
                'created_at': profile.created_at,
                'updated_at': profile.updated_at,
                'basic_info': profile.basic_info,
                'medical_history': profile.medical_history,
                'allergies': profile.allergies,
                'current_medications': profile.current_medications,
                'chronic_conditions': profile.chronic_conditions,
                'preferences': profile.preferences,
                'stats': profile.stats,
                'metadata': profile.metadata,
            }

        profile_json = json.dumps(profile_dict, ensure_ascii=False)

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO user_profiles
                    (user_id, profile_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    profile.user_id,
                    profile_json,
                    profile.created_at,
                    profile.updated_at or datetime.now().isoformat()
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT OR REPLACE INTO user_profiles
                    (user_id, profile_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    profile.user_id,
                    profile_json,
                    profile.created_at,
                    profile.updated_at or datetime.now().isoformat()
                ))
                db.commit()

        return True

    async def load_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        加载用户画像

        Args:
            user_id: 用户ID

        Returns:
            Optional[UserProfile]: 用户画像，如果不存在则返回None
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT profile_data FROM user_profiles WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT profile_data FROM user_profiles WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()

        if not row:
            return None

        profile_dict = json.loads(row[0])

        # 如果UserProfile类有from_dict方法，使用它
        if hasattr(UserProfile, 'from_dict'):
            return UserProfile.from_dict(profile_dict)
        else:
            return UserProfile(**profile_dict)

    async def get_or_create_profile(self, user_id: str) -> UserProfile:
        """
        获取或创建用户画像

        Args:
            user_id: 用户ID

        Returns:
            UserProfile: 用户画像
        """
        profile = await self.load_profile(user_id)
        if profile is None:
            profile = create_default_profile(user_id)
            await self.save_profile(profile)
        return profile

    async def update_from_context(
        self,
        user_id: str,
        entities: Dict[str, Any],
        source: str = "inference"
    ) -> List:
        """
        从对话上下文更新用户画像

        Args:
            user_id: 用户ID
            entities: 提取的实体
            source: 更新来源

        Returns:
            List: 应用的更新列表
        """
        from agent.user_profile import ProfileUpdate

        profile = await self.get_or_create_profile(user_id)
        updates = []

        # 提取疾病信息
        if 'disease' in entities:
            disease = entities['disease']
            if isinstance(disease, list):
                disease = disease[0] if disease else None
            if disease and disease not in profile.medical_history:
                profile.medical_history.append(disease)
                updates.append(ProfileUpdate(
                    user_id=user_id,
                    update_type='medical_history',
                    action='add',
                    data=disease,
                    source=source
                ))

        # 提取过敏信息
        if 'allergy' in entities:
            allergy = entities['allergy']
            if isinstance(allergy, list):
                allergy = allergy[0] if allergy else None
            if allergy and allergy not in profile.allergies:
                profile.allergies.append(allergy)
                updates.append(ProfileUpdate(
                    user_id=user_id,
                    update_type='allergy',
                    action='add',
                    data=allergy,
                    source=source
                ))

        # 提取用药信息
        if 'drug' in entities:
            drug = entities['drug']
            if isinstance(drug, list):
                drug = drug[0] if drug else None
            if drug:
                dosage = entities.get('dosage')
                profile.current_medications[drug] = {
                    'started': datetime.now().isoformat()
                }
                if dosage:
                    profile.current_medications[drug]['dosage'] = dosage
                updates.append(ProfileUpdate(
                    user_id=user_id,
                    update_type='medication',
                    action='add',
                    data={'drug': drug, 'dosage': dosage},
                    source=source
                ))

        # 更新统计信息
        profile.stats['last_updated'] = datetime.now().isoformat()
        profile.updated_at = datetime.now().isoformat()

        # 保存更新
        if updates:
            await self.save_profile(profile)
            await self._save_updates(updates)

        return updates

    async def _save_updates(self, updates: List) -> None:
        """保存更新记录"""
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                for update in updates:
                    update_dict = {
                        'user_id': update.user_id,
                        'update_type': update.update_type,
                        'action': update.action,
                        'data': json.dumps(update.data) if not isinstance(update.data, str) else update.data,
                        'source': update.source,
                        'timestamp': update.timestamp
                    }
                    await db.execute("""
                        INSERT INTO profile_updates
                        (user_id, update_type, action, data, source, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (update_dict['user_id'], update_dict['update_type'],
                          update_dict['action'], update_dict['data'],
                          update_dict['source'], update_dict['timestamp']))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                for update in updates:
                    update_dict = {
                        'user_id': update.user_id,
                        'update_type': update.update_type,
                        'action': update.action,
                        'data': json.dumps(update.data) if not isinstance(update.data, str) else update.data,
                        'source': update.source,
                        'timestamp': update.timestamp
                    }
                    db.execute("""
                        INSERT INTO profile_updates
                        (user_id, update_type, action, data, source, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (update_dict['user_id'], update_dict['update_type'],
                          update_dict['action'], update_dict['data'],
                          update_dict['source'], update_dict['timestamp']))
                db.commit()

    async def get_update_history(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取用户画像更新历史

        Args:
            user_id: 用户ID
            limit: 最大返回数量

        Returns:
            List[Dict]: 更新历史列表
        """
        await self.initialize()

        query = """
            SELECT id, user_id, update_type, action, data, source, timestamp
            FROM profile_updates
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                cursor = await db.execute(query, (user_id, limit))
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                cursor = db.execute(query, (user_id, limit))
                rows = cursor.fetchall()

        return [
            {
                'id': row['id'],
                'user_id': row['user_id'],
                'update_type': row['update_type'],
                'action': row['action'],
                'data': json.loads(row['data']) if row['data'] else None,
                'source': row['source'],
                'timestamp': row['timestamp']
            }
            for row in rows
        ]

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
                return cursor.rowcount > 0
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "DELETE FROM user_profiles WHERE user_id = ?",
                    (user_id,)
                )
                db.commit()
                return cursor.rowcount > 0

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取服务统计信息

        Returns:
            Dict: 统计信息
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                # 用户总数
                cursor = await db.execute("SELECT COUNT(*) FROM user_profiles")
                total_users = (await cursor.fetchone())[0]

                # 更新记录总数
                cursor = await db.execute("SELECT COUNT(*) FROM profile_updates")
                total_updates = (await cursor.fetchone())[0]

                # 数据库大小
                cursor = await db.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size = (await cursor.fetchone())[0]
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("SELECT COUNT(*) FROM user_profiles")
                total_users = cursor.fetchone()[0]

                cursor = db.execute("SELECT COUNT(*) FROM profile_updates")
                total_updates = cursor.fetchone()[0]

                cursor = db.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size = cursor.fetchone()[0]

        return {
            "total_users": total_users,
            "total_updates": total_updates,
            "db_size_bytes": db_size,
        }


# ============================================================
# 全局用户画像服务实例
# ============================================================

_global_profile_service: Optional[ProfileService] = None


def get_profile_service(db_path: str = "data/profiles.db") -> ProfileService:
    """获取全局用户画像服务"""
    global _global_profile_service
    if _global_profile_service is None:
        _global_profile_service = ProfileService(db_path)
    return _global_profile_service


def reset_profile_service():
    """重置全局用户画像服务"""
    global _global_profile_service
    _global_profile_service = None
