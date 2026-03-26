# -*- coding: utf-8 -*-
"""
医疗智能助手 - 行为日志数据服务
记录用户行为日志，用于分析和优化
"""

import json
import sqlite3
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, Counter

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False


class ActionType(Enum):
    """行为类型枚举"""
    # 咨询类
    SYMPTOM_INQUIRY = "symptom_inquiry"  # 症状咨询
    MEDICATION_CONSULT = "medication_consult"  # 用药咨询
    DEPARTMENT_QUERY = "department_query"  # 科室查询
    HEALTH_EDUCATION = "health_education"  # 健康教育
    REPORT_INTERPRET = "report_interpret"  # 报告解读

    # 服务类
    APPOINTMENT = "appointment"  # 预约挂号
    APPOINTMENT_CANCEL = "appointment_cancel"  # 取消预约
    ONLINE_CONSULT = "online_consult"  # 在线问诊
    FOLLOWUP_FEEDBACK = "followup_feedback"  # 随访反馈

    # 慢病类
    CHRONIC_RECORD = "chronic_record"  # 慢病记录
    CHRONIC_QUERY = "chronic_query"  # 慢病查询

    # 管理类
    CHECKUP_BOOKING = "checkup_booking"  # 体检预约
    REMINDER_SETTING = "reminder_setting"  # 提醒设置
    PROFILE_UPDATE = "profile_update"  # 档案更新

    # 交互类
    GREETING = "greeting"  # 问候
    HELP = "help"  # 帮助
    UNKNOWN = "unknown"  # 未知意图


class SessionStatus(Enum):
    """会话状态"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ERROR = "error"


@dataclass
class BehaviorLog:
    """行为日志记录"""
    log_id: str
    user_id: str
    session_id: str
    action_type: str
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "log_id": self.log_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "action_type": self.action_type,
            "intent": self.intent,
            "entities": self.entities,
            "parameters": self.parameters,
            "result": self.result,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BehaviorLog":
        """从字典创建"""
        return cls(**data)


@dataclass
class SessionLog:
    """会话日志"""
    session_id: str
    user_id: str
    start_time: str
    end_time: Optional[str] = None
    status: str = SessionStatus.ACTIVE.value
    total_interactions: int = 0
    intents: List[str] = field(default_factory=list)
    satisfaction_score: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DailyStats:
    """日统计数据"""
    date: str
    total_users: int
    total_sessions: int
    total_interactions: int
    action_counts: Dict[str, int]
    avg_session_duration: float
    error_count: int


class BehaviorLogService:
    """
    行为日志数据服务
    记录用户行为日志，用于分析和优化
    """

    def __init__(self, db_path: str = "data/behavior_logs.db"):
        """
        初始化行为日志服务

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._initialized = False
        self._session_cache: Dict[str, SessionLog] = {}

        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_schema_statements(self) -> List[str]:
        """获取数据库表结构SQL语句"""
        return [
            """CREATE TABLE IF NOT EXISTS behavior_logs (
                log_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                intent TEXT,
                entities TEXT NOT NULL DEFAULT '{}',
                parameters TEXT NOT NULL DEFAULT '{}',
                result TEXT,
                error_message TEXT,
                timestamp TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS session_logs (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                total_interactions INTEGER NOT NULL DEFAULT 0,
                intents TEXT NOT NULL DEFAULT '[]',
                satisfaction_score INTEGER,
                metadata TEXT NOT NULL DEFAULT '{}'
            )""",
            """CREATE INDEX IF NOT EXISTS idx_behavior_logs_user_id
                ON behavior_logs (user_id)""",
            """CREATE INDEX IF NOT EXISTS idx_behavior_logs_session_id
                ON behavior_logs (session_id)""",
            """CREATE INDEX IF NOT EXISTS idx_behavior_logs_timestamp
                ON behavior_logs (timestamp)""",
            """CREATE INDEX IF NOT EXISTS idx_behavior_logs_action_type
                ON behavior_logs (action_type)""",
            """CREATE INDEX IF NOT EXISTS idx_session_logs_user_id
                ON session_logs (user_id)""",
            """CREATE INDEX IF NOT EXISTS idx_session_logs_start_time
                ON session_logs (start_time)""",
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

    def _generate_log_id(self) -> str:
        """生成日志ID"""
        return f"BL{datetime.now().strftime('%Y%m%d%H%M%S%f')[:20]}"

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"SS{datetime.now().strftime('%Y%m%d%H%M%S%f')[:20]}"

    # ========== 行为日志操作 ==========

    async def log_behavior(
        self,
        user_id: str,
        action_type: str,
        session_id: Optional[str] = None,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        记录用户行为

        Args:
            user_id: 用户ID
            action_type: 行为类型
            session_id: 会话ID（可选，自动创建）
            intent: 意图
            entities: 实体
            parameters: 参数
            result: 结果
            error_message: 错误信息
            ip_address: IP地址
            user_agent: 用户代理

        Returns:
            str: 日志ID
        """
        await self.initialize()

        # 如果没有会话ID，创建新会话
        if not session_id:
            session_id = await self.create_session(user_id)

        log = BehaviorLog(
            log_id=self._generate_log_id(),
            user_id=user_id,
            session_id=session_id,
            action_type=action_type,
            intent=intent,
            entities=entities or {},
            parameters=parameters or {},
            result=result,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # 保存日志
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO behavior_logs
                    (log_id, user_id, session_id, action_type, intent,
                     entities, parameters, result, error_message, timestamp,
                     ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log.log_id, log.user_id, log.session_id, log.action_type,
                    log.intent, json.dumps(log.entities, ensure_ascii=False),
                    json.dumps(log.parameters, ensure_ascii=False), log.result,
                    log.error_message, log.timestamp, log.ip_address, log.user_agent
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT INTO behavior_logs
                    (log_id, user_id, session_id, action_type, intent,
                     entities, parameters, result, error_message, timestamp,
                     ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log.log_id, log.user_id, log.session_id, log.action_type,
                    log.intent, json.dumps(log.entities, ensure_ascii=False),
                    json.dumps(log.parameters, ensure_ascii=False), log.result,
                    log.error_message, log.timestamp, log.ip_address, log.user_agent
                ))
                db.commit()

        # 更新会话
        await self._update_session(session_id, action_type, intent)

        return log.log_id

    async def get_logs(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        action_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取行为日志

        Args:
            user_id: 用户ID（可选）
            session_id: 会话ID（可选）
            action_type: 行为类型（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            limit: 最大返回数量

        Returns:
            List[Dict]: 日志列表
        """
        await self.initialize()

        query = "SELECT * FROM behavior_logs WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        if action_type:
            query += " AND action_type = ?"
            params.append(action_type)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(query, params)
                rows = cursor.fetchall()

        return [
            {
                "log_id": row[0],
                "user_id": row[1],
                "session_id": row[2],
                "action_type": row[3],
                "intent": row[4],
                "entities": json.loads(row[5]) if row[5] else {},
                "parameters": json.loads(row[6]) if row[6] else {},
                "result": row[7],
                "error_message": row[8],
                "timestamp": row[9],
                "ip_address": row[10],
                "user_agent": row[11]
            }
            for row in rows
        ]

    # ========== 会话操作 ==========

    async def create_session(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        创建新会话

        Args:
            user_id: 用户ID
            metadata: 元数据

        Returns:
            str: 会话ID
        """
        await self.initialize()

        session_id = self._generate_session_id()
        now = datetime.now().isoformat()

        session = SessionLog(
            session_id=session_id,
            user_id=user_id,
            start_time=now,
            metadata=metadata or {}
        )

        self._session_cache[session_id] = session

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO session_logs
                    (session_id, user_id, start_time, status, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    session_id, user_id, now, SessionStatus.ACTIVE.value,
                    json.dumps(metadata or {}, ensure_ascii=False)
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT INTO session_logs
                    (session_id, user_id, start_time, status, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    session_id, user_id, now, SessionStatus.ACTIVE.value,
                    json.dumps(metadata or {}, ensure_ascii=False)
                ))
                db.commit()

        return session_id

    async def _update_session(
        self,
        session_id: str,
        action_type: str,
        intent: Optional[str] = None
    ) -> None:
        """更新会话"""
        if session_id in self._session_cache:
            session = self._session_cache[session_id]
            session.total_interactions += 1
            if intent and intent not in session.intents:
                session.intents.append(intent)

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                # 更新交互次数
                await db.execute("""
                    UPDATE session_logs
                    SET total_interactions = total_interactions + 1
                    WHERE session_id = ?
                """, (session_id,))

                # 更新意图列表
                if intent:
                    await db.execute("""
                        UPDATE session_logs
                        SET intents = CASE
                            WHEN intents IS NULL OR intents = '[]' THEN ?
                            WHEN instr(intents, ?) = 0 THEN intents || ',' || ?
                            ELSE intents
                        END
                        WHERE session_id = ?
                    """, (f'["{intent}"]', intent, intent, session_id))

                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    UPDATE session_logs
                    SET total_interactions = total_interactions + 1
                    WHERE session_id = ?
                """, (session_id,))

                if intent:
                    cursor = db.execute(
                        "SELECT intents FROM session_logs WHERE session_id = ?",
                        (session_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        intents = json.loads(row[0]) if row[0] else []
                        if intent not in intents:
                            intents.append(intent)
                            db.execute("""
                                UPDATE session_logs
                                SET intents = ?
                                WHERE session_id = ?
                            """, (json.dumps(intents, ensure_ascii=False), session_id))

                db.commit()

    async def close_session(
        self,
        session_id: str,
        status: str = SessionStatus.COMPLETED.value,
        satisfaction_score: Optional[int] = None
    ) -> bool:
        """
        关闭会话

        Args:
            session_id: 会话ID
            status: 会话状态
            satisfaction_score: 满意度评分（1-5）

        Returns:
            bool: 是否关闭成功
        """
        await self.initialize()

        now = datetime.now().isoformat()

        if session_id in self._session_cache:
            session = self._session_cache[session_id]
            session.end_time = now
            session.status = status
            session.satisfaction_score = satisfaction_score

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE session_logs
                    SET end_time = ?, status = ?, satisfaction_score = ?
                    WHERE session_id = ?
                """, (now, status, satisfaction_score, session_id))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    UPDATE session_logs
                    SET end_time = ?, status = ?, satisfaction_score = ?
                    WHERE session_id = ?
                """, (now, status, satisfaction_score, session_id))
                db.commit()

        return True

    async def get_session(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            Optional[Dict]: 会话信息
        """
        await self.initialize()

        if session_id in self._session_cache:
            session = self._session_cache[session_id]
            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "start_time": session.start_time,
                "end_time": session.end_time,
                "status": session.status,
                "total_interactions": session.total_interactions,
                "intents": session.intents,
                "satisfaction_score": session.satisfaction_score,
                "metadata": session.metadata,
            }

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM session_logs WHERE session_id = ?",
                    (session_id,)
                )
                row = await cursor.fetchone()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT * FROM session_logs WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()

        if not row:
            return None

        return {
            "session_id": row[0],
            "user_id": row[1],
            "start_time": row[2],
            "end_time": row[3],
            "status": row[4],
            "total_interactions": row[5],
            "intents": json.loads(row[6]) if row[6] else [],
            "satisfaction_score": row[7],
            "metadata": json.loads(row[8]) if row[8] else {},
        }

    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取用户会话列表

        Args:
            user_id: 用户ID
            limit: 最大返回数量

        Returns:
            List[Dict]: 会话列表
        """
        await self.initialize()

        query = """
            SELECT * FROM session_logs
            WHERE user_id = ?
            ORDER BY start_time DESC
            LIMIT ?
        """

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, (user_id, limit))
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(query, (user_id, limit))
                rows = cursor.fetchall()

        return [
            {
                "session_id": row[0],
                "user_id": row[1],
                "start_time": row[2],
                "end_time": row[3],
                "status": row[4],
                "total_interactions": row[5],
                "intents": json.loads(row[6]) if row[6] else [],
                "satisfaction_score": row[7],
                "metadata": json.loads(row[8]) if row[8] else {},
            }
            for row in rows
        ]

    # ========== 统计分析 ==========

    async def get_user_action_counts(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, int]:
        """
        获取用户行为统计

        Args:
            user_id: 用户ID
            days: 统计天数

        Returns:
            Dict: 行为类型计数
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        logs = await self.get_logs(
            user_id=user_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            limit=10000
        )

        counts = Counter()
        for log in logs:
            counts[log["action_type"]] += 1

        return dict(counts)

    async def get_daily_stats(
        self,
        date: Optional[str] = None
    ) -> DailyStats:
        """
        获取日统计数据

        Args:
            date: 日期（YYYY-MM-DD），默认为今天

        Returns:
            DailyStats: 日统计数据
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        start_time = f"{date}T00:00:00"
        end_time = f"{date}T23:59:59"

        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                # 总用户数
                cursor = await db.execute("""
                    SELECT COUNT(DISTINCT user_id) FROM behavior_logs
                    WHERE timestamp >= ? AND timestamp <= ?
                """, (start_time, end_time))
                total_users = (await cursor.fetchone())[0]

                # 总会话数
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM session_logs
                    WHERE start_time >= ? AND start_time <= ?
                """, (start_time, end_time))
                total_sessions = (await cursor.fetchone())[0]

                # 总交互数
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM behavior_logs
                    WHERE timestamp >= ? AND timestamp <= ?
                """, (start_time, end_time))
                total_interactions = (await cursor.fetchone())[0]

                # 行为类型统计
                cursor = await db.execute("""
                    SELECT action_type, COUNT(*) as count
                    FROM behavior_logs
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY action_type
                """, (start_time, end_time))
                action_counts_rows = await cursor.fetchall()

                # 平均会话时长
                cursor = await db.execute("""
                    SELECT AVG(
                        CASE
                            WHEN end_time IS NOT NULL
                            THEN (julianday(end_time) - julianday(start_time)) * 86400
                            ELSE NULL
                        END
                    ) FROM session_logs
                    WHERE start_time >= ? AND start_time <= ?
                """, (start_time, end_time))
                avg_duration_row = await cursor.fetchone()
                avg_session_duration = avg_duration_row[0] or 0

                # 错误数
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM behavior_logs
                    WHERE timestamp >= ? AND timestamp <= ?
                    AND error_message IS NOT NULL
                """, (start_time, end_time))
                error_count = (await cursor.fetchone())[0]
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("""
                    SELECT COUNT(DISTINCT user_id) FROM behavior_logs
                    WHERE timestamp >= ? AND timestamp <= ?
                """, (start_time, end_time))
                total_users = cursor.fetchone()[0]

                cursor = db.execute("""
                    SELECT COUNT(*) FROM session_logs
                    WHERE start_time >= ? AND start_time <= ?
                """, (start_time, end_time))
                total_sessions = cursor.fetchone()[0]

                cursor = db.execute("""
                    SELECT COUNT(*) FROM behavior_logs
                    WHERE timestamp >= ? AND timestamp <= ?
                """, (start_time, end_time))
                total_interactions = cursor.fetchone()[0]

                cursor = db.execute("""
                    SELECT action_type, COUNT(*) as count
                    FROM behavior_logs
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY action_type
                """, (start_time, end_time))
                action_counts_rows = cursor.fetchall()

                cursor = db.execute("""
                    SELECT AVG(
                        CASE
                            WHEN end_time IS NOT NULL
                            THEN (julianday(end_time) - julianday(start_time)) * 86400
                            ELSE NULL
                        END
                    ) FROM session_logs
                    WHERE start_time >= ? AND start_time <= ?
                """, (start_time, end_time))
                avg_duration_row = cursor.fetchone()
                avg_session_duration = avg_duration_row[0] or 0

                cursor = db.execute("""
                    SELECT COUNT(*) FROM behavior_logs
                    WHERE timestamp >= ? AND timestamp <= ?
                    AND error_message IS NOT NULL
                """, (start_time, end_time))
                error_count = cursor.fetchone()[0]

        action_counts = {row[0]: row[1] for row in action_counts_rows}

        return DailyStats(
            date=date,
            total_users=total_users,
            total_sessions=total_sessions,
            total_interactions=total_interactions,
            action_counts=action_counts,
            avg_session_duration=round(avg_session_duration, 2),
            error_count=error_count
        )

    async def get_popular_actions(
        self,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取热门行为

        Args:
            days: 统计天数
            limit: 最大返回数量

        Returns:
            List[Dict]: 热门行为列表
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        await self.initialize()

        query = """
            SELECT action_type, COUNT(*) as count
            FROM behavior_logs
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY action_type
            ORDER BY count DESC
            LIMIT ?
        """

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    query,
                    (start_date.isoformat(), end_date.isoformat(), limit)
                )
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    query,
                    (start_date.isoformat(), end_date.isoformat(), limit)
                )
                rows = cursor.fetchall()

        return [
            {"action_type": row[0], "count": row[1]}
            for row in rows
        ]

    async def get_error_logs(
        self,
        days: int = 7,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取错误日志

        Args:
            days: 查询天数
            limit: 最大返回数量

        Returns:
            List[Dict]: 错误日志列表
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        await self.initialize()

        query = """
            SELECT * FROM behavior_logs
            WHERE error_message IS NOT NULL
            AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT ?
        """

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    query,
                    (start_date.isoformat(), end_date.isoformat(), limit)
                )
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    query,
                    (start_date.isoformat(), end_date.isoformat(), limit)
                )
                rows = cursor.fetchall()

        return [
            {
                "log_id": row[0],
                "user_id": row[1],
                "session_id": row[2],
                "action_type": row[3],
                "intent": row[4],
                "error_message": row[8],
                "timestamp": row[9],
            }
            for row in rows
        ]

    # ========== 数据清理 ==========

    async def cleanup_old_logs(self, days: int = 90) -> int:
        """
        清理旧日志

        Args:
            days: 保留天数

        Returns:
            int: 删除的记录数
        """
        await self.initialize()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM behavior_logs WHERE timestamp < ?",
                    (cutoff_date,)
                )
                await db.commit()
                deleted_count = cursor.rowcount
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "DELETE FROM behavior_logs WHERE timestamp < ?",
                    (cutoff_date,)
                )
                db.commit()
                deleted_count = cursor.rowcount

        return deleted_count

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
                cursor = await db.execute("SELECT COUNT(*) FROM behavior_logs")
                total_logs = (await cursor.fetchone())[0]

                cursor = await db.execute("SELECT COUNT(*) FROM session_logs")
                total_sessions = (await cursor.fetchone())[0]

                cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM behavior_logs")
                total_users = (await cursor.fetchone())[0]
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("SELECT COUNT(*) FROM behavior_logs")
                total_logs = cursor.fetchone()[0]

                cursor = db.execute("SELECT COUNT(*) FROM session_logs")
                total_sessions = cursor.fetchone()[0]

                cursor = db.execute("SELECT COUNT(DISTINCT user_id) FROM behavior_logs")
                total_users = cursor.fetchone()[0]

        return {
            "total_logs": total_logs,
            "total_sessions": total_sessions,
            "total_users": total_users,
            "session_cache_size": len(self._session_cache),
        }


# ============================================================
# 全局服务实例
# ============================================================

_global_behavior_log_service: Optional[BehaviorLogService] = None


def get_behavior_log_service(
    db_path: str = "data/behavior_logs.db"
) -> BehaviorLogService:
    """获取全局行为日志服务"""
    global _global_behavior_log_service
    if _global_behavior_log_service is None:
        _global_behavior_log_service = BehaviorLogService(db_path)
    return _global_behavior_log_service


def reset_behavior_log_service():
    """重置全局行为日志服务"""
    global _global_behavior_log_service
    _global_behavior_log_service = None
