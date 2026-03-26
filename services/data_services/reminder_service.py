# -*- coding: utf-8 -*-
"""
医疗智能助手 - 提醒数据服务
管理提醒数据，包括用药提醒、随访提醒等
"""

import json
import sqlite3
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False


class ReminderType(Enum):
    """提醒类型枚举"""
    MEDICATION = "medication"  # 用药提醒
    APPOINTMENT = "appointment"  # 预约提醒
    FOLLOWUP = "followup"  # 随访提醒
    CHECKUP = "checkup"  # 体检提醒
    REFILL = "refill"  # 复诊提醒
    MEASUREMENT = "measurement"  # 测量提醒（血压、血糖等）
    CUSTOM = "custom"  # 自定义提醒


class ReminderStatus(Enum):
    """提醒状态"""
    PENDING = "pending"  # 待发送
    SENT = "sent"  # 已发送
    ACKNOWLEDGED = "acknowledged"  # 已确认
    DISMISSED = "dismissed"  # 已忽略
    CANCELLED = "cancelled"  # 已取消
    EXPIRED = "expired"  # 已过期


class RepeatType(Enum):
    """重复类型"""
    ONCE = "once"  # 一次性
    DAILY = "daily"  # 每天
    WEEKLY = "weekly"  # 每周
    MONTHLY = "monthly"  # 每月
    CUSTOM = "custom"  # 自定义


@dataclass
class Reminder:
    """提醒"""
    reminder_id: str
    user_id: str
    reminder_type: str
    title: str
    description: Optional[str] = None
    reminder_time: Optional[str] = None  # 提醒时间
    repeat_type: str = RepeatType.ONCE.value
    repeat_config: Dict[str, Any] = field(default_factory=dict)  # 重复配置
    status: str = ReminderStatus.PENDING.value
    sent_count: int = 0
    acknowledged_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "reminder_id": self.reminder_id,
            "user_id": self.user_id,
            "reminder_type": self.reminder_type,
            "title": self.title,
            "description": self.description,
            "reminder_time": self.reminder_time,
            "repeat_type": self.repeat_type,
            "repeat_config": self.repeat_config,
            "status": self.status,
            "sent_count": self.sent_count,
            "acknowledged_time": self.acknowledged_time,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Reminder":
        """从字典创建"""
        return cls(**data)


@dataclass
class ReminderLog:
    """提醒日志"""
    log_id: str
    reminder_id: str
    user_id: str
    sent_time: str
    status: str
    channel: str  # push, sms, email, in_app
    error_message: Optional[str] = None


class ReminderDataService:
    """
    提醒数据服务
    管理提醒数据，包括用药提醒、随访提醒等
    """

    def __init__(self, db_path: str = "data/reminders.db"):
        """
        初始化提醒服务

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._initialized = False
        self._cache: Dict[str, Reminder] = {}

        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_schema_statements(self) -> List[str]:
        """获取数据库表结构SQL语句"""
        return [
            """CREATE TABLE IF NOT EXISTS reminders (
                reminder_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                reminder_time TEXT,
                repeat_type TEXT NOT NULL DEFAULT 'once',
                repeat_config TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending',
                sent_count INTEGER NOT NULL DEFAULT 0,
                acknowledged_time TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS reminder_logs (
                log_id TEXT PRIMARY KEY,
                reminder_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                sent_time TEXT NOT NULL,
                status TEXT NOT NULL,
                channel TEXT NOT NULL,
                error_message TEXT,
                FOREIGN KEY (reminder_id) REFERENCES reminders (reminder_id)
            )""",
            """CREATE INDEX IF NOT EXISTS idx_reminders_user_id
                ON reminders (user_id)""",
            """CREATE INDEX IF NOT EXISTS idx_reminders_status
                ON reminders (status)""",
            """CREATE INDEX IF NOT EXISTS idx_reminders_reminder_time
                ON reminders (reminder_time)""",
            """CREATE INDEX IF NOT EXISTS idx_reminder_logs_reminder_id
                ON reminder_logs (reminder_id)""",
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

    def _generate_reminder_id(self) -> str:
        """生成提醒ID"""
        return f"RM{datetime.now().strftime('%Y%m%d%H%M%S%f')[:20]}"

    def _generate_log_id(self) -> str:
        """生成日志ID"""
        return f"RL{datetime.now().strftime('%Y%m%d%H%M%S%f')[:20]}"

    async def _save_reminder(self, reminder: Reminder) -> None:
        """保存提醒到数据库"""
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO reminders
                    (reminder_id, user_id, reminder_type, title, description,
                     reminder_time, repeat_type, repeat_config, status,
                     sent_count, acknowledged_time, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    reminder.reminder_id, reminder.user_id, reminder.reminder_type,
                    reminder.title, reminder.description, reminder.reminder_time,
                    reminder.repeat_type, json.dumps(reminder.repeat_config, ensure_ascii=False),
                    reminder.status, reminder.sent_count, reminder.acknowledged_time,
                    json.dumps(reminder.metadata, ensure_ascii=False),
                    reminder.created_at, reminder.updated_at
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT OR REPLACE INTO reminders
                    (reminder_id, user_id, reminder_type, title, description,
                     reminder_time, repeat_type, repeat_config, status,
                     sent_count, acknowledged_time, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    reminder.reminder_id, reminder.user_id, reminder.reminder_type,
                    reminder.title, reminder.description, reminder.reminder_time,
                    reminder.repeat_type, json.dumps(reminder.repeat_config, ensure_ascii=False),
                    reminder.status, reminder.sent_count, reminder.acknowledged_time,
                    json.dumps(reminder.metadata, ensure_ascii=False),
                    reminder.created_at, reminder.updated_at
                ))
                db.commit()

    def _load_reminder_from_row(self, row: tuple) -> Reminder:
        """从数据库行加载提醒"""
        return Reminder(
            reminder_id=row[0],
            user_id=row[1],
            reminder_type=row[2],
            title=row[3],
            description=row[4],
            reminder_time=row[5],
            repeat_type=row[6],
            repeat_config=json.loads(row[7]) if row[7] else {},
            status=row[8],
            sent_count=row[9],
            acknowledged_time=row[10],
            metadata=json.loads(row[11]) if row[11] else {},
            created_at=row[12],
            updated_at=row[13]
        )

    # ========== CRUD 操作 ==========

    async def create_reminder(
        self,
        user_id: str,
        reminder_type: str,
        title: str,
        description: Optional[str] = None,
        reminder_time: Optional[str] = None,
        repeat_type: str = RepeatType.ONCE.value,
        repeat_config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建提醒

        Args:
            user_id: 用户ID
            reminder_type: 提醒类型
            title: 标题
            description: 描述
            reminder_time: 提醒时间
            repeat_type: 重复类型
            repeat_config: 重复配置
            metadata: 元数据

        Returns:
            Dict: 提醒数据
        """
        await self.initialize()

        now = datetime.now().isoformat()
        reminder = Reminder(
            reminder_id=self._generate_reminder_id(),
            user_id=user_id,
            reminder_type=reminder_type,
            title=title,
            description=description,
            reminder_time=reminder_time,
            repeat_type=repeat_type,
            repeat_config=repeat_config or {},
            metadata=metadata or {},
            created_at=now,
            updated_at=now
        )

        await self._save_reminder(reminder)
        self._cache[reminder.reminder_id] = reminder

        return reminder.to_dict()

    async def get_reminder(self, reminder_id: str) -> Optional[Dict[str, Any]]:
        """
        获取提醒

        Args:
            reminder_id: 提醒ID

        Returns:
            Optional[Dict]: 提醒数据
        """
        await self.initialize()

        # 先检查缓存
        if reminder_id in self._cache:
            return self._cache[reminder_id].to_dict()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM reminders WHERE reminder_id = ?",
                    (reminder_id,)
                )
                row = await cursor.fetchone()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT * FROM reminders WHERE reminder_id = ?",
                    (reminder_id,)
                )
                row = cursor.fetchone()

        if not row:
            return None

        reminder = self._load_reminder_from_row(row)
        self._cache[reminder_id] = reminder

        return reminder.to_dict()

    async def get_user_reminders(
        self,
        user_id: str,
        reminder_type: Optional[str] = None,
        status: Optional[str] = None,
        active_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取用户提醒列表

        Args:
            user_id: 用户ID
            reminder_type: 提醒类型（可选）
            status: 状态（可选）
            active_only: 只获取活跃提醒
            limit: 最大返回数量

        Returns:
            List[Dict]: 提醒列表
        """
        await self.initialize()

        query = "SELECT * FROM reminders WHERE user_id = ?"
        params = [user_id]

        if reminder_type:
            query += " AND reminder_type = ?"
            params.append(reminder_type)

        if status:
            query += " AND status = ?"
            params.append(status)

        if active_only:
            query += " AND status IN ('pending', 'sent')"

        query += " ORDER BY reminder_time ASC LIMIT ?"
        params.append(limit)

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(query, params)
                rows = cursor.fetchall()

        return [self._load_reminder_from_row(row).to_dict() for row in rows]

    async def update_reminder(
        self,
        reminder_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        更新提醒

        Args:
            reminder_id: 提醒ID
            data: 更新数据

        Returns:
            bool: 是否更新成功
        """
        reminder_dict = await self.get_reminder(reminder_id)
        if not reminder_dict:
            return False

        # 更新字段
        updatable_fields = [
            "title", "description", "reminder_time",
            "repeat_type", "status"
        ]

        for field in updatable_fields:
            if field in data:
                reminder_dict[field] = data[field]

        if "repeat_config" in data:
            reminder_dict["repeat_config"].update(data["repeat_config"])

        if "metadata" in data:
            reminder_dict["metadata"].update(data["metadata"])

        reminder_dict["updated_at"] = datetime.now().isoformat()

        reminder = Reminder.from_dict(reminder_dict)
        await self._save_reminder(reminder)
        self._cache[reminder_id] = reminder

        return True

    async def cancel_reminder(self, reminder_id: str) -> bool:
        """
        取消提醒

        Args:
            reminder_id: 提醒ID

        Returns:
            bool: 是否取消成功
        """
        return await self.update_reminder(reminder_id, {"status": ReminderStatus.CANCELLED.value})

    async def delete_reminder(self, reminder_id: str) -> bool:
        """
        删除提醒

        Args:
            reminder_id: 提醒ID

        Returns:
            bool: 是否删除成功
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM reminders WHERE reminder_id = ?",
                    (reminder_id,)
                )
                await db.commit()
                deleted = cursor.rowcount > 0
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "DELETE FROM reminders WHERE reminder_id = ?",
                    (reminder_id,)
                )
                db.commit()
                deleted = cursor.rowcount > 0

        if deleted and reminder_id in self._cache:
            del self._cache[reminder_id]

        return deleted

    # ========== 提醒状态操作 ==========

    async def mark_sent(self, reminder_id: str) -> bool:
        """
        标记为已发送

        Args:
            reminder_id: 提醒ID

        Returns:
            bool: 是否标记成功
        """
        reminder_dict = await self.get_reminder(reminder_id)
        if not reminder_dict:
            return False

        reminder_dict["status"] = ReminderStatus.SENT.value
        reminder_dict["sent_count"] += 1
        reminder_dict["updated_at"] = datetime.now().isoformat()

        reminder = Reminder.from_dict(reminder_dict)
        await self._save_reminder(reminder)
        self._cache[reminder_id] = reminder

        return True

    async def mark_acknowledged(
        self,
        reminder_id: str,
        acknowledged_time: Optional[str] = None
    ) -> bool:
        """
        标记为已确认

        Args:
            reminder_id: 提醒ID
            acknowledged_time: 确认时间

        Returns:
            bool: 是否标记成功
        """
        reminder_dict = await self.get_reminder(reminder_id)
        if not reminder_dict:
            return False

        reminder_dict["status"] = ReminderStatus.ACKNOWLEDGED.value
        reminder_dict["acknowledged_time"] = acknowledged_time or datetime.now().isoformat()
        reminder_dict["updated_at"] = datetime.now().isoformat()

        reminder = Reminder.from_dict(reminder_dict)
        await self._save_reminder(reminder)
        self._cache[reminder_id] = reminder

        return True

    async def mark_dismissed(self, reminder_id: str) -> bool:
        """
        标记为已忽略

        Args:
            reminder_id: 提醒ID

        Returns:
            bool: 是否标记成功
        """
        return await self.update_reminder(reminder_id, {"status": ReminderStatus.DISMISSED.value})

    # ========== 查询操作 ==========

    async def get_due_reminders(
        self,
        before_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取到期的提醒

        Args:
            before_time: 时间截止点（可选）

        Returns:
            List[Dict]: 到期提醒列表
        """
        await self.initialize()

        if before_time is None:
            before_time = datetime.now().isoformat()

        query = """
            SELECT * FROM reminders
            WHERE status IN ('pending', 'sent')
            AND reminder_time <= ?
            ORDER BY reminder_time ASC
        """

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, (before_time,))
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(query, (before_time,))
                rows = cursor.fetchall()

        return [self._load_reminder_from_row(row).to_dict() for row in rows]

    async def get_reminders_by_type(
        self,
        reminder_type: str,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        按类型获取提醒

        Args:
            reminder_type: 提醒类型
            user_id: 用户ID（可选）

        Returns:
            List[Dict]: 提醒列表
        """
        await self.initialize()

        if user_id:
            query = "SELECT * FROM reminders WHERE user_id = ? AND reminder_type = ?"
            params = (user_id, reminder_type)
        else:
            query = "SELECT * FROM reminders WHERE reminder_type = ?"
            params = (reminder_type,)

        query += " ORDER BY reminder_time ASC"

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(query, params)
                rows = cursor.fetchall()

        return [self._load_reminder_from_row(row).to_dict() for row in rows]

    # ========== 特定类型提醒便捷方法 ==========

    async def create_medication_reminder(
        self,
        user_id: str,
        drug_name: str,
        dosage: str,
        reminder_times: List[str],
        repeat_type: str = RepeatType.DAILY.value
    ) -> Dict[str, Any]:
        """
        创建用药提醒

        Args:
            user_id: 用户ID
            drug_name: 药品名称
            dosage: 剂量
            reminder_times: 提醒时间列表
            repeat_type: 重复类型

        Returns:
            Dict: 提醒数据
        """
        return await self.create_reminder(
            user_id=user_id,
            reminder_type=ReminderType.MEDICATION.value,
            title=f"用药提醒：{drug_name}",
            description=f"请服用 {drug_name}，剂量：{dosage}",
            reminder_time=reminder_times[0] if reminder_times else None,
            repeat_type=repeat_type,
            repeat_config={"drug_name": drug_name, "dosage": dosage, "times": reminder_times},
            metadata={"drug_name": drug_name, "dosage": dosage}
        )

    async def create_appointment_reminder(
        self,
        user_id: str,
        hospital: str,
        department: str,
        doctor: Optional[str],
        appointment_time: str
    ) -> Dict[str, Any]:
        """
        创建预约提醒

        Args:
            user_id: 用户ID
            hospital: 医院
            department: 科室
            doctor: 医生
            appointment_time: 预约时间

        Returns:
            Dict: 提醒数据
        """
        title = f"预约提醒：{hospital} {department}"
        if doctor:
            title += f" {doctor}医生"

        return await self.create_reminder(
            user_id=user_id,
            reminder_type=ReminderType.APPOINTMENT.value,
            title=title,
            description=f"您在 {hospital} {department} 有预约",
            reminder_time=appointment_time,
            repeat_type=RepeatType.ONCE.value,
            metadata={"hospital": hospital, "department": department, "doctor": doctor}
        )

    async def create_followup_reminder(
        self,
        user_id: str,
        followup_content: str,
        reminder_time: str
    ) -> Dict[str, Any]:
        """
        创建随访提醒

        Args:
            user_id: 用户ID
            followup_content: 随访内容
            reminder_time: 提醒时间

        Returns:
            Dict: 提醒数据
        """
        return await self.create_reminder(
            user_id=user_id,
            reminder_type=ReminderType.FOLLOWUP.value,
            title="随访提醒",
            description=followup_content,
            reminder_time=reminder_time,
            repeat_type=RepeatType.ONCE.value,
            metadata={"content": followup_content}
        )

    async def create_measurement_reminder(
        self,
        user_id: str,
        measurement_type: str,
        reminder_times: List[str],
        repeat_type: str = RepeatType.DAILY.value
    ) -> Dict[str, Any]:
        """
        创建测量提醒（血压、血糖等）

        Args:
            user_id: 用户ID
            measurement_type: 测量类型（血压、血糖等）
            reminder_times: 提醒时间列表
            repeat_type: 重复类型

        Returns:
            Dict: 提醒数据
        """
        return await self.create_reminder(
            user_id=user_id,
            reminder_type=ReminderType.MEASUREMENT.value,
            title=f"{measurement_type}测量提醒",
            description=f"请测量{measurement_type}",
            reminder_time=reminder_times[0] if reminder_times else None,
            repeat_type=repeat_type,
            repeat_config={"type": measurement_type, "times": reminder_times},
            metadata={"measurement_type": measurement_type}
        )

    # ========== 提醒日志 ==========

    async def log_reminder_sent(
        self,
        reminder_id: str,
        user_id: str,
        channel: str,
        status: str = "sent",
        error_message: Optional[str] = None
    ) -> str:
        """
        记录提醒发送日志

        Args:
            reminder_id: 提醒ID
            user_id: 用户ID
            channel: 发送渠道
            status: 状态
            error_message: 错误信息

        Returns:
            str: 日志ID
        """
        await self.initialize()

        log_id = self._generate_log_id()
        sent_time = datetime.now().isoformat()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO reminder_logs
                    (log_id, reminder_id, user_id, sent_time, status, channel, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (log_id, reminder_id, user_id, sent_time, status, channel, error_message))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT INTO reminder_logs
                    (log_id, reminder_id, user_id, sent_time, status, channel, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (log_id, reminder_id, user_id, sent_time, status, channel, error_message))
                db.commit()

        return log_id

    async def get_reminder_logs(
        self,
        reminder_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取提醒日志

        Args:
            reminder_id: 提醒ID
            limit: 最大返回数量

        Returns:
            List[Dict]: 日志列表
        """
        await self.initialize()

        query = """
            SELECT * FROM reminder_logs
            WHERE reminder_id = ?
            ORDER BY sent_time DESC
            LIMIT ?
        """

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, (reminder_id, limit))
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(query, (reminder_id, limit))
                rows = cursor.fetchall()

        return [
            {
                "log_id": row[0],
                "reminder_id": row[1],
                "user_id": row[2],
                "sent_time": row[3],
                "status": row[4],
                "channel": row[5],
                "error_message": row[6]
            }
            for row in rows
        ]

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
                cursor = await db.execute("SELECT COUNT(*) FROM reminders")
                total_reminders = (await cursor.fetchone())[0]

                cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM reminders")
                total_users = (await cursor.fetchone())[0]

                cursor = await db.execute("""
                    SELECT reminder_type, COUNT(*) as count
                    FROM reminders
                    GROUP BY reminder_type
                """)
                type_counts = {row[0]: row[1] for row in await cursor.fetchall()}

                cursor = await db.execute("""
                    SELECT status, COUNT(*) as count
                    FROM reminders
                    GROUP BY status
                """)
                status_counts = {row[0]: row[1] for row in await cursor.fetchall()}
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("SELECT COUNT(*) FROM reminders")
                total_reminders = cursor.fetchone()[0]

                cursor = db.execute("SELECT COUNT(DISTINCT user_id) FROM reminders")
                total_users = cursor.fetchone()[0]

                cursor = db.execute("""
                    SELECT reminder_type, COUNT(*) as count
                    FROM reminders
                    GROUP BY reminder_type
                """)
                type_counts = {row[0]: row[1] for row in cursor.fetchall()}

                cursor = db.execute("""
                    SELECT status, COUNT(*) as count
                    FROM reminders
                    GROUP BY status
                """)
                status_counts = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_reminders": total_reminders,
            "total_users": total_users,
            "type_counts": type_counts,
            "status_counts": status_counts,
            "cache_size": len(self._cache),
        }

    async def cleanup_old_reminders(self, days: int = 30) -> int:
        """
        清理旧提醒

        Args:
            days: 保留天数

        Returns:
            int: 删除的记录数
        """
        await self.initialize()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # 只删除已完成、已取消、已过期的提醒
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    DELETE FROM reminders
                    WHERE status IN ('acknowledged', 'cancelled', 'expired')
                    AND (updated_at < ? OR (acknowledged_time IS NOT NULL AND acknowledged_time < ?))
                """, (cutoff_date, cutoff_date))
                await db.commit()
                deleted_count = cursor.rowcount
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("""
                    DELETE FROM reminders
                    WHERE status IN ('acknowledged', 'cancelled', 'expired')
                    AND (updated_at < ? OR (acknowledged_time IS NOT NULL AND acknowledged_time < ?))
                """, (cutoff_date, cutoff_date))
                db.commit()
                deleted_count = cursor.rowcount

        return deleted_count


# ============================================================
# 全局服务实例
# ============================================================

_global_reminder_service: Optional[ReminderDataService] = None


def get_reminder_service(
    db_path: str = "data/reminders.db"
) -> ReminderDataService:
    """获取全局提醒服务"""
    global _global_reminder_service
    if _global_reminder_service is None:
        _global_reminder_service = ReminderDataService(db_path)
    return _global_reminder_service


def reset_reminder_service():
    """重置全局提醒服务"""
    global _global_reminder_service
    _global_reminder_service = None
