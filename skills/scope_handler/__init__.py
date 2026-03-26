# -*- coding: utf-8 -*-
"""
边界处理Skill
识别并处理非医疗场景，礼貌拒绝并引导至医疗相关话题
"""

import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class ScopeResult:
    """边界检测结果"""
    is_out_of_scope: bool
    detected_topic: Optional[str] = None
    response: str = ""
    suggestions: List[str] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class ScopeHandlerSkill:
    """
    边界处理Skill
    识别并处理非医疗场景，礼貌拒绝并引导至医疗相关话题
    """

    # 非医疗场景识别规则
    OUT_OF_SCOPE_PATTERNS = {
        "天气": {
            "patterns": [
                r"(天气|气温|下雨|下雪|刮风|台风|暴雨|大雪|高温)",
                r"(今天|明天|后天).{0,5}(天气|气温)"
            ],
            "response": "我专注于医疗健康领域，无法查询天气信息。",
            "suggestions": [
                "我可以帮您了解健康知识",
                "请问有什么健康问题想咨询吗？"
            ]
        },
        "财经": {
            "patterns": [
                r"(股票|基金|汇率|理财|投资|炒股|股价)",
                r"(涨|跌).{0,10}(股票|基金)",
                r"(上证|深证|创业板|A股|港股|美股)"
            ],
            "response": "我不提供财经资讯和投资建议。",
            "suggestions": [
                "健康是最大的财富，有什么健康问题可以帮您？",
                "请问您有什么健康方面的疑问吗？"
            ]
        },
        "新闻": {
            "patterns": [
                r"(新闻|热点|时事|资讯|头条|八卦)",
                r"(今天|最近).{0,10}(新闻|热点)"
            ],
            "response": "我不是新闻资讯助手，无法提供新闻信息。",
            "suggestions": [
                "我可以为您提供健康资讯和医疗知识",
                "请问您想了解哪些健康知识？"
            ]
        },
        "娱乐": {
            "patterns": [
                r"(电影|电视剧|综艺|娱乐|明星|偶像|粉丝|追星)",
                r"(看|听).{0,10}(电影|电视|综艺|歌)"
            ],
            "response": "我对娱乐信息不太了解。",
            "suggestions": [
                "健康生活也需要娱乐，我可以建议一些健康的生活方式",
                "请问您有什么健康问题需要咨询吗？"
            ]
        },
        "技术": {
            "patterns": [
                r"(电脑|手机|软件|网络|编程|代码|程序|bug)",
                r"(修|修理).{0,10}(电脑|手机|网络)"
            ],
            "response": "我无法提供技术支持和电子产品维修建议。",
            "suggestions": [
                "如果您长时间使用电子产品，我可以提供一些健康用眼建议",
                "请问您有什么健康问题需要咨询吗？"
            ]
        },
        "生活服务": {
            "patterns": [
                r"(快递|外卖|打车|购物|淘宝|京东|拼多多)",
                r"(订|买|订票|购票|预订).{0,10}(票|酒店|餐厅)"
            ],
            "response": "我不提供生活服务。",
            "suggestions": [
                "我可以帮您了解健康知识和就医指南",
                "请问您有什么健康方面的需求？"
            ]
        },
        "法律": {
            "patterns": [
                r"(律师|法律|诉讼|打官司|起诉|合同|纠纷)",
                r"(违法|犯罪|判刑|坐牢)"
            ],
            "response": "我不提供法律咨询服务。",
            "suggestions": [
                "保持健康心态很重要，我可以提供一些心理健康建议",
                "请问您有什么健康问题需要咨询吗？"
            ]
        },
        "教育": {
            "patterns": [
                r"(考试|升学|分数|成绩|作业|补习|辅导)",
                r"(学|教).{0,10}(数学|语文|英语|物理|化学)"
            ],
            "response": "我不提供教育辅导服务。",
            "suggestions": [
                "良好的身体是学习的基础，我可以提供一些健康建议",
                "请问您有什么健康问题需要咨询吗？"
            ]
        },
        "情感": {
            "patterns": [
                r"(分手|恋爱|相亲|结婚|离婚|出轨)",
                r"(前任|现任|男朋友|女朋友|老公|老婆)"
            ],
            "response": "情感问题不是我的专业领域。",
            "suggestions": [
                "心理健康也很重要，我可以提供一些保持心理健康的建议",
                "请问您有什么健康问题需要咨询吗？"
            ]
        },
    }

    # 医疗相关关键词（用于确认是否真的是医疗场景）
    MEDICAL_KEYWORDS = [
        "症状", "治疗", "药物", "医生", "医院", "科室", "挂号",
        "疼痛", "发烧", "感冒", "咳嗽", "头痛", "腹痛", "胸痛",
        "血压", "血糖", "血脂", "尿酸", "胆固醇",
        "高血压", "糖尿病", "心脏病", "感冒", "发烧",
        "体检", "检查", "化验", "报告", "诊断",
        "手术", "住院", "门诊", "急诊", "救护车",
        "用药", "吃药", "药品", "副作用", "过敏"
    ]

    def __init__(self, mcp_client=None):
        """
        初始化边界处理Skill

        Args:
            mcp_client: MCP客户端
        """
        self.mcp_client = mcp_client

    async def handle(self, text: str) -> ScopeResult:
        """
        处理边界情况

        Args:
            text: 用户输入

        Returns:
            ScopeResult: 处理结果
        """
        # 首先检查是否包含医疗关键词
        has_medical_keyword = any(
            keyword in text for keyword in self.MEDICAL_KEYWORDS
        )

        # 如果有医疗关键词，可能是在医疗场景内
        if has_medical_keyword:
            return ScopeResult(
                is_out_of_scope=False,
                response=""
            )

        # 检查非医疗场景
        for topic, config in self.OUT_OF_SCOPE_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, text, re.IGNORECASE):
                    return ScopeResult(
                        is_out_of_scope=True,
                        detected_topic=topic,
                        response=self._format_refusal_response(topic, config),
                        suggestions=config["suggestions"]
                    )

        # 未明确识别场景
        return ScopeResult(
            is_out_of_scope=False,
            response=""
        )

    def _format_refusal_response(self, topic: str, config: Dict) -> str:
        """格式化拒绝响应"""
        response = f"""## 🤔 抱歉

{config['response']}

---

### 💡 我的专长

我是医疗健康助手，可以帮您：

- 🩺 **症状咨询** - 告诉我您的不适，我帮您分析
- 🏥 **科室推荐** - 不确定挂什么科，我来推荐
- 💊 **用药咨询** - 了解药品用法、副作用等
- 📅 **预约挂号** - 帮您预约医生
- 📚 **健康知识** - 疾病预防、健康生活方式

"""
        if config.get("suggestions"):
            response += "\n".join(f"- {suggestion}" for suggestion in config["suggestions"])

        response += "\n\n---\n\n"
        response += "> 💡 请告诉我您有什么健康问题，我会尽力帮助您。"

        return response

    def get_medical_capabilities(self) -> str:
        """获取医疗能力说明"""
        return """## 🏥 我的医疗健康服务

我可以为您提供以下帮助：

### 🩺 咨询服务
- **症状分析**: 描述您的症状，我帮您分析可能的原因
- **科室推荐**: 告诉我症状，我推荐合适的科室
- **用药咨询**: 了解药品的用法、副作用和注意事项
- **健康知识**: 疾病预防、饮食禁忌、运动建议

### 🏥 医疗服务
- **预约挂号**: 帮您预约医院门诊
- **在线问诊**: 连接医生进行图文/视频问诊
- **体检服务**: 推荐合适的体检套餐
- **报告解读**: 帮您解读检查报告

### 📊 慢病管理
- **慢病记录**: 记录血压、血糖等监测数据
- **慢病咨询**: 高血压、糖尿病等慢病管理建议
- **随访服务**: 术后随访、慢病随访计划
- **健康提醒**: 用药提醒、复诊提醒

### 🆘 紧急处理
- **紧急识别**: 识别紧急医疗情况
- **急救指导**: 提供急救操作指导
- **120拨打**: 引导拨打急救电话

---

请问您有什么健康问题需要咨询？
"""


# 便捷函数
async def handle_scope(text: str, mcp_client=None) -> Optional[str]:
    """
    处理边界情况（便捷函数）

    Args:
        text: 用户输入
        mcp_client: MCP客户端

    Returns:
        Optional[str]: 如果是边界情况返回拒绝响应，否则返回None
    """
    skill = ScopeHandlerSkill(mcp_client)
    result = await skill.handle(text)
    return result.response if result.is_out_of_scope else None


if __name__ == "__main__":
    # 测试用例
    async def test():
        skill = ScopeHandlerSkill()

        # 测试边界情况
        test_cases = [
            ("今天天气怎么样", "天气"),
            ("股票涨了还是跌了", "财经"),
            ("最近有什么新闻", "新闻"),
            ("我想看电影", "娱乐"),
            ("电脑坏了怎么办", "技术"),
            ("我头痛怎么办", None),  # 医疗场景
        ]

        for text, expected_topic in test_cases:
            print(f"\n输入: {text}")
            result = await skill.handle(text)
            if result.is_out_of_scope:
                print(f"检测到非医疗场景: {result.detected_topic}")
                print(result.response[:150] + "...")
            else:
                print("医疗场景，正常处理")

    import asyncio
    asyncio.run(test())
