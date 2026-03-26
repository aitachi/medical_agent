# -*- coding: utf-8 -*-
"""
医疗智能助手 - 健康档案数据服务
提供用户健康档案数据，包括病史、过敏史、手术史等
"""

import json
import sqlite3
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from enum import Enum

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False


class RecordType(Enum):
    """记录类型枚举"""
    BASIC_INFO = "basic_info"
    MEDICAL_HISTORY = "medical_history"
    SURGERY_HISTORY = "surgery_history"
    HOSPITALIZATION = "hospitalization"
    ALLERGY = "allergy"
    MEDICATION = "medication"
    FAMILY_HISTORY = "family_history"
    CHECKUP = "checkup"
    REPORT = "report"


@dataclass
class BasicHealthInfo:
    """基础健康信息"""
    blood_type: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    bmi: Optional[float] = None
    rh_factor: Optional[str] = None


@dataclass
class MedicalHistory:
    """病史记录"""
    disease_name: str
    diagnosis_date: Optional[str] = None
    status: str = "active"  # active, recovered, chronic
    description: Optional[str] = None
    hospital: Optional[str] = None
    doctor: Optional[str] = None


@dataclass
class SurgeryHistory:
    """手术史记录"""
    surgery_name: str
    surgery_date: Optional[str] = None
    hospital: Optional[str] = None
    doctor: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Hospitalization:
    """住院记录"""
    reason: str
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    hospital: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Allergy:
    """过敏记录"""
    allergen: str
    allergy_type: str  # drug, food, other
    reaction: Optional[str] = None
    severity: str = "moderate"  # mild, moderate, severe
    diagnosed_date: Optional[str] = None


@dataclass
class Medication:
    """用药记录"""
    drug_name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str = "active"  # active, completed, discontinued
    prescribed_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class FamilyHistory:
    """家族病史"""
    relationship: str  # father, mother, grandfather, grandmother, etc.
    disease: str
    status: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class CheckupRecord:
    """体检记录"""
    checkup_date: str
    checkup_type: Optional[str] = None
    hospital: Optional[str] = None
    summary: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)
    abnormal_indicators: List[str] = field(default_factory=list)


@dataclass
class LabReport:
    """检查报告记录"""
    report_date: str
    report_type: str  # blood_test, urine_test, imaging, etc.
    hospital: Optional[str] = None
    items: Dict[str, Any] = field(default_factory=dict)
    abnormal_items: List[str] = field(default_factory=list)
    report_url: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class HealthRecord:
    """健康档案"""
    user_id: str
    basic_info: Dict[str, Any] = field(default_factory=dict)
    medical_history: List[Dict[str, Any]] = field(default_factory=list)
    surgery_history: List[Dict[str, Any]] = field(default_factory=list)
    hospitalizations: List[Dict[str, Any]] = field(default_factory=list)
    allergies: List[Dict[str, Any]] = field(default_factory=list)
    current_medications: List[Dict[str, Any]] = field(default_factory=list)
    past_medications: List[Dict[str, Any]] = field(default_factory=list)
    family_history: List[Dict[str, Any]] = field(default_factory=list)
    checkups: List[Dict[str, Any]] = field(default_factory=list)
    lab_reports: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "basic_info": self.basic_info,
            "medical_history": self.medical_history,
            "surgery_history": self.surgery_history,
            "hospitalizations": self.hospitalizations,
            "allergies": self.allergies,
            "current_medications": self.current_medications,
            "past_medications": self.past_medications,
            "family_history": self.family_history,
            "checkups": self.checkups,
            "lab_reports": self.lab_reports,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HealthRecord":
        """从字典创建"""
        return cls(**data)


class HealthRecordsService:
    """
    健康档案数据服务
    提供用户健康档案数据，包括病史、过敏史、手术史等
    """

    def __init__(self, db_path: str = "data/health_records.db"):
        """
        初始化健康档案服务

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._initialized = False
        self._cache: Dict[str, HealthRecord] = {}

        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_schema_statements(self) -> List[str]:
        """获取数据库表结构SQL语句"""
        return [
            """CREATE TABLE IF NOT EXISTS health_records (
                user_id TEXT PRIMARY KEY,
                basic_info TEXT NOT NULL DEFAULT '{}',
                medical_history TEXT NOT NULL DEFAULT '[]',
                surgery_history TEXT NOT NULL DEFAULT '[]',
                hospitalizations TEXT NOT NULL DEFAULT '[]',
                allergies TEXT NOT NULL DEFAULT '[]',
                current_medications TEXT NOT NULL DEFAULT '[]',
                past_medications TEXT NOT NULL DEFAULT '[]',
                family_history TEXT NOT NULL DEFAULT '[]',
                checkups TEXT NOT NULL DEFAULT '[]',
                lab_reports TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            """CREATE INDEX IF NOT EXISTS idx_health_records_medical_history
                ON health_records (user_id)""",
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

    async def _save_record(self, record: HealthRecord) -> None:
        """保存健康档案到数据库"""
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO health_records
                    (user_id, basic_info, medical_history, surgery_history,
                     hospitalizations, allergies, current_medications,
                     past_medications, family_history, checkups, lab_reports,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.user_id,
                    json.dumps(record.basic_info, ensure_ascii=False),
                    json.dumps(record.medical_history, ensure_ascii=False),
                    json.dumps(record.surgery_history, ensure_ascii=False),
                    json.dumps(record.hospitalizations, ensure_ascii=False),
                    json.dumps(record.allergies, ensure_ascii=False),
                    json.dumps(record.current_medications, ensure_ascii=False),
                    json.dumps(record.past_medications, ensure_ascii=False),
                    json.dumps(record.family_history, ensure_ascii=False),
                    json.dumps(record.checkups, ensure_ascii=False),
                    json.dumps(record.lab_reports, ensure_ascii=False),
                    record.created_at,
                    record.updated_at
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT OR REPLACE INTO health_records
                    (user_id, basic_info, medical_history, surgery_history,
                     hospitalizations, allergies, current_medications,
                     past_medications, family_history, checkups, lab_reports,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.user_id,
                    json.dumps(record.basic_info, ensure_ascii=False),
                    json.dumps(record.medical_history, ensure_ascii=False),
                    json.dumps(record.surgery_history, ensure_ascii=False),
                    json.dumps(record.hospitalizations, ensure_ascii=False),
                    json.dumps(record.allergies, ensure_ascii=False),
                    json.dumps(record.current_medications, ensure_ascii=False),
                    json.dumps(record.past_medications, ensure_ascii=False),
                    json.dumps(record.family_history, ensure_ascii=False),
                    json.dumps(record.checkups, ensure_ascii=False),
                    json.dumps(record.lab_reports, ensure_ascii=False),
                    record.created_at,
                    record.updated_at
                ))
                db.commit()

    def _load_from_row(self, row: tuple) -> Dict[str, Any]:
        """从数据库行加载健康档案"""
        return {
            "user_id": row[0],
            "basic_info": json.loads(row[1]) if row[1] else {},
            "medical_history": json.loads(row[2]) if row[2] else [],
            "surgery_history": json.loads(row[3]) if row[3] else [],
            "hospitalizations": json.loads(row[4]) if row[4] else [],
            "allergies": json.loads(row[5]) if row[5] else [],
            "current_medications": json.loads(row[6]) if row[6] else [],
            "past_medications": json.loads(row[7]) if row[7] else [],
            "family_history": json.loads(row[8]) if row[8] else [],
            "checkups": json.loads(row[9]) if row[9] else [],
            "lab_reports": json.loads(row[10]) if row[10] else [],
            "created_at": row[11],
            "updated_at": row[12],
        }

    # ========== CRUD 操作 ==========

    async def get_record(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取健康档案

        Args:
            user_id: 用户ID

        Returns:
            Dict: 健康档案数据，如果不存在返回None
        """
        await self.initialize()

        # 先检查缓存
        if user_id in self._cache:
            return self._cache[user_id].to_dict()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM health_records WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT * FROM health_records WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()

        if not row:
            return None

        record_dict = self._load_from_row(row)
        self._cache[user_id] = HealthRecord.from_dict(record_dict)

        return record_dict

    async def create_record(self, user_id: str) -> Dict[str, Any]:
        """
        创建健康档案

        Args:
            user_id: 用户ID

        Returns:
            Dict: 创建的健康档案
        """
        await self.initialize()

        now = datetime.now().isoformat()
        record = HealthRecord(user_id=user_id, created_at=now, updated_at=now)

        await self._save_record(record)
        self._cache[user_id] = record

        return record.to_dict()

    async def get_or_create_record(self, user_id: str) -> Dict[str, Any]:
        """
        获取或创建健康档案

        Args:
            user_id: 用户ID

        Returns:
            Dict: 健康档案数据
        """
        record = await self.get_record(user_id)
        if not record:
            record = await self.create_record(user_id)
        return record

    async def update_record(
        self,
        user_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        更新健康档案

        Args:
            user_id: 用户ID
            data: 更新数据

        Returns:
            bool: 是否更新成功
        """
        record = await self.get_record(user_id)
        if not record:
            return False

        # 更新基础信息
        if "basic_info" in data:
            record["basic_info"].update(data["basic_info"])

        # 计算BMI
        if "height" in record["basic_info"] and "weight" in record["basic_info"]:
            height_m = record["basic_info"]["height"] / 100 if record["basic_info"]["height"] else 0
            weight = record["basic_info"]["weight"] or 0
            if height_m > 0 and weight > 0:
                record["basic_info"]["bmi"] = round(weight / (height_m ** 2), 2)

        record["updated_at"] = datetime.now().isoformat()

        await self._save_record(HealthRecord.from_dict(record))

        # 更新缓存
        if user_id in self._cache:
            self._cache[user_id] = HealthRecord.from_dict(record)

        return True

    async def delete_record(self, user_id: str) -> bool:
        """
        删除健康档案

        Args:
            user_id: 用户ID

        Returns:
            bool: 是否删除成功
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM health_records WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()
                deleted = cursor.rowcount > 0
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "DELETE FROM health_records WHERE user_id = ?",
                    (user_id,)
                )
                db.commit()
                deleted = cursor.rowcount > 0

        if deleted and user_id in self._cache:
            del self._cache[user_id]

        return deleted

    # ========== 基础信息操作 ==========

    async def get_basic_info(self, user_id: str) -> Dict[str, Any]:
        """获取基础健康信息"""
        record = await self.get_record(user_id)
        return record["basic_info"] if record else {}

    async def update_basic_info(
        self,
        user_id: str,
        info: Dict[str, Any]
    ) -> bool:
        """更新基础健康信息"""
        record = await self.get_record(user_id)
        if not record:
            record = await self.create_record(user_id)

        record["basic_info"].update(info)

        # 自动计算BMI
        if "height" in info and "weight" in info:
            height_m = info["height"] / 100 if info["height"] else 0
            weight = info["weight"] or 0
            if height_m > 0 and weight > 0:
                record["basic_info"]["bmi"] = round(weight / (height_m ** 2), 2)

        record["updated_at"] = datetime.now().isoformat()

        await self._save_record(HealthRecord.from_dict(record))

        if user_id in self._cache:
            self._cache[user_id] = HealthRecord.from_dict(record)

        return True

    # ========== 病史操作 ==========

    async def get_medical_history(self, user_id: str) -> List[Dict[str, Any]]:
        """获取病史列表"""
        record = await self.get_record(user_id)
        return record["medical_history"] if record else []

    async def add_medical_history(
        self,
        user_id: str,
        disease: str,
        diagnosis_date: Optional[str] = None,
        status: str = "active",
        description: Optional[str] = None,
        hospital: Optional[str] = None,
        doctor: Optional[str] = None
    ) -> bool:
        """添加病史记录"""
        record = await self.get_or_create_record(user_id)

        history_entry = {
            "disease_name": disease,
            "diagnosis_date": diagnosis_date,
            "status": status,
            "description": description,
            "hospital": hospital,
            "doctor": doctor,
            "added_at": datetime.now().isoformat()
        }

        record["medical_history"].append(history_entry)
        record["updated_at"] = datetime.now().isoformat()

        await self._save_record(HealthRecord.from_dict(record))

        if user_id in self._cache:
            self._cache[user_id] = HealthRecord.from_dict(record)

        return True

    async def has_disease(self, user_id: str, disease: str) -> bool:
        """检查是否有某种疾病"""
        medical_history = await self.get_medical_history(user_id)
        return any(
            h["disease_name"] == disease or disease in h.get("disease_name", "")
            for h in medical_history
        )

    async def get_active_diseases(self, user_id: str) -> List[str]:
        """获取活动性疾病列表"""
        medical_history = await self.get_medical_history(user_id)
        return [
            h["disease_name"] for h in medical_history
            if h.get("status") == "active"
        ]

    # ========== 手术史操作 ==========

    async def get_surgery_history(self, user_id: str) -> List[Dict[str, Any]]:
        """获取手术史列表"""
        record = await self.get_record(user_id)
        return record["surgery_history"] if record else []

    async def add_surgery_history(
        self,
        user_id: str,
        surgery_name: str,
        surgery_date: Optional[str] = None,
        hospital: Optional[str] = None,
        doctor: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """添加手术史记录"""
        record = await self.get_or_create_record(user_id)

        surgery_entry = {
            "surgery_name": surgery_name,
            "surgery_date": surgery_date,
            "hospital": hospital,
            "doctor": doctor,
            "description": description,
            "added_at": datetime.now().isoformat()
        }

        record["surgery_history"].append(surgery_entry)
        record["updated_at"] = datetime.now().isoformat()

        await self._save_record(HealthRecord.from_dict(record))

        if user_id in self._cache:
            self._cache[user_id] = HealthRecord.from_dict(record)

        return True

    # ========== 住院记录操作 ==========

    async def get_hospitalizations(self, user_id: str) -> List[Dict[str, Any]]:
        """获取住院记录列表"""
        record = await self.get_record(user_id)
        return record["hospitalizations"] if record else []

    async def add_hospitalization(
        self,
        user_id: str,
        reason: str,
        admission_date: Optional[str] = None,
        discharge_date: Optional[str] = None,
        hospital: Optional[str] = None,
        department: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """添加住院记录"""
        record = await self.get_or_create_record(user_id)

        hospitalization_entry = {
            "reason": reason,
            "admission_date": admission_date,
            "discharge_date": discharge_date,
            "hospital": hospital,
            "department": department,
            "description": description,
            "added_at": datetime.now().isoformat()
        }

        record["hospitalizations"].append(hospitalization_entry)
        record["updated_at"] = datetime.now().isoformat()

        await self._save_record(HealthRecord.from_dict(record))

        if user_id in self._cache:
            self._cache[user_id] = HealthRecord.from_dict(record)

        return True

    # ========== 过敏记录操作 ==========

    async def get_allergies(self, user_id: str) -> List[Dict[str, Any]]:
        """获取过敏记录列表"""
        record = await self.get_record(user_id)
        return record["allergies"] if record else []

    async def add_allergy(
        self,
        user_id: str,
        allergen: str,
        allergy_type: str = "drug",
        reaction: Optional[str] = None,
        severity: str = "moderate",
        diagnosed_date: Optional[str] = None
    ) -> bool:
        """添加过敏记录"""
        record = await self.get_or_create_record(user_id)

        allergy_entry = {
            "allergen": allergen,
            "allergy_type": allergy_type,
            "reaction": reaction,
            "severity": severity,
            "diagnosed_date": diagnosed_date,
            "added_at": datetime.now().isoformat()
        }

        record["allergies"].append(allergy_entry)
        record["updated_at"] = datetime.now().isoformat()

        await self._save_record(HealthRecord.from_dict(record))

        if user_id in self._cache:
            self._cache[user_id] = HealthRecord.from_dict(record)

        return True

    async def has_allergy(self, user_id: str, allergen: str) -> bool:
        """检查是否有某种过敏"""
        allergies = await self.get_allergies(user_id)
        return any(
            a["allergen"] == allergen or allergen in a.get("allergen", "")
            for a in allergies
        )

    async def get_drug_allergies(self, user_id: str) -> List[str]:
        """获取药物过敏列表"""
        allergies = await self.get_allergies(user_id)
        return [
            a["allergen"] for a in allergies
            if a.get("allergy_type") == "drug"
        ]

    # ========== 用药记录操作 ==========

    async def get_current_medications(self, user_id: str) -> List[Dict[str, Any]]:
        """获取当前用药列表"""
        record = await self.get_record(user_id)
        return record["current_medications"] if record else []

    async def get_past_medications(self, user_id: str) -> List[Dict[str, Any]]:
        """获取过往用药列表"""
        record = await self.get_record(user_id)
        return record["past_medications"] if record else []

    async def add_medication(
        self,
        user_id: str,
        drug_name: str,
        dosage: Optional[str] = None,
        frequency: Optional[str] = None,
        start_date: Optional[str] = None,
        prescribed_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """添加当前用药记录"""
        record = await self.get_or_create_record(user_id)

        medication_entry = {
            "drug_name": drug_name,
            "dosage": dosage,
            "frequency": frequency,
            "start_date": start_date,
            "end_date": None,
            "status": "active",
            "prescribed_by": prescribed_by,
            "notes": notes,
            "added_at": datetime.now().isoformat()
        }

        record["current_medications"].append(medication_entry)
        record["updated_at"] = datetime.now().isoformat()

        await self._save_record(HealthRecord.from_dict(record))

        if user_id in self._cache:
            self._cache[user_id] = HealthRecord.from_dict(record)

        return True

    async def discontinue_medication(
        self,
        user_id: str,
        drug_name: str,
        end_date: Optional[str] = None
    ) -> bool:
        """停用药物"""
        record = await self.get_record(user_id)
        if not record:
            return False

        for med in record["current_medications"]:
            if med["drug_name"] == drug_name and med.get("status") == "active":
                med["status"] = "discontinued"
                med["end_date"] = end_date or datetime.now().isoformat()

                # 移到过往用药
                record["past_medications"].append(med)
                record["current_medications"].remove(med)
                record["updated_at"] = datetime.now().isoformat()

                await self._save_record(HealthRecord.from_dict(record))

                if user_id in self._cache:
                    self._cache[user_id] = HealthRecord.from_dict(record)

                return True

        return False

    async def is_taking_medication(self, user_id: str, drug_name: str) -> bool:
        """检查是否正在使用某种药物"""
        medications = await self.get_current_medications(user_id)
        return any(
            m["drug_name"] == drug_name and m.get("status") == "active"
            for m in medications
        )

    # ========== 家族病史操作 ==========

    async def get_family_history(self, user_id: str) -> List[Dict[str, Any]]:
        """获取家族病史列表"""
        record = await self.get_record(user_id)
        return record["family_history"] if record else []

    async def add_family_history(
        self,
        user_id: str,
        relationship: str,
        disease: str,
        status: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """添加家族病史"""
        record = await self.get_or_create_record(user_id)

        family_entry = {
            "relationship": relationship,
            "disease": disease,
            "status": status,
            "notes": notes,
            "added_at": datetime.now().isoformat()
        }

        record["family_history"].append(family_entry)
        record["updated_at"] = datetime.now().isoformat()

        await self._save_record(HealthRecord.from_dict(record))

        if user_id in self._cache:
            self._cache[user_id] = HealthRecord.from_dict(record)

        return True

    # ========== 体检记录操作 ==========

    async def get_checkups(self, user_id: str) -> List[Dict[str, Any]]:
        """获取体检记录列表"""
        record = await self.get_record(user_id)
        return record["checkups"] if record else []

    async def add_checkup(
        self,
        user_id: str,
        checkup_date: str,
        checkup_type: Optional[str] = None,
        hospital: Optional[str] = None,
        summary: Optional[str] = None,
        results: Optional[Dict[str, Any]] = None,
        abnormal_indicators: Optional[List[str]] = None
    ) -> bool:
        """添加体检记录"""
        record = await self.get_or_create_record(user_id)

        checkup_entry = {
            "checkup_date": checkup_date,
            "checkup_type": checkup_type,
            "hospital": hospital,
            "summary": summary,
            "results": results or {},
            "abnormal_indicators": abnormal_indicators or [],
            "added_at": datetime.now().isoformat()
        }

        record["checkups"].append(checkup_entry)
        record["updated_at"] = datetime.now().isoformat()

        await self._save_record(HealthRecord.from_dict(record))

        if user_id in self._cache:
            self._cache[user_id] = HealthRecord.from_dict(record)

        return True

    async def get_latest_checkup(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取最新体检记录"""
        checkups = await self.get_checkups(user_id)
        if checkups:
            return max(checkups, key=lambda x: x.get("checkup_date", ""))
        return None

    # ========== 检查报告操作 ==========

    async def get_lab_reports(self, user_id: str) -> List[Dict[str, Any]]:
        """获取检查报告列表"""
        record = await self.get_record(user_id)
        return record["lab_reports"] if record else []

    async def add_lab_report(
        self,
        user_id: str,
        report_date: str,
        report_type: str,
        hospital: Optional[str] = None,
        items: Optional[Dict[str, Any]] = None,
        abnormal_items: Optional[List[str]] = None,
        report_url: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """添加检查报告记录"""
        record = await self.get_or_create_record(user_id)

        report_entry = {
            "report_date": report_date,
            "report_type": report_type,
            "hospital": hospital,
            "items": items or {},
            "abnormal_items": abnormal_items or [],
            "report_url": report_url,
            "notes": notes,
            "added_at": datetime.now().isoformat()
        }

        record["lab_reports"].append(report_entry)
        record["updated_at"] = datetime.now().isoformat()

        await self._save_record(HealthRecord.from_dict(record))

        if user_id in self._cache:
            self._cache[user_id] = HealthRecord.from_dict(record)

        return True

    async def get_reports_by_type(
        self,
        user_id: str,
        report_type: str
    ) -> List[Dict[str, Any]]:
        """按类型获取检查报告"""
        reports = await self.get_lab_reports(user_id)
        return [r for r in reports if r.get("report_type") == report_type]

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
                cursor = await db.execute("SELECT COUNT(*) FROM health_records")
                total_users = (await cursor.fetchone())[0]

                cursor = await db.execute("""
                    SELECT
                        SUM(json_array_length(medical_history)) as med_count,
                        SUM(json_array_length(allergies)) as allergy_count,
                        SUM(json_array_length(current_medications)) as med_count
                    FROM health_records
                """)
                stats_row = await cursor.fetchone()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("SELECT COUNT(*) FROM health_records")
                total_users = cursor.fetchone()[0]

                cursor = db.execute("""
                    SELECT
                        SUM(json_array_length(medical_history)) as med_count,
                        SUM(json_array_length(allergies)) as allergy_count,
                        SUM(json_array_length(current_medications)) as med_count
                    FROM health_records
                """)
                stats_row = cursor.fetchone()

        return {
            "total_users": total_users,
            "cache_size": len(self._cache),
        }


# ============================================================
# 全局服务实例
# ============================================================

_global_health_records_service: Optional[HealthRecordsService] = None


def get_health_records_service(
    db_path: str = "data/health_records.db"
) -> HealthRecordsService:
    """获取全局健康档案服务"""
    global _global_health_records_service
    if _global_health_records_service is None:
        _global_health_records_service = HealthRecordsService(db_path)
    return _global_health_records_service


def reset_health_records_service():
    """重置全局健康档案服务"""
    global _global_health_records_service
    _global_health_records_service = None
