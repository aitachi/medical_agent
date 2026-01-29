# -*- coding: utf-8 -*-
"""
医疗智能助手 - 会话持久化存储
使用SQLite存储对话上下文和会话历史
"""

import json
import sqlite3
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

# 尝试导入aiosqlite
try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False

# 尝试导入agent模块中的DialogueContext
try:
    from agent.medical_agent import DialogueContext, IntentResult
    DIALOGUE_CONTEXT_AVAILABLE = True
except ImportError:
    DIALOGUE_CONTEXT_AVAILABLE = False

    # 定义简化版本
    @dataclass
    class IntentResult:
        intent: str
        confidence: float

    @dataclass
    class DialogueContext:
        session_id: str
        user_id: str
        history: List[Dict] = None
        current_intent: Optional[IntentResult] = None
        accumulated_entities: Dict[str, Any] = None
        metadata: Dict[str, Any] = None
        turn_count: int = 0
        start_time: str = None

        def __post_init__(self):
            if self.history is None:
                self.history = []
            if self.accumulated_entities is None:
                self.accumulated_entities = {}
            if self.metadata is None:
                self.metadata = {}
            if self.start_time is None:
                self.start_time = datetime.now().isoformat()


@dataclass
class SessionRecord:
    """会话记录"""
    session_id: str
    user_id: str
    created_at: str
    updated_at: str
    turn_count: int
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TurnRecord:
    """对话轮次记录"""
    id: Optional[int]
    session_id: str
    turn: int
    timestamp: str
    user_input: str
    agent_response: str
    intent: str
    confidence: float
    entities: Dict[str, Any] = None

    def __post_init__(self):
        if self.entities is None:
            self.entities = {}


class SessionStore:
    """
    会话存储
    提供会话持久化功能
    """

    def __init__(self, db_path: str = "data/sessions.db"):
        """
        初始化会话存储

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
            """CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                history TEXT,
                entities TEXT,
                current_intent TEXT,
                metadata TEXT,
                turn_count INTEGER DEFAULT 0,
                start_time TEXT,
                updated_at TEXT,
                expires_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                user_input TEXT NOT NULL,
                agent_response TEXT NOT NULL,
                intent TEXT,
                confidence REAL,
                entities TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
            )""",
            """CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id)""",
            """CREATE INDEX IF NOT EXISTS idx_turns_session_id ON turns (session_id)""",
            """CREATE INDEX IF NOT EXISTS idx_turns_timestamp ON turns (timestamp)""",
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
            # 同步版本
            self._initialize_sync()

        self._initialized = True

    def _initialize_sync(self):
        """同步初始化"""
        with sqlite3.connect(self.db_path) as db:
            for stmt in self._get_schema_statements():
                db.execute(stmt)
            db.commit()
        self._initialized = True

    async def save_session(self, context: DialogueContext, ttl: int = 86400):
        """
        保存会话

        Args:
            context: 对话上下文
            ttl: 会话生存时间（秒）
        """
        await self.initialize()

        # 序列化数据
        history_json = json.dumps(context.history, ensure_ascii=False)
        entities_json = json.dumps(context.accumulated_entities, ensure_ascii=False)
        metadata_json = json.dumps(context.metadata, ensure_ascii=False)

        # 序列化当前意图
        current_intent_json = None
        if context.current_intent:
            if hasattr(context.current_intent, 'intent'):
                intent_val = context.current_intent.intent
                if hasattr(intent_val, 'value'):
                    intent_val = intent_val.value
                current_intent_json = json.dumps({
                    'intent': intent_val,
                    'confidence': context.current_intent.confidence
                }, ensure_ascii=False)
            else:
                current_intent_json = json.dumps(context.current_intent, ensure_ascii=False)

        # 计算过期时间
        expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO sessions
                    (session_id, user_id, history, entities, current_intent, metadata, turn_count, start_time, updated_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    context.session_id,
                    context.user_id,
                    history_json,
                    entities_json,
                    current_intent_json,
                    metadata_json,
                    context.turn_count,
                    context.start_time,
                    datetime.now().isoformat(),
                    expires_at
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT OR REPLACE INTO sessions
                    (session_id, user_id, history, entities, current_intent, metadata, turn_count, start_time, updated_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    context.session_id,
                    context.user_id,
                    history_json,
                    entities_json,
                    current_intent_json,
                    metadata_json,
                    context.turn_count,
                    context.start_time,
                    datetime.now().isoformat(),
                    expires_at
                ))
                db.commit()

    async def load_session(self, session_id: str) -> Optional[DialogueContext]:
        """
        加载会话

        Args:
            session_id: 会话ID

        Returns:
            Optional[DialogueContext]: 对话上下文，如果不存在或已过期则返回None
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                cursor = await db.execute("""
                    SELECT * FROM sessions
                    WHERE session_id = ? AND (expires_at IS NULL OR expires_at > datetime('now'))
                """, (session_id,))
                row = await cursor.fetchone()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                cursor = db.execute("""
                    SELECT * FROM sessions
                    WHERE session_id = ? AND (expires_at IS NULL OR expires_at > datetime('now'))
                """, (session_id,))
                row = cursor.fetchone()

        if not row:
            return None

        # 反序列化数据
        history = json.loads(row['history']) if row['history'] else []
        entities = json.loads(row['entities']) if row['entities'] else {}
        metadata = json.loads(row['metadata']) if row['metadata'] else {}

        # 反序列化当前意图
        current_intent = None
        if row['current_intent']:
            intent_data = json.loads(row['current_intent'])
            current_intent = IntentResult(
                intent=intent_data.get('intent', 'unknown'),
                confidence=intent_data.get('confidence', 0.0)
            )

        # 创建上下文对象
        context = DialogueContext(
            session_id=row['session_id'],
            user_id=row['user_id'],
            history=history,
            current_intent=current_intent,
            accumulated_entities=entities,
            metadata=metadata,
            turn_count=row['turn_count'],
            start_time=row['start_time']
        )

        return context

    async def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否删除成功
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM sessions WHERE session_id = ?",
                    (session_id,)
                )
                await db.commit()
                return cursor.rowcount > 0
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "DELETE FROM sessions WHERE session_id = ?",
                    (session_id,)
                )
                db.commit()
                return cursor.rowcount > 0

    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 10,
        active_only: bool = False
    ) -> List[SessionRecord]:
        """
        获取用户的会话列表

        Args:
            user_id: 用户ID
            limit: 最大返回数量
            active_only: 是否只返回未过期的会话

        Returns:
            List[SessionRecord]: 会话记录列表
        """
        await self.initialize()

        if active_only:
            where_clause = "WHERE user_id = ? AND (expires_at IS NULL OR expires_at > datetime('now'))"
            params = (user_id,)
        else:
            where_clause = "WHERE user_id = ?"
            params = (user_id,)

        query = f"""
            SELECT session_id, user_id, turn_count, metadata, start_time, updated_at
            FROM sessions
            {where_clause}
            ORDER BY updated_at DESC
            LIMIT ?
        """

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                cursor = await db.execute(query, params + (limit,))
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                cursor = db.execute(query, params + (limit,))
                rows = cursor.fetchall()

        return [
            SessionRecord(
                session_id=row['session_id'],
                user_id=row['user_id'],
                created_at=row['start_time'],
                updated_at=row['updated_at'],
                turn_count=row['turn_count'],
                metadata=json.loads(row['metadata']) if row['metadata'] else {}
            )
            for row in rows
        ]

    async def get_session_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[TurnRecord]:
        """
        获取会话历史

        Args:
            session_id: 会话ID
            limit: 最大返回数量

        Returns:
            List[TurnRecord]: 对话轮次记录列表
        """
        await self.initialize()

        if limit:
            query = """
                SELECT * FROM turns
                WHERE session_id = ?
                ORDER BY turn ASC
                LIMIT ?
            """
            params = (session_id, limit)
        else:
            query = """
                SELECT * FROM turns
                WHERE session_id = ?
                ORDER BY turn ASC
            """
            params = (session_id,)

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                cursor = db.execute(query, params)
                rows = cursor.fetchall()

        return [
            TurnRecord(
                id=row['id'],
                session_id=row['session_id'],
                turn=row['turn'],
                timestamp=row['timestamp'],
                user_input=row['user_input'],
                agent_response=row['agent_response'],
                intent=row['intent'],
                confidence=row['confidence'],
                entities=json.loads(row['entities']) if row['entities'] else {}
            )
            for row in rows
        ]

    async def add_turn(
        self,
        session_id: str,
        turn: int,
        user_input: str,
        agent_response: str,
        intent: str,
        confidence: float,
        entities: Dict[str, Any] = None
    ):
        """
        添加对话轮次

        Args:
            session_id: 会话ID
            turn: 轮次号
            user_input: 用户输入
            agent_response: 助手响应
            intent: 意图
            confidence: 置信度
            entities: 实体
        """
        await self.initialize()

        entities_json = json.dumps(entities or {}, ensure_ascii=False)

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO turns
                    (session_id, turn, timestamp, user_input, agent_response, intent, confidence, entities)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    turn,
                    datetime.now().isoformat(),
                    user_input,
                    agent_response,
                    intent,
                    confidence,
                    entities_json
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT INTO turns
                    (session_id, turn, timestamp, user_input, agent_response, intent, confidence, entities)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    turn,
                    datetime.now().isoformat(),
                    user_input,
                    agent_response,
                    intent,
                    confidence,
                    entities_json
                ))
                db.commit()

    async def cleanup_expired(self, days: int = 7) -> int:
        """
        清理过期会话

        Args:
            days: 保留天数

        Returns:
            int: 清理的会话数
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    DELETE FROM sessions
                    WHERE expires_at < datetime('now', '-' || ? || ' days')
                """, (days,))
                await db.commit()
                return cursor.rowcount
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("""
                    DELETE FROM sessions
                    WHERE expires_at < datetime('now', '-' || ? || ' days')
                """, (days,))
                db.commit()
                return cursor.rowcount

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息

        Returns:
            Dict: 统计信息
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                # 会话总数
                cursor = await db.execute("SELECT COUNT(*) FROM sessions")
                total_sessions = (await cursor.fetchone())[0]

                # 活跃会话数
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM sessions
                    WHERE expires_at IS NULL OR expires_at > datetime('now')
                """)
                active_sessions = (await cursor.fetchone())[0]

                # 对话轮次总数
                cursor = await db.execute("SELECT COUNT(*) FROM turns")
                total_turns = (await cursor.fetchone())[0]

                # 数据库大小
                cursor = await db.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size = (await cursor.fetchone())[0]
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("SELECT COUNT(*) FROM sessions")
                total_sessions = cursor.fetchone()[0]

                cursor = db.execute("""
                    SELECT COUNT(*) FROM sessions
                    WHERE expires_at IS NULL OR expires_at > datetime('now')
                """)
                active_sessions = cursor.fetchone()[0]

                cursor = db.execute("SELECT COUNT(*) FROM turns")
                total_turns = cursor.fetchone()[0]

                cursor = db.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size = cursor.fetchone()[0]

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_turns": total_turns,
            "db_size_bytes": db_size,
        }


# ============================================================
# 全局会话存储实例
# ============================================================

_global_session_store: Optional[SessionStore] = None


def get_session_store(db_path: str = "data/sessions.db") -> SessionStore:
    """获取全局会话存储"""
    global _global_session_store
    if _global_session_store is None:
        _global_session_store = SessionStore(db_path)
    return _global_session_store


def reset_session_store():
    """重置全局会话存储"""
    global _global_session_store
    _global_session_store = None
