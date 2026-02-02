# -*- coding: utf-8 -*-
"""
医疗智能助手 - 算法命中测试
测试意图分类准确性和Skill路由效果
"""
import asyncio
import sys
import os
import json
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.medical_agent import (
    MedicalAgent, IntentClassifier, IntentType,
    DialogueContext, ResponseFormatter
)
from mcp_protocol.mcp_protocol import MCPFactory, MCPClient
from mcp_tools.medical_tools import create_medical_mcp_server


# ============================================================
# 测试数据集
# ============================================================

TEST_CASES = {
    "symptom_inquiry": [
        # 直接症状描述
        ("我头痛", 0.8, "symptom-analyzer"),
        ("我头痛好几天了", 0.8, "symptom-analyzer"),
        ("最近一直头晕", 0.7, "symptom-analyzer"),
        ("我发烧了", 0.8, "symptom-analyzer"),
        ("咳嗽厉害", 0.8, "symptom-analyzer"),
        ("肚子疼", 0.8, "symptom-analyzer"),
        ("胸闷气短", 0.7, "symptom-analyzer"),
        ("恶心想吐", 0.7, "symptom-analyzer"),
        ("拉肚子", 0.7, "symptom-analyzer"),
        ("失眠睡不着", 0.7, "symptom-analyzer"),
        # 症状询问
        ("头痛怎么回事", 0.7, "symptom-analyzer"),
        ("发烧是什么症状", 0.7, "symptom-analyzer"),
        ("咳嗽怎么办", 0.7, "symptom-analyzer"),
        # 程度描述
        ("头痛剧烈", 0.6, "symptom-analyzer"),
        ("有点头疼", 0.5, "symptom-analyzer"),
        ("非常难受", 0.5, "symptom-analyzer"),
    ],

    "department_query": [
        # 直接科室询问
        ("头痛挂什么科", 0.9, "department-recommender"),
        ("头痛去哪个科", 0.9, "department-recommender"),
        ("头痛看什么科", 0.9, "department-recommender"),
        ("头晕应该挂哪个科", 0.9, "department-recommender"),
        ("发烧挂哪个科", 0.8, "department-recommender"),
        ("肚子疼看什么科", 0.8, "department-recommender"),
        # 科室确认
        ("头痛是神经内科吗", 0.7, "department-recommender"),
        ("有没有头痛科", 0.7, "department-recommender"),
        # 间接科室询问
        ("哪个科看头痛", 0.8, "department-recommender"),
        ("什么科看心脏病", 0.7, "department-recommender"),
    ],

    "medication_consult": [
        # 用法询问
        ("阿莫西林怎么吃", 0.9, "medication-advisor"),
        ("布洛芬怎么用", 0.9, "medication-advisor"),
        ("感冒药用法用量", 0.8, "medication-advisor"),
        ("退烧药吃多少", 0.8, "medication-advisor"),
        # 副作用询问
        ("阿莫西林有什么副作用", 0.9, "medication-advisor"),
        ("布洛芬副作用", 0.9, "medication-advisor"),
        ("对乙酰氨基酚不良反应", 0.9, "medication-advisor"),
        # 禁忌询问
        ("阿莫西林禁忌", 0.9, "medication-advisor"),
        ("感冒药有什么禁忌", 0.8, "medication-advisor"),
        # 相互作用
        ("阿莫西林能一起吃吗", 0.8, "medication-advisor"),
        ("吃药相互作用", 0.7, "medication-advisor"),
        # 一般询问
        ("阿莫西林是什么药", 0.7, "medication-advisor"),
        ("这个药安全吗", 0.5, "medication-advisor"),
    ],

    "appointment": [
        # 直接挂号
        ("我想挂号", 1.0, "appointment-service"),
        ("我要挂号", 1.0, "appointment-service"),
        ("帮我挂号", 1.0, "appointment-service"),
        ("预约挂号", 1.0, "appointment-service"),
        # 预约
        ("预约个号", 0.9, "appointment-service"),
        ("想预约门诊", 0.9, "appointment-service"),
        ("预约医生", 0.8, "appointment-service"),
        # 排队
        ("排号", 0.9, "appointment-service"),
        ("想看医生", 0.8, "appointment-service"),
    ],

    "health_education": [
        # 疾病预防
        ("怎么预防高血压", 0.9, "health-educator"),
        ("如何预防糖尿病", 0.9, "health-educator"),
        ("感冒怎么预防", 0.9, "health-educator"),
        ("怎么预防心血管疾病", 0.9, "health-educator"),
        ("高血压如何预防", 0.9, "health-educator"),
        ("预防感冒的方法", 0.8, "health-educator"),
        # 健康保持
        ("如何保持健康", 0.8, "health-educator"),
        ("怎么保持身体健康", 0.8, "health-educator"),
        ("保持健康的方法", 0.7, "health-educator"),
        # 饮食相关
        ("高血压不能吃什么", 0.8, "health-educator"),
        ("糖尿病饮食注意什么", 0.8, "health-educator"),
        ("痛风饮食禁忌", 0.8, "health-educator"),
        ("有什么运动建议", 0.8, "health-educator"),
        ("锻炼建议", 0.7, "health-educator"),
        # 生活方式
        ("健康生活方式", 0.7, "health-educator"),
        ("养生建议", 0.7, "health-educator"),
    ],

    "greeting": [
        ("你好", 0.9, "greeting-handler"),
        ("您好", 0.9, "greeting-handler"),
        ("嗨", 0.9, "greeting-handler"),
        ("hello", 0.9, "greeting-handler"),
        ("hi", 0.9, "greeting-handler"),
        ("早上好", 0.9, "greeting-handler"),
        ("下午好", 0.9, "greeting-handler"),
        ("晚上好", 0.9, "greeting-handler"),
        ("谢谢", 0.9, "greeting-handler"),
        ("感谢", 0.9, "greeting-handler"),
        ("再见", 0.9, "greeting-handler"),
        ("拜拜", 0.9, "greeting-handler"),
    ],

    "unknown": [
        # 否定句
        ("不痛", 0.0, "fallback-handler"),
        ("没病", 0.0, "fallback-handler"),
        ("没有不舒服", 0.0, "fallback-handler"),
        # 无意义输入
        ("啊啊啊", 0.0, "fallback-handler"),
        ("痛痛痛", 0.0, "fallback-handler"),
        # 不相关
        ("今天天气怎么样", 0.0, "fallback-handler"),
        ("股票行情", 0.0, "fallback-handler"),
    ],

    "edge_cases": [
        # 模糊输入
        ("不舒服", 0.3, "symptom-analyzer"),  # 可能是症状
        ("难受", 0.3, "symptom-analyzer"),
        ("有点痛", 0.4, "symptom-analyzer"),
        # 多意图
        ("头痛发烧应该挂什么科", 0.5, "department-recommender"),  # 科室优先
        ("吃阿莫西林可以治头痛吗", 0.4, "medication-consul"),  # 用药优先
        # 上下文依赖
        ("是的", 0.0, "fallback-handler"),  # 需要上下文
        ("不是", 0.0, "fallback-handler"),
    ],
}


# ============================================================
# 测试类
# ============================================================

class AlgorithmHitTester:
    """算法命中测试器"""

    def __init__(self):
        self.classifier = IntentClassifier()
        self.results = defaultdict(lambda: {
            "total": 0,
            "correct_intent": 0,
            "correct_skill": 0,
            "confidence_scores": [],
            "details": []
        })
        self.start_time = datetime.now()

    async def test_intent_classification(self):
        """测试意图分类"""
        print("\n" + "="*70)
        print("意图分类命中测试")
        print("="*70)

        for intent_type, test_cases in TEST_CASES.items():
            if intent_type == "edge_cases":
                continue

            print(f"\n--- 意图类型: {intent_type} ---")

            for text, expected_conf, expected_skill in test_cases:
                result = await self.classifier.classify(text, DialogueContext("test", "user"))

                # 检查意图是否正确
                intent_correct = result.intent.value == intent_type

                # 检查Skill是否正确
                skill_correct = result.target_skill == expected_skill

                # 记录结果
                self.results[intent_type]["total"] += 1
                if intent_correct:
                    self.results[intent_type]["correct_intent"] += 1
                if skill_correct:
                    self.results[intent_type]["correct_skill"] += 1
                self.results[intent_type]["confidence_scores"].append(result.confidence)
                self.results[intent_type]["details"].append({
                    "text": text,
                    "predicted_intent": result.intent.value,
                    "expected_intent": intent_type,
                    "predicted_skill": result.target_skill,
                    "expected_skill": expected_skill,
                    "confidence": result.confidence,
                    "intent_correct": intent_correct,
                    "skill_correct": skill_correct
                })

                status = "PASS" if (intent_correct and skill_correct) else "FAIL"
                print(f"  [{status}] '{text}'")
                print(f"       意图: {result.intent.value} (期望: {intent_type}) "
                      f"| Skill: {result.target_skill} (期望: {expected_skill}) "
                      f"| 置信度: {result.confidence:.2f}")

    async def test_edge_cases(self):
        """测试边缘情况"""
        print("\n" + "="*70)
        print("边缘情况测试")
        print("="*70)

        for text, expected_conf, expected_skill in TEST_CASES["edge_cases"]:
            result = await self.classifier.classify(text, DialogueContext("test", "user"))

            print(f"\n  测试: '{text}'")
            print(f"       预测意图: {result.intent.value}")
            print(f"       预测Skill: {result.target_skill}")
            print(f"       置信度: {result.confidence:.2f}")
            print(f"       需要澄清: {result.requires_clarification}")

            self.results["edge_cases"]["total"] += 1
            self.results["edge_cases"]["details"].append({
                "text": text,
                "predicted_intent": result.intent.value,
                "predicted_skill": result.target_skill,
                "confidence": result.confidence,
                "requires_clarification": result.requires_clarification
            })

    def calculate_statistics(self):
        """计算统计数据"""
        print("\n" + "="*70)
        print("测试统计报告")
        print("="*70)

        total_tests = 0
        total_intent_correct = 0
        total_skill_correct = 0
        all_confidences = []

        for intent_type, data in self.results.items():
            if intent_type == "edge_cases":
                continue

            total = data["total"]
            intent_correct = data["correct_intent"]
            skill_correct = data["correct_skill"]
            confidences = data["confidence_scores"]

            if total == 0:
                continue

            intent_acc = intent_correct / total * 100
            skill_acc = skill_correct / total * 100
            avg_conf = sum(confidences) / len(confidences) if confidences else 0

            total_tests += total
            total_intent_correct += intent_correct
            total_skill_correct += skill_correct
            all_confidences.extend(confidences)

            print(f"\n{intent_type.upper()}:")
            print(f"  测试数量: {total}")
            print(f"  意图准确率: {intent_acc:.1f}% ({intent_correct}/{total})")
            print(f"  Skill准确率: {skill_acc:.1f}% ({skill_correct}/{total})")
            print(f"  平均置信度: {avg_conf:.2f}")

        # 总体统计
        if total_tests > 0:
            overall_intent_acc = total_intent_correct / total_tests * 100
            overall_skill_acc = total_skill_correct / total_tests * 100
            overall_avg_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0

            print("\n" + "="*70)
            print("总体结果:")
            print(f"  总测试数: {total_tests}")
            print(f"  意图分类准确率: {overall_intent_acc:.1f}%")
            print(f"  Skill路由准确率: {overall_skill_acc:.1f}%")
            print(f"  平均置信度: {overall_avg_conf:.2f}")

            # 评级
            if overall_intent_acc >= 95:
                grade = "A+ (优秀)"
            elif overall_intent_acc >= 90:
                grade = "A (良好)"
            elif overall_intent_acc >= 80:
                grade = "B (中等)"
            elif overall_intent_acc >= 70:
                grade = "C (及格)"
            else:
                grade = "D (需改进)"

            print(f"  综合评级: {grade}")

        return {
            "total_tests": total_tests,
            "intent_accuracy": total_intent_correct / total_tests * 100 if total_tests > 0 else 0,
            "skill_accuracy": total_skill_correct / total_tests * 100 if total_tests > 0 else 0,
            "avg_confidence": sum(all_confidences) / len(all_confidences) if all_confidences else 0
        }

    def save_results(self, stats):
        """保存测试结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        results = {
            "test_time": datetime.now().isoformat(),
            "statistics": stats,
            "results_by_intent": {
                k: {
                    "total": v["total"],
                    "intent_accuracy": v["correct_intent"] / v["total"] * 100 if v["total"] > 0 else 0,
                    "skill_accuracy": v["correct_skill"] / v["total"] * 100 if v["total"] > 0 else 0,
                    "avg_confidence": sum(v["confidence_scores"]) / len(v["confidence_scores"]) if v["confidence_scores"] else 0,
                    "details": v["details"]
                }
                for k, v in self.results.items()
            }
        }

        output_dir = os.path.join(os.path.dirname(__file__), "results")
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(output_dir, f"algorithm_hit_results_{timestamp}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n测试结果已保存到: {output_file}")
        return output_file


# ============================================================
# 主程序
# ============================================================

async def main():
    """主测试程序"""
    print("\n" + "="*70)
    print("医疗智能助手 - 算法命中测试")
    print("="*70)

    tester = AlgorithmHitTester()

    # 运行测试
    await tester.test_intent_classification()
    await tester.test_edge_cases()

    # 计算统计
    stats = tester.calculate_statistics()

    # 保存结果
    tester.save_results(stats)

    print("\n" + "="*70)
    print("测试完成!")
    print("="*70)

    return stats


if __name__ == "__main__":
    stats = asyncio.run(main())
    sys.exit(0 if stats["intent_accuracy"] >= 80 else 1)
