# -*- coding: utf-8 -*-
"""
医疗数据生成配置
"""

# 阿里云DashScope配置
DASHSCOPE_API_KEY = "sk-a9a4edb1b4214016baa11c9be3b9fec4"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_MODEL = "qwen-max"  # 使用最强模型确保数据质量

# 数据输出目录
DATA_DIR = "d:/Users/liu.liu/Desktop/github/medical/data"

# 数据生成任务配置
DATA_GENERATION_TASKS = {
    "knowledge_base": {
        "enabled": True,
        "items": {
            "symptoms": 200,
            "diseases": 500
        },
        "output": "knowledge/knowledge_base.json"
    },
    "departments": {
        "enabled": True,
        "items": {
            "departments": 200,
            "doctors": 2000
        },
        "output": "departments/departments.json"
    },
    "drugs": {
        "enabled": True,
        "items": {
            "drugs": 10000
        },
        "output": "drugs/drugs.json"
    },
    "lab_items": {
        "enabled": True,
        "items": {
            "lab_tests": 500
        },
        "output": "lab/lab_items.json"
    },
    "patients": {
        "enabled": True,
        "items": {
            "patients": 50000,
            "health_records": 50000
        },
        "output": "patients/patients.json"
    },
    "pathology": {
        "enabled": True,
        "items": {
            "pathology_items": 100,
            "reports": 5000
        },
        "output": "pathology/reports.json"
    },
    "emergency": {
        "enabled": True,
        "items": {
            "guides": 50
        },
        "output": "emergency/guides.json"
    },
    "followup": {
        "enabled": True,
        "items": {
            "plans": 5000,
            "records": 50000
        },
        "output": "followup/records.json"
    }
}

# 数据质量标准
QUALITY_STANDARDS = {
    "completeness": 0.95,  # 95%字段完整
    "accuracy": 0.99,      # 99%准确率
    "consistency": 0.98,   # 98%一致性
    "validation": True     # 需要人工审核
}

# 公开数据源
PUBLIC_DATA_SOURCES = {
    "github": [
        "https://github.com/innovi/medical-icd-10",
        "https://github.com/FactCodes/ICD-10-PCS",
        "https://github.com/kjw0612/awesome-health-datasets",
        "https://github.com/nflorez/medical-datasets"
    ],
    "government": [
        "国家卫健委ICD-10编码",
        "国家药监局药品数据库",
        "国家临床路径"
    ],
    "medical": [
        "医脉通",
        "丁香园",
        "中华医学会指南"
    ]
}
