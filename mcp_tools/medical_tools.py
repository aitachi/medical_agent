"""
医疗领域 MCP 工具实现
包含11个核心工具：
1. medical_knowledge_query - 医学知识查询
2. hospital_department_query - 医院科室查询
3. drug_database_query - 药品数据库查询
4. appointment_booking - 预约挂号
5. lab_report_query - 检查报告解读
6. chronic_disease_query - 慢病管理数据
7. online_consult - 在线问诊服务
8. emergency_guide - 急救指南查询
9. followup_manage - 随访管理
10. health_checkup - 体检套餐管理
11. reminder_manage - 提醒服务
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_protocol.mcp_protocol import (
    MCPTool, MCPToolHandler, MCPServer, MCPHost, MCPFactory
)


# ============================================================
# 工具1: 医学知识查询
# ============================================================

class MedicalKnowledgeHandler(MCPToolHandler):
    """医学知识查询处理器"""

    # 模拟医学知识库
    KNOWLEDGE_BASE = {
        "症状": {
            "头痛": {
                "description": "头部疼痛是一种常见的症状",
                "common_causes": ["紧张性头痛", "偏头痛", "颈椎病", "高血压"],
                "red_flags": ["剧烈突发头痛", "伴有发热颈强", "意识改变", "神经功能缺损"],
                "department": "神经内科",
                "self_care": ["休息", "避免刺激", "适当按摩"]
            },
            "发热": {
                "description": "体温升高超过正常范围（腋温>37.3℃）",
                "common_causes": ["感染性疾病", "炎症反应", "肿瘤", "内分泌疾病"],
                "red_flags": ["体温>39℃", "持续高烧>3天", "意识模糊", "惊厥"],
                "department": "发热门诊/内科",
                "self_care": ["多饮水", "物理降温", "注意休息"]
            },
            "咳嗽": {
                "description": "呼吸道常见的防御性反射",
                "common_causes": ["感冒", "咽炎", "支气管炎", "肺炎", "过敏"],
                "red_flags": ["咳血", "呼吸困难", "持续>2周", "胸痛"],
                "department": "呼吸内科",
                "self_care": ["多饮温水", "避免刺激", "保持空气湿润"]
            },
            "腹痛": {
                "description": "腹部疼痛",
                "common_causes": ["消化不良", "胃炎", "肠炎", "阑尾炎", "胆结石"],
                "red_flags": ["剧烈疼痛", "板状腹", "呕血便血", "高热"],
                "department": "消化内科/急诊",
                "self_care": ["禁食", "观察", "及时就医"]
            },
            "胸痛": {
                "description": "胸部疼痛",
                "common_causes": ["心绞痛", "心肌梗死", "肺炎", "气胸", "肋间神经痛"],
                "red_flags": ["压榨性疼痛", "放射痛", "呼吸困难", "大汗淋漓"],
                "department": "心血管内科/急诊",
                "self_care": ["立即就医", "休息", "呼叫120"]
            }
        },
        "疾病": {
            "高血压": {
                "description": "血压持续升高（收缩压≥140mmHg或舒张压≥90mmHg）",
                "symptoms": ["头痛头晕", "心悸", "视力模糊"],
                "complications": ["心脏病", "脑卒中", "肾衰竭"],
                "department": "心血管内科",
                "lifestyle": ["低盐饮食", "规律运动", "控制体重", "戒烟限酒"]
            },
            "糖尿病": {
                "description": "代谢性疾病，以高血糖为特征",
                "symptoms": ["多饮多尿", "多食", "体重下降"],
                "complications": ["视网膜病变", "肾病", "神经病变"],
                "department": "内分泌科",
                "lifestyle": ["控制饮食", "规律运动", "监测血糖", "规范用药"]
            }
        }
    }

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行医学知识查询"""
        query_type = params.get("query_type", "symptom")  # symptom 或 disease
        keyword = params.get("keyword", "")

        if not keyword:
            return {
                "success": False,
                "error": "请提供查询关键词"
            }

        # 根据查询类型查找
        if query_type == "symptom":
            result = self.KNOWLEDGE_BASE["症状"].get(keyword)
        elif query_type == "disease":
            result = self.KNOWLEDGE_BASE["疾病"].get(keyword)
        else:
            return {
                "success": False,
                "error": f"不支持的查询类型: {query_type}"
            }

        if result:
            return {
                "success": True,
                "query_type": query_type,
                "keyword": keyword,
                "data": result
            }
        else:
            return {
                "success": False,
                "error": f"未找到关于「{keyword}」的信息",
                "suggestions": list(self.KNOWLEDGE_BASE[query_type].keys()) if query_type in self.KNOWLEDGE_BASE else []
            }


# ============================================================
# 工具2: 医院科室查询
# ============================================================

class HospitalDepartmentHandler(MCPToolHandler):
    """医院科室查询处理器"""

    # 科室数据库
    DEPARTMENTS = {
        "内科": {
            "sub_departments": ["心血管内科", "消化内科", "呼吸内科", "内分泌科", "神经内科", "肾内科", "血液科", "风湿免疫科"],
            "symptoms": ["胸闷", "腹痛", "咳嗽", "多饮多尿", "头痛", "水肿"],
            "description": "主要治疗内脏器官疾病"
        },
        "外科": {
            "sub_departments": ["普外科", "骨科", "神经外科", "胸外科", "泌尿外科", "整形外科"],
            "symptoms": ["外伤", "骨折", "肿瘤", "结石"],
            "description": "主要需要手术治疗的疾病"
        },
        "妇产科": {
            "sub_departments": ["产科", "妇科", "生殖医学科"],
            "symptoms": ["怀孕", "月经不调", "下腹痛"],
            "description": "女性生殖系统相关疾病"
        },
        "儿科": {
            "sub_departments": ["新生儿科", "小儿内科", "小儿外科"],
            "symptoms": ["发热", "咳嗽", "腹泻"],  # 14岁以下
            "description": "14岁以下儿童疾病"
        },
        "眼科": {
            "sub_departments": ["屈光科", "眼底病科", "白内障科", "青光眼科"],
            "symptoms": ["视力下降", "眼痛", "眼红", "流泪"],
            "description": "眼部疾病诊治"
        },
        "耳鼻喉科": {
            "sub_departments": ["耳科", "鼻科", "喉科"],
            "symptoms": ["耳鸣", "鼻塞", "咽痛", "声音嘶哑"],
            "description": "耳鼻咽喉疾病诊治"
        },
        "口腔科": {
            "sub_departments": "牙体牙髓科、牙周科、口腔颌面外科",
            "symptoms": ["牙痛", "牙龈出血", "口腔溃疡"],
            "description": "口腔及牙齿疾病诊治"
        },
        "皮肤科": {
            "sub_departments": ["皮肤内科", "皮肤外科", "美容皮肤科"],
            "symptoms": ["皮疹", "瘙痒", "脱发"],
            "description": "皮肤疾病诊治"
        },
        "精神科": {
            "sub_departments": ["精神科", "心理科", "心身医学科"],
            "symptoms": ["失眠", "焦虑", "抑郁"],
            "description": "精神心理疾病诊治"
        },
        "急诊科": {
            "sub_departments": ["内科急诊", "外科急诊", "儿科急诊"],
            "symptoms": ["高热", "剧烈疼痛", "大出血", "呼吸困难", "意识丧失"],
            "description": "急危重症救治"
        }
    }

    # 症状到科室的映射
    SYMPTOM_DEPARTMENT_MAP = {
        "头痛": "神经内科",
        "头晕": "神经内科",
        "失眠": "神经内科/精神科",
        "胸痛": "心血管内科",
        "心悸": "心血管内科",
        "腹痛": "消化内科",
        "恶心": "消化内科",
        "呕吐": "消化内科",
        "咳嗽": "呼吸内科",
        "气促": "呼吸内科",
        "发热": "发热门诊",
        "多饮多尿": "内分泌科",
        "关节痛": "风湿免疫科/骨科",
        "皮疹": "皮肤科",
        "牙痛": "口腔科",
        "眼痛": "眼科",
        "耳鸣": "耳鼻喉科",
        "咽痛": "耳鼻喉科",
        "月经不调": "妇科",
        "乳房肿块": "乳腺外科",
        "外伤": "急诊科/外科",
        "骨折": "骨科"
    }

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行科室查询"""
        query_type = params.get("query_type", "list")  # list, by_symptom, detail

        if query_type == "list":
            # 列出所有科室
            return {
                "success": True,
                "departments": [
                    {
                        "name": name,
                        "description": info["description"],
                        "sub_departments": info["sub_departments"]
                    }
                    for name, info in self.DEPARTMENTS.items()
                ]
            }

        elif query_type == "by_symptom":
            # 根据症状推荐科室
            symptom = params.get("symptom", "")

            if not symptom:
                return {
                    "success": False,
                    "error": "请提供症状描述"
                }

            # 查找匹配的科室
            departments = []
            for key, dept in self.SYMPTOM_DEPARTMENT_MAP.items():
                if key in symptom or symptom in key:
                    departments.append({"symptom": key, "department": dept})

            if departments:
                return {
                    "success": True,
                    "symptom": symptom,
                    "recommendations": departments
                }
            else:
                return {
                    "success": False,
                    "error": f"未找到与「{symptom}」相关的科室",
                    "suggestion": "建议咨询导诊台或普通内科"
                }

        elif query_type == "detail":
            # 获取科室详情
            department = params.get("department", "")

            if department in self.DEPARTMENTS:
                info = self.DEPARTMENTS[department]
                return {
                    "success": True,
                    "department": department,
                    "detail": info
                }
            else:
                return {
                    "success": False,
                    "error": f"未找到科室: {department}"
                }

        else:
            return {
                "success": False,
                "error": f"不支持的查询类型: {query_type}"
            }


# ============================================================
# 工具3: 药品数据库查询
# ============================================================

class DrugDatabaseHandler(MCPToolHandler):
    """药品数据库查询处理器"""

    # 药品数据库
    DRUG_DATABASE = {
        "阿莫西林": {
            "generic_name": "阿莫西林",
            "english_name": "Amoxicillin",
            "category": "抗生素",
            "sub_category": "青霉素类",
            "indications": ["呼吸道感染", "尿路感染", "皮肤软组织感染", "消化道感染"],
            "dosage": {
                "adult": "0.5g, 每6-8小时一次",
                "children": "按体重20-40mg/kg/日，分3-4次"
            },
            "contraindications": ["青霉素过敏史"],
            "side_effects": ["恶心", "呕吐", "腹泻", "皮疹"],
            "interactions": ["丙磺舒可延缓排泄", "与避孕药合用可降低避孕药效果"],
            "warnings": "青霉素过敏者禁用，使用前需做皮试"
        },
        "布洛芬": {
            "generic_name": "布洛芬",
            "english_name": "Ibuprofen",
            "category": "解热镇痛药",
            "sub_category": "非甾体抗炎药",
            "indications": ["发热", "头痛", "牙痛", "关节痛", "痛经"],
            "dosage": {
                "adult": "0.2-0.4g, 每4-6小时一次，每日不超过1.2g",
                "children": "5-10mg/kg/次，每6-8小时一次"
            },
            "contraindications": ["活动性消化道溃疡", "阿司匹林过敏", "严重心衰"],
            "side_effects": ["胃肠道反应", "头晕", "皮疹", "肾损害"],
            "interactions": ["与阿司匹林合用增加出血风险", "与抗凝药合用需监测"],
            "warnings": "饭后服用，有胃病史慎用"
        },
        "对乙酰氨基酚": {
            "generic_name": "对乙酰氨基酚",
            "english_name": "Paracetamol",
            "category": "解热镇痛药",
            "indications": ["发热", "头痛", "关节痛", "痛经"],
            "dosage": {
                "adult": "0.5g, 每4-6小时一次，每日不超过2g",
                "children": "10-15mg/kg/次，每4-6小时一次"
            },
            "contraindications": ["严重肝肾功能不全"],
            "side_effects": ["偶见皮疹", "过量可致肝损害"],
            "interactions": ["与酒精同用增加肝毒性"],
            "warnings": "超量使用可致严重肝损害，注意其他含对乙酰氨基酚的复方制剂"
        },
        "二甲双胍": {
            "generic_name": "二甲双胍",
            "english_name": "Metformin",
            "category": "降糖药",
            "sub_category": "双胍类",
            "indications": ["2型糖尿病"],
            "dosage": {
                "start": "0.5g, 每日2次",
                "maintenance": "1-1.5g, 每日2次"
            },
            "contraindications": ["严重肾功能不全", "酮症酸中毒", "严重感染"],
            "side_effects": ["恶心", "腹泻", "乳酸酸中毒（罕见但严重）"],
            "interactions": ["与碘造影剂合用需停药"],
            "warnings": "定期检查肾功能，避免饮酒"
        },
        "硝苯地平": {
            "generic_name": "硝苯地平",
            "english_name": "Nifedipine",
            "category": "降压药",
            "sub_category": "钙通道阻滞剂",
            "indications": ["高血压", "心绞痛"],
            "dosage": {
                "adult": "10mg, 每日2-3次"
            },
            "contraindications": ["严重主动脉瓣狭窄", "心源性休克"],
            "side_effects": ["面部潮红", "头痛", "下肢水肿", "心悸"],
            "interactions": ["与β受体阻滞剂合用需谨慎"],
            "warnings": "避免突然停药，定期监测血压"
        },
        "奥美拉唑": {
            "generic_name": "奥美拉唑",
            "english_name": "Omeprazole",
            "category": "抑酸药",
            "sub_category": "质子泵抑制剂",
            "indications": ["胃溃疡", "十二指肠溃疡", "反流性食管炎", "幽门螺杆菌根除"],
            "dosage": {
                "adult": "20mg, 每日1次，晨起空腹服用"
            },
            "contraindications": ["对本品过敏", "严重肾功能不全"],
            "side_effects": ["头痛", "腹泻", "便秘"],
            "interactions": ["可降低氯吡格雷效果"],
            "warnings": "长期使用需定期检查"
        }
    }

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行药品查询"""
        query_type = params.get("query_type", "info")  # info, interaction, contraindication
        drug_name = params.get("drug_name", "")

        if not drug_name:
            return {
                "success": False,
                "error": "请提供药品名称"
            }

        # 查找药品
        drug = self.DRUG_DATABASE.get(drug_name)
        if not drug:
            return {
                "success": False,
                "error": f"未找到药品: {drug_name}",
                "available_drugs": list(self.DRUG_DATABASE.keys())
            }

        if query_type == "info":
            # 返回完整信息
            return {
                "success": True,
                "drug_name": drug_name,
                "info": drug
            }

        elif query_type == "dosage":
            # 返回用法用量
            return {
                "success": True,
                "drug_name": drug_name,
                "dosage": drug["dosage"],
                "warnings": drug.get("warnings", "")
            }

        elif query_type == "interaction":
            # 返回药物相互作用
            other_drug = params.get("other_drug", "")
            interactions = drug.get("interactions", [])

            return {
                "success": True,
                "drug_name": drug_name,
                "other_drug": other_drug,
                "interactions": interactions,
                "warning": "请告知医生您正在使用的所有药物"
            }

        elif query_type == "side_effects":
            # 返回副作用
            return {
                "success": True,
                "drug_name": drug_name,
                "side_effects": drug.get("side_effects", []),
                "contraindications": drug.get("contraindications", [])
            }

        else:
            return {
                "success": False,
                "error": f"不支持的查询类型: {query_type}"
            }


# ============================================================
# 工具4: 预约挂号
# ============================================================

class AppointmentBookingHandler(MCPToolHandler):
    """预约挂号处理器"""

    # 模拟医生排班数据
    DOCTOR_SCHEDULES = {
        "内科": {
            "张医生": {"title": "主任医师", "specialty": "心血管疾病", "schedule": ["周一上午", "周三下午", "周五上午"]},
            "李医生": {"title": "副主任医师", "specialty": "消化系统疾病", "schedule": ["周二上午", "周四下午"]},
            "王医生": {"title": "主治医师", "specialty": "内分泌疾病", "schedule": ["周一下午", "周三上午", "周五下午"]}
        },
        "外科": {
            "赵医生": {"title": "主任医师", "specialty": "普外科", "schedule": ["周一全天", "周四上午"]},
            "钱医生": {"title": "副主任医师", "specialty": "骨科", "schedule": ["周二全天", "周五上午"]}
        },
        "神经内科": {
            "孙医生": {"title": "主任医师", "specialty": "脑血管病", "schedule": ["周三上午", "周五下午"]},
            "周医生": {"title": "主治医师", "specialty": "头痛头晕", "schedule": ["周二下午", "周四上午"]}
        },
        "呼吸内科": {
            "吴医生": {"title": "副主任医师", "specialty": "慢性咳嗽", "schedule": ["周一上午", "周三下午"]},
            "郑医生": {"title": "主治医师", "specialty": "哮喘", "schedule": ["周二上午", "周四下午"]}
        },
        "皮肤科": {
            "冯医生": {"title": "主任医师", "specialty": "湿疹皮炎", "schedule": ["周三上午", "周五上午"]},
            "陈医生": {"title": "主治医师", "specialty": "痤疮", "schedule": ["周一下午", "周四下午"]}
        }
    }

    # 模拟预约记录
    _appointments = {}

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行预约挂号操作"""
        action = params.get("action", "query")  # query, book, cancel, list

        if action == "query_availability":
            # 查询号源
            department = params.get("department", "")
            date = params.get("date", "")

            if not department:
                return {
                    "success": False,
                    "error": "请提供科室名称"
                }

            if department not in self.DOCTOR_SCHEDULES:
                return {
                    "success": False,
                    "error": f"暂未开通{department}预约",
                    "available_departments": list(self.DOCTOR_SCHEDULES.keys())
                }

            doctors = self.DOCTOR_SCHEDULES[department]
            doctor_list = []
            for name, info in doctors.items():
                doctor_list.append({
                    "name": name,
                    "title": info["title"],
                    "specialty": info["specialty"],
                    "schedule": info["schedule"]
                })

            return {
                "success": True,
                "department": department,
                "date": date,
                "doctors": doctor_list
            }

        elif action == "book":
            # 预约挂号
            appointment_id = f"APT{datetime.now().strftime('%Y%m%d%H%M%S')}"
            department = params.get("department", "")
            doctor_name = params.get("doctor", "")
            patient_name = params.get("patient_name", "")
            appointment_time = params.get("appointment_time", "")

            if not all([department, doctor_name, patient_name, appointment_time]):
                return {
                    "success": False,
                    "error": "请提供完整的预约信息"
                }

            # 检查号源
            if department not in self.DOCTOR_SCHEDULES:
                return {
                    "success": False,
                    "error": f"科室{department}不存在"
                }

            if doctor_name not in self.DOCTOR_SCHEDULES[department]:
                return {
                    "success": False,
                    "error": f"{department}没有{doctor_name}医生"
                }

            # 保存预约
            self._appointments[appointment_id] = {
                "appointment_id": appointment_id,
                "department": department,
                "doctor": doctor_name,
                "patient_name": patient_name,
                "appointment_time": appointment_time,
                "status": "confirmed",
                "created_at": datetime.now().isoformat()
            }

            return {
                "success": True,
                "appointment_id": appointment_id,
                "message": f"预约成功！请于{appointment_time}前往{department}找{doctor_name}就诊",
                "appointment": self._appointments[appointment_id]
            }

        elif action == "cancel":
            # 取消预约
            appointment_id = params.get("appointment_id", "")

            if appointment_id in self._appointments:
                self._appointments[appointment_id]["status"] = "cancelled"
                return {
                    "success": True,
                    "appointment_id": appointment_id,
                    "message": "预约已取消"
                }
            else:
                return {
                    "success": False,
                    "error": "预约号不存在"
                }

        elif action == "list":
            # 查询我的预约
            patient_name = params.get("patient_name", "")

            if not patient_name:
                return {
                    "success": False,
                    "error": "请提供患者姓名"
                }

            my_appointments = [
                apt for apt in self._appointments.values()
                if apt["patient_name"] == patient_name
            ]

            return {
                "success": True,
                "patient_name": patient_name,
                "appointments": my_appointments,
                "count": len(my_appointments)
            }

        elif action == "list_departments":
            # 列出可预约科室
            return {
                "success": True,
                "departments": list(self.DOCTOR_SCHEDULES.keys())
            }

        else:
            return {
                "success": False,
                "error": f"不支持的操作: {action}"
            }


# ============================================================
# 工具5: 检查报告解读
# ============================================================

class LabReportHandler(MCPToolHandler):
    """检查报告解读处理器"""

    # 参考范围数据库
    REFERENCE_RANGES = {
        "血常规": {
            "WBC": {"name": "白细胞", "unit": "10^9/L", "normal": "4-10", "clinical": "升高提示感染/炎症，降低提示免疫力下降"},
            "RBC": {"name": "红细胞", "unit": "10^12/L", "normal": "4.0-5.5", "clinical": "降低提示贫血"},
            "HGB": {"name": "血红蛋白", "unit": "g/L", "normal": "120-160", "clinical": "男性<120，女性<110提示贫血"},
            "HCT": {"name": "红细胞压积", "unit": "%", "normal": "40-50", "clinical": "反映红细胞体积占比"},
            "PLT": {"name": "血小板", "unit": "10^9/L", "normal": "100-300", "clinical": "减少提示出血风险增加"}
        },
        "生化": {
            "ALT": {"name": "谷丙转氨酶", "unit": "U/L", "normal": "0-40", "clinical": "升高提示肝细胞损伤"},
            "AST": {"name": "谷草转氨酶", "unit": "U/L", "normal": "0-40", "clinical": "升高提示肝损伤/心肌损伤"},
            "GLU": {"name": "血糖", "unit": "mmol/L", "normal": "3.9-6.1", "clinical": "空腹>7.0提示糖尿病，<3.9低血糖"},
            "TG": {"name": "甘油三酯", "unit": "mmol/L", "normal": "<1.7", "clinical": "升高为高甘油三酯血症"},
            "CHOL": {"name": "总胆固醇", "unit": "mmol/L", "normal": "<5.2", "clinical": "升高为高胆固醇血症"},
            "CREA": {"name": "肌酐", "unit": "μmol/L", "normal": "44-133", "clinical": "升高提示肾功能减退"},
            "UA": {"name": "尿酸", "unit": "μmol/L", "normal": "150-420", "clinical": "升高提示高尿酸血症/痛风"},
            "K": {"name": "钾", "unit": "mmol/L", "normal": "3.5-5.5", "clinical": "异常可致心律失常"},
            "NA": {"name": "钠", "unit": "mmol/L", "normal": "135-145", "clinical": "异常提示电解质紊乱"}
        },
        "尿常规": {
            "SG": {"name": "比重", "unit": "", "normal": "1.010-1.030", "clinical": "反映肾脏浓缩功能"},
            "PH": {"name": "酸碱度", "unit": "", "normal": "4.6-8.0", "clinical": "受饮食和疾病影响"},
            "PRO": {"name": "蛋白", "unit": "", "normal": "阴性", "clinical": "阳性提示蛋白尿/肾脏问题"},
            "GLU": {"name": "葡萄糖", "unit": "", "normal": "阴性", "clinical": "阳性提示血糖过高"},
            "LEU": {"name": "白细胞", "unit": "", "normal": "阴性", "clinical": "阳性提示尿路感染"},
            "ERY": {"name": "红细胞", "unit": "", "normal": "阴性", "clinical": "阳性提示血尿"}
        },
        "凝血功能": {
            "PT": {"name": "凝血酶原时间", "unit": "s", "normal": "11-15", "clinical": "延长提示凝血功能障碍"},
            "INR": {"name": "国际标准化比值", "unit": "", "normal": "0.8-1.2", "clinical": "服用华法林患者需监测"},
            "APTT": {"name": "活化部分凝血活酶时间", "unit": "s", "normal": "25-40", "clinical": "延长提示内源凝血异常"}
        },
        "肿瘤标志物": {
            "CEA": {"name": "癌胚抗原", "unit": "ng/mL", "normal": "<5", "clinical": "升高提示消化道肿瘤等"},
            "AFP": {"name": "甲胎蛋白", "unit": "ng/mL", "normal": "<20", "clinical": "升高提示肝癌/生殖细胞肿瘤"},
            "CA125": {"name": "糖类抗原125", "unit": "U/mL", "normal": "<35", "clinical": "升高提示卵巢癌等"},
            "CA19_9": {"name": "糖类抗原19-9", "unit": "U/mL", "normal": "<37", "clinical": "升高提示胰腺癌/胆道肿瘤"},
            "PSA": {"name": "前列腺特异性抗原", "unit": "ng/mL", "normal": "<4", "clinical": "升高提示前列腺癌"}
        }
    }

    # 异常结果解读模板
    INTERPRETATION_TEMPLATES = {
        "anemia": "血红蛋白降低，提示贫血。建议：补充富含铁的食物，必要时就医检查贫血原因。",
        "infection": "白细胞升高，提示可能存在感染或炎症。建议：结合临床症状，必要时抗感染治疗。",
        "liver_injury": "转氨酶升高，提示肝细胞可能受损。建议：避免饮酒，复查肝功能，查找原因。",
        "kidney_injury": "肌酐升高，提示肾功能可能减退。建议：查尿常规，肾内科就诊。",
        "hyperglycemia": "血糖升高，建议：控制饮食，规律运动，内分泌科就诊排查糖尿病。",
        "hypoglycemia": "血糖降低，建议：及时补充糖分，排查低血糖原因。",
        "hyperlipidemia": "血脂升高，建议：低脂饮食，增加运动，必要时降脂治疗。",
        "hyperuricemia": "尿酸升高，建议：低嘌呤饮食，多饮水，避免痛风发作。",
        "proteinuria": "尿蛋白阳性，建议：查24小时尿蛋白，肾内科就诊。",
        "tumor_marker_elevated": "肿瘤标志物升高，需结合影像学检查，建议肿瘤专科就诊。"
    }

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行检查报告解读"""
        action = params.get("action", "interpret")  # interpret, reference, list_items

        if action == "reference":
            # 查询参考范围
            category = params.get("category", "")
            item = params.get("item", "")

            if not category:
                return {
                    "success": False,
                    "error": "请提供检查类别",
                    "available_categories": list(self.REFERENCE_RANGES.keys())
                }

            if category not in self.REFERENCE_RANGES:
                return {
                    "success": False,
                    "error": f"不支持的检查类别: {category}",
                    "available_categories": list(self.REFERENCE_RANGES.keys())
                }

            category_data = self.REFERENCE_RANGES[category]

            if item:
                # 查询具体项目
                if item in category_data:
                    return {
                        "success": True,
                        "category": category,
                        "item": item,
                        "reference": category_data[item]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"未找到项目: {item}",
                        "available_items": list(category_data.keys())
                    }
            else:
                # 返回整个类别的参考范围
                return {
                    "success": True,
                    "category": category,
                    "items": category_data
                }

        elif action == "interpret":
            # 解读报告
            category = params.get("category", "")
            results = params.get("results", {})  # {项目: 值}

            if not category or not results:
                return {
                    "success": False,
                    "error": "请提供检查类别和检查结果"
                }

            if category not in self.REFERENCE_RANGES:
                return {
                    "success": False,
                    "error": f"不支持的检查类别: {category}"
                }

            category_data = self.REFERENCE_RANGES[category]
            abnormal_items = []
            normal_items = []

            for item, value in results.items():
                if item not in category_data:
                    continue

                ref = category_data[item]
                normal_range = ref["normal"]

                # 解析参考范围并判断是否异常
                is_abnormal, interpretation = self._evaluate_result(item, value, normal_range)

                if is_abnormal:
                    abnormal_items.append({
                        "item": item,
                        "name": ref["name"],
                        "value": value,
                        "unit": ref["unit"],
                        "normal_range": normal_range,
                        "clinical": ref["clinical"],
                        "interpretation": interpretation
                    })
                else:
                    normal_items.append({
                        "item": item,
                        "name": ref["name"],
                        "value": value,
                        "unit": ref["unit"]
                    })

            # 生成综合建议
            suggestions = self._generate_suggestions(abnormal_items)

            return {
                "success": True,
                "category": category,
                "summary": {
                    "total": len(results),
                    "abnormal": len(abnormal_items),
                    "normal": len(normal_items)
                },
                "abnormal_items": abnormal_items,
                "normal_items": normal_items,
                "suggestions": suggestions,
                "disclaimer": "本解读仅供参考，具体请咨询医生"
            }

        elif action == "list_categories":
            # 列出所有检查类别
            return {
                "success": True,
                "categories": [
                    {
                        "name": cat,
                        "items": list(items.keys())
                    }
                    for cat, items in self.REFERENCE_RANGES.items()
                ]
            }

        else:
            return {
                "success": False,
                "error": f"不支持的操作: {action}"
            }

    def _evaluate_result(self, item: str, value: Any, normal_range: str) -> tuple:
        """评估检查结果是否异常"""
        try:
            # 尝试转换为数值
            if isinstance(value, str):
                # 提取数值部分
                import re
                num_match = re.search(r"[\d.]+", str(value))
                if num_match:
                    num_value = float(num_match.group())
                else:
                    return False, ""
            else:
                num_value = float(value)

            # 解析参考范围
            if "-" in normal_range:
                # 范围格式: "4-10"
                parts = normal_range.split("-")
                min_val = float(parts[0])
                max_val = float(parts[1]) if len(parts) > 1 else min_val

                if num_value < min_val:
                    return True, f"低于正常范围下限（{normal_range}）"
                elif num_value > max_val:
                    return True, f"高于正常范围上限（{normal_range}）"
                else:
                    return False, ""

            elif normal_range.startswith("<"):
                # 上限格式: "<5"
                max_val = float(normal_range.replace("<", "").replace("=", ""))
                if num_value >= max_val:
                    return True, f"高于正常上限（{normal_range}）"
                return False, ""

            elif normal_range == "阴性":
                # 阴性/阳性
                if str(value).strip() not in ["阴性", "-", "negative"]:
                    return True, "阳性结果"
                return False, ""

            else:
                return False, ""

        except (ValueError, TypeError):
            return False, ""

    def _generate_suggestions(self, abnormal_items: list) -> list:
        """生成综合建议"""
        suggestions = []

        for item in abnormal_items:
            item_code = item["item"]

            # 根据项目生成针对性建议
            if item_code in ["HGB", "RBC"]:
                suggestions.append(self.INTERPRETATION_TEMPLATES.get("anemia"))
            elif item_code == "WBC":
                suggestions.append(self.INTERPRETATION_TEMPLATES.get("infection"))
            elif item_code in ["ALT", "AST"]:
                suggestions.append(self.INTERPRETATION_TEMPLATES.get("liver_injury"))
            elif item_code == "CREA":
                suggestions.append(self.INTERPRETATION_TEMPLATES.get("kidney_injury"))
            elif item_code == "GLU":
                value = float(str(item["value"]).replace("[^0-9.]", ""))
                if value > 6.1:
                    suggestions.append(self.INTERPRETATION_TEMPLATES.get("hyperglycemia"))
                else:
                    suggestions.append(self.INTERPRETATION_TEMPLATES.get("hypoglycemia"))
            elif item_code in ["TG", "CHOL"]:
                suggestions.append(self.INTERPRETATION_TEMPLATES.get("hyperlipidemia"))
            elif item_code == "UA":
                suggestions.append(self.INTERPRETATION_TEMPLATES.get("hyperuricemia"))
            elif item_code == "PRO" and item.get("category") == "尿常规":
                suggestions.append(self.INTERPRETATION_TEMPLATES.get("proteinuria"))
            elif item_code in ["CEA", "AFP", "CA125", "CA19_9", "PSA"]:
                suggestions.append(self.INTERPRETATION_TEMPLATES.get("tumor_marker_elevated"))

        # 去重
        return list(dict.fromkeys(suggestions))


# ============================================================
# 工具6: 慢病管理数据
# ============================================================

class ChronicDiseaseHandler(MCPToolHandler):
    """慢病管理数据处理器"""

    # 模拟患者慢病数据
    _patient_records = {
        "P001": {
            "patient_id": "P001",
            "name": "张三",
            "chronic_conditions": [
                {
                    "condition": "高血压",
                    "diagnosis_date": "2020-05-15",
                    "severity": "2级",
                    "status": "控制中"
                },
                {
                    "condition": "2型糖尿病",
                    "diagnosis_date": "2021-08-20",
                    "severity": "轻度",
                    "status": "控制中"
                }
            ],
            "medications": [
                {"name": "硝苯地平", "dosage": "10mg 每日2次", "since": "2020-05-20"},
                {"name": "二甲双胍", "dosage": "0.5g 每日2次", "since": "2021-08-25"}
            ]
        }
    }

    # 血压/血糖监测记录
    _monitoring_records = {}

    # 控制目标参考
    CONTROL_TARGETS = {
        "高血压": {
            "general": "<140/90 mmHg",
            "ideal": "<130/80 mmHg",
            "home": "<135/85 mmHg"
        },
        "糖尿病": {
            "fasting_glucose": "4.4-7.0 mmol/L",
            "postprandial_2h": "<10.0 mmol/L",
            "hba1c": "<7.0%"
        },
        "高脂血症": {
            "ldl_c": "<2.6 mmol/L (一般人群)",
            "ldl_c_high_risk": "<1.8 mmol/L (高危人群)",
            "tg": "<1.7 mmol/L"
        },
        "慢性肾病": {
            "egfr": ">90 mL/min/1.73m²",
            "proteinuria": "<0.3 g/24h"
        }
    }

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行慢病管理操作"""
        action = params.get("action", "query")  # query, record, analyze, targets

        if action == "query":
            # 查询患者慢病信息
            patient_id = params.get("patient_id", "")

            if not patient_id:
                return {
                    "success": False,
                    "error": "请提供患者ID"
                }

            if patient_id not in self._patient_records:
                return {
                    "success": False,
                    "error": f"未找到患者: {patient_id}"
                }

            return {
                "success": True,
                "patient": self._patient_records[patient_id]
            }

        elif action == "record":
            # 记录监测数据（血压/血糖等）
            patient_id = params.get("patient_id", "")
            record_type = params.get("record_type", "")  # blood_pressure, blood_glucose
            value = params.get("value", {})
            recorded_at = params.get("recorded_at", datetime.now().isoformat())

            if not all([patient_id, record_type, value]):
                return {
                    "success": False,
                    "error": "请提供完整的记录信息"
                }

            record_id = f"{record_type}_{patient_id}_{int(datetime.now().timestamp())}"

            if patient_id not in self._monitoring_records:
                self._monitoring_records[patient_id] = {}

            if record_type not in self._monitoring_records[patient_id]:
                self._monitoring_records[patient_id][record_type] = []

            record = {
                "record_id": record_id,
                "record_type": record_type,
                "value": value,
                "recorded_at": recorded_at
            }

            self._monitoring_records[patient_id][record_type].append(record)

            return {
                "success": True,
                "record_id": record_id,
                "message": f"{record_type}记录成功",
                "record": record
            }

        elif action == "analyze":
            # 分析监测趋势
            patient_id = params.get("patient_id", "")
            record_type = params.get("record_type", "")
            days = params.get("days", 30)  # 分析最近N天

            if not patient_id or not record_type:
                return {
                    "success": False,
                    "error": "请提供患者ID和记录类型"
                }

            if patient_id not in self._monitoring_records:
                return {
                    "success": False,
                    "error": "该患者暂无监测记录"
                }

            if record_type not in self._monitoring_records[patient_id]:
                return {
                    "success": False,
                    "error": f"该患者暂无{record_type}记录"
                }

            records = self._monitoring_records[patient_id][record_type]

            # 筛选最近N天的记录
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_records = [
                r for r in records
                if datetime.fromisoformat(r["recorded_at"]) >= cutoff_date
            ]

            if not recent_records:
                return {
                    "success": False,
                    "error": f"最近{days}天内无记录"
                }

            # 计算统计信息
            analysis = self._calculate_trend(recent_records, record_type)

            return {
                "success": True,
                "patient_id": patient_id,
                "record_type": record_type,
                "period_days": days,
                "total_records": len(recent_records),
                "analysis": analysis
            }

        elif action == "targets":
            # 获取控制目标
            condition = params.get("condition", "")

            if not condition:
                return {
                    "success": True,
                    "conditions": list(self.CONTROL_TARGETS.keys())
                }

            if condition not in self.CONTROL_TARGETS:
                return {
                    "success": False,
                    "error": f"未找到疾病: {condition}",
                    "available": list(self.CONTROL_TARGETS.keys())
                }

            return {
                "success": True,
                "condition": condition,
                "targets": self.CONTROL_TARGETS[condition]
            }

        elif action == "get_medication_reminder":
            # 获取用药提醒
            patient_id = params.get("patient_id", "")

            if patient_id not in self._patient_records:
                return {
                    "success": False,
                    "error": f"未找到患者: {patient_id}"
                }

            medications = self._patient_records[patient_id].get("medications", [])

            reminders = []
            for med in medications:
                reminders.append({
                    "medication": med["name"],
                    "dosage": med["dosage"],
                    "reminder_text": f"请按时服用 {med['name']}，剂量：{med['dosage']}"
                })

            return {
                "success": True,
                "patient_id": patient_id,
                "reminders": reminders
            }

        else:
            return {
                "success": False,
                "error": f"不支持的操作: {action}"
            }

    def _calculate_trend(self, records: list, record_type: str) -> dict:
        """计算监测趋势"""
        if record_type == "blood_pressure":
            # 血压趋势分析
            systolic_values = [r["value"].get("systolic") for r in records if r["value"].get("systolic")]
            diastolic_values = [r["value"].get("diastolic") for r in records if r["value"].get("diastolic")]

            if not systolic_values:
                return {"error": "无有效数据"}

            avg_sys = sum(systolic_values) / len(systolic_values)
            avg_dia = sum(diastolic_values) / len(diastolic_values) if diastolic_values else 0

            # 判断控制情况
            control_status = "良好"
            if avg_sys >= 140 or avg_dia >= 90:
                control_status = "欠佳"
            elif avg_sys >= 130 or avg_dia >= 80:
                control_status = "尚可"

            return {
                "avg_systolic": round(avg_sys, 1),
                "avg_diastolic": round(avg_dia, 1),
                "max_systolic": max(systolic_values),
                "min_systolic": min(systolic_values),
                "control_status": control_status,
                "recommendation": "建议继续监测，保持规律用药" if control_status == "良好" else "建议就医调整用药"
            }

        elif record_type == "blood_glucose":
            # 血糖趋势分析
            values = [r["value"].get("glucose") for r in records if r["value"].get("glucose")]

            if not values:
                return {"error": "无有效数据"}

            avg_glucose = sum(values) / len(values)

            control_status = "良好"
            if avg_glucose > 7.0:
                control_status = "欠佳"
            elif avg_glucose > 6.1:
                control_status = "尚可"

            return {
                "avg_glucose": round(avg_glucose, 1),
                "max_glucose": max(values),
                "min_glucose": min(values),
                "control_status": control_status
            }

        else:
            return {"error": "不支持的记录类型"}


# ============================================================
# 工具7: 在线问诊服务
# ============================================================

class OnlineConsultHandler(MCPToolHandler):
    """在线问诊服务处理器"""

    # 模拟医生资源
    _DOCTORS = {
        "D001": {
            "id": "D001",
            "name": "王医生",
            "title": "主任医师",
            "department": "心血管内科",
            "specialty": "高血压、冠心病",
            "experience": "20年",
            "rating": 4.9,
            "consultation_count": 5230,
            "price": {"text": 50, "video": 100, "phone": 80},
            "availability": "online"
        },
        "D002": {
            "id": "D002",
            "name": "李医生",
            "title": "副主任医师",
            "department": "内分泌科",
            "specialty": "糖尿病、甲状腺疾病",
            "experience": "15年",
            "rating": 4.8,
            "consultation_count": 3680,
            "price": {"text": 40, "video": 80, "phone": 60},
            "availability": "online"
        },
        "D003": {
            "id": "D003",
            "name": "赵医生",
            "title": "主治医师",
            "department": "呼吸内科",
            "specialty": "慢性咳嗽、哮喘",
            "experience": "10年",
            "rating": 4.7,
            "consultation_count": 2100,
            "price": {"text": 30, "video": 60, "phone": 50},
            "availability": "busy"
        },
        "D004": {
            "id": "D004",
            "name": "刘医生",
            "title": "主任医师",
            "department": "消化内科",
            "specialty": "胃炎、胃溃疡",
            "experience": "18年",
            "rating": 4.9,
            "consultation_count": 4500,
            "price": {"text": 50, "video": 100, "phone": 80},
            "availability": "online"
        }
    }

    # 模拟问诊记录
    _consultations = {}

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行在线问诊操作"""
        action = params.get("action", "list_doctors")  # list_doctors, get_doctor, create, get_consultation, add_message

        if action == "list_doctors":
            # 列出可用医生
            department = params.get("department", "")

            doctors = self._DOCTORS
            if department:
                doctors = {k: v for k, v in self._DOCTORS.items() if v["department"] == department}

            return {
                "success": True,
                "doctors": [
                    {
                        "id": d["id"],
                        "name": d["name"],
                        "title": d["title"],
                        "department": d["department"],
                        "specialty": d["specialty"],
                        "experience": d["experience"],
                        "rating": d["rating"],
                        "price": d["price"],
                        "availability": d["availability"]
                    }
                    for d in doctors.values()
                ]
            }

        elif action == "get_doctor":
            # 获取医生详情
            doctor_id = params.get("doctor_id", "")

            if doctor_id not in self._DOCTORS:
                return {
                    "success": False,
                    "error": f"未找到医生: {doctor_id}"
                }

            doctor = self._DOCTORS[doctor_id]

            return {
                "success": True,
                "doctor": doctor
            }

        elif action == "create":
            # 创建问诊
            consult_id = f"C{datetime.now().strftime('%Y%m%d%H%M%S')}"
            patient_id = params.get("patient_id", "")
            patient_name = params.get("patient_name", "")
            doctor_id = params.get("doctor_id", "")
            consult_type = params.get("consult_type", "text")  # text, video, phone
            chief_complaint = params.get("chief_complaint", "")
            description = params.get("description", "")

            if not all([patient_id, patient_name, doctor_id, chief_complaint]):
                return {
                    "success": False,
                    "error": "请提供完整的问诊信息"
                }

            if doctor_id not in self._DOCTORS:
                return {
                    "success": False,
                    "error": f"未找到医生: {doctor_id}"
                }

            doctor = self._DOCTORS[doctor_id]
            price = doctor["price"].get(consult_type, 0)

            consultation = {
                "consult_id": consult_id,
                "patient_id": patient_id,
                "patient_name": patient_name,
                "doctor_id": doctor_id,
                "doctor_name": doctor["name"],
                "consult_type": consult_type,
                "chief_complaint": chief_complaint,
                "description": description,
                "price": price,
                "status": "waiting",  # waiting, ongoing, completed
                "created_at": datetime.now().isoformat(),
                "messages": []
            }

            self._consultations[consult_id] = consultation

            return {
                "success": True,
                "consult_id": consult_id,
                "message": f"问诊创建成功，咨询费：{price}元",
                "consultation": {
                    "consult_id": consult_id,
                    "doctor_name": doctor["name"],
                    "price": price,
                    "status": "waiting"
                }
            }

        elif action == "get_consultation":
            # 获取问诊详情
            consult_id = params.get("consult_id", "")

            if consult_id not in self._consultations:
                return {
                    "success": False,
                    "error": f"未找到问诊: {consult_id}"
                }

            return {
                "success": True,
                "consultation": self._consultations[consult_id]
            }

        elif action == "add_message":
            # 添加消息
            consult_id = params.get("consult_id", "")
            sender = params.get("sender", "")  # patient, doctor
            content = params.get("content", "")
            msg_type = params.get("msg_type", "text")  # text, image, voice

            if consult_id not in self._consultations:
                return {
                    "success": False,
                    "error": f"未找到问诊: {consult_id}"
                }

            message = {
                "id": f"MSG{len(self._consultations[consult_id]['messages']) + 1}",
                "sender": sender,
                "content": content,
                "type": msg_type,
                "timestamp": datetime.now().isoformat()
            }

            self._consultations[consult_id]["messages"].append(message)

            return {
                "success": True,
                "message_id": message["id"],
                "message": message
            }

        elif action == "list_departments":
            # 列出支持的科室
            departments = set(d["department"] for d in self._DOCTORS.values())

            return {
                "success": True,
                "departments": list(departments)
            }

        else:
            return {
                "success": False,
                "error": f"不支持的操作: {action}"
            }


# ============================================================
# 工具8: 急救指南查询
# ============================================================

class EmergencyGuideHandler(MCPToolHandler):
    """急救指南查询处理器"""

    # 急救指南数据库
    EMERGENCY_GUIDES = {
        "心脏骤停": {
            "level": "E",
            "description": "心脏突然停止跳动，是最危急的情况",
            "symptoms": ["意识丧失", "呼吸停止或异常喘息", "大动脉搏动消失"],
            "immediate_actions": [
                "立即呼叫120",
                "让患者平卧在硬质平面",
                "开始心肺复苏（CPR）：30次按压+2次人工呼吸",
                "按压位置：两乳头连线中点",
                "按压深度：5-6厘米",
                "按压频率：100-120次/分钟"
            ],
            "dont": [
                "不要等待症状缓解",
                "不要让患者进食或饮水",
                "不要随意搬动患者"
            ],
            "equipment": ["AED（自动体外除颤器）如有"]
        },
        "心肌梗死": {
            "level": "E",
            "description": "冠状动脉阻塞导致心肌缺血坏死",
            "symptoms": ["胸骨后压榨性疼痛", "放射至左肩、左臂、下颌", "大汗淋漓", "呼吸困难", "恶心呕吐"],
            "immediate_actions": [
                "立即拨打120",
                "让患者停止活动，半卧位休息",
                "如有硝酸甘油，舌下含服1片",
                "保持呼吸道通畅",
                "安抚患者情绪"
            ],
            "dont": [
                "不要让患者强行活动",
                "不要独自前往医院",
                "不要进食或饮水"
            ],
            "equipment": []
        },
        "脑卒中": {
            "level": "E",
            "description": "脑血管意外，俗称中风",
            "symptoms": ["突发肢体无力或麻木", "说话不清或理解困难", "面部歪斜", "视物模糊", "剧烈头痛"],
            "immediate_actions": [
                "立即拨打120，记录发病时间",
                "让患者平卧，头偏向一侧",
                "解开衣领，保持呼吸通畅",
                "不要给患者进食或药物",
                "尽快送至有溶栓能力的医院"
            ],
            "dont": [
                "不要等待观察",
                "不要自行服用药物",
                "不要搬动患者头部",
                "时间窗内溶栓最重要（发病3-4.5小时内）"
            ],
            "equipment": []
        },
        "严重过敏反应": {
            "level": "E",
            "description": "严重的全身性过敏反应，可危及生命",
            "symptoms": ["全身皮疹", "面部或喉头水肿", "呼吸困难", "血压下降", "意识改变"],
            "immediate_actions": [
                "立即拨打120",
                "停止接触过敏原",
                "让患者平卧，抬高下肢",
                "如有肾上腺素自动注射器，立即使用",
                "保持呼吸道通畅"
            ],
            "dont": [
                "不要继续接触可疑过敏原",
                "不要让患者站立"
            ],
            "equipment": ["肾上腺素自动注射器（如有过）"]
        },
        "气道异物梗阻": {
            "level": "E",
            "description": "异物阻塞气道，导致窒息",
            "symptoms": ["突然无法说话", "双手掐住喉咙", "剧烈咳嗽", "面色发绀", "意识丧失"],
            "immediate_actions": [
                "成人：海姆立克急救法",
                "- 站在患者身后，双臂环抱腰部",
                "- 一手握拳，拇指侧抵住上腹部",
                "- 另一手握住拳头，快速向内向上冲击",
                "儿童：适当力度施救",
                "意识丧失者：立即开始CPR"
            ],
            "dont": [
                "不要让患者饮水",
                "不要盲目拍背（清醒时）"
            ],
            "equipment": []
        },
        "严重出血": {
            "level": "A",
            "description": "大量出血，需立即止血",
            "symptoms": ["血液喷涌或快速渗出", "面色苍白", "冷汗", "血压下降"],
            "immediate_actions": [
                "立即拨打120",
                "直接压迫止血：用干净布料直接压在伤口上",
                "抬高受伤部位（高于心脏）",
                "持续压迫至少10分钟",
                "如止血带可用，可考虑使用（注意记录时间）"
            ],
            "dont": [
                "不要移除已浸透的敷料（在上面再加）",
                "不要冲洗伤口（除非轻微）"
            ],
            "equipment": ["止血带", "无菌敷料"]
        },
        "骨折": {
            "level": "A",
            "description": "骨骼完整性破坏",
            "symptoms": ["剧烈疼痛", "肿胀畸形", "活动障碍", "骨擦音或骨擦感"],
            "immediate_actions": [
                "立即拨打120",
                "不要移动受伤部位",
                "用夹板或周边物品固定",
                "固定范围包括骨折部位的上下两个关节",
                "开放性骨折：用干净布料覆盖，不要还纳"
            ],
            "dont": [
                "不要试图复位",
                "不要按摩或揉搓"
            ],
            "equipment": ["夹板", "绷带"]
        },
        "烧伤": {
            "level": "B",
            "description": "热力、化学或电能导致的组织损伤",
            "symptoms": ["皮肤红肿", "水疱", "疼痛", "皮肤碳化"],
            "immediate_actions": [
                "立即用流动凉水冲洗15-30分钟",
                "脱去受伤部位的衣物和饰品",
                "用干净布料轻轻覆盖",
                "小面积烧伤可涂抹烧伤膏"
            ],
            "dont": [
                "不要使用冰块直接冷敷",
                "不要刺破水疱",
                "不要涂抹偏方（牙膏、酱油等）"
            ],
            "equipment": ["流动凉水", "无菌敷料", "烧伤膏"]
        },
        "中暑": {
            "level": "B",
            "description": "高温环境导致的体温调节失衡",
            "symptoms": ["头晕头痛", "口渴多汗", "面色潮红", "体温升高", "意识模糊"],
            "immediate_actions": [
                "迅速转移到阴凉通风处",
                "解开衣扣，平卧休息",
                "补充含盐清凉饮料",
                "用湿毛巾擦拭身体降温",
                "重症中暑：立即拨打120"
            ],
            "dont": [
                "不要继续暴露在高温环境",
                "不要大量饮用纯水"
            ],
            "equipment": []
        },
        "低血糖": {
            "level": "C",
            "description": "血糖过低导致的症状",
            "symptoms": ["心慌手抖", "出汗", "饥饿感", "头晕", "意识模糊"],
            "immediate_actions": [
                "立即进食含糖食物（糖果、果汁、糖水）",
                "休息15分钟后复测血糖",
                "如仍未缓解，重复进食",
                "严重者：立即拨打120"
            ],
            "dont": [
                "不要强行喂食意识不清者",
                "不要等待"
            ],
            "equipment": ["葡萄糖片", "含糖饮料"]
        }
    }

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行急救指南查询"""
        action = params.get("action", "query")  # query, list, triage

        if action == "query":
            # 查询特定急救指南
            emergency_type = params.get("emergency_type", "")

            if not emergency_type:
                return {
                    "success": False,
                    "error": "请提供急救类型",
                    "available_types": list(self.EMERGENCY_GUIDES.keys())
                }

            # 模糊匹配
            matched = None
            for key in self.EMERGENCY_GUIDES.keys():
                if emergency_type in key or key in emergency_type:
                    matched = key
                    break

            if not matched:
                return {
                    "success": False,
                    "error": f"未找到「{emergency_type}」的急救指南",
                    "available_types": list(self.EMERGENCY_GUIDES.keys())
                }

            guide = self.EMERGENCY_GUIDES[matched]

            return {
                "success": True,
                "emergency_type": matched,
                "level": guide["level"],
                "guide": guide
            }

        elif action == "list":
            # 列出所有急救类型
            return {
                "success": True,
                "emergencies": [
                    {
                        "name": name,
                        "level": guide["level"],
                        "description": guide["description"]
                    }
                    for name, guide in self.EMERGENCY_GUIDES.items()
                ]
            }

        elif action == "triage":
            # 快速分诊评估
            symptoms = params.get("symptoms", [])

            if not symptoms:
                return {
                    "success": False,
                    "error": "请提供症状描述"
                }

            # 简单症状匹配
            matched_emergencies = []
            for name, guide in self.EMERGENCY_GUIDES.items():
                for symptom in symptoms:
                    if any(s in symptom for s in guide["symptoms"]):
                        matched_emergencies.append({
                            "name": name,
                            "level": guide["level"],
                            "match_reason": "症状匹配"
                        })
                        break

            # 按严重程度排序
            level_order = {"E": 0, "A": 1, "B": 2, "C": 3}
            matched_emergencies.sort(key=lambda x: level_order.get(x["level"], 99))

            if matched_emergencies:
                return {
                    "success": True,
                    "symptoms": symptoms,
                    "matched_emergencies": matched_emergencies,
                    "recommendation": "请立即拨打120" if matched_emergencies[0]["level"] == "E" else "建议尽快就医"
                }
            else:
                return {
                    "success": True,
                    "message": "未匹配到特定急救情况，建议咨询医生",
                    "symptoms": symptoms
                }

        else:
            return {
                "success": False,
                "error": f"不支持的操作: {action}"
            }


# ============================================================
# 工具9: 随访管理
# ============================================================

class FollowupManageHandler(MCPToolHandler):
    """随访管理处理器"""

    # 模拟随访计划
    _followup_plans = {
        "F001": {
            "plan_id": "F001",
            "patient_id": "P001",
            "patient_name": "张三",
            "disease": "高血压",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "frequency": "monthly",
            "status": "active",
            "items": [
                {"type": "blood_pressure", "name": "血压监测", "frequency": "weekly"},
                {"type": "medication", "name": "用药情况", "frequency": "monthly"},
                {"type": "symptom", "name": "症状评估", "frequency": "monthly"}
            ]
        }
    }

    # 随访记录
    _followup_records = {}

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行随访管理操作"""
        action = params.get("action", "query_plan")  # query_plan, create_plan, record, get_records

        if action == "query_plan":
            # 查询随访计划
            patient_id = params.get("patient_id", "")

            if not patient_id:
                return {
                    "success": False,
                    "error": "请提供患者ID"
                }

            plans = [p for p in self._followup_plans.values() if p["patient_id"] == patient_id]

            return {
                "success": True,
                "patient_id": patient_id,
                "plans": plans,
                "count": len(plans)
            }

        elif action == "create_plan":
            # 创建随访计划
            plan_id = f"F{datetime.now().strftime('%Y%m%d%H%M%S')}"
            patient_id = params.get("patient_id", "")
            patient_name = params.get("patient_name", "")
            disease = params.get("disease", "")
            frequency = params.get("frequency", "monthly")
            start_date = params.get("start_date", datetime.now().strftime("%Y-%m-%d"))
            end_date = params.get("end_date", "")
            items = params.get("items", [])

            if not all([patient_id, patient_name, disease]):
                return {
                    "success": False,
                    "error": "请提供完整的随访计划信息"
                }

            # 默认随访项目
            if not items:
                items = [
                    {"type": "symptom", "name": "症状评估", "frequency": frequency},
                    {"type": "medication", "name": "用药情况", "frequency": frequency}
                ]

            plan = {
                "plan_id": plan_id,
                "patient_id": patient_id,
                "patient_name": patient_name,
                "disease": disease,
                "start_date": start_date,
                "end_date": end_date,
                "frequency": frequency,
                "status": "active",
                "items": items
            }

            self._followup_plans[plan_id] = plan

            return {
                "success": True,
                "plan_id": plan_id,
                "message": "随访计划创建成功",
                "plan": plan
            }

        elif action == "record":
            # 记录随访数据
            record_id = f"FR{datetime.now().strftime('%Y%m%d%H%M%S')}"
            plan_id = params.get("plan_id", "")
            patient_id = params.get("patient_id", "")
            record_date = params.get("record_date", datetime.now().strftime("%Y-%m-%d"))
            data = params.get("data", {})  # {blood_pressure: {...}, medication: {...}, symptoms: [...]}

            if not all([plan_id, patient_id, data]):
                return {
                    "success": False,
                    "error": "请提供完整的随访记录信息"
                }

            if plan_id not in self._followup_plans:
                return {
                    "success": False,
                    "error": f"未找到随访计划: {plan_id}"
                }

            record = {
                "record_id": record_id,
                "plan_id": plan_id,
                "patient_id": patient_id,
                "record_date": record_date,
                "data": data,
                "created_at": datetime.now().isoformat()
            }

            self._followup_records[record_id] = record

            return {
                "success": True,
                "record_id": record_id,
                "message": "随访记录成功",
                "record": record
            }

        elif action == "get_records":
            # 获取随访记录
            patient_id = params.get("patient_id", "")
            plan_id = params.get("plan_id", "")
            limit = params.get("limit", 10)

            records = list(self._followup_records.values())

            if patient_id:
                records = [r for r in records if r["patient_id"] == patient_id]
            if plan_id:
                records = [r for r in records if r["plan_id"] == plan_id]

            # 按日期倒序
            records.sort(key=lambda x: x["record_date"], reverse=True)
            records = records[:limit]

            return {
                "success": True,
                "records": records,
                "count": len(records)
            }

        elif action == "feedback":
            # 随访反馈（医生给患者的建议）
            record_id = params.get("record_id", "")
            feedback = params.get("feedback", "")
            doctor_id = params.get("doctor_id", "")

            if not record_id or not feedback:
                return {
                    "success": False,
                    "error": "请提供记录ID和反馈内容"
                }

            if record_id in self._followup_records:
                self._followup_records[record_id]["feedback"] = {
                    "content": feedback,
                    "doctor_id": doctor_id,
                    "created_at": datetime.now().isoformat()
                }

                return {
                    "success": True,
                    "message": "反馈已记录"
                }
            else:
                return {
                    "success": False,
                    "error": f"未找到随访记录: {record_id}"
                }

        else:
            return {
                "success": False,
                "error": f"不支持的操作: {action}"
            }


# ============================================================
# 工具10: 体检套餐管理
# ============================================================

class HealthCheckupHandler(MCPToolHandler):
    """体检套餐管理处理器"""

    # 体检套餐数据库
    CHECKUP_PACKAGES = {
        "basic": {
            "id": "basic",
            "name": "基础体检套餐",
            "price": 299,
            "items": [
                {"name": "一般检查", "details": ["身高", "体重", "BMI", "血压"]},
                {"name": "内科检查", "details": ["心肺听诊", "腹部触诊"]},
                {"name": "血常规", "details": ["白细胞", "红细胞", "血红蛋白", "血小板"]},
                {"name": "尿常规", "details": ["比重", "pH", "蛋白", "葡萄糖", "白细胞"]},
                {"name": "肝功能", "details": ["ALT", "AST"]},
                {"name": "肾功能", "details": ["肌酐", "尿素氮"]},
                {"name": "空腹血糖", "details": ["GLU"]},
                {"name": "血脂", "details": ["总胆固醇", "甘油三酯"]},
                {"name": "心电图", "details": ["12导联心电图"]},
                {"name": "胸片", "details": ["胸部正位片"]}
            ],
            "suitable_for": "20-35岁健康人群基础健康体检",
            "duration": "半天",
            "notice": ["需空腹8-12小时", "体检前3天清淡饮食"]
        },
        "standard": {
            "id": "standard",
            "name": "标准体检套餐",
            "price": 699,
            "items": [
                {"name": "一般检查", "details": ["身高", "体重", "BMI", "血压", "体脂率"]},
                {"name": "内科检查", "details": ["心肺听诊", "腹部触诊"]},
                {"name": "外科检查", "details": ["浅表淋巴结", "甲状腺触诊"]},
                {"name": "血常规", "details": ["白细胞", "红细胞", "血红蛋白", "血小板", "血细胞比容"]},
                {"name": "尿常规", "details": ["全项"]},
                {"name": "肝功能", "details": ["ALT", "AST", "GGT", "总胆红素", "白蛋白"]},
                {"name": "肾功能", "details": ["肌酐", "尿素氮", "尿酸"]},
                {"name": "空腹血糖", "details": ["GLU"]},
                {"name": "血脂四项", "details": ["总胆固醇", "甘油三酯", "HDL-C", "LDL-C"]},
                {"name": "肿瘤标志物", "details": ["CEA", "AFP"]},
                {"name": "甲状腺功能", "details": ["TSH", "FT3", "FT4"]},
                {"name": "心电图", "details": ["12导联心电图"]},
                {"name": "腹部B超", "details": ["肝", "胆", "胰", "脾", "肾"]},
                {"name": "胸片", "details": ["胸部正位片"]}
            ],
            "suitable_for": "35-50岁人群定期体检",
            "duration": "1天",
            "notice": ["需空腹8-12小时", "体检前3天清淡饮食", "避免剧烈运动"]
        },
        "senior": {
            "id": "senior",
            "name": "高端体检套餐",
            "price": 1599,
            "items": [
                {"name": "一般检查", "details": ["身高", "体重", "BMI", "血压", "体脂率", "骨密度"]},
                {"name": "内科检查", "details": ["全面查体"]},
                {"name": "外科检查", "details": ["全身浅表器官"]},
                {"name": "眼科检查", "details": ["视力", "眼压", "眼底"]},
                {"name": "耳鼻喉科", "details": ["耳鼻喉常规检查"]},
                {"name": "口腔科", "details": ["牙齿", "牙周", "黏膜"]},
                {"name": "血常规", "details": ["全血细胞计数"]},
                {"name": "尿常规", "details": ["全项+沉渣"]},
                {"name": "肝功能", "details": ["全套"]},
                {"name": "肾功能", "details": ["全套"]},
                {"name": "血糖", "details": ["空腹血糖", "糖化血红蛋白"]},
                {"name": "血脂全套", "details": ["7项"]},
                {"name": "心肌酶谱", "details": ["CK", "CK-MB", "LDH"]},
                {"name": "肿瘤标志物", "details": ["CEA", "AFP", "CA19-9", "CA125", "PSA(男)"]},
                {"name": "甲状腺功能", "details": ["全套"]},
                {"name": "同型半胱氨酸", "details": ["Hcy"]},
                {"name": "心电图", "details": ["12导联+运动试验(可选)"]},
                {"name": "心脏彩超", "details": ["心脏结构与功能"]},
                {"name": "颈部血管彩超", "details": ["颈动脉", "椎动脉"]},
                {"name": "腹部B超", "details": ["全腹部"]},
                {"name": "甲状腺彩超", "details": ["甲状腺"]},
                {"name": "低剂量CT", "details": ["肺部"]},
                {"name": "头颅MRI", "details": ["脑部(可选)"]}
            ],
            "suitable_for": "50岁以上人群或有慢性病人群",
            "duration": "1-2天",
            "notice": ["需空腹8-12小时", "体检前3天清淡饮食", "体检前1天禁止饮酒", "女性避开月经期"]
        },
        "executive": {
            "id": "executive",
            "name": "VIP尊享套餐",
            "price": 3999,
            "items": [
                {"name": "包含高端套餐所有项目", "details": []},
                {"name": "PET-CT", "details": ["全身肿瘤筛查"]},
                {"name": "心脏CTA", "details": ["冠状动脉成像"]},
                {"name": "头颈CTA", "details": ["脑血管成像"]},
                {"name": "胃肠镜", "details": ["无痛胃肠镜"]},
                {"name": "基因检测", "details": ["肿瘤易感基因筛查"]},
                {"name": "营养评估", "details": ["人体成分分析", "营养咨询"]},
                {"name": "中医体质辨识", "details": ["中医问诊", "舌诊", "脉诊"]}
            ],
            "suitable_for": "高端健康体检需求人群",
            "duration": "2天",
            "notice": ["需预约", "需空腹", "无痛胃肠镜需麻醉评估"],
            "vip_service": ["VIP通道", "一对一导诊", "专家报告解读", "营养早餐", "免费停车"]
        }
    }

    # 体检预约记录
    _checkup_bookings = {}

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行体检套餐操作"""
        action = params.get("action", "list_packages")  # list_packages, get_package, book, get_booking

        if action == "list_packages":
            # 列出所有套餐
            return {
                "success": True,
                "packages": [
                    {
                        "id": pkg["id"],
                        "name": pkg["name"],
                        "price": pkg["price"],
                        "item_count": len(pkg["items"]),
                        "suitable_for": pkg["suitable_for"]
                    }
                    for pkg in self.CHECKUP_PACKAGES.values()
                ]
            }

        elif action == "get_package":
            # 获取套餐详情
            package_id = params.get("package_id", "")

            if package_id not in self.CHECKUP_PACKAGES:
                return {
                    "success": False,
                    "error": f"未找到套餐: {package_id}",
                    "available": list(self.CHECKUP_PACKAGES.keys())
                }

            return {
                "success": True,
                "package": self.CHECKUP_PACKAGES[package_id]
            }

        elif action == "book":
            # 预约体检
            booking_id = f"CB{datetime.now().strftime('%Y%m%d%H%M%S')}"
            package_id = params.get("package_id", "")
            patient_name = params.get("patient_name", "")
            patient_id = params.get("patient_id", "")
            appointment_date = params.get("appointment_date", "")
            phone = params.get("phone", "")

            if not all([package_id, patient_name, appointment_date]):
                return {
                    "success": False,
                    "error": "请提供完整的预约信息"
                }

            if package_id not in self.CHECKUP_PACKAGES:
                return {
                    "success": False,
                    "error": f"未找到套餐: {package_id}"
                }

            package = self.CHECKUP_PACKAGES[package_id]

            booking = {
                "booking_id": booking_id,
                "package_id": package_id,
                "package_name": package["name"],
                "price": package["price"],
                "patient_id": patient_id,
                "patient_name": patient_name,
                "phone": phone,
                "appointment_date": appointment_date,
                "status": "confirmed",
                "created_at": datetime.now().isoformat()
            }

            self._checkup_bookings[booking_id] = booking

            return {
                "success": True,
                "booking_id": booking_id,
                "message": f"体检预约成功！套餐：{package['name']}，日期：{appointment_date}",
                "booking": booking,
                "notice": package.get("notice", [])
            }

        elif action == "get_booking":
            # 查询预约
            booking_id = params.get("booking_id", "")
            patient_id = params.get("patient_id", "")

            if booking_id:
                if booking_id in self._checkup_bookings:
                    return {
                        "success": True,
                        "booking": self._checkup_bookings[booking_id]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"未找到预约: {booking_id}"
                    }
            elif patient_id:
                bookings = [b for b in self._checkup_bookings.values() if b["patient_id"] == patient_id]
                return {
                    "success": True,
                    "bookings": bookings
                }
            else:
                return {
                    "success": False,
                    "error": "请提供预约ID或患者ID"
                }

        elif action == "recommend":
            # 套餐推荐
            age = params.get("age", 0)
            gender = params.get("gender", "")
            has_chronic_disease = params.get("has_chronic_disease", False)

            if not age:
                return {
                    "success": False,
                    "error": "请提供年龄信息"
                }

            # 推荐逻辑
            if age < 35:
                recommended = "basic"
            elif age < 50:
                recommended = "standard"
            elif has_chronic_disease:
                recommended = "senior"
            else:
                recommended = "senior"

            return {
                "success": True,
                "age": age,
                "recommended_package": self.CHECKUP_PACKAGES[recommended],
                "reason": f"根据{age}岁年龄特点推荐"
            }

        else:
            return {
                "success": False,
                "error": f"不支持的操作: {action}"
            }


# ============================================================
# 工具11: 提醒服务
# ============================================================

class ReminderManageHandler(MCPToolHandler):
    """提醒服务处理器"""

    # 提醒类型
    REMINDER_TYPES = {
        "medication": {
            "name": "用药提醒",
            "template": "请服用 {medication}，剂量：{dosage}",
            "repeat_options": ["daily", "specific_days", "as_needed"]
        },
        "appointment": {
            "name": "就诊预约提醒",
            "template": "您已预约 {department} {doctor} 医生，时间：{datetime}",
            "repeat_options": ["once"]
        },
        "checkup": {
            "name": "体检提醒",
            "template": "您预约的体检时间：{datetime}，地点：{location}",
            "repeat_options": ["once", "yearly"]
        },
        "followup": {
            "name": "随访提醒",
            "template": "请记录您的 {disease} 随访数据",
            "repeat_options": ["daily", "weekly", "monthly"]
        },
        "refill": {
            "name": "续药提醒",
            "template": "您的 {medication} 即将用完，请及时续方",
            "repeat_options": ["once"]
        },
        "measurement": {
            "name": "测量提醒",
            "template": "请测量 {item}（血压/血糖等）",
            "repeat_options": ["daily", "weekly", "specific_days"]
        }
    }

    # 提醒记录
    _reminders = {}
    _reminder_counter = 0

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行提醒服务操作"""
        action = params.get("action", "create")  # create, list, get, update, delete, complete

        if action == "create":
            # 创建提醒
            self._reminder_counter += 1
            reminder_id = f"REM{self._reminder_counter:06d}"

            user_id = params.get("user_id", "")
            reminder_type = params.get("reminder_type", "")
            title = params.get("title", "")
            content = params.get("content", "")
            remind_time = params.get("remind_time", "")  # HH:MM
            repeat = params.get("repeat", "once")  # once, daily, weekly, monthly, specific_days
            specific_days = params.get("specific_days", [])  # [1, 2, 3] 周一二三
            extra_data = params.get("extra_data", {})

            if not all([user_id, reminder_type, title, remind_time]):
                return {
                    "success": False,
                    "error": "请提供完整的提醒信息"
                }

            if reminder_type not in self.REMINDER_TYPES:
                return {
                    "success": False,
                    "error": f"不支持的提醒类型: {reminder_type}",
                    "available": list(self.REMINDER_TYPES.keys())
                }

            reminder = {
                "reminder_id": reminder_id,
                "user_id": user_id,
                "reminder_type": reminder_type,
                "title": title,
                "content": content,
                "remind_time": remind_time,
                "repeat": repeat,
                "specific_days": specific_days,
                "extra_data": extra_data,
                "status": "active",
                "created_at": datetime.now().isoformat()
            }

            self._reminders[reminder_id] = reminder

            return {
                "success": True,
                "reminder_id": reminder_id,
                "message": "提醒创建成功",
                "reminder": reminder
            }

        elif action == "list":
            # 列出提醒
            user_id = params.get("user_id", "")
            status = params.get("status", "")  # active, completed, cancelled

            if not user_id:
                return {
                    "success": False,
                    "error": "请提供用户ID"
                }

            reminders = list(self._reminders.values())

            if user_id:
                reminders = [r for r in reminders if r["user_id"] == user_id]
            if status:
                reminders = [r for r in reminders if r.get("status") == status]

            return {
                "success": True,
                "reminders": reminders,
                "count": len(reminders)
            }

        elif action == "get":
            # 获取单个提醒
            reminder_id = params.get("reminder_id", "")

            if reminder_id not in self._reminders:
                return {
                    "success": False,
                    "error": f"未找到提醒: {reminder_id}"
                }

            return {
                "success": True,
                "reminder": self._reminders[reminder_id]
            }

        elif action == "update":
            # 更新提醒
            reminder_id = params.get("reminder_id", "")
            updates = params.get("updates", {})

            if reminder_id not in self._reminders:
                return {
                    "success": False,
                    "error": f"未找到提醒: {reminder_id}"
                }

            # 更新字段
            for key, value in updates.items():
                if key in self._reminders[reminder_id] and key not in ["reminder_id", "user_id", "created_at"]:
                    self._reminders[reminder_id][key] = value

            return {
                "success": True,
                "message": "提醒更新成功",
                "reminder": self._reminders[reminder_id]
            }

        elif action == "delete":
            # 删除提醒
            reminder_id = params.get("reminder_id", "")

            if reminder_id not in self._reminders:
                return {
                    "success": False,
                    "error": f"未找到提醒: {reminder_id}"
                }

            self._reminders[reminder_id]["status"] = "cancelled"

            return {
                "success": True,
                "message": "提醒已取消"
            }

        elif action == "complete":
            # 标记提醒已完成
            reminder_id = params.get("reminder_id", "")

            if reminder_id not in self._reminders:
                return {
                    "success": False,
                    "error": f"未找到提醒: {reminder_id}"
                }

            self._reminders[reminder_id]["status"] = "completed"
            self._reminders[reminder_id]["completed_at"] = datetime.now().isoformat()

            # 处理重复提醒
            reminder = self._reminders[reminder_id]
            if reminder["repeat"] != "once":
                return {
                    "success": True,
                    "message": "提醒已完成（重复提醒将继续生效）",
                    "reminder": reminder,
                    "is_recurring": True
                }

            return {
                "success": True,
                "message": "提醒已完成",
                "reminder": reminder,
                "is_recurring": False
            }

        elif action == "get_types":
            # 获取提醒类型
            return {
                "success": True,
                "reminder_types": [
                    {
                        "type": key,
                        "name": value["name"],
                        "template": value["template"],
                        "repeat_options": value["repeat_options"]
                    }
                    for key, value in self.REMINDER_TYPES.items()
                ]
            }

        else:
            return {
                "success": False,
                "error": f"不支持的操作: {action}"
            }


# ============================================================
# 创建MCP服务器并注册所有工具
# ============================================================

async def create_medical_mcp_server(host: MCPHost) -> MCPServer:
    """创建医疗MCP服务器并注册所有工具"""

    # 创建服务器
    server = MCPFactory.create_server(
        server_id="medical-mcp-server",
        name="医疗MCP服务器",
        host="localhost",
        port=50051,
        mcp_host=host,
        protocol="grpc"
    )

    # ========== 工具1: 医学知识查询 ==========
    server.register_tool(
        MCPTool(
            name="medical_knowledge_query",
            description="查询医学知识，包括症状描述、常见病因、红旗征、推荐科室等",
            category="medical_knowledge",
            input_schema={
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["symptom", "disease"],
                        "description": "查询类型"
                    },
                    "keyword": {
                        "type": "string",
                        "description": "关键词（症状或疾病名称）"
                    }
                },
                "required": ["keyword"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"type": "object"},
                    "error": {"type": "string"}
                }
            }
        ),
        MedicalKnowledgeHandler()
    )

    # ========== 工具2: 医院科室查询 ==========
    server.register_tool(
        MCPTool(
            name="hospital_department_query",
            description="查询医院科室信息，根据症状推荐挂号科室",
            category="hospital",
            input_schema={
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["list", "by_symptom", "detail"],
                        "description": "查询类型"
                    },
                    "symptom": {
                        "type": "string",
                        "description": "症状描述"
                    },
                    "department": {
                        "type": "string",
                        "description": "科室名称"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "departments": {"type": "array"},
                    "recommendations": {"type": "array"}
                }
            }
        ),
        HospitalDepartmentHandler()
    )

    # ========== 工具3: 药品数据库查询 ==========
    server.register_tool(
        MCPTool(
            name="drug_database_query",
            description="查询药品信息，包括用法用量、副作用、禁忌症、药物相互作用等",
            category="drug",
            input_schema={
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["info", "dosage", "interaction", "side_effects"],
                        "description": "查询类型"
                    },
                    "drug_name": {
                        "type": "string",
                        "description": "药品名称"
                    },
                    "other_drug": {
                        "type": "string",
                        "description": "其他药品（查询相互作用时使用）"
                    }
                },
                "required": ["drug_name"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "info": {"type": "object"}
                }
            }
        ),
        DrugDatabaseHandler()
    )

    # ========== 工具4: 预约挂号 ==========
    server.register_tool(
        MCPTool(
            name="appointment_booking",
            description="预约挂号服务，支持查询号源、预约、取消预约等操作",
            category="appointment",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["query_availability", "book", "cancel", "list", "list_departments"],
                        "description": "操作类型"
                    },
                    "department": {
                        "type": "string",
                        "description": "科室"
                    },
                    "doctor": {
                        "type": "string",
                        "description": "医生姓名"
                    },
                    "patient_name": {
                        "type": "string",
                        "description": "患者姓名"
                    },
                    "appointment_time": {
                        "type": "string",
                        "description": "预约时间"
                    },
                    "appointment_id": {
                        "type": "string",
                        "description": "预约号"
                    },
                    "date": {
                        "type": "string",
                        "description": "日期"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "appointment_id": {"type": "string"},
                    "message": {"type": "string"}
                }
            }
        ),
        AppointmentBookingHandler()
    )

    # ========== 工具5: 检查报告解读 ==========
    server.register_tool(
        MCPTool(
            name="lab_report_query",
            description="检查报告解读，支持血常规、生化、尿常规、凝血功能、肿瘤标志物等参考范围查询和异常解读",
            category="lab",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["interpret", "reference", "list_categories"],
                        "description": "操作类型"
                    },
                    "category": {
                        "type": "string",
                        "description": "检查类别（血常规、生化、尿常规等）"
                    },
                    "item": {
                        "type": "string",
                        "description": "检查项目"
                    },
                    "results": {
                        "type": "object",
                        "description": "检查结果 {项目: 值}"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "abnormal_items": {"type": "array"},
                    "suggestions": {"type": "array"}
                }
            }
        ),
        LabReportHandler()
    )

    # ========== 工具6: 慢病管理数据 ==========
    server.register_tool(
        MCPTool(
            name="chronic_disease_query",
            description="慢病管理数据服务，支持患者慢病信息查询、监测数据记录、趋势分析、控制目标查询",
            category="chronic",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["query", "record", "analyze", "targets", "get_medication_reminder"],
                        "description": "操作类型"
                    },
                    "patient_id": {
                        "type": "string",
                        "description": "患者ID"
                    },
                    "record_type": {
                        "type": "string",
                        "enum": ["blood_pressure", "blood_glucose"],
                        "description": "记录类型"
                    },
                    "value": {
                        "type": "object",
                        "description": "监测值"
                    },
                    "condition": {
                        "type": "string",
                        "description": "疾病名称"
                    },
                    "days": {
                        "type": "integer",
                        "description": "分析天数"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "analysis": {"type": "object"},
                    "targets": {"type": "object"}
                }
            }
        ),
        ChronicDiseaseHandler()
    )

    # ========== 工具7: 在线问诊服务 ==========
    server.register_tool(
        MCPTool(
            name="online_consult",
            description="在线问诊服务，支持医生列表查询、创建问诊、发送消息",
            category="consult",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list_doctors", "get_doctor", "create", "get_consultation", "add_message", "list_departments"],
                        "description": "操作类型"
                    },
                    "doctor_id": {
                        "type": "string",
                        "description": "医生ID"
                    },
                    "department": {
                        "type": "string",
                        "description": "科室"
                    },
                    "patient_id": {
                        "type": "string",
                        "description": "患者ID"
                    },
                    "patient_name": {
                        "type": "string",
                        "description": "患者姓名"
                    },
                    "consult_type": {
                        "type": "string",
                        "enum": ["text", "video", "phone"],
                        "description": "问诊类型"
                    },
                    "chief_complaint": {
                        "type": "string",
                        "description": "主诉"
                    },
                    "consult_id": {
                        "type": "string",
                        "description": "问诊ID"
                    },
                    "sender": {
                        "type": "string",
                        "description": "发送者"
                    },
                    "content": {
                        "type": "string",
                        "description": "消息内容"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "doctors": {"type": "array"},
                    "consult_id": {"type": "string"}
                }
            }
        ),
        OnlineConsultHandler()
    )

    # ========== 工具8: 急救指南查询 ==========
    server.register_tool(
        MCPTool(
            name="emergency_guide",
            description="急救指南查询，支持常见急救场景处理指导、快速分诊评估",
            category="emergency",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["query", "list", "triage"],
                        "description": "操作类型"
                    },
                    "emergency_type": {
                        "type": "string",
                        "description": "急救类型（心脏骤停、心肌梗死、脑卒中等）"
                    },
                    "symptoms": {
                        "type": "array",
                        "description": "症状列表"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "level": {"type": "string"},
                    "guide": {"type": "object"}
                }
            }
        ),
        EmergencyGuideHandler()
    )

    # ========== 工具9: 随访管理 ==========
    server.register_tool(
        MCPTool(
            name="followup_manage",
            description="随访管理服务，支持随访计划创建、随访记录、医生反馈",
            category="followup",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["query_plan", "create_plan", "record", "get_records", "feedback"],
                        "description": "操作类型"
                    },
                    "patient_id": {
                        "type": "string",
                        "description": "患者ID"
                    },
                    "plan_id": {
                        "type": "string",
                        "description": "计划ID"
                    },
                    "disease": {
                        "type": "string",
                        "description": "疾病名称"
                    },
                    "frequency": {
                        "type": "string",
                        "description": "随访频率"
                    },
                    "data": {
                        "type": "object",
                        "description": "随访数据"
                    },
                    "feedback": {
                        "type": "string",
                        "description": "反馈内容"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "plan_id": {"type": "string"},
                    "records": {"type": "array"}
                }
            }
        ),
        FollowupManageHandler()
    )

    # ========== 工具10: 体检套餐管理 ==========
    server.register_tool(
        MCPTool(
            name="health_checkup",
            description="体检套餐管理，支持套餐查询、预约、推荐",
            category="checkup",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list_packages", "get_package", "book", "get_booking", "recommend"],
                        "description": "操作类型"
                    },
                    "package_id": {
                        "type": "string",
                        "description": "套餐ID"
                    },
                    "patient_name": {
                        "type": "string",
                        "description": "患者姓名"
                    },
                    "patient_id": {
                        "type": "string",
                        "description": "患者ID"
                    },
                    "appointment_date": {
                        "type": "string",
                        "description": "预约日期"
                    },
                    "age": {
                        "type": "integer",
                        "description": "年龄（用于推荐）"
                    },
                    "booking_id": {
                        "type": "string",
                        "description": "预约ID"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "packages": {"type": "array"},
                    "booking_id": {"type": "string"}
                }
            }
        ),
        HealthCheckupHandler()
    )

    # ========== 工具11: 提醒服务 ==========
    server.register_tool(
        MCPTool(
            name="reminder_manage",
            description="提醒服务，支持用药提醒、就诊提醒、随访提醒、测量提醒等多种类型",
            category="reminder",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "list", "get", "update", "delete", "complete", "get_types"],
                        "description": "操作类型"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "用户ID"
                    },
                    "reminder_type": {
                        "type": "string",
                        "description": "提醒类型"
                    },
                    "title": {
                        "type": "string",
                        "description": "提醒标题"
                    },
                    "content": {
                        "type": "string",
                        "description": "提醒内容"
                    },
                    "remind_time": {
                        "type": "string",
                        "description": "提醒时间 HH:MM"
                    },
                    "repeat": {
                        "type": "string",
                        "description": "重复规则"
                    },
                    "reminder_id": {
                        "type": "string",
                        "description": "提醒ID"
                    },
                    "status": {
                        "type": "string",
                        "description": "状态筛选"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "reminder_id": {"type": "string"},
                    "reminders": {"type": "array"}
                }
            }
        ),
        ReminderManageHandler()
    )

    return server


# ============================================================
# 使用示例
# ============================================================

async def main():
    """演示MCP工具的使用"""

    # 创建Host
    host = MCPFactory.create_host("medical-mcp-host")
    await host.start()

    # 创建服务器
    server = await create_medical_mcp_server(host)
    await server.start()

    print("\n" + "="*60)
    print("医疗MCP服务器已启动")
    print("="*60)

    # 创建客户端
    from mcp_protocol.mcp_protocol import MCPClient
    client = MCPClient("test-client", host)
    await client.start()

    print("\n=== 测试1: 医学知识查询 ===")
    result = await client.call_tool(
        "medical_knowledge_query",
        {"query_type": "symptom", "keyword": "头痛"}
    )
    print(json.dumps(result.data, ensure_ascii=False, indent=2))

    print("\n=== 测试2: 医院科室查询 ===")
    result = await client.call_tool(
        "hospital_department_query",
        {"query_type": "by_symptom", "symptom": "头痛"}
    )
    print(json.dumps(result.data, ensure_ascii=False, indent=2))

    print("\n=== 测试3: 药品数据库查询 ===")
    result = await client.call_tool(
        "drug_database_query",
        {"query_type": "info", "drug_name": "阿莫西林"}
    )
    print(json.dumps(result.data, ensure_ascii=False, indent=2))

    print("\n=== 测试4: 预约挂号 ===")
    result = await client.call_tool(
        "appointment_booking",
        {
            "action": "book",
            "department": "内科",
            "doctor": "张医生",
            "patient_name": "张三",
            "appointment_time": "2024-01-15 09:00"
        }
    )
    print(json.dumps(result.data, ensure_ascii=False, indent=2))

    # 停止服务
    await client.stop()
    await server.stop()
    await host.stop()
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
