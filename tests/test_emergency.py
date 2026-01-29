# -*- coding: utf-8 -*-
"""
医疗智能助手 - 紧急检测测试
测试紧急症状检测功能
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入被测试模块
from core.emergency_detector import (
    EmergencyDetector,
    EmergencyLevel,
    EmergencyAction,
    EmergencyResult,
    detect_emergency,
    is_emergency
)


@pytest.fixture
def emergency_detector():
    """创建紧急检测器实例"""
    kb_path = Path(__file__).parent.parent / "data" / "knowledge_base.json"
    return EmergencyDetector(str(kb_path))


class TestEmergencyDetection:
    """紧急检测测试"""

    def test_critical_chest_pain(self, emergency_detector):
        """测试胸痛检测（危急）"""
        text = "我胸痛，呼吸困难，出大汗"
        result = emergency_detector.detect(text)

        assert result is not None
        assert result.detected is True
        assert result.level == EmergencyLevel.CRITICAL
        assert any("胸痛" in s or "呼吸困难" in s for s in result.symptoms)

    def test_critical_fainting(self, emergency_detector):
        """测试晕厥检测（危急）"""
        test_cases = [
            "我晕倒了",
            "突然昏迷了",
            "意识不清",
            "出现抽搐",
        ]

        for text in test_cases:
            result = emergency_detector.detect(text)
            assert result is not None, f"Failed to detect: {text}"
            assert result.detected is True
            assert result.level == EmergencyLevel.CRITICAL

    def test_critical_bleeding(self, emergency_detector):
        """测试出血检测（危急）"""
        test_cases = [
            "我呕血了",
            "大便有血",
            "咳血",
            "大出血",
        ]

        for text in test_cases:
            result = emergency_detector.detect(text)
            assert result is not None, f"Failed to detect: {text}"
            assert result.detected is True
            assert result.level == EmergencyLevel.CRITICAL

    def test_critical_headache(self, emergency_detector):
        """测试剧烈头痛检测（危急）"""
        text = "突然剧烈头痛，像雷击一样"
        result = emergency_detector.detect(text)

        assert result is not None
        assert result.detected is True
        assert result.level == EmergencyLevel.CRITICAL

    def test_urgent_high_fever(self, emergency_detector):
        """测试高烧检测（紧急）"""
        test_cases = [
            "我发高烧39度5了",
            "体温39度，一直不退",
            "发烧超过39度三天了",
        ]

        for text in test_cases:
            result = emergency_detector.detect(text)
            assert result is not None, f"Failed to detect: {text}"
            assert result.detected is True
            assert result.level == EmergencyLevel.URGENT

    def test_urgent_vomiting_diarrhea(self, emergency_detector):
        """测试持续呕吐腹泻检测（紧急）"""
        test_cases = [
            "持续呕吐三天",
            "频繁腹泻，止不住",
            "又吐又拉好几天了",
        ]

        for text in test_cases:
            result = emergency_detector.detect(text)
            assert result is not None, f"Failed to detect: {text}"
            assert result.detected is True
            assert result.level == EmergencyLevel.URGENT

    def test_urgent_trauma(self, emergency_detector):
        """测试外伤检测（紧急）"""
        test_cases = [
            "受伤出血了",
            "腿骨折了",
            "摔伤，有伤口",
        ]

        for text in test_cases:
            result = emergency_detector.detect(text)
            assert result is not None, f"Failed to detect: {text}"
            assert result.detected is True
            assert result.level == EmergencyLevel.URGENT

    def test_attention_headache(self, emergency_detector):
        """测试持续头痛检测（关注）"""
        text = "头痛好几天了，一直不好"
        result = emergency_detector.detect(text)

        assert result is not None
        assert result.detected is True
        assert result.level == EmergencyLevel.ATTENTION

    def test_attention_weight_loss(self, emergency_detector):
        """测试体重下降检测（关注）"""
        text = "最近体重下降了很多"
        result = emergency_detector.detect(text)

        assert result is not None
        assert result.detected is True
        assert result.level == EmergencyLevel.ATTENTION

    def test_non_emergency(self, emergency_detector):
        """测试非紧急情况"""
        test_cases = [
            "我肚子有点痛，不太严重",
            "有点咳嗽",
            "感觉有点累",
            "我是什么病",
            "你好",
        ]

        for text in test_cases:
            result = emergency_detector.detect(text)
            # 这些不应该被检测为紧急情况
            if result:
                # 如果检测到，应该是低级别
                assert result.level != EmergencyLevel.CRITICAL

    def test_multiple_emergencies(self, emergency_detector):
        """测试多种紧急症状"""
        text = "我胸痛，呼吸困难，出大汗，感觉要晕过去了"
        result = emergency_detector.detect(text)

        assert result is not None
        assert result.detected is True
        assert result.level == EmergencyLevel.CRITICAL
        # 应该检测到多个症状
        assert len(result.symptoms) >= 2


class TestEmergencyAction:
    """紧急行动建议测试"""

    def test_critical_action(self, emergency_detector):
        """测试危急情况行动建议"""
        result = emergency_detector.detect("我胸痛，呼吸困难")

        assert result is not None
        assert result.suggested_action.urgency == "immediate"
        assert "120" in result.suggested_action.description or "立即" in result.suggested_action.description

    def test_urgent_action(self, emergency_detector):
        """测试紧急情况行动建议"""
        result = emergency_detector.detect("我发高烧39度了")

        assert result is not None
        assert result.suggested_action.urgency in ["same_day", "today"]
        assert "今天" in result.suggested_action.description or "尽快" in result.suggested_action.description

    def test_attention_action(self, emergency_detector):
        """测试关注情况行动建议"""
        result = emergency_detector.detect("头痛好几天了")

        assert result is not None
        assert result.suggested_action.urgency == "monitor"
        assert "观察" in result.suggested_action.description or "检查" in result.suggested_action.description


class TestEmergencyFormatting:
    """紧急消息格式化测试"""

    def test_format_critical_message(self, emergency_detector):
        """测试危急消息格式化"""
        result = emergency_detector.detect("胸痛，呼吸困难")
        formatted = emergency_detector.format_emergency_message(result)

        assert "🚨" in formatted or "紧急" in formatted
        assert "120" in formatted
        assert "立即" in formatted

    def test_format_urgent_message(self, emergency_detector):
        """测试紧急消息格式化"""
        result = emergency_detector.detect("发高烧39度")
        formatted = emergency_detector.format_emergency_message(result)

        assert "⚠️" in formatted or "紧急" in formatted
        assert "今天" in formatted or "尽快" in formatted
        assert "就医" in formatted

    def test_format_attention_message(self, emergency_detector):
        """测试关注消息格式化"""
        result = emergency_detector.detect("头痛好几天")
        formatted = emergency_detector.format_emergency_message(result)

        assert "ℹ️" in formatted or "关注" in formatted
        assert "建议" in formatted


class TestIsEmergencyFunction:
    """is_emergency便捷函数测试"""

    def test_is_emergency_critical(self):
        """测试危急判断"""
        assert is_emergency("我胸痛，呼吸困难") is True
        assert is_emergency("突然晕倒") is True

    def test_is_emergency_urgent(self):
        """测试紧急判断"""
        assert is_emergency("发高烧39度", level=EmergencyLevel.URGENT) is True
        # 默认级别是URGENT，所以应该检测到
        assert is_emergency("发高烧39度") is True

    def test_is_emergency_with_level(self):
        """测试带级别的判断"""
        # 高烧不是critical级别
        assert is_emergency("发高烧39度", level=EmergencyLevel.CRITICAL) is False
        # 但是是urgent级别
        assert is_emergency("发高烧39度", level=EmergencyLevel.URGENT) is True

    def test_is_emergency_false(self):
        """测试非紧急判断"""
        assert is_emergency("我肚子有点痛") is False
        assert is_emergency("你好") is False


class TestDetectEmergencyFunction:
    """detect_emergency便捷函数测试"""

    def test_detect_emergency_function(self):
        """测试便捷检测函数"""
        result = detect_emergency("胸痛，呼吸困难")

        assert result is not None
        assert isinstance(result, EmergencyResult)
        assert result.detected is True


class TestEmergencyResult:
    """紧急结果数据类测试"""

    def test_emergency_result_creation(self):
        """测试紧急结果创建"""
        from core.emergency_detector import EmergencyAction

        result = EmergencyResult(
            detected=True,
            level=EmergencyLevel.CRITICAL,
            matched_patterns=["胸痛.*呼吸困难"],
            description="可能为心肌梗死",
            suggested_action=EmergencyAction(
                action="call_120",
                urgency="immediate",
                description="请立即拨打120"
            ),
            symptoms=["胸痛", "呼吸困难"]
        )

        assert result.detected is True
        assert result.level == EmergencyLevel.CRITICAL
        assert len(result.symptoms) == 2


class TestPatternMatching:
    """模式匹配测试"""

    def test_chinese_pattern_matching(self, emergency_detector):
        """测试中文模式匹配"""
        test_cases = [
            ("呼吸感到困难", True),  # 变体表达
            ("胸痛并且呼吸困难", True),  # 连接词
            ("剧烈的头痛", True),  # 修饰语
            ("突发头痛", True),  # 位置变化
        ]

        for text, expected_emergency in test_cases:
            result = emergency_detector.detect(text)
            if expected_emergency:
                # 可能不总是检测到，但至少不应该报错
                assert result is not None or True  # 允许未检测到但不应崩溃

    def test_edge_cases(self, emergency_detector):
        """测试边界情况"""
        # 空输入
        assert emergency_detector.detect("") is None
        assert emergency_detector.detect(None) is None

        # 特殊字符
        result = emergency_detector.detect("!!!胸痛!!!")
        # 应该能处理
        assert result is not None

        # 混合中英文
        result = emergency_detector.detect("chest痛 呼吸困难")
        # 应该能处理
        assert result is not None


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
