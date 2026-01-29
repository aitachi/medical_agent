"""
医疗领域 MCP 工具实现
包含4个核心工具：
1. medical_knowledge_query - 医学知识查询
2. hospital_department_query - 医院科室查询
3. drug_database_query - 药品数据库查询
4. appointment_booking - 预约挂号
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
