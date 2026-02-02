#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理器 - MySQL 数据访问层
"""

import pymysql
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器 - 单例模式"""

    _instance = None
    _config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '',
        'database': 'medical_agent',
        'charset': 'utf8mb4',
        'autocommit': False
    }

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

    @classmethod
    def configure(cls, config: Dict):
        """配置数据库连接"""
        cls._config.update(config)

    def connect(self):
        """建立数据库连接"""
        try:
            self._conn = pymysql.connect(**self._config)
            logger.info(f"[DB] 已连接到数据库 {self._config['database']}")
        except Exception as e:
            logger.error(f"[DB] 数据库连接失败: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("[DB] 数据库连接已关闭")

    def reconnect(self):
        """重新连接数据库"""
        self.close()
        self.connect()

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
        finally:
            cursor.close()

    # ============================================================
    # 会话管理
    # ============================================================

    def create_session(self, session_id: str, user_id: str = None, metadata: Dict = None) -> bool:
        """创建会话"""
        sql = """INSERT INTO sessions (session_id, user_id, metadata)
                 VALUES (%s, %s, %s)
                 ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP"""
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
        sql = "SELECT * FROM sessions WHERE session_id = %s"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (session_id,))
                result = cursor.fetchone()
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                return None
        except Exception as e:
            logger.error(f"[DB] 获取会话失败: {e}")
            return None

    def update_session(self, session_id: str, **kwargs) -> bool:
        """更新会话信息"""
        if not kwargs:
            return True

        set_clause = ", ".join([f"{k} = %s" for k in kwargs.keys()])
        sql = f"UPDATE sessions SET {set_clause} WHERE session_id = %s"

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
        sql = "DELETE FROM sessions WHERE session_id = %s"
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
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
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
                self.update_session(session_id, message_count=self.get_session_message_count(session_id))
            return True
        except Exception as e:
            logger.error(f"[DB] 添加消息失败: {e}")
            return False

    def get_session_messages(self, session_id: str, limit: int = 50) -> List[Dict]:
        """获取会话消息历史"""
        sql = """SELECT * FROM conversation_messages
                 WHERE session_id = %s
                 ORDER BY created_at ASC
                 LIMIT %s"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (session_id, limit))
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"[DB] 获取消息历史失败: {e}")
            return []

    def get_session_message_count(self, session_id: str) -> int:
        """获取会话消息数量"""
        sql = "SELECT COUNT(*) FROM conversation_messages WHERE session_id = %s"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (session_id,))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"[DB] 获取消息计数失败: {e}")
            return 0

    # ============================================================
    # 知识库查询
    # ============================================================

    def search_drugs(self, keyword: str, limit: int = 10) -> List[Dict]:
        """搜索药品"""
        sql = """SELECT * FROM drugs
                 WHERE generic_name LIKE %s
                    OR english_name LIKE %s
                    OR category LIKE %s
                 LIMIT %s"""
        try:
            with self.get_cursor() as cursor:
                like_pattern = f"%{keyword}%"
                cursor.execute(sql, (like_pattern, like_pattern, like_pattern, limit))
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"[DB] 搜索药品失败: {e}")
            return []

    def search_diseases(self, keyword: str, limit: int = 10) -> List[Dict]:
        """搜索疾病"""
        sql = """SELECT * FROM diseases
                 WHERE name LIKE %s
                    OR description LIKE %s
                 LIMIT %s"""
        try:
            with self.get_cursor() as cursor:
                like_pattern = f"%{keyword}%"
                cursor.execute(sql, (like_pattern, like_pattern, limit))
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"[DB] 搜索疾病失败: {e}")
            return []

    def search_symptoms(self, keyword: str, limit: int = 10) -> List[Dict]:
        """搜索症状"""
        sql = """SELECT * FROM symptoms
                 WHERE name LIKE %s
                    OR description LIKE %s
                 LIMIT %s"""
        try:
            with self.get_cursor() as cursor:
                like_pattern = f"%{keyword}%"
                cursor.execute(sql, (like_pattern, like_pattern, limit))
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"[DB] 搜索症状失败: {e}")
            return []

    def get_department_by_symptom(self, symptom_name: str) -> Optional[Dict]:
        """根据症状获取建议科室"""
        # 首先在症状表中查找
        sql = "SELECT department_hint FROM symptoms WHERE name = %s"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (symptom_name,))
                result = cursor.fetchone()
                if result and result[0]:
                    return {'hint': result[0]}
        except Exception as e:
            logger.error(f"[DB] 查询科室建议失败: {e}")

        # 如果症状表没有，在科室表中搜索
        sql = "SELECT * FROM departments WHERE common_symptoms LIKE %s LIMIT 1"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (f"%{symptom_name}%",))
                result = cursor.fetchone()
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
        except Exception as e:
            logger.error(f"[DB] 查询科室失败: {e}")

        return None

    def get_drug_interactions(self, drug_name: str) -> List[Dict]:
        """获取药物相互作用"""
        sql = """SELECT * FROM drug_interactions
                 WHERE drug_a = %s OR drug_b = %s"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (drug_name, drug_name))
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"[DB] 查询药物相互作用失败: {e}")
            return []

    # ============================================================
    # 系统配置
    # ============================================================

    def get_config(self, key: str, default: Any = None) -> Any:
        """获取系统配置"""
        sql = "SELECT config_value FROM system_config WHERE config_key = %s"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (key,))
                result = cursor.fetchone()
                if result:
                    value = result[0]
                    # 尝试解析为 JSON
                    try:
                        return json.loads(value)
                    except:
                        # 尝试转换为数字或布尔值
                        if value.isdigit():
                            return int(value)
                        if value.replace('.', '', 1).isdigit():
                            return float(value)
                        if value.lower() in ('true', 'false'):
                            return value.lower() == 'true'
                        return value
                return default
        except Exception as e:
            logger.error(f"[DB] 获取配置失败: {e}")
            return default

    def set_config(self, key: str, value: Any) -> bool:
        """设置系统配置"""
        sql = """INSERT INTO system_config (config_key, config_value)
                 VALUES (%s, %s)
                 ON DUPLICATE KEY UPDATE config_value = %s"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (key, json.dumps(value) if isinstance(value, (dict, list)) else str(value), json.dumps(value) if isinstance(value, (dict, list)) else str(value)))
            return True
        except Exception as e:
            logger.error(f"[DB] 设置配置失败: {e}")
            return False

    # ============================================================
    # API 日志
    # ============================================================

    def log_api_request(self, session_id: str, endpoint: str, method: str,
                       request_data: Dict = None, response_code: int = None,
                       response_time_ms: int = None, error_message: str = None,
                       ip_address: str = None, user_agent: str = None) -> bool:
        """记录 API 请求"""
        sql = """INSERT INTO api_logs
                 (session_id, endpoint, method, request_data, response_code,
                  response_time_ms, error_message, ip_address, user_agent)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (
                    session_id,
                    endpoint,
                    method,
                    json.dumps(request_data, ensure_ascii=False) if request_data else None,
                    response_code,
                    response_time_ms,
                    error_message,
                    ip_address,
                    user_agent
                ))
            return True
        except Exception as e:
            logger.error(f"[DB] 记录 API 日志失败: {e}")
            return False

    # ============================================================
    # 统计查询
    # ============================================================

    def get_statistics(self) -> Dict:
        """获取系统统计信息"""
        stats = {}

        tables = ['drugs', 'diseases', 'symptoms', 'departments',
                  'training_samples', 'sessions', 'conversation_messages']

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
