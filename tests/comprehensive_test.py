# -*- coding: utf-8 -*-
"""
医疗智能Agent综合测试
使用5000条测试数据测试意图识别准确率和全流程功能
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from collections import defaultdict

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.medical_agent import MedicalAgent, IntentType


class ComprehensiveTestRunner:
    """综合测试运行器"""

    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = os.path.join(
                os.path.dirname(__file__),
                "algorithem",
                "test_dataset_5000.json"
            )
        self.data_path = data_path
        self.agent = None
        self.test_data = []
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "data_source": data_path,
            "ml_classifier_status": "unknown",
            "intent_classification": {},
            "functional_tests": {},
            "performance_metrics": {}
        }

    async def setup(self):
        """初始化"""
        print("=" * 70)
        print("医疗智能Agent综合测试")
        print("=" * 70)
        print(f"数据源: {self.data_path}")

        # 加载测试数据
        print("\n[1/3] 加载测试数据...")
        await self._load_test_data()
        print(f"    已加载 {len(self.test_data)} 条测试样本")

        # 初始化Agent
        print("\n[2/3] 初始化Agent...")
        self.agent = MedicalAgent()
        await self.agent.start()

        if self.agent.classifier.ml_enabled:
            print("    ML意图分类器已启用 (准确率: 99.89%)")
            self.results["ml_classifier_status"] = "enabled"
        else:
            print("    使用规则分类器")
            self.results["ml_classifier_status"] = "rule_based"

        print("\n[3/3] 开始测试...")

    async def _load_test_data(self):
        """加载测试数据"""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.test_data = data.get('samples', [])
        except Exception as e:
            print(f"    错误: 加载数据失败 - {e}")
            raise

    async def test_intent_classification(self):
        """测试意图识别准确率"""
        print("\n" + "-" * 70)
        print("测试A: 意图识别准确率测试")
        print("-" * 70)

        stats = {
            "total": 0,
            "correct": 0,
            "by_intent": defaultdict(lambda: {"total": 0, "correct": 0}),
            "confidence_distribution": []
        }

        intent_name_map = {
            "symptom_inquiry": "症状咨询",
            "department_query": "科室查询",
            "medication_consult": "用药咨询",
            "appointment": "预约挂号",
            "health_education": "健康教育",
            "greeting": "问候",
            "unknown": "未知"
        }

        # 抽样测试（测试所有数据）
        sample_size = len(self.test_data)
        print(f"    测试样本数: {sample_size}")

        for i, sample in enumerate(self.test_data):
            text = sample.get('text', '')
            true_intent = sample.get('intent', 'unknown')

            # 预测意图
            context = self.agent.get_or_create_context(f"test_{i}", "test_user")
            result = await self.agent.classifier.classify(text, context)

            # 统计
            is_correct = result.intent.value == true_intent
            stats["total"] += 1
            if is_correct:
                stats["correct"] += 1
                stats["by_intent"][true_intent]["correct"] += 1
            stats["by_intent"][true_intent]["total"] += 1
            stats["confidence_distribution"].append(result.confidence)

            # 进度显示
            if (i + 1) % 500 == 0:
                current_acc = stats["correct"] / stats["total"] * 100
                print(f"    进度: {i+1}/{sample_size} | 当前准确率: {current_acc:.2f}%")

        # 计算结果
        overall_accuracy = stats["correct"] / stats["total"] * 100
        avg_confidence = sum(stats["confidence_distribution"]) / len(stats["confidence_distribution"])

        print(f"\n    总体准确率: {overall_accuracy:.2f}% ({stats['correct']}/{stats['total']})")
        print(f"    平均置信度: {avg_confidence:.4f}")

        print("\n    各意图分类准确率:")
        print(f"    {'意图':<12} {'准确率':<10} {'正确/总数'}")
        print(f"    {'-'*40}")

        for intent, counts in sorted(stats["by_intent"].items(), key=lambda x: -x[1]["total"]):
            acc = counts["correct"] / counts["total"] * 100 if counts["total"] > 0 else 0
            name_cn = intent_name_map.get(intent, intent)
            print(f"    {name_cn:<12} {acc:>6.2f}%    {counts['correct']}/{counts['total']}")

        self.results["intent_classification"] = {
            "overall_accuracy": overall_accuracy,
            "correct": stats["correct"],
            "total": stats["total"],
            "avg_confidence": avg_confidence,
            "by_intent": dict(stats["by_intent"])
        }

        return overall_accuracy

    async def test_functional_workflows(self):
        """测试全流程功能"""
        print("\n" + "-" * 70)
        print("测试B: 全流程功能测试")
        print("-" * 70)

        # 从测试数据中抽取典型样本
        test_cases = []
        intent_samples = defaultdict(list)

        for sample in self.test_data:
            intent = sample.get('intent', 'unknown')
            intent_samples[intent].append(sample)

        # 每种意图取3个样本
        for intent, samples in intent_samples.items():
            test_cases.extend(samples[:3])

        print(f"    测试样本数: {len(test_cases)}")

        results = {
            "total": len(test_cases),
            "success": 0,
            "failed": 0,
            "errors": []
        }

        for i, case in enumerate(test_cases[:100]):  # 最多测试100个
            text = case.get('text', '')
            true_intent = case.get('intent', 'unknown')

            try:
                response = await self.agent.process(text, f"func_test_{i}", "test_user")

                if response and len(response) > 0:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"空响应: {text[:30]}")

            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"异常: {text[:30]} - {str(e)}")

        success_rate = results["success"] / results["total"] * 100
        print(f"    成功率: {success_rate:.2f}% ({results['success']}/{results['total']})")
        print(f"    失败数: {results['failed']}")

        if results["errors"] and len(results["errors"]) <= 10:
            print(f"\n    错误详情:")
            for err in results["errors"][:5]:
                print(f"      - {err}")

        self.results["functional_tests"] = results
        return success_rate

    async def test_edge_cases(self):
        """测试边缘案例"""
        print("\n" + "-" * 70)
        print("测试C: 边缘案例测试")
        print("-" * 70)

        edge_cases = [
            ("否定句", "不头痛", IntentType.UNKNOWN),
            ("否定句", "没病", IntentType.UNKNOWN),
            ("否定句", "不痛不痒", IntentType.UNKNOWN),
            ("短输入", "痛", IntentType.SYMPTOM_INQUIRY),
            ("短输入", "药", IntentType.MEDICATION_CONSULT),
            ("混合", "头痛但是不发烧", IntentType.SYMPTOM_INQUIRY),
            ("英文混合", "我headache", IntentType.SYMPTOM_INQUIRY),
            ("模糊", "那个", IntentType.UNKNOWN),
            ("空", "啊啊啊", IntentType.UNKNOWN),
            ("问候", "你好呀", IntentType.GREETING),
        ]

        results = {
            "total": len(edge_cases),
            "correct": 0
        }

        for name, text, expected in edge_cases:
            context = self.agent.get_or_create_context("edge_test", "test_user")
            result = await self.agent.classifier.classify(text, context)

            is_correct = result.intent == expected
            if is_correct:
                results["correct"] += 1

            status = "[OK]" if is_correct else "[--]"
            print(f"    {status} {name}: '{text}' -> {result.intent.value} (期望: {expected.value})")

        accuracy = results["correct"] / results["total"] * 100
        print(f"\n    边缘案例准确率: {accuracy:.2f}% ({results['correct']}/{results['total']})")

        self.results["edge_cases"] = results
        return accuracy

    async def test_response_quality(self):
        """测试响应质量"""
        print("\n" + "-" * 70)
        print("测试D: 响应质量测试")
        print("-" * 70)

        quality_tests = [
            "我头痛",
            "头痛挂什么科",
            "阿莫西林怎么吃",
            "怎么预防高血压",
            "你好",
            "我想挂号",
        ]

        for text in quality_tests:
            response = await self.agent.process(text, "quality_test", "test_user")
            print(f"\n    输入: {text}")
            print(f"    响应长度: {len(response)} 字符")

            # 检查响应质量
            has_content = len(response) > 50
            has_disclaimer = "免责声明" in response or "disclaimer" in response.lower()
            print(f"    内容丰富: {'是' if has_content else '否'}")
            print(f"    含免责声明: {'是' if has_disclaimer else '否'}")

    def save_report(self):
        """保存测试报告"""
        report_dir = os.path.join(os.path.dirname(__file__), "algorithem")
        os.makedirs(report_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(report_dir, f"comprehensive_test_report_{timestamp}.json")

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n    测试报告已保存: {report_path}")

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 70)
        print("测试摘要报告")
        print("=" * 70)

        print(f"\n测试时间: {self.results['timestamp']}")
        print(f"数据来源: {self.results['data_source']}")
        print(f"分类器状态: {self.results['ml_classifier_status']}")

        print(f"\n意图识别准确率: {self.results['intent_classification']['overall_accuracy']:.2f}%")
        print(f"功能测试成功率: {self.results['functional_tests']['success'] / self.results['functional_tests']['total'] * 100:.2f}%")

        if "edge_cases" in self.results:
            print(f"边缘案例准确率: {self.results['edge_cases']['correct'] / self.results['edge_cases']['total'] * 100:.2f}%")

    async def teardown(self):
        """清理资源"""
        await self.agent.stop()


async def main():
    """主函数"""
    runner = ComprehensiveTestRunner()

    try:
        await runner.setup()
        await runner.test_intent_classification()
        await runner.test_functional_workflows()
        await runner.test_edge_cases()
        await runner.test_response_quality()

        runner.print_summary()
        runner.save_report()

        print("\n" + "=" * 70)
        print("测试完成!")
        print("=" * 70)

    finally:
        await runner.teardown()


if __name__ == "__main__":
    asyncio.run(main())
