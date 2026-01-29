# -*- coding: utf-8 -*-
"""
医疗智能助手 - 紧急症状检测器
检测用户输入中的紧急医疗症状
"""

import re
import json
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class EmergencyLevel(Enum):
    """紧急程度级别"""
    CRITICAL = "critical"    # 需要立即就医/拨打120
    URGENT = "urgent"        # 当天就医
    ATTENTION = "attention"  # 需要关注监测


@dataclass
class EmergencyAction:
    """紧急处理建议"""
    action: str           # 建议行动
    urgency: str          # 紧急程度: immediate, same_day, monitor
    description: str      # 详细说明


@dataclass
class EmergencyResult:
    """紧急检测结果"""
    detected: bool                        # 是否检测到紧急情况
    level: Optional[EmergencyLevel]       # 紧急级别
    matched_patterns: List[str]           # 匹配到的模式
    description: str                      # 描述
    suggested_action: EmergencyAction     # 建议行动
    symptoms: List[str]                   # 相关症状


class EmergencyDetector:
    """
    紧急症状检测器
    通过模式匹配检测用户输入中的紧急医疗症状
    """

    # 内置紧急模式（如果外部文件不可用时使用）
    DEFAULT_PATTERNS = {
        EmergencyLevel.CRITICAL: [
            r"(胸痛|心悸).+(呼吸困难|大汗|放射)",
            r"(意识|昏迷|晕厥|抽搐|癫痫)",
            r"呕血|便血|咳血|大出血",
            r"呼吸.{0,5}困难|呼吸.{0,5}急促|喘.{0,3}不",
            r"((剧烈|突发).{0,3}|雷击.{0,2})头痛|剧烈突发头痛",
            r"板状.{0,2}腹|腹痛.{0,3}(冷汗|板状)|剧烈突发.{0,3}腹痛",
            r"窒息|气管.{0,3}堵塞|气道.{0,3}梗阻",
        ],
        EmergencyLevel.URGENT: [
            r"(高烧|发热|体温).{0,3}(39度|39℃|39C|三天|3天)",
            r"(持续|严重|频繁).{0,3}(呕吐|腹泻)",
            r"剧烈.{0,3}腹痛|腹痛.{0,3}(剧烈|严重)",
            r"(外伤).{0,3}(出血|骨折|脱臼|受伤)",
            r"心悸.{0,3}胸闷|心跳.{0,3}快|心律.{0,3}不齐",
            r"(烧|烫)伤",
        ],
        EmergencyLevel.ATTENTION: [
            r"头痛.{0,10}(几天|一周|持续|反复)",
            r"头晕.{0,10}(几天|一周|持续|反复)",
            r"(体重|体形).{0,3}下降|消瘦",
            r"盗汗|低热|下午.{0,2}热",
            r"食欲.{0,3}不振|乏力.{0,3}明显",
        ]
    }

    # 紧急行动建议
    ACTIONS = {
        EmergencyLevel.CRITICAL: EmergencyAction(
            action="call_120",
            urgency="immediate",
            description="请立即停止活动，保持镇静，立即拨打120急救电话"
        ),
        EmergencyLevel.URGENT: EmergencyAction(
            action="visit_today",
            urgency="same_day",
            description="请于今天内前往医院就诊，不要延误"
        ),
        EmergencyLevel.ATTENTION: EmergencyAction(
            action="monitor",
            urgency="monitor",
            description="建议您尽快就医检查，同时密切观察症状变化"
        ),
    }

    def __init__(self, knowledge_base_path: Optional[str] = None):
        """
        初始化紧急检测器

        Args:
            knowledge_base_path: 外部知识库路径
        """
        self.patterns = dict(self.DEFAULT_PATTERNS)
        self.descriptions = {}
        self.knowledge_base_path = knowledge_base_path

        # 尝试从外部知识库加载
        if knowledge_base_path:
            self._load_from_knowledge_base()

        # 编译正则表达式
        self._compiled_patterns = self._compile_patterns()

    def _load_from_knowledge_base(self):
        """从外部知识库加载紧急模式"""
        try:
            kb_path = Path(self.knowledge_base_path)
            if not kb_path.exists():
                return

            with open(kb_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            emergency_patterns = data.get('emergency_patterns', {})

            # 转换外部格式
            for level_str, patterns_list in emergency_patterns.items():
                level = EmergencyLevel(level_str)
                extracted_patterns = []
                self.descriptions[level] = []

                for item in patterns_list:
                    pattern_list = item.get('patterns', [])
                    extracted_patterns.extend(pattern_list)
                    self.descriptions[level].append({
                        'patterns': pattern_list,
                        'description': item.get('description', ''),
                        'action': item.get('action', ''),
                    })

                self.patterns[level] = extracted_patterns

        except Exception as e:
            import warnings
            warnings.warn(f"Failed to load emergency patterns from knowledge base: {e}")

    def _compile_patterns(self) -> Dict[EmergencyLevel, List[re.Pattern]]:
        """编译正则表达式模式"""
        compiled = {}
        for level, patterns in self.patterns.items():
            compiled[level] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled

    def detect(self, text: str) -> Optional[EmergencyResult]:
        """
        检测文本中的紧急症状

        Args:
            text: 用户输入文本

        Returns:
            EmergencyResult: 检测结果，如果没有检测到紧急情况则返回None
        """
        if not text:
            return None

        # 按优先级检测（critical -> urgent -> attention）
        for level in [EmergencyLevel.CRITICAL, EmergencyLevel.URGENT, EmergencyLevel.ATTENTION]:
            patterns = self._compiled_patterns.get(level, [])
            matched = []

            for pattern in patterns:
                if pattern.search(text):
                    matched.append(pattern.pattern)

            if matched:
                # 获取描述和建议
                description = self._get_description(level, matched)
                action = self._get_action(level, matched)

                # 提取症状关键词
                symptoms = self._extract_symptoms(text, matched)

                return EmergencyResult(
                    detected=True,
                    level=level,
                    matched_patterns=matched,
                    description=description,
                    suggested_action=action,
                    symptoms=symptoms
                )

        return None

    def _get_description(self, level: EmergencyLevel, patterns: List[str]) -> str:
        """获取紧急情况描述"""
        level_descriptions = {
            EmergencyLevel.CRITICAL: "检测到需要立即处理的紧急情况！",
            EmergencyLevel.URGENT: "检测到需要当天就医的情况！",
            EmergencyLevel.ATTENTION: "检测到需要关注的健康问题！",
        }

        base = level_descriptions.get(level, "检测到潜在健康问题")

        # 尝试从知识库获取更详细的描述
        if level in self.descriptions:
            for desc_item in self.descriptions[level]:
                for pattern in desc_item['patterns']:
                    if any(pattern in p for p in patterns):
                        return desc_item['description']

        return base

    def _get_action(self, level: EmergencyLevel, patterns: List[str]) -> EmergencyAction:
        """获取建议行动"""
        # 从知识库获取具体建议
        if level in self.descriptions:
            for desc_item in self.descriptions[level]:
                for pattern in desc_item['patterns']:
                    if any(pattern in p for p in patterns):
                        return EmergencyAction(
                            action="follow_advice",
                            urgency=desc_item.get('action', '').split()[0] if desc_item.get('action') else 'monitor',
                            description=desc_item.get('action', self.ACTIONS[level].description)
                        )

        # 使用默认建议
        return self.ACTIONS[level]

    def _extract_symptoms(self, text: str, patterns: List[str]) -> List[str]:
        """从文本和模式中提取症状关键词"""
        symptoms = []

        # 常见症状词
        symptom_keywords = [
            "胸痛", "头痛", "腹痛", "呼吸困难", "昏迷", "晕厥",
            "抽搐", "呕血", "便血", "咳血", "高烧", "发热",
            "呕吐", "腹泻", "心悸", "外伤", "骨折", "出血"
        ]

        for keyword in symptom_keywords:
            if keyword in text:
                symptoms.append(keyword)

        # 如果没有匹配到关键词，从模式中提取
        if not symptoms:
            for pattern in patterns:
                # 简单提取中文词
                chinese_words = re.findall(r'[\u4e00-\u9fff]+', pattern)
                symptoms.extend(chinese_words[:3])  # 限制数量

        return list(set(symptoms))[:5]  # 去重并限制数量

    def detect_multiple(self, texts: List[str]) -> List[EmergencyResult]:
        """
        批量检测多个文本

        Args:
            texts: 文本列表

        Returns:
            List[EmergencyResult]: 检测结果列表
        """
        results = []
        for text in texts:
            result = self.detect(text)
            if result:
                results.append(result)
        return results

    def get_level_from_text(self, text: str) -> Optional[EmergencyLevel]:
        """
        快速获取文本的紧急级别

        Args:
            text: 输入文本

        Returns:
            Optional[EmergencyLevel]: 紧急级别，如果不是紧急情况则返回None
        """
        result = self.detect(text)
        return result.level if result else None

    def format_emergency_message(self, result: EmergencyResult) -> str:
        """
        格式化紧急情况的用户消息

        Args:
            result: 检测结果

        Returns:
            str: 格式化的消息
        """
        level_emoji = {
            EmergencyLevel.CRITICAL: "🚨",
            EmergencyLevel.URGENT: "⚠️",
            EmergencyLevel.ATTENTION: "ℹ️"
        }

        emoji = level_emoji.get(result.level, "⚠️")

        message = f"{emoji} **紧急提醒**\n\n"
        message += f"**描述**: {result.description}\n\n"

        if result.symptoms:
            message += f"**检测到的症状**: {', '.join(result.symptoms)}\n\n"

        message += f"**建议行动**: {result.suggested_action.description}\n\n"

        # 根据级别添加额外提示
        if result.level == EmergencyLevel.CRITICAL:
            message += "\n---\n\n"
            message += "> 📞 **请立即拨打 120 急救电话**\n"
            message += "> 📍 请告知您的具体位置和患者情况\n"
            message += "> ⏱️ 在救护车到达前，请保持患者平静，避免移动"

        elif result.level == EmergencyLevel.URGENT:
            message += "\n---\n\n"
            message += "> 🏥 请尽快前往最近的医院急诊科就诊\n"
            message += "> 👨‍⚕️ 如情况加重，请立即拨打120"

        elif result.level == EmergencyLevel.ATTENTION:
            message += "\n---\n\n"
            message += "> 📅 建议预约医生进行详细检查\n"
            message += "> 👀 请密切观察症状变化，如有加重请及时就医"

        return message

    def reload_patterns(self, knowledge_base_path: Optional[str] = None):
        """
        重新加载紧急模式

        Args:
            knowledge_base_path: 新的知识库路径，如果为None则使用原路径
        """
        if knowledge_base_path:
            self.knowledge_base_path = knowledge_base_path

        self.patterns = dict(self.DEFAULT_PATTERNS)
        self.descriptions = {}

        if self.knowledge_base_path:
            self._load_from_knowledge_base()

        self._compiled_patterns = self._compile_patterns()


# ============================================================
# 便捷函数
# ============================================================

def detect_emergency(text: str, knowledge_base_path: Optional[str] = None) -> Optional[EmergencyResult]:
    """
    检测文本中的紧急症状

    Args:
        text: 用户输入文本
        knowledge_base_path: 知识库路径

    Returns:
        Optional[EmergencyResult]: 检测结果
    """
    detector = EmergencyDetector(knowledge_base_path)
    return detector.detect(text)


def is_emergency(text: str, level: EmergencyLevel = EmergencyLevel.URGENT) -> bool:
    """
    判断文本是否包含指定级别或更高级别的紧急情况

    Args:
        text: 输入文本
        level: 比较级别，默认为URGENT

    Returns:
        bool: 是否为紧急情况
    """
    detector = EmergencyDetector()
    result = detector.detect(text)

    if not result:
        return False

    # 级别比较
    level_order = {
        EmergencyLevel.CRITICAL: 3,
        EmergencyLevel.URGENT: 2,
        EmergencyLevel.ATTENTION: 1
    }

    return level_order.get(result.level, 0) >= level_order.get(level, 0)


# ============================================================
# 测试代码
# ============================================================

if __name__ == "__main__":
    # 测试紧急检测
    test_cases = [
        "我胸痛，呼吸困难，出大汗",
        "我妈突然晕倒了",
        "我头痛好几天了，一直不好",
        "我发高烧39度5了",
        "最近体重下降了很多，很担心",
        "我肚子有点痛，不太严重",
    ]

    detector = EmergencyDetector()

    print("=" * 60)
    print("紧急症状检测测试")
    print("=" * 60)

    for text in test_cases:
        print(f"\n输入: {text}")
        result = detector.detect(text)

        if result:
            print(f"  -> 检测到紧急情况! 级别: {result.level.value}")
            print(f"  -> 描述: {result.description}")
            print(f"  -> 症状: {result.symptoms}")
            print("\n" + detector.format_emergency_message(result))
        else:
            print("  -> 未检测到紧急情况")
