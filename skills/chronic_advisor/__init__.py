# -*- coding: utf-8 -*-
"""
慢病咨询Skill
提供慢病管理咨询，包括用药指导、生活方式建议、并发症预防等
"""

import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class DiseaseType(Enum):
    """疾病类型"""
    HYPERTENSION = "hypertension"    # 高血压
    DIABETES = "diabetes"            # 糖尿病
    HYPERLIPIDEMIA = "hyperlipidemia"# 高血脂
    CORONARY = "coronary"            # 冠心病
    COPD = "copd"                    # 慢阻肺
    GOUT = "gout"                    # 痛风
    STROKE = "stroke"                # 脑卒中


@dataclass
class AdvisoryResult:
    """咨询结果"""
    disease: str
    topic: str
    content: str
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ChronicAdvisorSkill:
    """
    慢病咨询Skill
    提供慢病管理咨询，包括用药指导、生活方式建议、并发症预防等
    """

    # 慢病知识库
    DISEASE_KNOWLEDGE = {
        DiseaseType.HYPERTENSION: {
            "description": "高血压是以血压升高为主要特征的慢性病，长期高血压可损害心、脑、肾等器官。",
            "causes": ["遗传因素", "高盐饮食", "肥胖", "缺乏运动", "精神紧张", "吸烟饮酒"],
            "symptoms": ["头痛头晕", "心悸", "耳鸣", "视力模糊", "颈项僵硬"],
            "complications": ["心脏病", "脑卒中", "肾衰竭", "眼底病变", "动脉硬化"],
            "medication_principles": [
                "长期规律服药，不能擅自停药",
                "从小剂量开始，逐渐调整",
                "优先选择长效制剂",
                "联合用药可增强效果减少副作用"
            ],
            "lifestyle": {
                "diet": [
                    "低盐饮食，每日食盐<6g",
                    "低脂饮食，少吃动物内脏",
                    "多吃蔬菜水果",
                    "限制饮酒",
                    "戒烟"
                ],
                "exercise": [
                    "每周3-5次有氧运动",
                    "每次30分钟以上",
                    "选择散步、游泳、太极拳等",
                    "避免剧烈运动"
                ],
                "monitoring": [
                    "每日监测血压",
                    "记录血压变化",
                    "定期复查心肾功能"
                ]
            }
        },
        DiseaseType.DIABETES: {
            "description": "糖尿病是一种代谢性疾病，以高血糖为特征，长期高血糖可导致多种并发症。",
            "causes": ["遗传因素", "肥胖", "不良饮食习惯", "缺乏运动", "年龄因素"],
            "symptoms": ["多饮多尿", "多食", "体重下降", "乏力", "视力模糊"],
            "complications": ["视网膜病变", "肾病", "神经病变", "心血管疾病", "足病"],
            "medication_principles": [
                "根据血糖水平选择药物",
                "遵医嘱规律用药",
                "注意低血糖反应",
                "定期监测糖化血红蛋白"
            ],
            "lifestyle": {
                "diet": [
                    "控制碳水化合物摄入",
                    "选择低升糖指数食物",
                    "少量多餐",
                    "限制甜食和含糖饮料",
                    "高纤维饮食"
                ],
                "exercise": [
                    "每周至少150分钟运动",
                    "饭后散步30分钟",
                    "避免空腹运动",
                    "随身携带糖块"
                ],
                "monitoring": [
                    "定期监测空腹血糖",
                    "定期监测餐后血糖",
                    "每3个月查糖化血红蛋白"
                ]
            }
        },
        DiseaseType.HYPERLIPIDEMIA: {
            "description": "高血脂是指血液中胆固醇或甘油三酯水平升高，是心血管疾病的重要危险因素。",
            "causes": ["遗传因素", "高脂饮食", "缺乏运动", "肥胖", "年龄因素"],
            "symptoms": ["通常无明显症状", "严重时可出现头晕乏力"],
            "complications": ["动脉粥样硬化", "冠心病", "脑卒中", "胰腺炎"],
            "medication_principles": [
                "根据血脂异常类型选择药物",
                "他汀类药物晚上服用效果更好",
                "注意肝功能和肌肉症状",
                "长期用药定期复查"
            ],
            "lifestyle": {
                "diet": [
                    "低脂饮食",
                    "少吃动物内脏和油炸食品",
                    "多吃蔬菜水果和粗粮",
                    "限制酒精"
                ],
                "exercise": [
                    "每周运动5次以上",
                    "有氧运动为主",
                    "控制体重"
                ],
                "monitoring": [
                    "定期检测血脂",
                    "关注肝功能"
                ]
            }
        },
        DiseaseType.GOUT: {
            "description": "痛风是由于尿酸代谢异常导致尿酸盐沉积的疾病，常表现为关节疼痛。",
            "causes": ["高嘌呤饮食", "饮酒", "肥胖", "遗传因素", "肾功能不全"],
            "symptoms": ["关节红肿热痛", "多发于拇趾", "夜间发作"],
            "complications": ["痛风石", "关节畸形", "肾结石", "肾功能损害"],
            "medication_principles": [
                "急性期抗炎止痛",
                "缓解期降尿酸治疗",
                "小剂量开始逐渐加量",
                "多喝水促进尿酸排泄"
            ],
            "lifestyle": {
                "diet": [
                    "严格低嘌呤饮食",
                    "避免动物内脏、海鲜、浓汤",
                    "禁酒尤其是啤酒",
                    "多喝水每日2000ml以上"
                ],
                "exercise": [
                    "缓解期适度运动",
                    "避免剧烈运动",
                    "控制体重"
                ],
                "monitoring": [
                    "定期检测尿酸",
                    "关注肾功能"
                ]
            }
        },
        DiseaseType.CORONARY: {
            "description": "冠心病是冠状动脉粥样硬化性心脏病的简称，是由于冠状动脉狭窄导致心肌缺血的疾病。",
            "causes": ["高血脂", "高血压", "糖尿病", "吸烟", "肥胖", "缺乏运动"],
            "symptoms": ["胸痛胸闷", "心悸气短", "活动后加重"],
            "complications": ["心肌梗死", "心力衰竭", "心律失常", "猝死"],
            "medication_principles": [
                "长期服用抗血小板药物",
                "控制危险因素",
                "随身携带硝酸甘油",
                "定期复查"
            ],
            "lifestyle": {
                "diet": ["低盐低脂", "地中海饮食", "控制体重"],
                "exercise": ["适度有氧运动", "避免剧烈运动", "注意症状变化"],
                "monitoring": ["定期心电图", "关注胸痛症状"]
            }
        },
        DiseaseType.COPD: {
            "description": "慢阻肺是慢性阻塞性肺疾病的简称，是一种常见的慢性呼吸系统疾病。",
            "causes": ["吸烟", "空气污染", "职业暴露", "感染"],
            "symptoms": ["慢性咳嗽", "咳痰", "气短", "活动后呼吸困难"],
            "complications": ["肺心病", "呼吸衰竭", "肺大泡"],
            "medication_principles": [
                "规律使用支气管舒张剂",
                "急性期加用激素",
                "长期氧疗",
                "接种流感疫苗和肺炎疫苗"
            ],
            "lifestyle": {
                "diet": ["高蛋白饮食", "充足热量"],
                "exercise": ["肺功能锻炼", "呼吸训练"],
                "monitoring": ["定期肺功能检查", "关注症状变化"]
            }
        }
    }

    def __init__(self, mcp_client=None):
        """
        初始化慢病咨询Skill

        Args:
            mcp_client: MCP客户端，用于调用外部慢病管理系统
        """
        self.mcp_client = mcp_client

    async def advise(
        self,
        disease: str,
        topic: str = "general"
    ) -> AdvisoryResult:
        """
        提供慢病咨询

        Args:
            disease: 疾病类型
            topic: 咨询主题

        Returns:
            AdvisoryResult: 咨询结果
        """
        # 转换疾病类型
        try:
            disease_enum = DiseaseType(disease.lower())
        except ValueError:
            return AdvisoryResult(
                disease=disease,
                topic=topic,
                content=f"抱歉，暂不支持{disease}相关咨询。支持的疾病包括：高血压、糖尿病、高血脂、痛风、冠心病、慢阻肺。",
                warnings=["如有疑问请咨询专科医生"]
            )

        knowledge = self.DISEASE_KNOWLEDGE.get(disease_enum)

        if not knowledge:
            return AdvisoryResult(
                disease=disease,
                topic=topic,
                content=f"抱歉，暂未找到{disease}相关知识。",
                warnings=["如有疑问请咨询专科医生"]
            )

        # 根据主题生成内容
        content = ""
        recommendations = []
        warnings = []

        if topic == "description" or topic == "general":
            content = self._format_disease_description(disease, knowledge)
        elif topic == "diet":
            content, recommendations = self._format_diet_advice(disease, knowledge)
        elif topic == "exercise":
            content, recommendations = self._format_exercise_advice(disease, knowledge)
        elif topic == "medication":
            content, recommendations = self._format_medication_advice(disease, knowledge)
        elif topic == "complications":
            content = self._format_complications(disease, knowledge)
        elif topic == "monitoring":
            content, recommendations = self._format_monitoring_advice(disease, knowledge)
        else:
            content = self._format_disease_description(disease, knowledge)

        warnings.extend([
            "以上信息仅供参考",
            "请遵医嘱进行治疗",
            "如有不适及时就医"
        ])

        return AdvisoryResult(
            disease=disease,
            topic=topic,
            content=content,
            recommendations=recommendations,
            warnings=warnings
        )

    def _format_disease_description(self, disease: str, knowledge: Dict) -> str:
        """格式化疾病描述"""
        content = f"## {self._get_disease_name(disease)}\n\n"
        content += f"{knowledge['description']}\n\n"

        content += "### 📋 常见症状\n\n"
        for symptom in knowledge.get('symptoms', []):
            content += f"- {symptom}\n"
        content += "\n"

        content += "### 🔍 病因\n\n"
        for cause in knowledge.get('causes', []):
            content += f"- {cause}\n"
        content += "\n"

        return content

    def _format_diet_advice(self, disease: str, knowledge: Dict) -> tuple:
        """格式化饮食建议"""
        content = f"## {self._get_disease_name(disease)} - 饮食建议\n\n"
        recommendations = []

        lifestyle = knowledge.get('lifestyle', {})
        diet_advice = lifestyle.get('diet', [])

        if diet_advice:
            content += "### 🥗 饮食原则\n\n"
            for advice in diet_advice:
                content += f"- {advice}\n"
                recommendations.append(advice)
            content += "\n"

        return content, recommendations

    def _format_exercise_advice(self, disease: str, knowledge: Dict) -> tuple:
        """格式化运动建议"""
        content = f"## {self._get_disease_name(disease)} - 运动建议\n\n"
        recommendations = []

        lifestyle = knowledge.get('lifestyle', {})
        exercise_advice = lifestyle.get('exercise', [])

        if exercise_advice:
            content += "### 🏃 运动原则\n\n"
            for advice in exercise_advice:
                content += f"- {advice}\n"
                recommendations.append(advice)
            content += "\n"

        return content, recommendations

    def _format_medication_advice(self, disease: str, knowledge: Dict) -> tuple:
        """格式化用药建议"""
        content = f"## {self._get_disease_name(disease)} - 用药指导\n\n"
        recommendations = []

        medication = knowledge.get('medication_principles', [])

        if medication:
            content += "### 💊 用药原则\n\n"
            for principle in medication:
                content += f"- {principle}\n"
                recommendations.append(principle)
            content += "\n"

        content += "> ⚠️ **重要**: 请严格遵医嘱用药，不要擅自调整剂量或停药\n\n"

        return content, recommendations

    def _format_complications(self, disease: str, knowledge: Dict) -> str:
        """格式化并发症说明"""
        content = f"## {self._get_disease_name(disease)} - 并发症预防\n\n"

        content += "### ⚠️ 可能的并发症\n\n"
        for complication in knowledge.get('complications', []):
            content += f"- {complication}\n"
        content += "\n"

        content += "### ✅ 预防措施\n\n"
        content += "- 规律治疗，控制指标达标\n"
        content += "- 定期复查相关项目\n"
        content += "- 保持健康生活方式\n"
        content += "- 警惕并发症早期症状\n\n"

        return content

    def _format_monitoring_advice(self, disease: str, knowledge: Dict) -> tuple:
        """格式化监测建议"""
        content = f"## {self._get_disease_name(disease)} - 监测指导\n\n"
        recommendations = []

        lifestyle = knowledge.get('lifestyle', {})
        monitoring = lifestyle.get('monitoring', [])

        if monitoring:
            content += "### 📊 监测要点\n\n"
            for item in monitoring:
                content += f"- {item}\n"
                recommendations.append(item)
            content += "\n"

        return content, recommendations

    def _get_disease_name(self, disease: str) -> str:
        """获取疾病中文名"""
        name_map = {
            "hypertension": "高血压",
            "diabetes": "糖尿病",
            "hyperlipidemia": "高血脂",
            "gout": "痛风",
            "coronary": "冠心病",
            "copd": "慢阻肺",
            "stroke": "脑卒中"
        }
        return name_map.get(disease.lower(), disease)

    def format_result(self, result: AdvisoryResult) -> str:
        """格式化咨询结果"""
        response = result.content

        if result.recommendations:
            response += "### 💡 建议\n\n"
            for rec in result.recommendations:
                response += f"- {rec}\n"
            response += "\n"

        response += "---\n\n"

        if result.warnings:
            response += "### ⚠️ 注意事项\n\n"
            for warning in result.warnings:
                response += f"- {warning}\n"

        return response


# 便捷函数
async def chronic_advise(disease: str, topic: str = "general", mcp_client=None) -> str:
    """
    慢病咨询（便捷函数）

    Args:
        disease: 疾病类型
        topic: 咨询主题
        mcp_client: MCP客户端

    Returns:
        str: 格式化的咨询结果
    """
    skill = ChronicAdvisorSkill(mcp_client)
    result = await skill.advise(disease, topic)
    return skill.format_result(result)


if __name__ == "__main__":
    # 测试用例
    async def test():
        skill = ChronicAdvisorSkill()

        # 测试高血压咨询
        result = await skill.advise("hypertension", "diet")
        print(skill.format_result(result))

        print("\n" + "="*60 + "\n")

        # 测试糖尿病用药咨询
        result = await skill.advise("diabetes", "medication")
        print(skill.format_result(result))

    import asyncio
    asyncio.run(test())
