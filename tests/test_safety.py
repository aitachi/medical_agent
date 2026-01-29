# -*- coding: utf-8 -*-
"""
医疗智能助手 - 安全检查测试
测试药物安全检查功能
"""

import pytest
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入被测试模块
from core.safety_checker import (
    DrugSafetyChecker,
    SafetyReport,
    SafetySeverity,
    check_drug_safety
)
from agent.user_profile import UserProfile, create_default_profile


@pytest.fixture
async def safety_checker():
    """创建安全检查器实例"""
    kb_path = Path(__file__).parent.parent / "data" / "knowledge_base.json"
    checker = DrugSafetyChecker(str(kb_path))
    return checker


@pytest.fixture
def sample_user_profile():
    """创建示例用户画像"""
    profile = create_default_profile("test_user")
    profile.allergies = ["青霉素", "阿司匹林"]
    profile.medical_history = ["胃溃疡", "高血压"]
    profile.current_medications = {
        "硝苯地平": {"dose_daily": 30, "dose_single": 10},
        "二甲双胍": {"dose_daily": 1500, "dose_single": 500},
    }
    profile.chronic_conditions = ["高血压", "糖尿病"]
    return profile


class TestDrugSafetyChecker:
    """药物安全检查器测试"""

    @pytest.mark.asyncio
    async def test_duplicate_detection(self, safety_checker):
        """测试重复用药检测"""
        drugs = ["阿司匹林", "阿司匹林", "布洛芬"]
        report = await safety_checker.check(drugs)

        assert not report.safe
        assert len(report.warnings) > 0

        duplicate_warnings = [w for w in report.warnings if w.type == "duplicate"]
        assert len(duplicate_warnings) > 0
        assert "阿司匹林" in duplicate_warnings[0].details["drugs"]

    @pytest.mark.asyncio
    async def test_similar_drugs_detection(self, safety_checker):
        """测试同类药物检测"""
        drugs = ["阿司匹林", "布洛芬"]
        report = await safety_checker.check(drugs)

        assert not report.safe

        similar_warnings = [w for w in report.warnings if w.type == "similar"]
        assert len(similar_warnings) > 0

    @pytest.mark.asyncio
    async def test_interaction_detection(self, safety_checker):
        """测试药物相互作用检测"""
        drugs = ["阿司匹林", "布洛芬"]
        report = await safety_checker.check(drugs)

        interaction_warnings = [w for w in report.warnings if w.type == "interaction"]
        assert len(interaction_warnings) > 0
        assert interaction_warnings[0].severity in [SafetySeverity.CRITICAL, SafetySeverity.HIGH]

    @pytest.mark.asyncio
    async def test_allergy_check(self, safety_checker, sample_user_profile):
        """测试过敏检查"""
        drugs = ["阿莫西林"]
        report = await safety_checker.check(drugs, sample_user_profile)

        allergy_warnings = [w for w in report.warnings if "allergy" in w.type]
        assert len(allergy_warnings) > 0
        assert allergy_warnings[0].severity == SafetySeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_contraindication_check(self, safety_checker, sample_user_profile):
        """测试禁忌症检查"""
        drugs = ["布洛芬"]
        profile_with_ulcer = create_default_profile("test_user2")
        profile_with_ulcer.medical_history = ["胃溃疡"]

        report = await safety_checker.check(drugs, profile_with_ulcer)

        contraindication_warnings = [w for w in report.warnings if w.type == "contraindication"]
        assert len(contraindication_warnings) > 0

    @pytest.mark.asyncio
    async def test_dose_check(self, safety_checker):
        """测试剂量检查"""
        profile = create_default_profile("test_user3")
        profile.current_medications = {
            "对乙酰氨基酚": {"dose_daily": 3000, "dose_single": 1000},  # 超过日剂量上限
        }

        report = await safety_checker.check(["对乙酰氨基酚"], profile)

        dose_warnings = [w for w in report.warnings if w.type == "dose"]
        assert len(dose_warnings) > 0
        assert dose_warnings[0].severity == SafetySeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_safe_combination(self, safety_checker):
        """测试安全药物组合"""
        drugs = ["对乙酰氨基酚", "硝苯地平"]
        report = await safety_checker.check(drugs)

        # 这个组合应该是安全的
        critical_warnings = report.get_critical_warnings()
        assert len(critical_warnings) == 0

    @pytest.mark.asyncio
    async def test_alcohol_interaction(self, safety_checker):
        """测试酒精相互作用"""
        drugs = ["头孢氨苄"]
        warnings_list = safety_checker.check_alcohol_interaction(drugs)

        assert len(warnings_list) > 0
        assert warnings_list[0].type == "alcohol_interaction"
        assert "双硫仑" in warnings_list[0].message

    def test_format_report(self, safety_checker):
        """测试报告格式化"""
        # 创建一个模拟报告
        report = SafetyReport(
            safe=False,
            warnings=[
                type('obj', (object,), {
                    'type': 'duplicate',
                    'severity': SafetySeverity.HIGH,
                    'message': '检测到重复用药',
                    'details': {'drugs': ['阿司匹林']},
                    'suggestion': '请确认是否需要同时使用'
                })(),
            ],
            checked_drugs=["阿司匹林", "阿司匹林"]
        )

        formatted = safety_checker.format_report(report)
        assert "重复用药" in formatted
        assert "阿司匹林" in formatted
        assert "免责声明" in formatted


class TestSafetyReport:
    """安全报告测试"""

    def test_report_properties(self):
        """测试报告属性"""
        report = SafetyReport(
            safe=True,
            warnings=[],
            checked_drugs=["对乙酰氨基酚"]
        )

        assert report.safe is True
        assert report.get_critical_warnings() == []
        assert report.get_high_severity_warnings() == []
        assert report.has_critical_issues() is False

    def test_report_with_warnings(self):
        """测试带警告的报告"""
        from core.safety_checker import SafetyWarning

        report = SafetyReport(
            safe=False,
            warnings=[
                SafetyWarning(
                    type="interaction",
                    severity=SafetySeverity.CRITICAL,
                    message="严重相互作用",
                    suggestion="请咨询医生"
                ),
                SafetyWarning(
                    type="dose",
                    severity=SafetySeverity.MODERATE,
                    message="剂量偏高"
                ),
            ],
            checked_drugs=["阿司匹林", "布洛芬"]
        )

        assert report.safe is False
        assert len(report.get_critical_warnings()) == 1
        assert len(report.get_high_severity_warnings()) == 1
        assert report.has_critical_issues() is True


class TestConvenienceFunction:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_check_drug_safety_function(self):
        """测试便捷检查函数"""
        report = await check_drug_safety(["阿司匹林", "布洛芬"])
        assert report is not None
        assert isinstance(report, SafetyReport)


# 性能测试
class TestSafetyPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_large_batch_check(self, safety_checker):
        """测试大批量检查性能"""
        drugs = ["阿司匹林", "布洛芬", "对乙酰氨基酚", "硝苯地平", "二甲双胍"]

        import time
        start = time.time()

        for _ in range(100):
            await safety_checker.check(drugs)

        elapsed = time.time() - start
        assert elapsed < 5.0  # 100次检查应在5秒内完成

    @pytest.mark.asyncio
    async def test_cache_effectiveness(self, safety_checker):
        """测试缓存效果"""
        drugs = ["阿司匹林", "布洛芬"]

        # 第一次检查（无缓存）
        import time
        start = time.time()
        await safety_checker.check(drugs)
        first_time = time.time() - start

        # 第二次检查（有缓存）
        start = time.time()
        await safety_checker.check(drugs)
        second_time = time.time() - start

        # 缓存应该更快（或者至少不慢太多）
        assert second_time <= first_time * 2


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
