# -*- coding: utf-8 -*-
"""
帮助处理Skill
提供使用帮助，介绍医疗助手的功能和使用方法
"""

import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class HelpResult:
    """帮助结果"""
    content: str
    examples: List[str]
    quick_actions: List[str]


class HelpHandlerSkill:
    """
    帮助处理Skill
    提供使用帮助，介绍医疗助手的功能和使用方法
    """

    # 帮助内容
    HELP_CONTENT = """## 👋 欢迎使用医疗智能助手

我是您的专业医疗健康助手，可以为您提供全方位的健康服务。

---

## 🎯 我能帮您做什么

### 🩺 症状咨询
描述您的身体不适，我帮您分析可能的原因和注意事项。

**尝试说**:
- "我头痛好几天了"
- "最近一直咳嗽，怎么回事"
- "肚子痛应该挂什么科"

### 🏥 医疗服务
帮您预约挂号、在线问诊、查看预约等。

**尝试说**:
- "我想预约挂号"
- "在线问诊怎么操作"
- "查看我的预约"

### 💊 用药咨询
了解药品的用法用量、副作用、注意事项等。

**尝试说**:
- "阿莫西林怎么吃"
- "降压药有什么副作用"
- "感冒药可以和消炎药一起吃吗"

### 🩹 慢病管理
记录血压血糖、获取慢病管理建议、设置随访计划。

**尝试说**:
- "记录血压130/85"
- "血糖6.5正常吗"
- "高血压需要注意什么"

### 📊 报告解读
上传或描述检查报告，我帮您解读各项指标。

**尝试说**:
- "帮我看看血常规报告"
- "血压偏高是什么意思"
- "血糖7.0严重吗"

### 🏥 体检服务
推荐体检套餐、了解体检注意事项。

**尝试说**:
- "推荐个体检套餐"
- "35岁女性做什么体检"
- "体检前要注意什么"

### 🔔 提醒服务
设置用药提醒、复诊提醒、测量提醒。

**尝试说**:
- "设置每天早上的用药提醒"
- "提醒我明天复查"
- "每天8点提醒我测血压"

### 🆘 紧急处理
识别紧急医疗情况，提供急救指导。

**如遇紧急情况，直接描述症状**:
- "我妈突然昏迷了"
- "胸痛呼吸困难"
- "孩子高烧抽搐"

---

## 💡 使用小贴士

1. **直接描述**: 直接说出您的症状或问题
2. **提供细节**: 尽量提供详细信息，如持续时间、严重程度
3. **上传图片**: 问诊时可上传相关照片
4. **保持对话**: 多轮对话可以帮助我更好地理解您的情况

---

## 📞 联系方式

- 如有系统问题或建议，请联系客服
- 紧急情况请直接拨打120

---

请问您有什么健康问题需要咨询？
"""

    # 功能示例
    FUNCTION_EXAMPLES = {
        "症状咨询": [
            "我头痛好几天了，特别是早上",
            "最近咳嗽有痰，是什么原因",
            "肚子痛应该挂什么科"
        ],
        "用药咨询": [
            "阿莫西林怎么吃",
            "降压药有什么副作用",
            "感冒药能和消炎药一起吃吗"
        ],
        "慢病管理": [
            "记录血压130/85",
            "血糖6.5正常吗",
            "高血压饮食要注意什么"
        ],
        "医疗服务": [
            "我想预约心内科",
            "在线问诊怎么操作",
            "查看我的预约记录"
        ],
        "体检服务": [
            "推荐个体检套餐",
            "30岁男性做什么体检",
            "体检前要注意什么"
        ],
        "报告解读": [
            "帮我看看血常规报告",
            "胆固醇偏高是什么意思",
            "尿常规白细胞阳性怎么办"
        ]
    }

    def __init__(self, mcp_client=None):
        """
        初始化帮助处理Skill

        Args:
            mcp_client: MCP客户端
        """
        self.mcp_client = mcp_client

    async def handle(self, topic: Optional[str] = None) -> HelpResult:
        """
        处理帮助请求

        Args:
            topic: 帮助主题（可选）

        Returns:
            HelpResult: 帮助结果
        """
        if topic:
            content = self._get_topic_help(topic)
        else:
            content = self.HELP_CONTENT

        examples = self._get_examples(topic)
        quick_actions = self._get_quick_actions()

        return HelpResult(
            content=content,
            examples=examples,
            quick_actions=quick_actions
        )

    def _get_topic_help(self, topic: str) -> str:
        """获取特定主题的帮助"""
        topic_help = {
            "症状咨询": """## 🩺 症状咨询

我可以帮您分析症状，给出参考建议。

### 如何使用

直接描述您的症状，例如：
- "我头痛好几天了"
- "最近一直咳嗽，有痰"
- "肚子痛，有点恶心"

### 我会提供

- 可能的原因分析
- 危险信号提醒
- 建议的科室
- 自我护理建议

> ⚠️ 提醒：我的建议仅供参考，不能替代医生诊断。
""",
            "用药咨询": """## 💊 用药咨询

我可以帮您了解药品的相关信息。

### 如何使用

询问药品相关问题，例如：
- "阿莫西林怎么吃"
- "降压药有什么副作用"
- "感冒药能一起吃吗"

### 我会提供

- 药品用法用量
- 可能的副作用
- 禁忌症
- 药物相互作用

> ⚠️ 提醒：请严格遵医嘱用药，不要擅自调整剂量。
""",
            "慢病管理": """## 🩹 慢病管理

我可以帮您管理慢病监测和获取健康建议。

### 如何使用

1. **记录数据**:
   - "记录血压130/85"
   - "空腹血糖6.5"

2. **获取建议**:
   - "高血压需要注意什么"
   - "糖尿病能吃什么"

3. **查看趋势**:
   - "查看最近的血压记录"

### 支持的慢病

- 高血压
- 糖尿病
- 高血脂
- 痛风
""",
            "在线问诊": """## 🏥 在线问诊

我可以帮您连接医生进行在线问诊。

### 问诊类型

1. **图文问诊** - 通过文字和图片沟通，24小时内回复
2. **视频问诊** - 面对面视频沟通，即时回复
3. **电话问诊** - 医生电话回拨

### 如何使用

1. 说"我想在线问诊"
2. 选择问诊类型
3. 描述您的症状
4. 选择医生
5. 支付费用
6. 开始问诊

### 适合场景

- 症状较轻，需要专业建议
- 复诊咨询
- 不方便前往医院
""",
            "体检服务": """## 🏥 体检服务

我可以帮您选择合适的体检套餐。

### 如何使用

- "推荐个体检套餐"
- "35岁女性做什么体检"
- "体检前要注意什么"

### 体检套餐类型

- **基础体检**: 适合年轻健康人群
- **全面体检**: 适合40岁以上或有家族史
- **专项体检**: 心血管、女性、男性等专项
- **高端体检**: 高管人群，全面深度检查

### 体检前注意事项

- 体检前3天清淡饮食
- 体检前1晚20点后禁食
- 体检当日早晨空腹
- 女性避开月经期
"""
        }

        return topic_help.get(topic, self.HELP_CONTENT)

    def _get_examples(self, topic: Optional[str]) -> List[str]:
        """获取示例"""
        if topic and topic in self.FUNCTION_EXAMPLES:
            return self.FUNCTION_EXAMPLES[topic]

        # 所有示例
        all_examples = []
        for examples in self.FUNCTION_EXAMPLES.values():
            all_examples.extend(examples[:2])  # 每类取2个
        return all_examples[:8]

    def _get_quick_actions(self) -> List[str]:
        """获取快捷操作"""
        return [
            "描述症状咨询",
            "预约挂号",
            "在线问诊",
            "用药咨询",
            "记录慢病数据",
            "解读检查报告",
            "设置用药提醒",
            "查看我的预约"
        ]

    def format_help(self, result: HelpResult) -> str:
        """格式化帮助响应"""
        content = result.content

        if result.examples:
            content += "\n\n## 💬 试试这样问\n\n"
            for example in result.examples:
                content += f"- "{example}"\n"

        if result.quick_actions:
            content += "\n\n## ⚡ 快捷操作\n\n"
            for action in result.quick_actions:
                content += f"- {action}\n"

        return content


# 便捷函数
async def get_help(topic: Optional[str] = None, mcp_client=None) -> str:
    """
    获取帮助（便捷函数）

    Args:
        topic: 帮助主题
        mcp_client: MCP客户端

    Returns:
        str: 格式化的帮助内容
    """
    skill = HelpHandlerSkill(mcp_client)
    result = await skill.handle(topic)
    return skill.format_help(result)


if __name__ == "__main__":
    # 测试用例
    async def test():
        skill = HelpHandlerSkill()

        # 测试通用帮助
        result = await skill.handle()
        print(skill.format_help(result))

        print("\n" + "="*60 + "\n")

        # 测试主题帮助
        result2 = await skill.handle("症状咨询")
        print(skill.format_help(result2))

    import asyncio
    asyncio.run(test())
