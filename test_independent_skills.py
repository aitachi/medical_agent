# -*- coding: utf-8 -*-
"""
独立Skill功能测试
测试不调用MCP的三个Skill: intent-classifier, health-educator, response-formatter
"""
import asyncio
import sys
sys.path.insert(0, '.')

from agent.medical_agent import (
    IntentType, IntentClassifier, HealthKnowledgeBase,
    ResponseFormatter, DialogueContext, SkillRequest, SkillInvoker
)


async def test_intent_classifier_skill():
    """测试意图分类Skill功能"""
    print("=" * 60)
    print("Skill 1/3: Intent Classifier (意图分类)")
    print("=" * 60)

    classifier = IntentClassifier()

    test_cases = [
        # 健康教育测试
        ("怎么预防高血压", IntentType.HEALTH_EDUCATION, "预防"),
        ("糖尿病不能吃什么", IntentType.HEALTH_EDUCATION, "饮食"),
        ("运动对健康的好处", IntentType.HEALTH_EDUCATION, "运动"),
        ("保持健康的生活方式", IntentType.HEALTH_EDUCATION, "生活"),

        # 症状咨询测试
        ("我头痛好几天了", IntentType.SYMPTOM_INQUIRY, "症状"),

        # 用药咨询测试
        ("阿莫西林怎么吃", IntentType.MEDICATION_CONSULT, "药品"),

        # 科室查询测试
        ("头痛挂什么科", IntentType.DEPARTMENT_QUERY, "科室"),

        # 预约挂号测试
        ("我想挂个号", IntentType.APPOINTMENT, "预约"),
    ]

    print("\n意图分类结果:")
    print("-" * 60)

    correct = 0
    for text, expected, category in test_cases:
        result = await classifier.classify(text, DialogueContext("test", "user"))
        status = "PASS" if result.intent == expected else "FAIL"
        if result.intent == expected:
            correct += 1

        print(f"\n[{status}] '{text}'")
        print(f"  意图: {result.intent.value}")
        print(f"  置信度: {result.confidence:.2f}")
        print(f"  实体: {result.entities}")
        print(f"  目标Skill: {result.target_skill}")

    accuracy = correct / len(test_cases) * 100
    print(f"\n准确率: {accuracy:.1f}% ({correct}/{len(test_cases)})")

    return accuracy >= 90


async def test_health_educator_skill():
    """测试健康教育Skill功能"""
    print("\n" + "=" * 60)
    print("Skill 2/3: Health Educator (健康教育)")
    print("=" * 60)

    health_kb = HealthKnowledgeBase()
    skill_invoker = SkillInvoker(mcp_client=None)

    # 测试1: 疾病预防知识
    print("\n[测试1] 疾病预防知识")
    prevention = health_kb.get_disease_prevention("高血压")
    if prevention:
        print(f"  高血压预防: {len(prevention.get('prevention', {}))} 类建议")

    # 测试2: 饮食禁忌
    print("\n[测试2] 饮食禁忌")
    restrictions = health_kb.get_food_restrictions("高血压")
    print(f"  高血压禁忌: {len(restrictions)} 种食物")
    for item in restrictions[:3]:
        print(f"    - {item}")

    # 测试3: 完整Skill调用
    print("\n[测试3] 完整Skill调用")

    test_queries = [
        ("怎么预防高血压", {"health_topic": "高血压", "query_type": "prevention"}),
        ("高血压不能吃什么", {"query_type": "diet"}),
        ("有什么运动建议", {"query_type": "exercise"}),
    ]

    for query, entities in test_queries:
        request = SkillRequest(
            skill_name="health-educator",
            intent=IntentType.HEALTH_EDUCATION,
            entities=entities,
            context=DialogueContext("test", "user"),
            metadata={"user_input": query}
        )

        response = await skill_invoker.invoke(request)
        print(f"\n  查询: {query}")
        print(f"  响应长度: {len(response.content)} 字符")
        print(f"  包含免责声明: {'免责声明' in response.content}")
        print(f"  追问建议: {len(response.follow_up_suggestions)} 条")

    return True


async def test_response_formatter_skill():
    """测试响应格式化Skill功能"""
    print("\n" + "=" * 60)
    print("Skill 3/3: Response Formatter (响应格式化)")
    print("=" * 60)

    formatter = ResponseFormatter()

    # 测试1: 症状响应格式化
    print("\n[测试1] 症状响应格式化")
    symptom_data = {
        "description": "头部疼痛",
        "common_causes": ["紧张性头痛", "偏头痛"],
        "red_flags": ["剧烈突发头痛", "意识改变"],
        "department": "神经内科",
        "self_care": ["休息", "避免刺激"]
    }
    formatted = formatter._format_symptom_response("头痛", symptom_data)
    print(f"  格式化后长度: {len(formatted)} 字符")
    print(f"  包含免责声明: {'免责声明' in formatted}")
    print(f"  包含危险信号: {'危险信号' in formatted}")
    print(f"  包含建议科室: {'科室' in formatted}")

    # 测试2: 药品响应格式化
    print("\n[测试2] 药品响应格式化")
    drug_data = {
        "generic_name": "阿莫西林",
        "category": "抗生素",
        "dosage": {"adult": "0.5g, 每6-8小时一次"},
        "side_effects": ["恶心", "腹泻", "皮疹"],
        "contraindications": ["青霉素过敏"],
        "warnings": "使用前需做皮试"
    }
    formatted = formatter._format_drug_response("阿莫西林", "info", drug_data)
    print(f"  格式化后长度: {len(formatted)} 字符")
    print(f"  包含免责声明: {'免责声明' in formatted}")
    print(f"  包含用法用量: {'用法用量' in formatted}")
    print(f"  包含副作用: {'副作用' in formatted}")

    # 测试3: 健康教育响应格式化
    print("\n[测试3] 健康教育响应格式化")
    formatted = formatter._format_health_response("这是健康建议内容")
    print(f"  格式化后长度: {len(formatted)} 字符")
    print(f"  包含免责声明: {'免责声明' in formatted}")

    # 测试4: 问候响应格式化
    print("\n[测试4] 问候响应格式化")
    formatted = formatter._format_greeting_response("您好！")
    print(f"  格式化后长度: {len(formatted)} 字符")
    print(f"  包含免责声明: {'免责声明' in formatted}")

    # 测试5: 紧急警告添加
    print("\n[测试5] 紧急警告添加")
    response = "这是普通响应"
    with_warning = formatter.add_emergency_warning(response)
    print(f"  原始长度: {len(response)}")
    print(f"  添加警告后: {len(with_warning)}")
    print(f"  包含紧急标志: {'🚨' in with_warning}")

    return True


async def test_integrated_skills():
    """测试集成Skill功能 - 展示完整对话流程"""
    print("\n" + "=" * 60)
    print("集成测试: 完整对话流程")
    print("=" * 60)

    from mcp_protocol.mcp_protocol import MCPFactory, MCPClient
    from mcp_tools.medical_tools import create_medical_mcp_server
    from agent.medical_agent import MedicalAgent

    # 初始化
    host = MCPFactory.create_host("integrated-test-host")
    await host.start()

    mcp_server = await create_medical_mcp_server(host)
    await mcp_server.start()

    mcp_client = MCPClient("test-client", host)
    await mcp_client.start()

    agent = MedicalAgent(mcp_client=mcp_client)
    await agent.start()

    # 测试对话 - 覆盖所有Skill
    test_dialogues = [
        ("你好", "greeting-handler", "问候"),
        ("我头痛", "symptom-analyzer", "症状分析(MCP)"),
        ("怎么预防高血压", "health-educator", "健康教育(内置KB)"),
        ("头痛挂什么科", "department-recommender", "科室推荐(MCP)"),
        ("阿莫西林怎么吃", "medication-advisor", "用药咨询(MCP)"),
        ("有什么运动建议", "health-educator", "健康教育(内置KB)"),
    ]

    print("\n对话流程:")
    print("-" * 60)

    for user_input, expected_skill, description in test_dialogues:
        response = await agent.process(user_input, session_id="integrated-test")

        # 获取使用的意图
        context = agent.get_context("integrated-test")
        last_intent = context.history[-1]["intent"] if context.history else "unknown"

        print(f"\n  用户: {user_input}")
        print(f"  意图: {last_intent}")
        print(f"  期望Skill: {expected_skill}")
        print(f"  响应长度: {len(response)} 字符")

    # 验证
    context = agent.get_context("integrated-test")
    success = context.turn_count == len(test_dialogues)

    # 清理
    await agent.stop()
    await mcp_client.stop()
    await mcp_server.stop()
    await host.stop()

    print(f"\n  对话轮数: {context.turn_count}")
    print(f"  测试结果: {'PASS' if success else 'FAIL'}")

    return success


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("独立Skill功能测试")
    print("测试三个不调用MCP的Skill")
    print("=" * 60)

    results = {}

    # 测试1: Intent Classifier
    results["intent_classifier"] = await test_intent_classifier_skill()

    # 测试2: Health Educator
    results["health_educator"] = await test_health_educator_skill()

    # 测试3: Response Formatter
    results["response_formatter"] = await test_response_formatter_skill()

    # 测试4: 集成测试
    results["integrated"] = await test_integrated_skills()

    # 汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)

    all_passed = True
    for skill, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {skill}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("所有独立Skill测试通过！")
    else:
        print("部分测试失败")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
