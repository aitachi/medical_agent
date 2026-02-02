"""
医疗智能 Agent 模块
实现基于语义的自动任务匹配和Skill调度
"""

import asyncio
from agent.query_rewriter import QueryRewriter
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Awaitable
from enum import Enum
from datetime import datetime
import difflib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# 枚举和常量定义
# ============================================================

class IntentType(Enum):
    """意图类型"""
    SYMPTOM_INQUIRY = "symptom_inquiry"
    DEPARTMENT_QUERY = "department_query"
    MEDICATION_CONSULT = "medication_consult"
    APPOINTMENT = "appointment"
    MY_APPOINTMENT = "my_appointment"
    FOLLOWUP = "followup"
    RECORDS = "records"
    REPORT_INTERPRET = "report_interpret"
    HEALTH_EDUCATION = "health_education"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class SkillPriority(Enum):
    """Skill优先级"""
    CRITICAL = 1  # 预约等关键操作
    HIGH = 2      # 用药咨询等安全敏感
    NORMAL = 3    # 一般咨询
    LOW = 4       # 闲聊等


# ============================================================
# 数据模型
# ============================================================

@dataclass
class IntentResult:
    """意图识别结果"""
    intent: IntentType
    confidence: float
    target_skill: str
    entities: Dict[str, Any] = field(default_factory=dict)
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
    alternatives: List[Dict] = field(default_factory=list)


@dataclass
class SkillRequest:
    """Skill请求"""
    skill_name: str
    intent: IntentType
    entities: Dict[str, Any]
    context: "DialogueContext"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResponse:
    """Skill响应"""
    success: bool
    content: str
    data: Any = None
    error: Optional[str] = None
    need_clarification: bool = False
    follow_up_suggestions: List[str] = field(default_factory=list)


@dataclass
class DialogueContext:
    """对话上下文"""
    session_id: str
    user_id: str
    history: List[Dict] = field(default_factory=list)
    current_intent: Optional[IntentResult] = None
    accumulated_entities: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    turn_count: int = 0
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_turn(self, user_input: str, agent_response: str, intent: IntentResult):
        """添加对话轮次"""
        self.history.append({
            "turn": self.turn_count,
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "agent_response": agent_response,
            "intent": intent.intent.value,
            "confidence": intent.confidence
        })
        self.turn_count += 1

    def get_last_intent(self) -> Optional[IntentType]:
        """获取上一个意图"""
        if self.history:
            last_intent_name = self.history[-1].get("intent")
            if last_intent_name:
                try:
                    return IntentType(last_intent_name)
                except ValueError:
                    pass
        return None

    def update_entities(self, entities: Dict[str, Any]):
        """更新累积的实体信息"""
        self.accumulated_entities.update(entities)


# ============================================================
# 响应格式化器
# ============================================================

class ResponseFormatter:
    """
    响应格式化器 - 统一格式化所有医疗响应
    """

    # 免责声明模板
    DISCLAIMER = "> ⚠️ **免责声明**: 以上信息仅供参考，不能替代专业医疗诊断和治疗。如有不适请及时就医。"

    # 紧急情况提示
    URGENT_WARNING = """🚨 **紧急情况**: 如有以下情况请立即就医或拨打120：
> - 剧烈疼痛或突发严重症状
> - 呼吸困难、意识模糊
> - 持续高烧不退
> - 严重外伤或大出血"""

    def __init__(self):
        self.formatters = {
            "symptom": self._format_symptom_response,
            "drug": self._format_drug_response,
            "department": self._format_department_response,
            "health": self._format_health_response,
            "greeting": self._format_greeting_response,
            "fallback": self._format_fallback_response,
        }

    def format(
        self,
        content: str,
        response_type: str,
        has_risk: bool = False,
        urgent: bool = False,
        **kwargs
    ) -> str:
        """
        格式化响应

        Args:
            content: 原始内容
            response_type: 响应类型
            has_risk: 是否包含风险提示
            urgent: 是否紧急
            **kwargs: 其他参数

        Returns:
            str: 格式化后的响应
        """
        formatter = self.formatters.get(response_type, self._format_default_response)

        if response_type == "symptom":
            # 症状类型需要额外参数
            symptom = kwargs.get("symptom", "症状")
            data = kwargs.get("data", {})
            return self._format_symptom_response(symptom, data)
        elif response_type == "drug":
            drug_name = kwargs.get("drug_name", "药品")
            query_type = kwargs.get("query_type", "info")
            data = kwargs.get("data", {})
            return self._format_drug_response(drug_name, query_type, data)

        return formatter(content, has_risk=has_risk, urgent=urgent, **kwargs)

    def _format_symptom_response(self, symptom: str, data: Dict) -> str:
        """格式化症状响应"""
        response = f"## 关于【{symptom}】\n\n"

        if data:
            response += f"**症状描述**: {data.get('description', '')}\n\n"

            # 常见原因
            causes = data.get('common_causes', [])
            if causes:
                response += f"**常见原因**:\n"
                for cause in causes[:5]:
                    response += f"- {cause}\n"
                response += "\n"

            # 红旗征
            red_flags = data.get('red_flags', [])
            if red_flags:
                response += f"### ⚠️ 危险信号\n\n"
                response += "如有以下情况请立即就医：\n"
                for flag in red_flags:
                    response += f"- {flag}\n"
                response += "\n"

            # 建议科室
            response += f"**建议科室**: {data.get('department', '内科')}\n\n"

            # 自我护理
            self_care = data.get('self_care', [])
            if self_care:
                response += f"**自我护理建议**:\n"
                for care in self_care:
                    response += f"- {care}\n"
                response += "\n"

            response += f"💡 **小贴士**: {data.get('tip', '注意休息，保持良好的生活习惯')}\n\n"
        else:
            response += f"关于{symptom}的相关信息，建议您咨询专业医生。\n\n"
            response += "### ⚠️ 注意\n\n"
            response += "- 如症状持续或加重，请及时就医\n"
            response += "- 注意休息，避免过度劳累\n"

        response += "---\n\n"
        response += self.DISCLAIMER
        return response

    def _format_drug_response(self, drug_name: str, query_type: str, data: Dict) -> str:
        """格式化药品响应"""
        response = f"## 💊 {drug_name}\n\n"

        if data:
            response += f"**通用名**: {data.get('generic_name', drug_name)}\n"
            if "english_name" in data:
                response += f"**英文名**: {data['english_name']}\n"
            response += f"**分类**: {data.get('category', '')}\n\n"

            # 用法用量
            if query_type in ["info", "dosage"]:
                response += "### 💡 用法用量\n\n"
                dosage = data.get("dosage", {})
                if "adult" in dosage:
                    response += f"- **成人**: {dosage['adult']}\n"
                if "children" in dosage:
                    response += f"- **儿童**: {dosage['children']}\n"
                response += "\n"

            # 副作用
            side_effects = data.get("side_effects", [])
            if side_effects:
                response += "### 📝 可能的副作用\n\n"
                for se in side_effects:
                    response += f"- {se}\n"
                response += "\n"

            # 禁忌
            contraindications = data.get("contraindications", [])
            if contraindications:
                response += "### ⚠️ 禁忌症\n\n"
                for ct in contraindications:
                    response += f"- {ct}\n"
                response += "\n"

            # 注意事项
            warnings = data.get("warnings", "")
            if warnings:
                response += f"### ⚠️ 注意事项\n\n{warnings}\n\n"

            # 相互作用
            interactions = data.get("interactions", [])
            if interactions:
                response += "### 💊 药物相互作用\n\n"
                for interaction in interactions:
                    response += f"- {interaction}\n"
                response += "\n"
        else:
            response += "暂无详细信息，请咨询医生或药师。\n\n"

        response += "---\n\n"
        response += self.DISCLAIMER
        response += "\n\n> 💊 **用药提醒**: 请严格按医嘱或说明书使用，不要超量服用。"
        return response

    def _format_department_response(self, content: str, **kwargs) -> str:
        """格式化科室推荐响应"""
        response = content

        if not response.endswith("---"):
            response += "\n\n---\n\n"

        response += self.DISCLAIMER
        return response

    def _format_health_response(self, content: str, **kwargs) -> str:
        """格式化健康响应"""
        if not content.endswith("---"):
            content += "\n\n---\n\n"
        return content + self.DISCLAIMER

    def _format_greeting_response(self, content: str, **kwargs) -> str:
        """格式化问候响应"""
        return content  # 问候不需要免责声明

    def _format_fallback_response(self, content: str, **kwargs) -> str:
        """格式化兜底响应"""
        return content

    def _format_default_response(self, content: str, has_risk: bool = False, urgent: bool = False, **kwargs) -> str:
        """格式化默认响应"""
        response = content

        # 添加紧急提示
        if urgent:
            response += "\n\n---\n\n"
            response += self.URGENT_WARNING

        # 添加风险提示
        elif has_risk:
            response += "\n\n---\n\n"
            response += "> ⚠️ **注意**: 以上情况建议及时就医咨询。"

        # 添加免责声明
        if not response.endswith("---"):
            response += "\n\n---\n\n"
        response += self.DISCLAIMER

        return response

    def add_emergency_warning(self, response: str) -> str:
        """添加紧急警告"""
        if "🚨" not in response and "紧急" not in response:
            response += "\n\n---\n\n"
            response += self.URGENT_WARNING
        return response

    def add_disclaimer(self, response: str) -> str:
        """添加免责声明"""
        if "免责声明" not in response and "disclaimer" not in response.lower():
            if not response.endswith("---"):
                response += "\n\n---\n\n"
            response += self.DISCLAIMER
        return response

    def format_with_emoji(self, text: str, emoji_map: Dict[str, str] = None) -> str:
        """添加表情符号"""
        default_map = {
            "头痛": "🤕",
            "发热": "🌡️",
            "咳嗽": "🗣️",
            "腹痛": "😣",
            "胸痛": "💔",
            "药品": "💊",
            "医院": "🏥",
            "科室": "🏥",
            "医生": "👨‍⚕️",
            "健康": "💪",
            "运动": "🏃",
            "饮食": "🥗",
            "睡眠": "😴",
        }

        emoji_map = emoji_map or default_map
        for keyword, emoji in emoji_map.items():
            text = text.replace(keyword, f"{emoji} {keyword}")

        return text


# ============================================================
# 健康知识库
# ============================================================

class HealthKnowledgeBase:
    """健康知识库"""

    # 疾病预防知识
    DISEASE_PREVENTION = {
        "高血压": {
            "description": "血压持续升高（收缩压≥140mmHg或舒张压≥90mmHg）",
            "risk_factors": ["高盐饮食", "肥胖", "缺乏运动", "吸烟饮酒", "精神紧张"],
            "prevention": {
                "diet": ["低盐饮食（每日<6g）", "低脂饮食", "多吃蔬菜水果", "限制饮酒"],
                "exercise": ["每周3-5次运动", "每次30分钟以上", "有氧运动为主"],
                "lifestyle": ["控制体重", "戒烟限酒", "管理压力", "规律作息"]
            },
            "symptoms": ["头痛头晕", "心悸", "视力模糊", "耳鸣"],
            "complications": ["心脏病", "脑卒中", "肾衰竭", "眼底病变"]
        },
        "糖尿病": {
            "description": "代谢性疾病，以高血糖为特征",
            "risk_factors": ["肥胖", "家族史", "不良饮食习惯", "缺乏运动", "年龄因素"],
            "prevention": {
                "diet": ["控制碳水化合物", "低糖饮食", "高纤维饮食", "少量多餐"],
                "exercise": ["每周150分钟运动", "饭后散步", "避免久坐"],
                "lifestyle": ["控制体重", "定期监测血糖", "规律作息"]
            },
            "symptoms": ["多饮多尿", "多食", "体重下降", "乏力"],
            "complications": ["视网膜病变", "肾病", "神经病变", "心血管疾病"]
        },
        "感冒": {
            "description": "病毒性上呼吸道感染",
            "prevention": {
                "diet": ["多喝水", "多吃维生素C", "清淡饮食"],
                "exercise": ["适度运动增强免疫"],
                "lifestyle": ["勤洗手", "戴口罩", "避免接触病人", "注意保暖"]
            },
            "self_care": ["休息", "多喝温水", "盐水漱口", "注意通风"]
        },
        "心血管疾病": {
            "description": "心脏和血管系统疾病",
            "prevention": {
                "diet": ["低盐低脂", "地中海饮食", "多吃鱼类", "控制胆固醇"],
                "exercise": ["有氧运动", "避免剧烈运动", "循序渐进"],
                "lifestyle": ["戒烟", "控制三高", "管理压力", "定期体检"]
            }
        }
    }

    # 健康生活方式
    HEALTHY_LIFESTYLE = {
        "饮食": {
            "原则": [
                "食物多样，每天12种以上，每周25种以上",
                "谷类为主，粗细搭配",
                "多吃蔬菜水果（每日500克）",
                "适量鱼、禽、蛋、瘦肉",
                "少盐少油少糖"
            ],
            "三餐": ["早餐要吃好", "午餐要吃饱", "晚餐要吃少"],
            "饮水": "每日1.5-2升，白开水或淡茶"
        },
        "运动": {
            "原则": ["持之以恒", "循序渐进", "量力而行", "全面发展"],
            "推荐": ["每周150分钟中等强度有氧运动", "每周2-3次力量训练", "每天适量身体活动"],
            "注意事项": ["运动前热身", "运动后拉伸", "不适时停止"]
        },
        "睡眠": {
            "成人": "每日7-9小时",
            "儿童": "9-11小时",
            "老年人": "7-8小时",
            "建议": ["固定作息", "睡前不看手机", "保持卧室安静", "避免睡前咖啡"]
        },
        "心理": {
            "建议": ["保持积极心态", "学会减压", "培养爱好", "保持社交", "必要时求助"]
        }
    }

    # 食物禁忌
    FOOD_RESTRICTIONS = {
        "高血压": ["腌制品", "方便面", "动物内脏", "油炸食品", "浓茶咖啡"],
        "糖尿病": ["糖果", "蛋糕", "甜饮料", "白米饭/面", "高糖水果"],
        "痛风": ["海鲜", "动物内脏", "啤酒", "浓汤", "豆制品"],
        "胃病": ["辛辣食物", "生冷食物", "咖啡", "酒精", "过硬食物"]
    }

    def get_disease_prevention(self, disease: str) -> Optional[Dict]:
        """获取疾病预防知识"""
        # 模糊匹配
        for key, value in self.DISEASE_PREVENTION.items():
            if key in disease or disease in key:
                return value
        return None

    def get_healthy_lifestyle(self, category: str = None) -> Dict:
        """获取健康生活方式建议"""
        if category:
            return self.HEALTHY_LIFESTYLE.get(category, {})
        return self.HEALTHY_LIFESTYLE

    def get_food_restrictions(self, condition: str) -> List[str]:
        """获取饮食禁忌"""
        for key, value in self.FOOD_RESTRICTIONS.items():
            if key in condition or condition in key:
                return value
        return []


# ============================================================
# 意图分类器
# ============================================================

# 导入ML分类器（优先MLP）
try:
    from agent.mlp_intent_classifier import MLPIntentClassifier
    MLP_AVAILABLE = True
except ImportError:
    try:
        from .mlp_intent_classifier import MLPIntentClassifier
        MLP_AVAILABLE = True
    except ImportError:
        MLP_AVAILABLE = False

try:
    from agent.ml_intent_classifier import MLIntentClassifier
    LR_AVAILABLE = True
except ImportError:
    try:
        from .ml_intent_classifier import MLIntentClassifier
        LR_AVAILABLE = True
    except ImportError:
        LR_AVAILABLE = False

if not MLP_AVAILABLE and not LR_AVAILABLE:
    logger.warning("ML意图分类器未找到，将使用规则分类器")


class IntentClassifier:
    """
    意图分类器 - 支持MLP、逻辑回归、规则三种模式

    优先级:
    1. MLP神经网络 (准确率: 100%)
    2. 逻辑回归 (准确率: 99.89%)
    3. 规则分类器 (后备方案)
    """

    def __init__(self, use_ml: bool = True, mlp_model_path: str = None, lr_model_path: str = None):
        """
        初始化意图分类器

        Args:
            use_ml: 是否使用ML模型（默认True）
            mlp_model_path: MLP模型路径
            lr_model_path: 逻辑回归模型路径
        """
        self.use_ml = use_ml
        self.mlp_classifier = None
        self.lr_classifier = None
        self.ml_enabled = False
        self.classifier_type = "rule"

        # 尝试加载MLP模型（最优）
        if use_ml and MLP_AVAILABLE:
            try:
                self.mlp_classifier = MLPIntentClassifier(model_path=mlp_model_path)
                if self.mlp_classifier.is_trained:
                    self.ml_enabled = True
                    self.classifier_type = "mlp"
                    logger.info("MLP意图分类器已启用 (准确率: 100%)")
                else:
                    logger.info("MLP模型未训练，尝试逻辑回归...")
            except Exception as e:
                logger.warning(f"MLP分类器加载失败: {e}")

        # 如果MLP不可用，尝试逻辑回归
        if not self.ml_enabled and LR_AVAILABLE:
            try:
                self.lr_classifier = MLIntentClassifier(model_path=lr_model_path)
                if self.lr_classifier.is_trained:
                    self.ml_enabled = True
                    self.classifier_type = "logistic_regression"
                    logger.info("逻辑回归意图分类器已启用 (准确率: 99.89%)")
                else:
                    logger.info("逻辑回归模型未训练，使用规则分类器...")
            except Exception as e:
                logger.warning(f"逻辑回归分类器加载失败: {e}")

        # 规则分类器初始化（作为后备）
        self.intent_rules = self._init_rules()

        # 症状关键词库
        self.symptom_keywords = [
            "头痛", "头晕", "发热", "发烧", "咳嗽", "腹痛", "胸痛",
            "恶心", "呕吐", "腹泻", "失眠", "乏力", "疼痛", "痒",
            "不适", "难受", "不舒服",
            # 扩展症状词
            "好痛", "很痛", "特痛", "剧痛", "酸痛", "胀痛"
        ]

        # 药品关键词库
        self.drug_keywords = [
            "药", "胶囊", "片", "颗粒", "口服液", "注射",
            "阿莫西林", "布洛芬", "对乙酰氨基酚", "二甲双胍", "硝苯地平",
            "奥美拉唑", "头孢", "青霉素", "感冒药", "退烧药"
        ]

        # 科室关键词库
        self.department_keywords = [
            "科", "挂号", "预约", "门诊", "专家", "医生"
        ]

        # 问候语
        self.greetings = [
            "你好", "您好", "嗨", "hello", "hi",
            "早上好", "下午好", "晚上好", "晚安",
            "谢谢", "感谢", "再见", "拜拜"
        ]

        # 健康关键词
        self.health_keywords = [
            "预防", "怎么预防", "如何预防", "如何保持", "怎么保持",
            "不能吃什么", "禁忌", "注意事项", "健康", "养生",
            "运动", "锻炼", "活动", "健身", "建议", "推荐"
        ]

    def _init_rules(self) -> Dict[IntentType, List[Dict]]:
        """初始化意图匹配规则"""
        return {
            IntentType.SYMPTOM_INQUIRY: [
                {"patterns": [r"(我|最近)(.+?)(疼|痛|难受|不舒服|症状)", r"(.+?)怎么回事"], "weight": 1.0},
                {"patterns": [r"(.+?)是什么症状", r"(.+?)是什么病", r"(.+?)是啥病"], "weight": 0.9},
                {"patterns": [r"如果(.+?)(应该|要|该)怎么办", r"如果(.+?)(痛|病|难受)"], "weight": 0.8},
                {"patterns": [r"我(.+?)怎么样了", r"(.+?)怎么样", r"(.+?)怎么办"], "weight": 0.7},
            ],
            IntentType.DEPARTMENT_QUERY: [
                {"patterns": [r"(.+?)挂什么科", r"(.+?)去哪个科", r"(.+?)看什么科", r"(.+?)哪个科"], "weight": 1.0},
                {"patterns": [r"哪个科(.+?)", r"有(.+?)科吗"], "weight": 0.9},
                {"patterns": [r"(.+?)是(.+?)科(吗|吗|吗)?", r"(.+?)应该挂(.+?)科"], "weight": 0.8},
            ],
            IntentType.MEDICATION_CONSULT: [
                {"patterns": [r"(.+?药)(怎么吃|怎么用|用量|用法|服用)"], "weight": 1.0},
                {"patterns": [r"(.+?)有什么副作用", r"(.+?)副作用", r"(.+?)禁忌", r"(.+?)能一起吃"], "weight": 1.0},
                {"patterns": [r"吃(.+?)(可以|行)吗"], "weight": 0.8},
            ],
            IntentType.APPOINTMENT: [
                {"patterns": [r"想?挂(个)?号", r"预约(.+?)(号|门诊)", r"帮我挂号", r"我要挂号"], "weight": 1.0},
                {"patterns": [r"排号", r"想看医生"], "weight": 0.9},
            ],
            IntentType.REPORT_INTERPRET: [
                {"patterns": [r"看看(.+?)报告", r"(.+?)报告(怎么|如何)", r"(.+?)结果(.+?)(正常|异常)"], "weight": 1.0},
                {"patterns": [r"(.+?)指标(.+?)", r"化验(.+?)", r"体检(.+?)"], "weight": 0.9},
            ],
            IntentType.HEALTH_EDUCATION: [
                {"patterns": [r"怎么预防(.+?)", r"如何(保持|预防)(.+?)", r"(.+?)怎么预防"], "weight": 1.0},
                {"patterns": [r"(.+?)不能吃什么", r"(.+?)(要注意|注意|禁忌)", r"(.+?)饮食"], "weight": 0.8},
                {"patterns": [r"有什么运动建议", r"运动建议", r"锻炼建议", r"(.+?)运动", r"(.+?)健身"], "weight": 0.8},
            ],
        }

    async def classify(
        self,
        text: str,
        context: DialogueContext
    ) -> IntentResult:
        """
        分类用户意图

        优先使用ML模型（准确率99.89%），ML不可用时降级到规则系统

        Args:
            text: 用户输入
            context: 对话上下文

        Returns:
            IntentResult: 意图识别结果
        """
        text = text.strip()

        # 边界情况：问候语检测（最高优先级）
        text_lower = text.lower()
        for greeting in self.greetings:
            if greeting in text_lower:
                return IntentResult(
                    intent=IntentType.GREETING,
                    confidence=0.95,
                    target_skill="greeting-handler",
                    entities={}
                )

        # 边界情况：检查否定句 (如 "不头痛"、"不痛")
        negation_patterns = [
            r"^(不|没|没有|别|无)(.)*?(痛|病|难受|不舒服|症状)($|，|。)",
            r"^(不|没|没有|别|无).+?(痛|病|难受|不舒服)",
        ]
        for pattern in negation_patterns:
            if re.search(pattern, text):
                return IntentResult(
                    intent=IntentType.UNKNOWN,
                    confidence=0.0,
                    target_skill="fallback-handler",
                    entities={}
                )

        # 边界情况：检查重复词或无意义输入
        if len(text) < 20 and len(set(text)) <= 3 and text.strip():
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                target_skill="fallback-handler",
                entities={}
            )

        # ============ ML分类（优先） ============
        if self.ml_enabled:
            return await self._classify_with_ml(text, context)

        # ============ 规则分类（后备） ============
        return await self._classify_with_rules(text, context)

    async def _classify_with_ml(self, text: str, context: DialogueContext) -> IntentResult:
        """使用ML模型分类（优先MLP）"""
        try:
            # 使用MLP或逻辑回归
            if self.mlp_classifier is not None:
                top_results = self.mlp_classifier.predict_top_k(text, k=3)
            elif self.lr_classifier is not None:
                top_results = self.lr_classifier.predict_top_k(text, k=3)
            else:
                return await self._classify_with_rules(text, context)

            # 解码意图
            intent_label = top_results[0][0]
            confidence = top_results[0][1]

            # 转换为IntentType枚举
            intent_type = IntentType(intent_label)

            # 构建备选列表
            alternatives = [
                {"intent": label, "confidence": conf}
                for label, conf in top_results[1:]
            ]

            # 提取实体
            entities = await self._extract_entities(text, intent_type, context)

            return IntentResult(
                intent=intent_type,
                confidence=confidence,
                target_skill=self._get_skill_for_intent(intent_type),
                entities=entities,
                alternatives=alternatives
            )
        except Exception as e:
            logger.error(f"ML分类失败，降级到规则分类: {e}")
            return await self._classify_with_rules(text, context)

    async def _classify_with_rules(self, text: str, context: DialogueContext) -> IntentResult:
        """使用规则分类（后备方案）"""
        scores = {}  # intent -> score
        text_lower = text.lower()  # 转换为小写用于匹配

        # 1. 规则匹配
        for intent_type, rules in self.intent_rules.items():
            intent_score = 0.0

            for rule in rules:
                for pattern in rule["patterns"]:
                    if re.search(pattern, text, re.IGNORECASE):
                        intent_score += rule["weight"]

            if intent_score > 0:
                # 归一化分数
                scores[intent_type] = min(intent_score / len(rules), 1.0)

        # 2. 关键词加分
        for keyword in self.symptom_keywords:
            if keyword in text:
                scores[IntentType.SYMPTOM_INQUIRY] = scores.get(IntentType.SYMPTOM_INQUIRY, 0) + 0.2

        for keyword in self.drug_keywords:
            if keyword in text:
                scores[IntentType.MEDICATION_CONSULT] = scores.get(IntentType.MEDICATION_CONSULT, 0) + 0.3

        # 特殊模式：吃了X天药
        if re.search(r'吃.*?药|服用.*?|.*?药.*?[天次]', text):
            scores[IntentType.MEDICATION_CONSULT] = scores.get(IntentType.MEDICATION_CONSULT, 0) + 0.5

        # 2.5 混合英中检测 - 检查是否包含英文症状关键词
        mixed_symptoms = {
            "headache": "头痛", "fever": "发热", "cough": "咳嗽",
            "stomach ache": "胃痛", "nausea": "恶心",
            "pain": "痛", "ache": "痛"
        }
        for eng, chi in mixed_symptoms.items():
            if eng in text_lower:
                scores[IntentType.SYMPTOM_INQUIRY] = scores.get(IntentType.SYMPTOM_INQUIRY, 0) + 0.2

        for keyword in self.department_keywords:
            if keyword in text:
                scores[IntentType.DEPARTMENT_QUERY] = scores.get(IntentType.DEPARTMENT_QUERY, 0) + 0.2

        for keyword in self.health_keywords:
            if keyword in text:
                scores[IntentType.HEALTH_EDUCATION] = scores.get(IntentType.HEALTH_EDUCATION, 0) + 0.3

        # 3. 上下文关联
        last_intent = context.get_last_intent()
        if last_intent and last_intent != IntentType.GREETING:
            if last_intent in [IntentType.SYMPTOM_INQUIRY, IntentType.MEDICATION_CONSULT]:
                if len(text) < 20:  # 简短回复
                    scores[last_intent] = scores.get(last_intent, 0) + 0.3

        # 4. 确定最终意图
        if not scores:
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                target_skill="fallback-handler",
                requires_clarification=True,
                clarification_question="抱歉，我没有完全理解您的意思，可以换个说法吗？"
            )

        best_intent = max(scores.items(), key=lambda x: x[1])
        intent_type, confidence = best_intent

        # 检查置信度
        confidence_threshold = self._get_threshold(intent_type)
        if confidence < confidence_threshold:
            alternatives = [
                {"intent": intent.value, "confidence": conf}
                for intent, conf in sorted(scores.items(), key=lambda x: -x[1])[:3]
            ]
            return IntentResult(
                intent=intent_type,
                confidence=confidence,
                target_skill=self._get_skill_for_intent(intent_type),
                requires_clarification=True,
                clarification_question=f"您是想了解{self._get_intent_description(intent_type)}相关的内容吗？",
                alternatives=alternatives
            )

        # 5. 提取实体
        entities = await self._extract_entities(text, intent_type, context)

        # 6. 构建结果
        return IntentResult(
            intent=intent_type,
            confidence=confidence,
            target_skill=self._get_skill_for_intent(intent_type),
            entities=entities,
            alternatives=[
                {"intent": intent.value, "confidence": conf}
                for intent, conf in sorted(scores.items(), key=lambda x: -x[1])[:3]
                if intent != intent_type
            ]
        )

    def _get_threshold(self, intent: IntentType) -> float:
        """获取意图的置信度阈值"""
        thresholds = {
            IntentType.APPOINTMENT: 0.70,
            IntentType.MEDICATION_CONSULT: 0.30,
            IntentType.SYMPTOM_INQUIRY: 0.50,
            IntentType.DEPARTMENT_QUERY: 0.60,
            IntentType.HEALTH_EDUCATION: 0.40,
            IntentType.REPORT_INTERPRET: 0.60,
            IntentType.MY_APPOINTMENT: 0.60,
            IntentType.FOLLOWUP: 0.60,
            IntentType.RECORDS: 0.60,
        }
        return thresholds.get(intent, 0.60)

    def _get_skill_for_intent(self, intent: IntentType) -> str:
        """获取意图对应的Skill"""
        skill_map = {
            IntentType.SYMPTOM_INQUIRY: "symptom-analyzer",
            IntentType.DEPARTMENT_QUERY: "department-recommender",
            IntentType.MEDICATION_CONSULT: "medication-advisor",
            IntentType.APPOINTMENT: "appointment-service",
            IntentType.MY_APPOINTMENT: "my-appointment-handler",
            IntentType.FOLLOWUP: "followup-handler",
            IntentType.RECORDS: "records-handler",
            IntentType.REPORT_INTERPRET: "report-interpreter",
            IntentType.HEALTH_EDUCATION: "health-educator",
            IntentType.GREETING: "greeting-handler",
            IntentType.UNKNOWN: "fallback-handler",
        }
        return skill_map.get(intent, "fallback-handler")

    def _get_intent_description(self, intent: IntentType) -> str:
        """获取意图的中文描述"""
        descriptions = {
            IntentType.SYMPTOM_INQUIRY: "症状",
            IntentType.DEPARTMENT_QUERY: "挂号科室",
            IntentType.MEDICATION_CONSULT: "用药",
            IntentType.APPOINTMENT: "预约挂号",
            IntentType.MY_APPOINTMENT: "预约查询",
            IntentType.FOLLOWUP: "预约随访",
            IntentType.RECORDS: "治疗档案",
            IntentType.REPORT_INTERPRET: "报告解读",
            IntentType.HEALTH_EDUCATION: "健康知识",
        }
        return descriptions.get(intent, "相关")

    async def _extract_entities(
        self,
        text: str,
        intent: IntentType,
        context: DialogueContext
    ) -> Dict[str, Any]:
        """提取实体"""
        entities = {}

        if intent == IntentType.SYMPTOM_INQUIRY:
            # 提取症状
            for symptom in self.symptom_keywords:
                if symptom in text and len(symptom) > 1:
                    entities["symptom"] = symptom
                    break

            # 提取持续时间
            duration_match = re.search(r'(\d+)(天|周|个月|小时|日)', text)
            if duration_match:
                entities["duration"] = duration_match.group(0)

            # 提取严重程度
            severity_keywords = {
                "剧烈": "severe", "非常": "severe", "特别": "severe",
                "比较": "moderate", "挺": "moderate", "有点": "mild",
                "轻微": "mild", "稍微": "mild"
            }
            for keyword, level in severity_keywords.items():
                if keyword in text:
                    entities["severity"] = level
                    break

        elif intent == IntentType.DEPARTMENT_QUERY:
            entities["query"] = text

        elif intent == IntentType.MEDICATION_CONSULT:
            # 提取药品名称
            for drug in ["阿莫西林", "布洛芬", "对乙酰氨基酚", "二甲双胍", "硝苯地平", "奥美拉唑"]:
                if drug in text:
                    entities["drug_name"] = drug
                    break

            if "drug_name" not in entities:
                for drug in self.drug_keywords:
                    if drug in text and len(drug) > 1:
                        entities["drug_name"] = drug
                        break

            # 检测查询类型
            if "副作用" in text or "不良反应" in text:
                entities["query_type"] = "side_effects"
            elif "怎么吃" in text or "用法" in text or "用量" in text:
                entities["query_type"] = "dosage"
            elif "禁忌" in text:
                entities["query_type"] = "contraindication"
            elif "一起吃" in text or "相互作用" in text:
                entities["query_type"] = "interaction"
            else:
                entities["query_type"] = "info"

        elif intent == IntentType.HEALTH_EDUCATION:
            # 提取疾病/健康主题
            for disease in ["高血压", "糖尿病", "感冒", "心血管"]:
                if disease in text:
                    entities["health_topic"] = disease
                    break

            # 检测查询类型
            if "预防" in text:
                entities["query_type"] = "prevention"
            elif "吃" in text or "饮食" in text:
                entities["query_type"] = "diet"
            elif "运动" in text:
                entities["query_type"] = "exercise"
            else:
                entities["query_type"] = "general"

        elif intent == IntentType.APPOINTMENT:
            entities["action"] = "book"
            # 提取科室
            for dept in ["内科", "外科", "儿科", "妇科", "骨科", "眼科", "皮肤科", "神经内科", "心血管内科"]:
                if dept in text:
                    entities["department"] = dept
                    break

        elif intent == IntentType.MY_APPOINTMENT:
            entities["action"] = "query"
            # 提取手机号
            phone_match = re.search(r'1[3-9]\d{9}', text)
            if phone_match:
                entities["phone"] = phone_match.group(0)

        elif intent == IntentType.FOLLOWUP:
            entities["action"] = "followup"
            # 提取手机号
            phone_match = re.search(r'1[3-9]\d{9}', text)
            if phone_match:
                entities["phone"] = phone_match.group(0)
            # 检测操作类型
            if "添加" in text or "新增" in text or "记录" in text:
                entities["operation"] = "add"
            elif "查看" in text or "查询" in text or "显示" in text:
                entities["operation"] = "query"

        elif intent == IntentType.RECORDS:
            entities["action"] = "records"
            # 提取手机号
            phone_match = re.search(r'1[3-9]\d{9}', text)
            if phone_match:
                entities["phone"] = phone_match.group(0)

        return entities


# ============================================================
# Skill 调用器
# ============================================================

class SkillInvoker:
    """
    Skill调用器 - 负责调用具体的Skill
    """

    def __init__(self, mcp_client=None):
        self.mcp_client = mcp_client
        self.formatter = ResponseFormatter()
        self.health_kb = HealthKnowledgeBase()
        self.skills = {}
        self._init_builtin_skills()

    def _init_builtin_skills(self):
        """初始化内置Skill处理器"""
        self.skills = {
            "symptom-analyzer": self._symptom_analyzer_skill,
            "department-recommender": self._department_recommender_skill,
            "medication-advisor": self._medication_advisor_skill,
            "appointment-service": self._appointment_skill,
            "health-educator": self._health_educator_skill,
            "greeting-handler": self._greeting_skill,
            "fallback-handler": self._fallback_skill,
        }

    def register_skill(self, name: str, handler: Callable):
        """注册自定义Skill"""
        self.skills[name] = handler

    async def invoke(self, request: SkillRequest) -> SkillResponse:
        """调用Skill"""
        skill_name = request.skill_name

        if skill_name not in self.skills:
            return SkillResponse(
                success=False,
                content="抱歉，该功能暂未开放。",
                error=f"Skill not found: {skill_name}"
            )

        handler = self.skills[skill_name]

        try:
            response = await handler(request)
            # 使用响应格式化器处理所有响应
            if response.success:
                response.content = self.formatter.add_disclaimer(response.content)
            return response
        except Exception as e:
            logger.error(f"Skill {skill_name} error: {e}")
            return SkillResponse(
                success=False,
                content="处理请求时出错，请稍后重试。",
                error=str(e)
            )

    # ============ 调用MCP的Skill实现 ============

    async def _symptom_analyzer_skill(self, request: SkillRequest) -> SkillResponse:
        """症状分析Skill - 调用MCP工具"""
        entities = request.entities
        symptom = entities.get("symptom", "不适")
        duration = entities.get("duration", "")
        severity = entities.get("severity", "")

        # 调用MCP工具
        if self.mcp_client:
            mcp_result = await self.mcp_client.call_tool(
                "medical_knowledge_query",
                {"query_type": "symptom", "keyword": symptom}
            )

            if mcp_result.success and mcp_result.data:
                data = mcp_result.data.get("data", {})
                # 使用格式化器格式化响应
                content = self.formatter.format(
                    "",
                    response_type="symptom",
                    symptom=symptom,
                    data=data,
                    has_risk=len(data.get("red_flags", [])) > 0
                )
            else:
                content = self.formatter._format_symptom_response(symptom, {})
        else:
            content = self.formatter._format_symptom_response(symptom, {})

        return SkillResponse(
            success=True,
            content=content,
            follow_up_suggestions=[
                "还有其他不适吗？",
                "需要帮您推荐科室吗？"
            ]
        )

    async def _department_recommender_skill(self, request: SkillRequest) -> SkillResponse:
        """科室推荐Skill - 调用MCP工具"""
        entities = request.entities

        if self.mcp_client:
            symptom = entities.get("query", "")
            mcp_result = await self.mcp_client.call_tool(
                "hospital_department_query",
                {"query_type": "by_symptom", "symptom": symptom}
            )

            if mcp_result.success and mcp_result.data:
                recommendations = mcp_result.data.get("recommendations", [])
                content = "## 🏥 科室推荐\n\n"
                content += f"根据您描述的症状，建议挂以下科室：\n\n"

                for rec in recommendations[:3]:
                    content += f"### 🏥 {rec['department']}\n"
                    content += f"- 适用症状: {rec['symptom']}\n\n"

                content = self.formatter.format(content, response_type="department")
            else:
                content = self.formatter._format_department_response(
                    self._get_department_list()
                )
        else:
            content = self.formatter._format_department_response(
                self._get_department_list()
            )

        return SkillResponse(success=True, content=content)

    def _get_department_list(self) -> str:
        """获取科室列表"""
        departments = [
            ("内科", "头痛、胸闷、腹痛等内脏器官疾病"),
            ("外科", "需要手术治疗的外科疾病"),
            ("神经内科", "头痛、头晕、失眠等神经系统症状"),
            ("心血管内科", "胸痛、心悸、高血压等"),
            ("呼吸内科", "咳嗽、气促、发热等呼吸系统症状"),
            ("消化内科", "腹痛、恶心、呕吐等消化系统症状"),
            ("内分泌科", "糖尿病、甲状腺疾病等"),
            ("皮肤科", "皮疹、瘙痒等皮肤问题"),
            ("眼科", "视力问题、眼痛、眼红"),
            ("耳鼻喉科", "耳鸣、鼻塞、咽痛"),
        ]

        response = "## 🏥 本院科室\n\n"
        response += "| 科室 | 适用范围 |\n"
        response += "|------|---------|\n"

        for dept, desc in departments:
            response += f"| {dept} | {desc} |\n"

        response += "\n> 💡 请告诉我您的症状，我可以帮您推荐合适的科室。"
        return response

    async def _medication_advisor_skill(self, request: SkillRequest) -> SkillResponse:
        """用药咨询Skill - 调用MCP工具"""
        entities = request.entities
        drug_name = entities.get("drug_name", "")
        query_type = entities.get("query_type", "info")

        if not drug_name:
            content = """## 💊 用药咨询

请告诉我您想了解哪种药品的信息，包括：

- 用法用量
- 副作用
- 禁忌症
- 药物相互作用

---

> ⚠️ **免责声明**: 用药请遵医嘱，不要自行用药。"""
            return SkillResponse(success=True, content=content)

        # 调用MCP工具
        if self.mcp_client:
            mcp_result = await self.mcp_client.call_tool(
                "drug_database_query",
                {"query_type": query_type, "drug_name": drug_name}
            )

            if mcp_result.success and mcp_result.data:
                data = mcp_result.data.get("info", {})
                content = self.formatter.format(
                    "",
                    response_type="drug",
                    drug_name=drug_name,
                    query_type=query_type,
                    data=data,
                    has_risk=len(data.get("contraindications", [])) > 0
                )
            else:
                content = self.formatter._format_drug_not_found(drug_name)
        else:
            content = self.formatter._format_drug_not_found(drug_name)

        return SkillResponse(success=True, content=content)

    def _format_drug_not_found(self, drug_name: str) -> str:
        """药品未找到"""
        response = f"## 💊 {drug_name}\n\n"
        response += "抱歉，暂未收录该药品的详细信息。\n\n"
        response += "### 建议\n\n"
        response += "- 请确认药品名称是否正确\n"
        response += "- 咨询医生或药师\n"
        response += "- 参考药品说明书\n\n"
        response += "---\n\n"
        response += self.formatter.DISCLAIMER
        return response

    # ============ 不调用MCP的Skill实现 ============

    async def _health_educator_skill(self, request: SkillRequest) -> SkillResponse:
        """
        健康教育Skill - 不调用MCP，使用内置知识库
        根据用户查询提供针对性的健康知识
        """
        entities = request.entities
        query_type = entities.get("query_type", "general")
        health_topic = entities.get("health_topic", "")

        user_input = request.metadata.get("user_input", "")

        content = ""

        # 1. 疾病预防查询
        if health_topic:
            prevention = self.health_kb.get_disease_prevention(health_topic)
            if prevention:
                content = self._format_disease_prevention(health_topic, prevention)
            else:
                content = self._format_general_health_info()

        # 2. 饮食禁忌查询
        elif "不能吃" in user_input or "饮食" in user_input:
            # 查找相关疾病
            for condition in self.health_kb.FOOD_RESTRICTIONS.keys():
                if condition in user_input:
                    restrictions = self.health_kb.get_food_restrictions(condition)
                    content = self._format_food_restrictions(condition, restrictions)
                    break
            else:
                content = self._format_general_diet_advice()

        # 3. 运动建议
        elif "运动" in user_input:
            content = self._format_exercise_advice()

        # 4. 生活方式
        elif "生活" in user_input or "习惯" in user_input:
            content = self._format_lifestyle_advice()

        # 默认：通用健康信息
        else:
            content = self._format_general_health_info()

        return SkillResponse(
            success=True,
            content=content,
            follow_up_suggestions=[
                "还有什么健康问题想了解的吗？",
                "需要了解更多疾病预防知识吗？"
            ]
        )

    def _format_disease_prevention(self, disease: str, prevention: Dict) -> str:
        """格式化疾病预防信息"""
        response = f"## 📋 {disease}预防指南\n\n"

        if "description" in prevention:
            response += f"**疾病概述**: {prevention['description']}\n\n"

        # 风险因素
        risk_factors = prevention.get("risk_factors", [])
        if risk_factors:
            response += "### ⚠️ 风险因素\n\n"
            for factor in risk_factors:
                response += f"- {factor}\n"
            response += "\n"

        # 预防措施
        prev = prevention.get("prevention", {})
        if prev:
            response += "### ✅ 预防措施\n\n"

            if "diet" in prev:
                response += "**饮食建议**:\n"
                for advice in prev["diet"]:
                    response += f"- {advice}\n"
                response += "\n"

            if "exercise" in prev:
                response += "**运动建议**:\n"
                for advice in prev["exercise"]:
                    response += f"- {advice}\n"
                response += "\n"

            if "lifestyle" in prev:
                response += "**生活方式**:\n"
                for advice in prev["lifestyle"]:
                    response += f"- {advice}\n"
                response += "\n"

        # 症状识别
        symptoms = prevention.get("symptoms", [])
        if symptoms:
            response += "### 🩺 常见症状\n\n"
            response += f"{', '.join(symptoms)}\n\n"

        # 并发症
        complications = prevention.get("complications", [])
        if complications:
            response += "### ⚠️ 可能并发症\n\n"
            response += "如不及时控制，可能导致：\n"
            for comp in complications:
                response += f"- {comp}\n"
            response += "\n"

        response += "---\n\n"
        response += "> 💡 **提示**: 预防胜于治疗，保持健康生活方式是最好的预防方法。"
        return response

    def _format_food_restrictions(self, condition: str, restrictions: List[str]) -> str:
        """格式化饮食禁忌"""
        response = f"## 🚫 {condition}饮食禁忌\n\n"

        response += "### ❌ 需要避免的食物\n\n"
        for item in restrictions:
            response += f"- **{item}**\n"
        response += "\n"

        response += "### ✅ 饮食建议\n\n"
        if condition == "高血压":
            response += "- 选择低盐食品\n"
            response += "- 多吃新鲜蔬菜水果\n"
            response += "- 限制加工食品\n"
            response += "- 控制总热量\n"
        elif condition == "糖尿病":
            response += "- 选择低升糖指数食物\n"
            response += "- 控制碳水化合物摄入\n"
            response += "- 少量多餐\n"
            response += "- 增加膳食纤维\n"
        elif condition == "痛风":
            response += "- 低嘌呤饮食\n"
            response += "- 多喝水\n"
            response += "- 限制酒精\n"
            response += "- 减少高蛋白食物\n"
        elif condition == "胃病":
            response += "- 规律饮食\n"
            response += "- 细嚼慢咽\n"
            response += "- 避免刺激性食物\n"
            response += "- 选择易消化食物\n"

        response += "\n---\n\n"
        response += "> 💡 **提示**: 饮食调整需长期坚持，建议在医生或营养师指导下进行。"
        return response

    def _format_exercise_advice(self) -> str:
        """格式化运动建议"""
        response = """## 🏃 运动健康指南

### 运动原则
- **持之以恒**: 形成习惯比强度更重要
- **循序渐进**: 从小强度开始，逐渐增加
- **量力而行**: 根据自身情况调整
- **全面发展**: 有氧+力量+柔韧

### 推荐运动类型

**有氧运动** (每周150分钟):
- 快走、慢跑、游泳、骑自行车
- 跳绳、有氧操、舞蹈

**力量训练** (每周2-3次):
- 俯卧撑、深蹲、平板支撑
- 弹力带训练、哑铃训练

**柔韧性训练**:
- 瑜伽、太极、拉伸运动

### 注意事项
- 运动前热身5-10分钟
- 运动后拉伸放松
- 身体不适时停止
- 饭后1小时再运动

---

> 💡 找到自己喜欢的运动方式，才能长期坚持！
"""
        return response

    def _format_lifestyle_advice(self) -> str:
        """格式化生活方式建议"""
        response = """## 🌟 健康生活方式

### 🥗 饮食习惯
- 三餐规律，不暴饮暴食
- 低盐低脂，多吃蔬菜水果
- 充足饮水，每日1.5-2升
- 细嚼慢咽，每餐20分钟以上

### 😴 睡眠健康
- 成人每日7-9小时睡眠
- 固定作息时间
- 睡前1小时远离电子产品
- 营造良好睡眠环境

### 🏃 适量运动
- 每周至少150分钟中等强度运动
- 选择自己喜欢的运动方式
- 循序渐进，持之以恒

### 💆 心理调节
- 学会管理压力
- 保持社交活动
- 培养兴趣爱好
- 必要时寻求专业帮助

### 🚫 戒除不良习惯
- 戒烟
- 限酒
- 避免熬夜
- 减少久坐

---

> 💡 健康是一种习惯，从小事做起！
"""
        return response

    def _format_general_diet_advice(self) -> str:
        """格式化通用饮食建议"""
        response = """## 🥗 饮食健康指南

### 基本原则
- 食物多样，每天12种以上
- 谷类为主，粗细搭配
- 多吃蔬果（每日500克）
- 适量蛋白质
- 少盐少油少糖

### 三餐建议
- **早餐**: 要吃好（鸡蛋、牛奶、全麦面包）
- **午餐**: 要吃饱（荤素搭配）
- **晚餐**: 要吃少（清淡、七分饱）

### 注意事项
- 细嚼慢咽，每口嚼20-30次
- 定时定量，不暴饮暴食
- 饭后适度活动
- 充足饮水

---

> 💡 饮食是健康的基础，吃对了一切都对！
"""
        return response

    def _format_general_health_info(self) -> str:
        """格式化通用健康信息"""
        response = """## 📚 健康知识

### 常见疾病预防

**高血压**
- 低盐饮食，控制体重
- 规律运动，戒烟限酒
- 定期监测血压

**糖尿病**
- 控制碳水化合物摄入
- 增加运动量
- 定期检测血糖

**心血管疾病**
- 低脂低盐饮食
- 适量运动
- 控制三高（血压、血糖、血脂）

### 健康生活方式

**饮食**: 三餐规律，低盐低脂，多吃蔬果

**运动**: 每周150分钟中等强度运动

**睡眠**: 成人7-9小时，固定作息

**心理**: 管理压力，保持积极心态

---

> 💡 **提示**: 预防胜于治疗，定期体检是关键！
"""
        return response

    async def _greeting_skill(self, request: SkillRequest) -> SkillResponse:
        """问候处理Skill"""
        user_input = request.metadata.get("user_input", "")

        if any(word in user_input for word in ["你好", "您好"]):
            response = """## 👋 您好！

我是您的医疗健康助手，可以帮您：

- 🩺 **症状咨询** - 告诉我您的不适，我帮您分析
- 🏥 **科室推荐** - 不确定挂什么科，我来推荐
- 💊 **用药咨询** - 了解药品用法、副作用等
- 📅 **预约挂号** - 帮您预约医生
- 📚 **健康知识** - 疾病预防、健康生活方式

请问有什么可以帮您的？"""
        elif any(word in user_input for word in ["谢谢", "感谢"]):
            response = """## 😊 不客气！

很高兴能帮到您。如果还有其他健康问题，随时可以问我。

祝您身体健康！🌟"""
        else:
            response = """## 👋 您好！

我是医疗健康助手，有什么可以帮您的？

我可以帮您：
- 分析症状
- 推荐科室
- 用药咨询
- 健康指导"""
        return SkillResponse(success=True, content=response)

    async def _appointment_skill(self, request: SkillRequest) -> SkillResponse:
        """预约挂号Skill"""
        entities = request.entities
        department = entities.get("department", "")

        if department:
            response = f"""## 📅 预约挂号

您想预约 **{department}**，请确认以下信息：

### 预约流程
1. 选择科室：{department}
2. 选择医生：专家/普通
3. 选择时间：请提供方便的日期和时间
4. 确认预约：核对信息后确认

### 温馨提示
- 请提前1-3天预约
- 就诊时请携带身份证和医保卡
- 如需取消，请提前4小时

请告诉我您希望的就诊时间，我来帮您安排。

---

> ⚠️ **免责声明**: 预约成功后，请按时就诊。如需改期或取消，请提前联系医院。"""
        else:
            response = """## 📅 预约挂号

请告诉我以下信息，我来帮您预约：

### 需要的信息
1. **挂号科室** - 您想挂哪个科？
   - 内科、外科、妇科、儿科、骨科、眼科、耳鼻喉科等
2. **医生类型** - 专家门诊 / 普通门诊
3. **就诊时间** - 您希望什么时候来？

### 我可以帮您
- 推荐合适的科室（告诉我您的症状）
- 查看医生排班
- 协助预约挂号

请问您想挂哪个科？

---

> 💡 **提示**: 如果不确定挂什么科，可以先告诉我您的症状，我帮您推荐合适的科室。"""

        return SkillResponse(
            success=True,
            content=response,
            follow_up_suggestions=[
                "请问您希望什么时候就诊？",
                "需要帮您推荐科室吗？"
            ]
        )

    async def _fallback_skill(self, request: SkillRequest) -> SkillResponse:
        """兜底Skill"""
        user_input = request.metadata.get("user_input", "")

        response = """## 🤔 抱歉

我没有完全理解您的意思，可以试试：

1. **描述症状**: "我头痛"、"最近一直咳嗽"
2. **询问科室**: "头痛挂什么科"
3. **用药咨询**: "阿莫西林怎么吃"
4. **健康问题**: "怎么预防高血压"

或者换个说法再试试？

---

> 💡 **提示**: 您也可以直接告诉我您想了解什么，我会尽力帮助您。"""

        # 尝试提供相关建议
        suggestions = []
        if any(kw in user_input for kw in ["疼", "痛", "难受"]):
            suggestions.append("您可以描述一下具体的症状和部位吗？")
        if "药" in user_input:
            suggestions.append("请问您想了解哪种药品的信息？")
        if "预防" in user_input or "怎么" in user_input:
            suggestions.append("我可以提供健康生活方式的建议。")

        if suggestions:
            response += "\n\n" + "\n".join(f"> 💡 {s}" for s in suggestions)

        return SkillResponse(success=True, content=response)


# ============================================================
# 医疗 Agent 主类
# ============================================================

class MedicalAgent:
    """
    医疗智能Agent
    基于语义自动匹配任务并调度Skill
    """

    def __init__(self, agent_id: str = "medical-agent", mcp_client=None):
        self.agent_id = agent_id
        self.mcp_client = mcp_client
        self.classifier = IntentClassifier()
        self.skill_invoker = SkillInvoker(mcp_client)
        self.sessions: Dict[str, DialogueContext] = {}
        self._running = False

        # 查询重写器
        self.query_rewriter = QueryRewriter(llm_client=None)

    async def start(self):
        """启动Agent"""
        logger.info(f"[Agent] {self.agent_id} starting...")
        self._running = True
        logger.info(f"[Agent] {self.agent_id} started")

    async def stop(self):
        """停止Agent"""
        logger.info(f"[Agent] {self.agent_id} stopping...")
        self._running = False
        self.sessions.clear()
        logger.info(f"[Agent] {self.agent_id} stopped")

    def get_or_create_context(self, session_id: str, user_id: str) -> DialogueContext:
        """获取或创建对话上下文"""
        if session_id not in self.sessions:
            self.sessions[session_id] = DialogueContext(
                session_id=session_id,
                user_id=user_id
            )
        return self.sessions[session_id]

    async def process(
        self,
        user_input: str,
        session_id: str = "default",
        user_id: str = "anonymous"
    ) -> str:
        """
        处理用户输入

        Args:
            user_input: 用户输入文本
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            str: Agent响应
        """
        # 获取上下文
        context = self.get_or_create_context(session_id, user_id)

        # 1. 意图识别
        intent_result = await self.classifier.classify(user_input, context)

        # 保存当前意图到上下文（供API访问）
        context.current_intent = intent_result

        # 检查是否需要澄清
        if intent_result.requires_clarification:
            return intent_result.clarification_question

        # 2. 更新上下文
        context.update_entities(intent_result.entities)

        # 3. 构建Skill请求
        skill_request = SkillRequest(
            skill_name=intent_result.target_skill,
            intent=intent_result.intent,
            entities={**context.accumulated_entities, **intent_result.entities},
            context=context,
            metadata={"user_input": user_input}
        )

        # 4. 调用Skill
        skill_response = await self.skill_invoker.invoke(skill_request)

        # 5. 添加到历史
        context.add_turn(user_input, skill_response.content, intent_result)

        # 6. 返回响应
        return skill_response.content

    def get_context(self, session_id: str) -> Optional[DialogueContext]:
        """获取对话上下文"""
        return self.sessions.get(session_id)

    def clear_context(self, session_id: str):
        """清除对话上下文"""
        if session_id in self.sessions:
            del self.sessions[session_id]


# ============================================================
# 使用示例
# ============================================================

async def main():
    """演示Agent使用"""
    from mcp_tools.medical_tools import create_medical_mcp_server, MCPFactory
    from mcp_protocol.mcp_protocol import MCPClient

    # 创建MCP基础设施
    host = MCPFactory.create_host("medical-mcp-host")
    await host.start()

    server = await create_medical_mcp_server(host)
    await server.start()

    mcp_client = MCPClient("agent-mcp-client", host)
    await mcp_client.start()

    # 创建Agent
    agent = MedicalAgent(mcp_client=mcp_client)
    await agent.start()

    print("\n" + "="*60)
    print("医疗智能Agent已启动")
    print("="*60 + "\n")

    # 测试对话
    test_inputs = [
        "你好",
        "我头痛好几天了",
        "头痛应该挂什么科",
        "阿莫西林怎么吃",
        "怎么预防高血压",
    ]

    for user_input in test_inputs:
        print(f"👤 用户: {user_input}")
        response = await agent.process(user_input)
        print(f"🤖 助手:\n{response}\n")
        print("-" * 60)
        await asyncio.sleep(0.5)

    # 清理
    await agent.stop()
    await mcp_client.stop()
    await server.stop()
    await host.stop()


if __name__ == "__main__":
    asyncio.run(main())
