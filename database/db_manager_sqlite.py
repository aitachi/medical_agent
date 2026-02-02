#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理器 - SQLite 版本 (用于演示和开发)
"""

import sqlite3
import json
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器 - SQLite 版本"""

    _instance = None
    _db_path = '/root/medical_agent/data/medical_agent.db'

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化数据库管理器"""
        if self._initialized:
            return

        self._initialized = True
        self._conn = None
        self.connect()
        self._init_tables()

    @classmethod
    def configure(cls, db_path: str):
        """配置数据库路径"""
        cls._db_path = db_path

    def connect(self):
        """建立数据库连接"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row  # 返回字典格式
            logger.info(f"[DB] 已连接到 SQLite 数据库: {self._db_path}")
        except Exception as e:
            logger.error(f"[DB] 数据库连接失败: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("[DB] 数据库连接已关闭")

    def _init_tables(self):
        """初始化数据库表"""
        self._conn.execute('PRAGMA foreign_keys = ON')

        # 会话表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                user_id TEXT,
                status TEXT DEFAULT 'active',
                last_intent TEXT,
                metadata TEXT,
                message_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 对话消息表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_type TEXT NOT NULL,
                content TEXT NOT NULL,
                intent TEXT,
                confidence REAL,
                skill_invoked TEXT,
                entities TEXT,
                processing_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """)

        # 药品表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS drugs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generic_name TEXT NOT NULL UNIQUE,
                english_name TEXT,
                category TEXT,
                indications TEXT,
                contraindications TEXT,
                side_effects TEXT,
                dosage TEXT,
                interactions TEXT,
                warnings TEXT,
                common_allergens TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 疾病表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS diseases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT,
                description TEXT,
                symptoms TEXT,
                risk_factors TEXT,
                common_departments TEXT,
                prevention_advice TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 症状表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS symptoms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                body_part TEXT,
                description TEXT,
                common_diseases TEXT,
                severity TEXT,
                department_hint TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 科室表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                alias TEXT,
                description TEXT,
                common_diseases TEXT,
                common_symptoms TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 系统配置表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT NOT NULL UNIQUE,
                config_value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # API 日志表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS api_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                request_data TEXT,
                response_code INTEGER,
                response_time_ms INTEGER,
                error_message TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON conversation_messages(session_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_created ON api_logs(created_at)")

        self._conn.commit()
        logger.info("[DB] 数据库表初始化完成")

    @contextmanager
    def get_cursor(self):
        """获取数据库游标（上下文管理器）"""
        try:
            cursor = self._conn.cursor()
            yield cursor
            self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            logger.error(f"[DB] 数据库操作失败: {e}")
            raise

    # ============================================================
    # 会话管理
    # ============================================================

    def create_session(self, session_id: str, user_id: str = None, metadata: Dict = None) -> bool:
        """创建会话"""
        sql = """INSERT OR IGNORE INTO sessions (session_id, user_id, metadata)
                 VALUES (?, ?, ?)"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (
                    session_id,
                    user_id,
                    json.dumps(metadata, ensure_ascii=False) if metadata else None
                ))
            logger.debug(f"[DB] 创建会话: {session_id}")
            return True
        except Exception as e:
            logger.error(f"[DB] 创建会话失败: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        sql = "SELECT * FROM sessions WHERE session_id = ?"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (session_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"[DB] 获取会话失败: {e}")
            return None

    def update_session(self, session_id: str, **kwargs) -> bool:
        """更新会话信息"""
        if not kwargs:
            return True

        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        sql = f"UPDATE sessions SET {set_clause} WHERE session_id = ?"

        values = list(kwargs.values())
        if 'metadata' in values:
            idx = values.index('metadata')
            if isinstance(values[idx], dict):
                values[idx] = json.dumps(values[idx], ensure_ascii=False)

        values.append(session_id)

        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, values)
            return True
        except Exception as e:
            logger.error(f"[DB] 更新会话失败: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        sql = "DELETE FROM sessions WHERE session_id = ?"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (session_id,))
            logger.info(f"[DB] 删除会话: {session_id}")
            return True
        except Exception as e:
            logger.error(f"[DB] 删除会话失败: {e}")
            return False

    # ============================================================
    # 消息管理
    # ============================================================

    def add_message(self, session_id: str, message_type: str, content: str,
                    intent: str = None, confidence: float = None,
                    skill_invoked: str = None, entities: Dict = None,
                    processing_time_ms: int = None) -> bool:
        """添加消息"""
        sql = """INSERT INTO conversation_messages
                 (session_id, message_type, content, intent, confidence,
                  skill_invoked, entities, processing_time_ms)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (
                    session_id,
                    message_type,
                    content,
                    intent,
                    confidence,
                    skill_invoked,
                    json.dumps(entities, ensure_ascii=False) if entities else None,
                    processing_time_ms
                ))

                # 更新会话消息计数
                count = self.get_session_message_count(session_id)
                self.update_session(session_id, message_count=count)
            return True
        except Exception as e:
            logger.error(f"[DB] 添加消息失败: {e}")
            return False

    def get_session_messages(self, session_id: str, limit: int = 50) -> List[Dict]:
        """获取会话消息历史"""
        sql = """SELECT * FROM conversation_messages
                 WHERE session_id = ?
                 ORDER BY created_at ASC
                 LIMIT ?"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (session_id, limit))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"[DB] 获取消息历史失败: {e}")
            return []

    def get_session_message_count(self, session_id: str) -> int:
        """获取会话消息数量"""
        sql = "SELECT COUNT(*) FROM conversation_messages WHERE session_id = ?"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (session_id,))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"[DB] 获取消息计数失败: {e}")
            return 0

    # ============================================================
    # 知识库管理
    # ============================================================

    def bulk_insert_drugs(self, drugs_data: Dict) -> int:
        """批量插入药品数据"""
        sql = """INSERT OR IGNORE INTO drugs
                 (generic_name, english_name, category, indications, contraindications,
                  side_effects, dosage, interactions, warnings, common_allergens)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        count = 0
        try:
            with self.get_cursor() as cursor:
                for name, data in drugs_data.items():
                    cursor.execute(sql, (
                        name,
                        data.get('english_name'),
                        data.get('category'),
                        json.dumps(data.get('indications', []), ensure_ascii=False),
                        json.dumps(data.get('contraindications', []), ensure_ascii=False),
                        json.dumps(data.get('side_effects', []), ensure_ascii=False),
                        data.get('dosage'),
                        json.dumps(data.get('interactions', []), ensure_ascii=False),
                        data.get('warnings'),
                        json.dumps(data.get('common_allergens', []), ensure_ascii=False)
                    ))
                    count += 1
            return count
        except Exception as e:
            logger.error(f"[DB] 批量插入药品失败: {e}")
            return count

    def bulk_insert_diseases(self, diseases_data: Dict) -> int:
        """批量插入疾病数据"""
        sql = """INSERT OR IGNORE INTO diseases
                 (name, category, description, symptoms, risk_factors,
                  common_departments, prevention_advice)
                 VALUES (?, ?, ?, ?, ?, ?, ?)"""
        count = 0
        try:
            with self.get_cursor() as cursor:
                for name, data in diseases_data.items():
                    cursor.execute(sql, (
                        name,
                        data.get('category'),
                        data.get('description'),
                        json.dumps(data.get('symptoms', []), ensure_ascii=False),
                        json.dumps(data.get('risk_factors', []), ensure_ascii=False),
                        json.dumps(data.get('common_departments', []), ensure_ascii=False),
                        data.get('prevention_advice')
                    ))
                    count += 1
            return count
        except Exception as e:
            logger.error(f"[DB] 批量插入疾病失败: {e}")
            return count

    def bulk_insert_symptoms(self, symptoms_data: Dict) -> int:
        """批量插入症状数据"""
        sql = """INSERT OR IGNORE INTO symptoms
                 (name, body_part, description, common_diseases, severity, department_hint)
                 VALUES (?, ?, ?, ?, ?, ?)"""
        count = 0
        try:
            with self.get_cursor() as cursor:
                for name, data in symptoms_data.items():
                    cursor.execute(sql, (
                        name,
                        data.get('body_part'),
                        data.get('description'),
                        json.dumps(data.get('common_diseases', []), ensure_ascii=False),
                        data.get('severity'),
                        data.get('department_hint')
                    ))
                    count += 1
            return count
        except Exception as e:
            logger.error(f"[DB] 批量插入症状失败: {e}")
            return count

    def bulk_insert_departments(self, departments_data: Dict) -> int:
        """批量插入科室数据"""
        sql = """INSERT OR IGNORE INTO departments
                 (name, alias, description, common_diseases, common_symptoms)
                 VALUES (?, ?, ?, ?, ?)"""
        count = 0
        try:
            with self.get_cursor() as cursor:
                for name, data in departments_data.items():
                    cursor.execute(sql, (
                        name,
                        json.dumps(data.get('alias', []), ensure_ascii=False),
                        data.get('description'),
                        json.dumps(data.get('common_diseases', []), ensure_ascii=False),
                        json.dumps(data.get('common_symptoms', []), ensure_ascii=False)
                    ))
                    count += 1
            return count
        except Exception as e:
            logger.error(f"[DB] 批量插入科室失败: {e}")
            return count

    def search_drugs(self, keyword: str, limit: int = 10) -> List[Dict]:
        """搜索药品"""
        sql = """SELECT * FROM drugs
                 WHERE generic_name LIKE ?
                    OR english_name LIKE ?
                    OR category LIKE ?
                 LIMIT ?"""
        try:
            with self.get_cursor() as cursor:
                like_pattern = f"%{keyword}%"
                cursor.execute(sql, (like_pattern, like_pattern, like_pattern, limit))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"[DB] 搜索药品失败: {e}")
            return []

    def search_diseases(self, keyword: str, limit: int = 10) -> List[Dict]:
        """搜索疾病"""
        sql = """SELECT * FROM diseases
                 WHERE name LIKE ? OR description LIKE ?
                 LIMIT ?"""
        try:
            with self.get_cursor() as cursor:
                like_pattern = f"%{keyword}%"
                cursor.execute(sql, (like_pattern, like_pattern, limit))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"[DB] 搜索疾病失败: {e}")
            return []

    # ============================================================
    # 系统配置
    # ============================================================

    def get_config(self, key: str, default: Any = None) -> Any:
        """获取系统配置"""
        sql = "SELECT config_value FROM system_config WHERE config_key = ?"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (key,))
                row = cursor.fetchone()
                if row:
                    value = row[0]
                    try:
                        return json.loads(value)
                    except:
                        return value
                return default
        except Exception as e:
            logger.error(f"[DB] 获取配置失败: {e}")
            return default

    def set_config(self, key: str, value: Any) -> bool:
        """设置系统配置"""
        sql = """INSERT OR REPLACE INTO system_config (config_key, config_value)
                 VALUES (?, ?)"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (key, json.dumps(value) if isinstance(value, (dict, list)) else str(value)))
            return True
        except Exception as e:
            logger.error(f"[DB] 设置配置失败: {e}")
            return False

    # ============================================================
    # 统计查询
    # ============================================================

    def get_statistics(self) -> Dict:
        """获取系统统计信息"""
        stats = {}
        tables = ['drugs', 'diseases', 'symptoms', 'departments', 'sessions', 'conversation_messages']

        for table in tables:
            sql = f"SELECT COUNT(*) FROM {table}"
            try:
                with self.get_cursor() as cursor:
                    cursor.execute(sql)
                    stats[table] = cursor.fetchone()[0]
            except Exception as e:
                logger.error(f"[DB] 获取 {table} 统计失败: {e}")
                stats[table] = 0

        return stats


# 全局数据库管理器实例
db_manager = DatabaseManager()


def get_db() -> DatabaseManager:
    """获取数据库管理器实例"""
    return db_manager
