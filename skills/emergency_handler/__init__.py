# -*- coding: utf-8 -*-
"""
紧急处理Skill
识别紧急情况，提供急救指导和120拨打引导
"""

import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class EmergencyLevel(Enum):
    """紧急程度级别"""
    E_CRITICAL = "E"    # 危急 - 需要立即拨打120
    A_URGENT = "A"      # 紧急 - 立即急诊
    B_SOON = "B"        # 较急 - 尽快就医
    C_ROUTINE = "C"     # 普通 - 常规就诊


@dataclass
class EmergencyGuidance:
    """急救指导"""
    level: EmergencyLevel
    description: str
    symptoms: List[str]
    immediate_actions: List[str]
    first_aid: str
    when_to_call_120: str


@dataclass
class EmergencyResult:
    """紧急处理结果"""
    detected: bool
    level: Optional[EmergencyLevel] = None
    content: str = ""
    guidance: Optional[EmergencyGuidance] = None


class EmergencyHandlerSkill:
    """
    紧急处理Skill
    识别紧急情况，提供急救指导和120拨打引导
    """

    # 紧急情况模式库
    EMERGENCY_PATTERNS = {
        EmergencyLevel.E_CRITICAL: {
            "patterns": [
                r"(意识|昏迷|晕厥|抽搐|癫痫).{0,10}(丧失|不清)",
                r"呼吸.{0,10}(停止|困难|衰竭)",
                r"(大出血|大量出血|出血不止)",
                r"(心脏|心跳).{0,10}(骤停|停止)",
                r"窒息.{0,10}(气管|气道)",
                r"(触电|溺水|中毒).{0,20}(昏迷|意识不清)",
            ],
            "description": "危急情况 - 需要立即抢救",
            "call_120": "立即拨打120",
        },
        EmergencyLevel.A_URGENT: {
            "patterns": [
                r"(胸痛|心痛).{0,20}(剧烈|严重|放射性)",
                r"(呼吸困难|气促|喘不过气).{0,20}(严重|剧烈)",
                r"(严重|剧烈).{0,10}(过敏反应|过敏性休克)",
                r"(高烧|发热).{0,10}(39|40).{0,5}(度|℃)",
                r"(剧烈|严重).{0,10}(头痛|腹痛)",
                r"(严重|大量).{0,10}(呕吐|腹泻).{0,10}(脱水)",
                r"(烧|烫)伤.{0,10}(大面积|严重)",
            ],
            "description": "紧急情况 - 需要立即急诊",
            "call_120": "如有加重立即拨打120",
        },
        EmergencyLevel.B_SOON: {
            "patterns": [
                r"(头痛|头晕).{0,20}(几天|一周|持续|反复)",
                r"(高烧|发热).{0,10}(38|39).{0,5}(度|℃).{0,20}(持续|反复)",
                r"(咳嗽|气促).{0,20}(加重|持续)",
                r"(腹痛|腹泻).{0,20}(持续|反复)",
                r"(外伤|伤口).{0,20}(感染|红肿)",
            ],
            "description": "较急情况 - 尽快就医",
            "call_120": "必要时拨打120",
        },
    }

    # 急救指导库
    FIRST_AID_GUIDANCE = {
        "意识丧失": EmergencyGuidance(
            level=EmergencyLevel.E_CRITICAL,
            description="患者意识丧失，需要立即抢救",
            symptoms=["无反应", "可能无呼吸", "可能无脉搏"],
            immediate_actions=["检查呼吸", "检查脉搏", "开始CPR", "拨打120"],
            first_aid="""### CPR操作要点
1. **检查意识**: 拍打双肩呼唤
2. **检查呼吸**: 看胸廓起伏 5-10秒
3. **呼救**: 立即拨打120，取AED
4. **胸外按压**:
   - 位置: 两乳头连线中点
   - 深度: 5-6厘米
   - 频率: 100-120次/分钟
   - 比例: 30次按压:2次人工呼吸
5. **持续进行**: 直到急救人员到达""",
            when_to_call_120="立即拨打120"
        ),
        "呼吸困难": EmergencyGuidance(
            level=EmergencyLevel.A_URGENT,
            description="呼吸困难，需要立即处理",
            symptoms=["呼吸急促", "胸闷气短", "可能发绀"],
            immediate_actions=["保持坐位", "解开衣领", "开窗通风", "立即就医"],
            first_aid="""### 紧急处理
1. **体位**: 半坐位，身体前倾
2. **呼吸**: 缓慢深呼吸
3. **环境**: 保持空气流通
4. **用药**: 如有哮喘喷雾可使用
5. **就医**: 症状无缓解立即急诊""",
            when_to_call_120="如症状加重立即拨打120"
        ),
        "胸痛": EmergencyGuidance(
            level=EmergencyLevel.A_URGENT,
            description="胸痛可能是心肌梗死征兆",
            symptoms=["胸骨后疼痛", "可能放射至左肩臂", "可能伴出汗恶心"],
            immediate_actions=["停止活动", "保持镇静", "服用硝酸甘油", "立即呼叫急救"],
            first_aid="""### 紧急处理
1. **停止**: 立即停止一切活动
2. **体位**: 半卧位休息
3. **用药**: 舌下含服硝酸甘油
4. **呼救**: 立即拨打120
5. **准备**: 解开衣领，准备医保卡""",
            when_to_call_120="立即拨打120"
        ),
        "大出血": EmergencyGuidance(
            level=EmergencyLevel.E_CRITICAL,
            description="大出血需要立即止血",
            symptoms=["大量出血", "可能伴头晕冷汗", "可能休克"],
            immediate_actions=["按压止血", "抬高伤肢", "拨打120", "保暖"],
            first_aid="""### 止血方法
1. **直接压迫**: 用干净布料直接按压伤口
2. **抬高**: 将伤肢抬高至心脏以上
3. **加压**: 如仍出血，增加压力
4. **止血带**: 四肢大出血可用止血带
5. **休克**: 平卧，保暖，不要进食水""",
            when_to_call_120="立即拨打120"
        ),
        "严重过敏": EmergencyGuidance(
            level=EmergencyLevel.A_URGENT,
            description="严重过敏反应可能导致休克",
            symptoms=["皮疹瘙痒", "呼吸困难", "面部肿胀", "血压下降"],
            immediate_actions=["停止接触过敏原", "注射肾上腺素", "拨打120"],
            first_aid="""### 紧急处理
1. **脱离**: 立即停止接触过敏原
2. **体位**: 平卧，抬高下肢
3. **呼吸**: 保持呼吸道通畅
4. **用药**: 如有肾上腺素自动注射器立即使用
5. **呼救**: 立即拨打120""",
            when_to_call_120="立即拨打120"
        ),
        "高烧": EmergencyGuidance(
            level=EmergencyLevel.A_URGENT,
            description="高烧需要及时处理",
            symptoms=["体温>39℃", "可能伴寒战", "可能伴抽搐"],
            immediate_actions=["物理降温", "多喝水", "服用退烧药", "观察病情"],
            first_aid="""### 降温处理
1. **物理**: 温水擦浴，额头冷敷
2. **饮水**: 多喝水或淡盐水
3. **用药**: 服用布洛芬或对乙酰氨基酚
4. **观察**: 观察神志、尿量
5. **就医**: 超过40℃或持续不退立即就医""",
            when_to_call_120="体温>40℃或出现抽搐立即拨打120"
        ),
    }

    def __init__(self, mcp_client=None):
        """
        初始化紧急处理Skill

        Args:
            mcp_client: MCP客户端，用于调用外部急救系统
        """
        self.mcp_client = mcp_client

    async def handle(self, text: str) -> EmergencyResult:
        """
        处理紧急情况

        Args:
            text: 用户输入

        Returns:
            EmergencyResult: 处理结果
        """
        # 检测紧急级别
        detected_level = self._detect_emergency_level(text)

        if not detected_level:
            return EmergencyResult(detected=False)

        # 识别具体紧急情况
        guidance = self._identify_emergency(text, detected_level)

        # 生成响应内容
        content = self._format_emergency_response(detected_level, guidance)

        return EmergencyResult(
            detected=True,
            level=detected_level,
            content=content,
            guidance=guidance
        )

    def _detect_emergency_level(self, text: str) -> Optional[EmergencyLevel]:
        """检测紧急级别"""
        # 按优先级检查（E -> A -> B）
        for level in [EmergencyLevel.E_CRITICAL, EmergencyLevel.A_URGENT, EmergencyLevel.B_SOON]:
            patterns = self.EMERGENCY_PATTERNS[level]["patterns"]
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return level
        return None

    def _identify_emergency(
        self,
        text: str,
        level: EmergencyLevel
    ) -> Optional[EmergencyGuidance]:
        """识别具体紧急情况"""
        for key, guidance in self.FIRST_AID_GUIDANCE.items():
            if key in text:
                return guidance

        # 如果没有匹配到具体指导，创建通用指导
        pattern_info = self.EMERGENCY_PATTERNS.get(level)
        if pattern_info:
            return EmergencyGuidance(
                level=level,
                description=pattern_info["description"],
                symptoms=[],
                immediate_actions=["保持镇静", "评估情况", "必要时拨打120"],
                first_aid="请根据具体情况采取相应措施",
                when_to_call_120=pattern_info["call_120"]
            )
        return None

    def _format_emergency_response(
        self,
        level: EmergencyLevel,
        guidance: Optional[EmergencyGuidance]
    ) -> str:
        """格式化紧急响应"""
        level_config = {
            EmergencyLevel.E_CRITICAL: {
                "emoji": "🚨",
                "title": "危急情况",
                "call_120": "立即拨打120"
            },
            EmergencyLevel.A_URGENT: {
                "emoji": "⚠️",
                "title": "紧急情况",
                "call_120": "立即急诊"
            },
            EmergencyLevel.B_SOON: {
                "emoji": "⚡",
                "title": "较急情况",
                "call_120": "尽快就医"
            },
        }

        config = level_config.get(level, level_config[EmergencyLevel.B_SOON])

        content = f"""{config['emoji']} **{config['title']}检测**

"""

        if guidance:
            content += f"**情况描述**: {guidance.description}\n\n"

            if guidance.symptoms:
                content += "**典型症状**:\n"
                for symptom in guidance.symptoms:
                    content += f"- {symptom}\n"
                content += "\n"

            content += f"""### 📞 立即行动

1. **拨打120**: {guidance.when_to_call_120}
2. **保持镇静**: 不要慌张，冷静处理
3. **说明情况**: 告知地址、患者情况、联系方式
4. **准备信息**: 准备好患者基本信息、病史、用药史
5. **提前准备**: 楼下等待，引导救护车

---

### 🆘 急救指导

{guidance.first_aid}

---

### ⏱️ 持续施救

**在等待救护车期间，请持续进行急救措施，直到急救人员到达。**

---

### 📍 准备以下信息

- 患者姓名、年龄、性别
- 主要症状和持续时间
- 既往病史（高血压、糖尿病、心脏病等）
- 正在服用的药物
- 是否有药物过敏史

---

> 🏥 **重要**: 本指导仅供紧急情况参考，不能替代专业医疗救治。在确保安全的前提下，尽快寻求专业医疗帮助。
"""
        else:
            content += f"{config['emoji']} 检测到{config['title']}，{config['call_120']}。\n\n"
            content += "> 如情况紧急，请立即拨打120或前往最近医院急诊。"

        return content


# 便捷函数
async def handle_emergency(text: str, mcp_client=None) -> str:
    """
    处理紧急情况（便捷函数）

    Args:
        text: 用户输入
        mcp_client: MCP客户端

    Returns:
        str: 格式化的紧急响应
    """
    skill = EmergencyHandlerSkill(mcp_client)
    result = await skill.handle(text)
    return result.content


if __name__ == "__main__":
    # 测试用例
    async def test():
        skill = EmergencyHandlerSkill()

        # 测试危急情况
        test_cases = [
            "我妈突然昏迷了，叫不醒",
            "我胸痛很厉害，呼吸困难",
            "孩子高烧40度，还在抽搐",
            "头痛好几天了，一直不好"
        ]

        for text in test_cases:
            print(f"\n输入: {text}")
            result = await skill.handle(text)
            print(result[:200] + "...")

    import asyncio
    asyncio.run(test())
