"""
医疗智能助手 - Agent 框架实现示例
包含：意图识别、实体抽取、槽位填充、Hooks机制、Skill调用、MCP工具整合
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List, Callable, Awaitable
from enum import Enum
import asyncio
from functools import wraps
import re


# ============================================================
# 数据模型定义
# ============================================================

class IntentType(Enum):
    """意图类型枚举"""
    SYMPTOM_INQUIRY = "symptom_inquiry"
    DEPARTMENT_QUERY = "department_query"
    MEDICATION_CONSULT = "medication_consult"
    APPOINTMENT_BOOK = "appointment_book"
    REPORT_INTERPRET = "report_interpret"
    HEALTH_EDU = "health_edu"
    CHITCHAT = "chitchat"
    UNKNOWN = "unknown"


class EntityType(Enum):
    """实体类型枚举"""
    BODY_PART = "body_part"
    SYMPTOM = "symptom"
    DISEASE = "disease"
    MEDICINE = "medicine"
    TIME_DURATION = "time_duration"
    SEVERITY = "severity"
    VITAL_SIGN = "vital_sign"


@dataclass
class Intent:
    """意图识别结果"""
    name: IntentType
    confidence: float
    raw_text: str
    candidates: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Entity:
    """实体"""
    type: EntityType
    value: Any
    span: tuple[int, int]
    confidence: float
    raw_text: str


@dataclass
class SlotConfig:
    """槽位配置"""
    name: str
    slot_type: str
    required: bool = True
    description: str = ""
    prompt: str = ""
    enum_values: Optional[List[str]] = None


@dataclass
class SlotResult:
    """槽位填充结果"""
    complete: bool
    slots: Dict[str, Any]
    missing: List[str] = field(default_factory=list)
    pending_slot: Optional[str] = None
    prompt: Optional[str] = None
    error: Optional[str] = None


@dataclass
class MCPResult:
    """MCP工具调用结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    tool_name: str = ""
    execution_time: float = 0.0


@dataclass
class SkillResult:
    """Skill执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    response: str = ""
    need_clarification: bool = False


@dataclass
class DialogueContext:
    """对话上下文"""
    session_id: str
    user_id: str
    history: List[Dict] = field(default_factory=list)
    current_intent: Optional[Intent] = None
    filled_slots: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    turn_count: int = 0

    def add_turn(self, user_input: str, agent_response: str, intent: Optional[Intent] = None):
        """添加对话轮次"""
        self.history.append({
            "turn": self.turn_count,
            "user_input": user_input,
            "agent_response": agent_response,
            "intent": intent.name if intent else None,
            "timestamp": asyncio.get_event_loop().time()
        })
        self.turn_count += 1

    def get_last_intent(self) -> Optional[IntentType]:
        """获取上一个意图"""
        if self.history:
            last_turn = self.history[-1]
            intent_name = last_turn.get("intent")
            if intent_name:
                return IntentType(intent_name)
        return None


# ============================================================
# Hooks 系统
# ============================================================

class HookManager:
    """Hook管理器"""

    def __init__(self):
        self.hooks: Dict[str, List[Callable]] = {}

    def register(self, hook_name: str, handler: Callable, priority: int = 0):
        """注册Hook处理器"""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        self.hooks[hook_name].append((handler, priority))
        # 按优先级排序
        self.hooks[hook_name].sort(key=lambda x: x[1], reverse=True)

    async def execute(self, hook_name: str, *args, **kwargs) -> Any:
        """执行Hook"""
        if hook_name not in self.hooks:
            return None

        result = None
        for handler, _ in self.hooks[hook_name]:
            ret = handler(*args, **kwargs)
            if asyncio.iscoroutine(ret):
                ret = await ret
            if ret is not None:
                result = ret
        return result


def hook(hook_name: str = ""):
    """Hook装饰器"""
    def decorator(func):
        func._hook_name = hook_name or func.__name__
        return func
    return decorator


# ============================================================
# 意图识别器
# ============================================================

class IntentDetector:
    """意图识别器"""

    def __init__(self, config: Dict, hook_manager: HookManager):
        self.config = config
        self.hooks = hook_manager
        self.intent_patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[IntentType, List[str]]:
        """加载意图模式"""
        return {
            IntentType.SYMPTOM_INQUIRY: [
                r"(我|最近)(.+?)(疼|痛|难受|不舒服)",
                r"(.+?)怎么回事",
            ],
            IntentType.DEPARTMENT_QUERY: [
                r"(.+?)挂什么科",
                r"(.+?)去哪个科室",
                r"(.+科)在哪里",
            ],
            IntentType.MEDICATION_CONSULT: [
                r"(.+?药)(怎么吃|怎么用|用量)",
                r"(.+?)有什么副作用",
                r"(.+?)能一起吃吗",
            ],
            IntentType.APPOINTMENT_BOOK: [
                r"挂(个)?号",
                r"预约(.+?)门诊",
                r"想挂号",
            ],
            IntentType.REPORT_INTERPRET: [
                r"看看(.+?)报告",
                r"(.+?)结果正常吗",
                r"(.+?)指标(偏高|偏低)",
            ],
            IntentType.HEALTH_EDU: [
                r"怎么预防(.+?)",
                r"(.+?)不能吃什么",
                r"如何保持(.+?)",
            ],
            IntentType.CHITCHAT: [
                r"^(你好|您好|hi|hello)$",
                r"^(谢谢|感谢)$",
                r"^(你是谁|你叫什么)$",
            ],
        }

    async def detect(self, text: str, context: DialogueContext) -> Intent:
        """识别用户意图"""

        # before_intent hook
        text = await self.hooks.execute("before_intent", text, context) or text

        # 规则匹配
        detected_intent = None
        confidence = 0.0
        candidates = []

        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    conf = self._calculate_confidence(text, pattern, intent_type)
                    candidates.append({
                        "intent": intent_type,
                        "confidence": conf
                    })
                    if conf > confidence:
                        confidence = conf
                        detected_intent = intent_type

        # 未匹配到则返回未知意图
        if detected_intent is None:
            detected_intent = IntentType.UNKNOWN
            confidence = 0.0

        # 检查置信度阈值
        threshold = self.config.get("intent_threshold", 0.75)
        if confidence < threshold:
            # intent_fallback hook
            fallback_result = await self.hooks.execute(
                "intent_fallback", text, confidence, context
            )
            if fallback_result:
                return fallback_result

        result = Intent(
            name=detected_intent,
            confidence=confidence,
            raw_text=text,
            candidates=candidates
        )

        # after_intent hook
        result = await self.hooks.execute("after_intent", result, context) or result

        return result

    def _calculate_confidence(self, text: str, pattern: str, intent_type: IntentType) -> float:
        """计算置信度"""
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return 0.0

        base_confidence = 0.8

        # 根据匹配长度调整
        match_length = len(match.group(0))
        text_length = len(text)
        if match_length / text_length > 0.5:
            base_confidence += 0.1

        return min(base_confidence, 1.0)


# ============================================================
# 实体抽取器
# ============================================================

class EntityExtractor:
    """实体抽取器"""

    def __init__(self, config: Dict, hook_manager: HookManager):
        self.config = config
        self.hooks = hook_manager
        self.entity_patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[EntityType, Any]:
        """加载实体模式"""
        return {
            EntityType.BODY_PART: {
                "values": ["头部", "头", "颈部", "脖子", "胸部", "腹部", "肚子", "背", "腰"],
                "type": "enum"
            },
            EntityType.SYMPTOM: {
                "values": ["疼", "痛", "发热", "发烧", "咳嗽", "恶心", "呕吐", "头晕", "乏力"],
                "type": "enum"
            },
            EntityType.TIME_DURATION: {
                "patterns": [
                    r"(\d+)(天|日|周|个月)",
                    r"从(.+?)开始",
                    r"持续(.+?)"
                ],
                "type": "regex"
            },
            EntityType.SEVERITY: {
                "mapping": {
                    "轻微": "mild",
                    "有点": "mild",
                    "稍微": "mild",
                    "比较": "moderate",
                    "挺": "moderate",
                    "非常": "severe",
                    "特别": "severe",
                    "剧烈": "severe"
                },
                "type": "mapping"
            }
        }

    async def extract(self, text: str, intent: Intent, context: DialogueContext) -> List[Entity]:
        """抽取实体"""

        # before_extract hook
        text = await self.hooks.execute("before_extract", text, intent, context) or text

        entities = []

        for entity_type, config in self.entity_patterns.items():
            if config["type"] == "enum":
                for value in config["values"]:
                    if value in text:
                        start = text.find(value)
                        end = start + len(value)
                        entity = Entity(
                            type=entity_type,
                            value=value,
                            span=(start, end),
                            confidence=0.9,
                            raw_text=value
                        )
                        entities.append(entity)

            elif config["type"] == "regex":
                for pattern in config["patterns"]:
                    match = re.search(pattern, text)
                    if match:
                        entity = Entity(
                            type=entity_type,
                            value=match.group(0),
                            span=match.span(),
                            confidence=0.85,
                            raw_text=match.group(0)
                        )
                        entities.append(entity)

            elif config["type"] == "mapping":
                for key, value in config["mapping"].items():
                    if key in text:
                        start = text.find(key)
                        end = start + len(key)
                        entity = Entity(
                            type=entity_type,
                            value=value,
                            span=(start, end),
                            confidence=0.85,
                            raw_text=key
                        )
                        entities.append(entity)

        # entity_normalize hook
        normalized_entities = []
        for entity in entities:
            normalized = await self.hooks.execute("entity_normalize", entity) or entity
            normalized_entities.append(normalized)

        # after_extract hook
        result = await self.hooks.execute("after_extract", normalized_entities, context)
        if result:
            normalized_entities = result

        return normalized_entities


# ============================================================
# 槽位填充器
# ============================================================

class SlotFiller:
    """槽位填充器"""

    def __init__(self, config: Dict, hook_manager: HookManager):
        self.config = config
        self.hooks = hook_manager
        self.slot_templates = self._load_templates()

    def _load_templates(self) -> Dict[IntentType, Dict[str, SlotConfig]]:
        """加载槽位模板"""
        return {
            IntentType.SYMPTOM_INQUIRY: {
                "body_part": SlotConfig(
                    name="body_part",
                    slot_type="BODY_PART",
                    required=True,
                    description="不适部位",
                    prompt="请问您哪里不舒服？"
                ),
                "symptom": SlotConfig(
                    name="symptom",
                    slot_type="SYMPTOM",
                    required=True,
                    description="具体症状",
                    prompt="请问具体是什么感觉？比如疼痛、发热等？"
                ),
                "duration": SlotConfig(
                    name="duration",
                    slot_type="TIME_DURATION",
                    required=False,
                    description="持续时间",
                    prompt="请问这种情况持续多久了？"
                ),
                "severity": SlotConfig(
                    name="severity",
                    slot_type="SEVERITY",
                    required=False,
                    description="严重程度",
                    prompt="请问严重程度如何？轻微/中等/严重？"
                ),
            },
            IntentType.DEPARTMENT_QUERY: {
                "symptom_or_disease": SlotConfig(
                    name="symptom_or_disease",
                    slot_type="str",
                    required=True,
                    description="症状或疾病",
                    prompt="请问您有什么不适或想看什么病？"
                ),
            },
            IntentType.MEDICATION_CONSULT: {
                "medicine": SlotConfig(
                    name="medicine",
                    slot_type="MEDICINE",
                    required=True,
                    description="药物名称",
                    prompt="请问您咨询哪种药物？"
                ),
            },
        }

    async def fill(
        self,
        intent: Intent,
        entities: List[Entity],
        context: DialogueContext,
        user_input: str
    ) -> SlotResult:
        """填充槽位"""

        template = self.slot_templates.get(intent.name)
        if not template:
            return SlotResult(complete=True, slots={})

        # 合并上下文中的槽位
        current_slots = {**context.filled_slots}

        # before_fill hook
        current_slots = await self.hooks.execute("before_fill", current_slots, entities) or current_slots

        # 从实体映射到槽位
        for entity in entities:
            for slot_name, slot_config in template.items():
                if entity.type.value == slot_config.slot_type:
                    current_slots[slot_name] = entity.value

        # 更新上下文
        context.filled_slots = current_slots

        # 检查必填槽位
        missing = []
        for slot_name, slot_config in template.items():
            if slot_config.required and slot_name not in current_slots:
                missing.append(slot_name)

        if missing:
            # slot_required hook
            prompt = None
            for slot_name in missing:
                hook_prompt = await self.hooks.execute(
                    "slot_required", slot_name, template[slot_name]
                )
                if hook_prompt:
                    prompt = hook_prompt
                    break
                elif not prompt:
                    prompt = template[slot_name].prompt

            return SlotResult(
                complete=False,
                slots=current_slots,
                missing=missing,
                pending_slot=missing[0],
                prompt=prompt
            )

        # 检查槽位冲突
        conflict = await self.hooks.execute("slot_conflict", current_slots, template)
        if conflict:
            return SlotResult(
                complete=False,
                slots=current_slots,
                error=conflict
            )

        # after_fill hook
        result = await self.hooks.execute("after_fill", current_slots, context)

        return SlotResult(
            complete=True,
            slots=current_slots
        )


# ============================================================
# MCP 客户端
# ============================================================

class MCPClient:
    """MCP客户端"""

    def __init__(self, server_name: str, endpoint: str, timeout: int = 30):
        self.server_name = server_name
        self.endpoint = endpoint
        self.timeout = timeout
        self.available_tools = set()

    async def connect(self):
        """连接MCP服务器"""
        # 模拟连接
        print(f"[MCP] 连接到 {self.server_name} at {self.endpoint}")
        await asyncio.sleep(0.1)
        return True

    async def call_tool(self, tool_name: str, parameters: Dict) -> MCPResult:
        """调用MCP工具"""
        import time
        start_time = time.time()

        print(f"[MCP.{self.server_name}] 调用工具: {tool_name}")
        print(f"[MCP.{self.server_name}] 参数: {parameters}")

        # 模拟调用延迟
        await asyncio.sleep(0.2)

        # 模拟返回结果
        result = self._mock_result(tool_name, parameters)

        execution_time = time.time() - start_time

        return MCPResult(
            success=True,
            data=result,
            tool_name=tool_name,
            execution_time=execution_time
        )

    def _mock_result(self, tool_name: str, parameters: Dict) -> Dict:
        """模拟工具返回结果"""
        mock_results = {
            "query_symptom": {
                "description": f"{parameters.get('symptom', '症状')}的相关信息",
                "possible_causes": ["原因1", "原因2"],
                "red_flags": []
            },
            "check_red_flags": {
                "has_red_flag": False,
                "flags": [],
                "action": "继续观察"
            },
            "get_triage_suggestion": {
                "urgency": "routine",
                "department": "内科",
                "advice": "建议常规就诊"
            },
            "get_medicine_info": {
                "name": parameters.get("medicine_name", "药物"),
                "generic_name": "通用名",
                "description": "药物说明"
            },
            "get_departments": {
                "departments": [
                    {"id": "1", "name": "内科", "location": "1楼"},
                    {"id": "2", "name": "外科", "location": "2楼"},
                ]
            }
        }
        return mock_results.get(tool_name, {})

    async def list_tools(self) -> List[str]:
        """列出可用工具"""
        return list(self.available_tools)


# ============================================================
# MCP 管理器
# ============================================================

class MCPManager:
    """MCP管理器"""

    def __init__(self, config: Dict):
        self.config = config
        self.clients: Dict[str, MCPClient] = {}
        self._initialized = False

    async def initialize(self):
        """初始化所有MCP客户端"""
        if self._initialized:
            return

        for server_name, server_config in self.config.get("mcp_servers", {}).items():
            if server_config.get("enabled", True):
                client = MCPClient(
                    server_name=server_name,
                    endpoint=server_config["endpoint"],
                    timeout=server_config.get("timeout", 30)
                )
                await client.connect()
                self.clients[server_name] = client

        self._initialized = True

    def get_client(self, server_name: str) -> Optional[MCPClient]:
        """获取MCP客户端"""
        return self.clients.get(server_name)

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        parameters: Dict
    ) -> MCPResult:
        """调用工具"""
        client = self.get_client(server_name)
        if not client:
            return MCPResult(
                success=False,
                error=f"MCP server {server_name} not found"
            )

        return await client.call_tool(tool_name, parameters)


# ============================================================
# Skill 基类与实现
# ============================================================

class Skill(ABC):
    """Skill基类"""

    def __init__(
        self,
        name: str,
        description: str,
        mcp_manager: MCPManager,
        hook_manager: HookManager
    ):
        self.name = name
        self.description = description
        self.mcp_manager = mcp_manager
        self.hooks = hook_manager

    @abstractmethod
    async def execute(
        self,
        parameters: Dict,
        context: DialogueContext
    ) -> SkillResult:
        """执行Skill逻辑"""
        pass

    async def validate(self, parameters: Dict) -> bool:
        """验证参数"""
        return True


class SymptomAnalyzerSkill(Skill):
    """症状分析Skill"""

    def __init__(self, mcp_manager: MCPManager, hook_manager: HookManager):
        super().__init__(
            name="symptom_analyzer",
            description="分析用户症状，提供初步建议",
            mcp_manager=mcp_manager,
            hook_manager=hook_manager
        )

    async def execute(
        self,
        parameters: Dict,
        context: DialogueContext
    ) -> SkillResult:
        """执行症状分析"""

        # before_execute hook
        parameters = await self.hooks.execute("before_execute", self.name, parameters, context) or parameters

        body_part = parameters.get("body_part", "")
        symptom = parameters.get("symptom", "")
        duration = parameters.get("duration", "")
        severity = parameters.get("severity", "")

        # 调用MCP工具
        symptom_result = await self.mcp_manager.call_tool(
            "medical_knowledge",
            "query_symptom",
            {"symptom": symptom, "body_part": body_part}
        )

        red_flags_result = await self.mcp_manager.call_tool(
            "medical_knowledge",
            "check_red_flags",
            {"symptoms": [{"body_part": body_part, "symptom": symptom}]}
        )

        triage_result = await self.mcp_manager.call_tool(
            "medical_knowledge",
            "get_triage_suggestion",
            {"symptoms": [parameters], "patient_info": {}}
        )

        # 构建响应
        response_parts = [
            f"了解到您{body_part}{symptom}",
            f"持续{duration}" if duration else "",
        ]
        response_parts = [p for p in response_parts if p]
        response = "，".join(response_parts) + "。"

        if red_flags_result.data.get("has_red_flag"):
            response += "\n⚠️ **建议**: 根据您的症状，建议您尽快就医。"

        response += f"\n\n推荐科室: {triage_result.data.get('department', '内科')}"

        # after_execute hook
        result = SkillResult(
            success=True,
            data={
                "symptom_info": symptom_result.data,
                "red_flags": red_flags_result.data,
                "triage": triage_result.data
            },
            response=response
        )

        result = await self.hooks.execute("after_execute", result, context) or result

        return result


class DepartmentRecommenderSkill(Skill):
    """科室推荐Skill"""

    def __init__(self, mcp_manager: MCPManager, hook_manager: HookManager):
        super().__init__(
            name="department_recommender",
            description="根据症状推荐挂号科室",
            mcp_manager=mcp_manager,
            hook_manager=hook_manager
        )

    async def execute(
        self,
        parameters: Dict,
        context: DialogueContext
    ) -> SkillResult:
        """执行科室推荐"""

        symptom_or_disease = parameters.get("symptom_or_disease", "")

        # 调用MCP工具
        dept_result = await self.mcp_manager.call_tool(
            "hospital_system",
            "get_departments",
            {"hospital_id": "default"}
        )

        departments = dept_result.data.get("departments", [])

        # 简单匹配规则
        recommendations = []
        symptom_lower = symptom_or_disease.lower()

        for dept in departments:
            dept_name = dept["name"]
            if any(kw in symptom_lower for kw in ["头", "晕", "神"]):
                if dept_name == "神经内科":
                    recommendations.append(dept)
            elif dept_name == "内科":
                recommendations.append(dept)

        response = f"根据「{symptom_or_disease}」症状，建议挂号科室：\n\n"
        for dept in recommendations[:3]:
            response += f"- {dept['name']} ({dept['location']})\n"

        response += "\n需要我帮您挂号吗？"

        return SkillResult(
            success=True,
            data={"recommendations": recommendations},
            response=response
        )


class MedicationAdvisorSkill(Skill):
    """用药咨询Skill"""

    def __init__(self, mcp_manager: MCPManager, hook_manager: HookManager):
        super().__init__(
            name="medication_advisor",
            description="提供药物使用咨询",
            mcp_manager=mcp_manager,
            hook_manager=hook_manager
        )

    async def execute(
        self,
        parameters: Dict,
        context: DialogueContext
    ) -> SkillResult:
        """执行用药咨询"""

        medicine = parameters.get("medicine", "")

        # 调用MCP工具
        drug_result = await self.mcp_manager.call_tool(
            "drug_database",
            "get_medicine_info",
            {"medicine_name": medicine}
        )

        response = f"关于 {medicine} 的用药说明：\n\n"
        response += f"💊 **药品信息**\n"
        response += f"- 药品名称: {medicine}\n"
        response += f"- 请在医生指导下使用\n\n"
        response += f"⚠️ **注意事项**\n"
        response += f"- 请遵医嘱服用\n"
        response += f"- 如有不良反应请立即停药就医\n\n"
        response += "还有其他关于该药物的问题吗？"

        return SkillResult(
            success=True,
            data=drug_result.data,
            response=response
        )


# ============================================================
# Skill 注册中心
# ============================================================

class SkillRegistry:
    """Skill注册中心"""

    def __init__(self, mcp_manager: MCPManager, hook_manager: HookManager):
        self.skills: Dict[str, Skill] = {}
        self.intent_skill_map: Dict[IntentType, str] = {}
        self.mcp_manager = mcp_manager
        self.hooks = hook_manager

    def register(self, skill: Skill, intents: List[IntentType]):
        """注册Skill"""
        self.skills[skill.name] = skill
        for intent in intents:
            self.intent_skill_map[intent] = skill.name

    def get_skill(self, name: str) -> Optional[Skill]:
        """获取Skill"""
        return self.skills.get(name)

    def get_skill_by_intent(self, intent: IntentType) -> Optional[Skill]:
        """根据意图获取Skill"""
        skill_name = self.intent_skill_map.get(intent)
        return self.skills.get(skill_name) if skill_name else None


# ============================================================
# Agent 核心处理器
# ============================================================

class MedicalAgent:
    """医疗智能Agent"""

    def __init__(self, config: Dict):
        self.config = config

        # 初始化组件
        self.hook_manager = HookManager()
        self.intent_detector = IntentDetector(config, self.hook_manager)
        self.entity_extractor = EntityExtractor(config, self.hook_manager)
        self.slot_filler = SlotFiller(config, self.hook_manager)
        self.mcp_manager = MCPManager(config)

        # 初始化Skill注册中心
        self.skill_registry = SkillRegistry(self.mcp_manager, self.hook_manager)

        # 注册默认Hooks
        self._register_default_hooks()

    async def initialize(self):
        """初始化Agent"""
        await self.mcp_manager.initialize()

        # 注册Skills
        self.skill_registry.register(
            SymptomAnalyzerSkill(self.mcp_manager, self.hook_manager),
            [IntentType.SYMPTOM_INQUIRY]
        )
        self.skill_registry.register(
            DepartmentRecommenderSkill(self.mcp_manager, self.hook_manager),
            [IntentType.DEPARTMENT_QUERY]
        )
        self.skill_registry.register(
            MedicationAdvisorSkill(self.mcp_manager, self.hook_manager),
            [IntentType.MEDICATION_CONSULT]
        )

    def _register_default_hooks(self):
        """注册默认Hooks"""

        @hook("entity_normalize")
        async def normalize_body_part(entity: Entity) -> Optional[Entity]:
            """标准化身体部位"""
            if entity.type == EntityType.BODY_PART:
                mapping = {"头": "头部", "肚子": "腹部", "腰": "腰部"}
                if entity.value in mapping:
                    entity.value = mapping[entity.value]
            return entity

        @hook("after_response")
        async def append_disclaimer(response: str) -> str:
            """追加免责声明"""
            if not response.endswith("。"):
                response += "。"
            disclaimer = "\n\n⚠️ *本信息仅供参考，不能替代专业医疗建议。如有不适请及时就医。*"
            return response + disclaimer

        # 注册Hooks
        self.hook_manager.register("entity_normalize", normalize_body_part, priority=1)
        self.hook_manager.register("after_response", append_disclaimer, priority=1)

    async def process(
        self,
        user_input: str,
        context: DialogueContext
    ) -> str:
        """处理用户输入"""

        print(f"\n{'='*60}")
        print(f"用户输入: {user_input}")
        print(f"{'='*60}")

        # ========== 1. 意图识别 ==========
        print("[1/5] 意图识别...")
        intent = await self.intent_detector.detect(user_input, context)
        context.current_intent = intent
        print(f"    → 意图: {intent.name.value} (置信度: {intent.confidence:.2f})")

        # 未知意图处理
        if intent.name == IntentType.UNKNOWN:
            return "抱歉，我没有完全理解您的意思，可以换个说法吗？"

        # ========== 2. 实体抽取 ==========
        print("[2/5] 实体抽取...")
        entities = await self.entity_extractor.extract(user_input, intent, context)
        print(f"    → 抽取到 {len(entities)} 个实体:")
        for entity in entities:
            print(f"       - {entity.type.value}: {entity.value}")

        # ========== 3. 槽位填充 ==========
        print("[3/5] 槽位填充...")
        slot_result = await self.slot_filler.fill(intent, entities, context, user_input)

        if not slot_result.complete:
            print(f"    → 槽位未完整: {slot_result.missing}")
            print(f"    → 追问: {slot_result.prompt}")
            return slot_result.prompt

        print(f"    → 槽位完整: {list(slot_result.slots.keys())}")

        # ========== 4. Skill执行 ==========
        print("[4/5] Skill执行...")
        skill = self.skill_registry.get_skill_by_intent(intent.name)
        if not skill:
            return "抱歉，该功能暂未开放。"

        print(f"    → 调用Skill: {skill.name}")
        skill_result = await skill.execute(slot_result.slots, context)

        if not skill_result.success:
            return f"处理出错: {skill_result.error}"

        # ========== 5. 响应生成 ==========
        print("[5/5] 响应生成...")

        # before_response hook
        response = await self.hooks.execute("before_response", skill_result, context) or skill_result.response

        # format_response hook
        response = await self.hooks.execute("format_response", response, "markdown") or response

        # after_response hook
        response = await self.hooks.execute("after_response", response) or response

        # 添加到对话历史
        context.add_turn(user_input, response, intent)

        print(f"    → 响应生成完成")
        print(f"{'='*60}\n")

        return response


# ============================================================
# 使用示例
# ============================================================

async def main():
    """主函数示例"""

    # 配置
    config = {
        "intent_threshold": 0.75,
        "mcp_servers": {
            "medical_knowledge": {
                "enabled": True,
                "endpoint": "http://localhost:3001"
            },
            "hospital_system": {
                "enabled": True,
                "endpoint": "http://localhost:3002"
            },
            "drug_database": {
                "enabled": True,
                "endpoint": "http://localhost:3003"
            }
        }
    }

    # 创建Agent
    agent = MedicalAgent(config)
    await agent.initialize()

    # 创建对话上下文
    context = DialogueContext(
        session_id="session_001",
        user_id="user_001"
    )

    # 测试对话
    test_inputs = [
        "我头疼三天了",
        "挺疼的，有点恶心",
        "头疼应该挂什么科",
        "阿莫西林怎么吃"
    ]

    for user_input in test_inputs:
        response = await agent.process(user_input, context)
        print(f"\n🤖 助手: {response}\n")
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
