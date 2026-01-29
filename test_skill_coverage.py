# -*- coding: utf-8 -*-
"""
Skill覆盖测试 - 每个Skill 3个测试用例
验证所有Skill的命中率和响应正确性
"""
import asyncio
import sys
sys.path.insert(0, '.')

from mcp_protocol.mcp_protocol import MCPFactory, MCPClient
from mcp_tools.medical_tools import create_medical_mcp_server
from agent.medical_agent import MedicalAgent, IntentType, DialogueContext


# 每个Skill的3个测试用例
SKILL_TEST_CASES = {
    "greeting-handler": [
        "你好",
        "早上好",
        "hi",
    ],

    "symptom-analyzer": [
        "我头痛好几天了",
        "最近一直咳嗽，还有点发热",
        "胃不舒服，感觉恶心想吐",
    ],

    "department-recommender": [
        "头痛应该挂什么科",
        "我肚子疼去看哪个科室",
        "皮肤长红点要去哪科",
    ],

    "medication-advisor": [
        "阿莫西林怎么吃",
        "布洛芬有什么副作用",
        "这药一天吃几次，一次多少",
    ],

    "health-educator": [
        "怎么预防高血压",
        "糖尿病患者不能吃什么",
        "有什么运动建议吗",
    ],
}


async def test_skill_coverage():
    """测试所有Skill的覆盖情况"""

    print("\n" + "=" * 70)
    print("Skill覆盖测试 - 每个Skill 3个测试用例")
    print("=" * 70)

    # 初始化系统
    host = MCPFactory.create_host("skill-test-host")
    await host.start()

    server = await create_medical_mcp_server(host)
    await server.start()

    client = MCPClient("skill-test-client", host)
    await client.start()

    agent = MedicalAgent(mcp_client=client)
    await agent.start()

    print("\n[系统初始化完成]\n")

    # 测试结果
    results = {}
    total_tests = 0
    total_passed = 0

    # 逐个测试Skill
    for skill_name, test_cases in SKILL_TEST_CASES.items():
        print(f"\n{'=' * 70}")
        print(f"测试Skill: {skill_name}")
        print(f"{'=' * 70}")

        skill_results = []

        for i, user_input in enumerate(test_cases, 1):
            total_tests += 1

            # 获取预期意图
            context = agent.get_context("skill-test") or DialogueContext("skill-test", "test-user")
            intent_result = await agent.classifier.classify(user_input, context)

            # 处理用户输入
            try:
                response = await agent.process(user_input, session_id="skill-test", user_id="test-user")

                # 获取实际的target_skill
                actual_context = agent.get_context("skill-test")
                actual_skill = intent_result.target_skill

                # 验证Skill命中
                expected_skill = skill_name
                is_match = actual_skill == expected_skill

                if is_match:
                    total_passed += 1
                    status = "PASS"
                else:
                    status = "FAIL"

                skill_results.append({
                    "input": user_input,
                    "expected": expected_skill,
                    "actual": actual_skill,
                    "intent": intent_result.intent.value,
                    "confidence": intent_result.confidence,
                    "status": is_match,
                })

                print(f"\n  测试 {i}/3: '{user_input}'")
                print(f"    预期Skill: {expected_skill}")
                print(f"    实际Skill: {actual_skill}")
                print(f"    意图: {intent_result.intent.value}")
                print(f"    置信度: {intent_result.confidence:.2f}")
                print(f"    响应长度: {len(response)} 字符")
                print(f"    状态: [{status}]")

            except Exception as e:
                print(f"\n  测试 {i}/3: '{user_input}' - ERROR: {e}")
                skill_results.append({
                    "input": user_input,
                    "status": False,
                    "error": str(e)
                })

        results[skill_name] = skill_results

        # 汇总该Skill的测试结果
        passed = sum(1 for r in skill_results if r.get("status", False))
        print(f"\n  {skill_name} 通过率: {passed}/3")

    # 清理
    await agent.stop()
    await client.stop()
    await server.stop()
    await host.stop()

    # 总体汇总
    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)
    print(f"\n总测试数: {total_tests}")
    print(f"通过数: {total_passed}")
    print(f"通过率: {total_passed / total_tests * 100:.1f}%")

    print("\n各Skill通过情况:")
    print("-" * 70)
    for skill_name, skill_results in results.items():
        passed = sum(1 for r in skill_results if r.get("status", False))
        status = "PASS" if passed == 3 else "FAIL"
        print(f"  {skill_name:25} {passed}/3  [{status}]")

    print("\n" + "=" * 70)

    return total_passed == total_tests


if __name__ == "__main__":
    success = asyncio.run(test_skill_coverage())
    sys.exit(0 if success else 1)
