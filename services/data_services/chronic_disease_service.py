# -*- coding: utf-8 -*-
"""
医疗智能助手 - 慢病数据服务
提供慢病监测数据和趋势分析
"""

import json
import sqlite3
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
import statistics

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False


class DiseaseType(Enum):
    """慢病类型枚举"""
    HYPERTENSION = "hypertension"  # 高血压
    DIABETES = "diabetes"  # 糖尿病
    HYPERLIPIDEMIA = "hyperlipidemia"  # 高血脂
    CORONARY_DISEASE = "coronary_disease"  # 冠心病
    COPD = "copd"  # 慢阻肺
    STROKE = "stroke"  # 脑卒中
    CHRONIC_KIDNEY = "chronic_kidney"  # 慢性肾病
    OTHER = "other"


class RecordStatus(Enum):
    """记录状态"""
    NORMAL = "normal"  # 正常
    ELEVATED = "elevated"  # 偏高
    HIGH = "high"  # 高
    CRITICAL = "critical"  # 危险
    LOW = "low"  # 偏低


@dataclass
class ChronicRecord:
    """慢病监测记录"""
    record_id: str
    user_id: str
    disease_type: str
    measure_data: Dict[str, Any]
    measure_time: str
    status: str = "normal"
    note: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "record_id": self.record_id,
            "user_id": self.user_id,
            "disease_type": self.disease_type,
            "measure_data": self.measure_data,
            "measure_time": self.measure_time,
            "status": self.status,
            "note": self.note,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChronicRecord":
        """从字典创建"""
        return cls(**data)


@dataclass
class TrendAnalysis:
    """趋势分析结果"""
    trend: str  # rising, falling, stable, fluctuating
    change_percent: float
    avg_value: float
    min_value: float
    max_value: float
    latest_value: float
    recommendation: str


@dataclass
class DiseaseConfig:
    """疾病配置"""
    disease_type: str
    display_name: str
    measure_fields: List[str]
    normal_ranges: Dict[str, Dict[str, float]]
    alert_thresholds: Dict[str, Dict[str, float]]
    measure_frequency: str  # daily, weekly, monthly
    advice_templates: Dict[str, List[str]]


# 疾病配置
DISEASE_CONFIGS: Dict[str, DiseaseConfig] = {
    "hypertension": DiseaseConfig(
        disease_type="hypertension",
        display_name="高血压",
        measure_fields=["systolic", "diastolic", "heart_rate"],
        normal_ranges={
            "systolic": {"min": 90, "max": 140},
            "diastolic": {"min": 60, "max": 90},
            "heart_rate": {"min": 60, "max": 100}
        },
        alert_thresholds={
            "systolic": {"high": 160, "critical": 180, "low": 90},
            "diastolic": {"high": 100, "critical": 110, "low": 60},
            "heart_rate": {"high": 110, "critical": 130, "low": 50}
        },
        measure_frequency="daily",
        advice_templates={
            "normal": [
                "血压控制良好，请继续保持",
                "坚持规律测量血压",
                "保持健康的生活方式"
            ],
            "elevated": [
                "血压略偏高，请注意休息",
                "建议低盐饮食，每日食盐<6g",
                "规律作息，避免熬夜"
            ],
            "high": [
                "血压偏高，建议就医咨询",
                "按时服药，不要擅自停药",
                "注意监测血压变化"
            ],
            "critical": [
                "血压过高，请立即就医",
                "如有头晕、头痛等症状，拨打120",
                "停止剧烈活动，静卧休息"
            ]
        }
    ),
    "diabetes": DiseaseConfig(
        disease_type="diabetes",
        display_name="糖尿病",
        measure_fields=["fpg", "ppg", "hba1c"],  # 空腹血糖、餐后血糖、糖化血红蛋白
        normal_ranges={
            "fpg": {"min": 3.9, "max": 6.1},
            "ppg": {"min": 4.4, "max": 7.8},
            "hba1c": {"min": 4.0, "max": 6.0}
        },
        alert_thresholds={
            "fpg": {"high": 7.0, "critical": 11.1, "low": 3.9},
            "ppg": {"high": 11.1, "critical": 16.7, "low": 3.9},
            "hba1c": {"high": 6.5, "critical": 8.0, "low": 4.0}
        },
        measure_frequency="daily",
        advice_templates={
            "normal": [
                "血糖控制良好，请继续保持",
                "坚持规律饮食和运动",
                "定期检测糖化血红蛋白"
            ],
            "elevated": [
                "血糖略偏高，注意饮食控制",
                "减少碳水化合物摄入",
                "增加适量运动"
            ],
            "high": [
                "血糖偏高，建议就医调整用药",
                "严格控制饮食",
                "按时监测血糖"
            ],
            "critical": [
                "血糖过高，请立即就医",
                "如出现口渴、多尿等症状，及时就诊",
                "注意预防酮症酸中毒"
            ]
        }
    ),
    "hyperlipidemia": DiseaseConfig(
        disease_type="hyperlipidemia",
        display_name="高血脂",
        measure_fields=["tc", "tg", "ldl", "hdl"],  # 总胆固醇、甘油三酯、低密度、高密度
        normal_ranges={
            "tc": {"min": 0, "max": 5.2},
            "tg": {"min": 0, "max": 1.7},
            "ldl": {"min": 0, "max": 3.4},
            "hdl": {"min": 1.0, "max": 2.0}
        },
        alert_thresholds={
            "tc": {"high": 6.2, "critical": 7.0, "low": 0},
            "tg": {"high": 2.3, "critical": 5.6, "low": 0},
            "ldl": {"high": 4.1, "critical": 4.9, "low": 0},
            "hdl": {"high": 2.0, "critical": 2.5, "low": 0.8}
        },
        measure_frequency="weekly",
        advice_templates={
            "normal": [
                "血脂控制良好，请继续保持",
                "坚持低脂饮食",
                "保持适量运动"
            ],
            "elevated": [
                "血脂略偏高，注意饮食",
                "减少高脂肪食物摄入",
                "增加有氧运动"
            ],
            "high": [
                "血脂偏高，建议就医",
                "严格控制饮食",
                "遵医嘱服药"
            ],
            "critical": [
                "血脂过高，请及时就医",
                "避免高脂高胆固醇食物",
                "按医嘱调整治疗方案"
            ]
        }
    ),
}


class ChronicDiseaseService:
    """
    慢病数据服务
    提供慢病监测数据和趋势分析
    """

    def __init__(self, db_path: str = "data/chronic_disease.db"):
        """
        初始化慢病数据服务

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._initialized = False
        self._cache: Dict[str, List[ChronicRecord]] = {}

        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_schema_statements(self) -> List[str]:
        """获取数据库表结构SQL语句"""
        return [
            """CREATE TABLE IF NOT EXISTS chronic_records (
                record_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                disease_type TEXT NOT NULL,
                measure_data TEXT NOT NULL,
                measure_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'normal',
                note TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, disease_type, measure_time)
            )""",
            """CREATE INDEX IF NOT EXISTS idx_chronic_records_user_id
                ON chronic_records (user_id)""",
            """CREATE INDEX IF NOT EXISTS idx_chronic_records_user_disease
                ON chronic_records (user_id, disease_type)""",
            """CREATE INDEX IF NOT EXISTS idx_chronic_records_measure_time
                ON chronic_records (measure_time)""",
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

    def _generate_record_id(self) -> str:
        """生成记录ID"""
        return f"CR{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _evaluate_status(
        self,
        disease_type: str,
        measure_data: Dict[str, Any]
    ) -> str:
        """评估测量数据状态"""
        config = DISEASE_CONFIGS.get(disease_type)
        if not config:
            return "normal"

        status = "normal"
        for field, value in measure_data.items():
            if field not in config.alert_thresholds:
                continue

            thresholds = config.alert_thresholds[field]
            if value >= thresholds.get("critical", float("inf")):
                return "critical"
            if value >= thresholds.get("high", float("inf")):
                status = "high"
            elif value >= thresholds.get("elevated", float("inf")):
                if status != "high":
                    status = "elevated"
            elif value <= thresholds.get("low", float("-inf")):
                status = "low"

        return status

    async def _save_record(self, record: ChronicRecord) -> None:
        """保存记录到数据库"""
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO chronic_records
                    (record_id, user_id, disease_type, measure_data,
                     measure_time, status, note, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.record_id,
                    record.user_id,
                    record.disease_type,
                    json.dumps(record.measure_data, ensure_ascii=False),
                    record.measure_time,
                    record.status,
                    record.note,
                    record.created_at
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT OR REPLACE INTO chronic_records
                    (record_id, user_id, disease_type, measure_data,
                     measure_time, status, note, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.record_id,
                    record.user_id,
                    record.disease_type,
                    json.dumps(record.measure_data, ensure_ascii=False),
                    record.measure_time,
                    record.status,
                    record.note,
                    record.created_at
                ))
                db.commit()

    def _load_from_row(self, row: tuple) -> ChronicRecord:
        """从数据库行加载记录"""
        return ChronicRecord(
            record_id=row[0],
            user_id=row[1],
            disease_type=row[2],
            measure_data=json.loads(row[3]) if row[3] else {},
            measure_time=row[4],
            status=row[5],
            note=row[6],
            created_at=row[7]
        )

    # ========== CRUD 操作 ==========

    async def add_record(
        self,
        user_id: str,
        disease_type: str,
        measure_data: Dict[str, Any],
        measure_time: Optional[str] = None,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        添加慢病监测记录

        Args:
            user_id: 用户ID
            disease_type: 疾病类型
            measure_data: 测量数据
            measure_time: 测量时间
            note: 备注

        Returns:
            Dict: 记录数据
        """
        await self.initialize()

        if measure_time is None:
            measure_time = datetime.now().isoformat()

        # 评估状态
        status = self._evaluate_status(disease_type, measure_data)

        record = ChronicRecord(
            record_id=self._generate_record_id(),
            user_id=user_id,
            disease_type=disease_type,
            measure_data=measure_data,
            measure_time=measure_time,
            status=status,
            note=note
        )

        await self._save_record(record)

        # 更新缓存
        cache_key = f"{user_id}:{disease_type}"
        if cache_key not in self._cache:
            self._cache[cache_key] = []
        self._cache[cache_key].append(record)

        return record.to_dict()

    async def get_records(
        self,
        user_id: str,
        disease_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取慢病监测记录

        Args:
            user_id: 用户ID
            disease_type: 疾病类型（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            limit: 最大返回数量

        Returns:
            List[Dict]: 记录列表
        """
        await self.initialize()

        query = "SELECT * FROM chronic_records WHERE user_id = ?"
        params = [user_id]

        if disease_type:
            query += " AND disease_type = ?"
            params.append(disease_type)

        if start_date:
            query += " AND measure_time >= ?"
            params.append(start_date)

        if end_date:
            query += " AND measure_time <= ?"
            params.append(end_date)

        query += " ORDER BY measure_time DESC LIMIT ?"
        params.append(limit)

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(query, params)
                rows = cursor.fetchall()

        return [self._load_from_row(row).to_dict() for row in rows]

    async def get_latest_record(
        self,
        user_id: str,
        disease_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取最新记录

        Args:
            user_id: 用户ID
            disease_type: 疾病类型

        Returns:
            Optional[Dict]: 最新记录，如果不存在返回None
        """
        records = await self.get_records(user_id, disease_type, limit=1)
        return records[0] if records else None

    async def delete_record(self, record_id: str) -> bool:
        """
        删除记录

        Args:
            record_id: 记录ID

        Returns:
            bool: 是否删除成功
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM chronic_records WHERE record_id = ?",
                    (record_id,)
                )
                await db.commit()
                return cursor.rowcount > 0
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "DELETE FROM chronic_records WHERE record_id = ?",
                    (record_id,)
                )
                db.commit()
                return cursor.rowcount > 0

    # ========== 趋势分析 ==========

    async def analyze_trend(
        self,
        user_id: str,
        disease_type: str,
        field: str,
        days: int = 7
    ) -> Optional[TrendAnalysis]:
        """
        分析数据趋势

        Args:
            user_id: 用户ID
            disease_type: 疾病类型
            field: 分析字段
            days: 分析天数

        Returns:
            Optional[TrendAnalysis]: 趋势分析结果
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        records = await self.get_records(
            user_id,
            disease_type,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            limit=days * 10
        )

        if not records:
            return None

        # 提取指定字段的值
        values = []
        for record in reversed(records):  # 按时间正序
            value = record["measure_data"].get(field)
            if value is not None and isinstance(value, (int, float)):
                values.append(value)

        if len(values) < 2:
            return None

        # 计算统计数据
        avg_value = statistics.mean(values)
        min_value = min(values)
        max_value = max(values)
        latest_value = values[-1]
        first_value = values[0]

        # 计算变化百分比
        if first_value != 0:
            change_percent = ((latest_value - first_value) / first_value) * 100
        else:
            change_percent = 0

        # 判断趋势
        if change_percent > 10:
            trend = "rising"
        elif change_percent < -10:
            trend = "falling"
        elif max_value - min_value > avg_value * 0.2:
            trend = "fluctuating"
        else:
            trend = "stable"

        # 生成建议
        config = DISEASE_CONFIGS.get(disease_type)
        latest_record = await self.get_latest_record(user_id, disease_type)
        status = latest_record["status"] if latest_record else "normal"

        if config:
            recommendation = config.advice_templates.get(status, ["请继续监测"])[0]
        else:
            recommendation = "请继续监测"

        return TrendAnalysis(
            trend=trend,
            change_percent=round(change_percent, 2),
            avg_value=round(avg_value, 2),
            min_value=round(min_value, 2),
            max_value=round(max_value, 2),
            latest_value=round(latest_value, 2),
            recommendation=recommendation
        )

    async def get_analysis_summary(
        self,
        user_id: str,
        disease_type: str
    ) -> Dict[str, Any]:
        """
        获取分析摘要

        Args:
            user_id: 用户ID
            disease_type: 疾病类型

        Returns:
            Dict: 分析摘要
        """
        config = DISEASE_CONFIGS.get(disease_type)
        if not config:
            return {}

        latest_record = await self.get_latest_record(user_id, disease_type)
        if not latest_record:
            return {
                "disease_type": disease_type,
                "display_name": disease_type,
                "status": "no_data",
                "message": "暂无监测数据"
            }

        # 获取趋势分析
        trend_analyses = {}
        for field in config.measure_fields:
            trend = await self.analyze_trend(user_id, disease_type, field)
            if trend:
                trend_analyses[field] = {
                    "trend": trend.trend,
                    "latest_value": trend.latest_value,
                    "change_percent": trend.change_percent,
                    "recommendation": trend.recommendation
                }

        return {
            "disease_type": disease_type,
            "display_name": config.display_name,
            "latest_record": latest_record,
            "trend_analyses": trend_analyses,
            "overall_status": latest_record["status"],
            "measure_frequency": config.measure_frequency
        }

    # ========== 疾病管理 ==========

    async def get_user_diseases(self, user_id: str) -> List[str]:
        """
        获取用户监测的疾病列表

        Args:
            user_id: 用户ID

        Returns:
            List[str]: 疾病类型列表
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT DISTINCT disease_type FROM chronic_records WHERE user_id = ?",
                    (user_id,)
                )
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT DISTINCT disease_type FROM chronic_records WHERE user_id = ?",
                    (user_id,)
                )
                rows = cursor.fetchall()

        return [row[0] for row in rows]

    async def get_disease_config(self, disease_type: str) -> Optional[DiseaseConfig]:
        """
        获取疾病配置

        Args:
            disease_type: 疾病类型

        Returns:
            Optional[DiseaseConfig]: 疾病配置
        """
        return DISEASE_CONFIGS.get(disease_type)

    def get_all_disease_configs(self) -> Dict[str, DiseaseConfig]:
        """获取所有疾病配置"""
        return DISEASE_CONFIGS

    # ========== 数据导出 ==========

    async def export_records(
        self,
        user_id: str,
        disease_type: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        导出记录

        Args:
            user_id: 用户ID
            disease_type: 疾病类型
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[Dict]: 记录列表
        """
        return await self.get_records(
            user_id,
            disease_type,
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )

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
                cursor = await db.execute("SELECT COUNT(*) FROM chronic_records")
                total_records = (await cursor.fetchone())[0]

                cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM chronic_records")
                total_users = (await cursor.fetchone())[0]

                cursor = await db.execute("""
                    SELECT disease_type, COUNT(*) as count
                    FROM chronic_records
                    GROUP BY disease_type
                """)
                disease_counts = {row[0]: row[1] for row in await cursor.fetchall()}
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("SELECT COUNT(*) FROM chronic_records")
                total_records = cursor.fetchone()[0]

                cursor = db.execute("SELECT COUNT(DISTINCT user_id) FROM chronic_records")
                total_users = cursor.fetchone()[0]

                cursor = db.execute("""
                    SELECT disease_type, COUNT(*) as count
                    FROM chronic_records
                    GROUP BY disease_type
                """)
                disease_counts = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_records": total_records,
            "total_users": total_users,
            "disease_counts": disease_counts,
            "cache_size": len(self._cache),
        }

    async def get_abnormal_records(
        self,
        user_id: str,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        获取异常记录

        Args:
            user_id: 用户ID
            days: 查询天数

        Returns:
            List[Dict]: 异常记录列表
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        await self.initialize()

        query = """
            SELECT * FROM chronic_records
            WHERE user_id = ? AND measure_time >= ? AND measure_time <= ?
            AND status != 'normal'
            ORDER BY measure_time DESC
        """

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    query,
                    (user_id, start_date.isoformat(), end_date.isoformat())
                )
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    query,
                    (user_id, start_date.isoformat(), end_date.isoformat())
                )
                rows = cursor.fetchall()

        return [self._load_from_row(row).to_dict() for row in rows]


# ============================================================
# 全局服务实例
# ============================================================

_global_chronic_disease_service: Optional[ChronicDiseaseService] = None


def get_chronic_disease_service(
    db_path: str = "data/chronic_disease.db"
) -> ChronicDiseaseService:
    """获取全局慢病数据服务"""
    global _global_chronic_disease_service
    if _global_chronic_disease_service is None:
        _global_chronic_disease_service = ChronicDiseaseService(db_path)
    return _global_chronic_disease_service


def reset_chronic_disease_service():
    """重置全局慢病数据服务"""
    global _global_chronic_disease_service
    _global_chronic_disease_service = None
