"""
医疗智能助手全面功能测试
测试MCP协议、MCP工具、Skills、Agent等所有功能
"""

import asyncio
import sys
import os
import json
import time
from typing import List, Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_protocol.mcp_protocol import (
    MCPFactory, MCPHost, MCPServer, MCPClient, MCPTool, MCPToolHandler
)
from mcp_tools.medical_tools import (
    MedicalKnowledgeHandler,
    HospitalDepartmentHandler,
    DrugDatabaseHandler,
    AppointmentBookingHandler
)
from agent.medical_agent import MedicalAgent, IntentType, DialogueContext


# ============================================================
# 测试框架
# ============================================================

class TestResult:
    """测试结果"""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.duration = 0.0
        self.details = []

    def add_detail(self, detail: str):
        self.details.append(detail)

    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} | {self.name} ({self.duration:.3f}s)"


class TestSuite:
    """测试套件"""
    def __init__(self, name: str):
        self.name = name
        self.results: List[TestResult] = []

    def add_result(self, result: TestResult):
        self.results.append(result)

    def print_summary(self):
        """打印测试摘要"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        print("\n" + "="*70)
        print(f"测试套件: {self.name}")
        print("="*70)

        for result in self.results:
            print(result)
            if result.error:
                print(f"    错误: {result.error}")
            for detail in result.details:
                print(f"    - {detail}")

        print("-"*70)
        print(f"总计: {total} | 通过: {passed} | 失败: {failed}")
        print("="*70 + "\n")

        return failed == 0


async def run_test(test_func, test_name: str) -> TestResult:
    """运行单个测试"""
    result = TestResult(test_name)
    start_time = time.time()

    try:
        await test_func(result)
        result.passed = True
    except Exception as e:
        result.error = str(e)
        import traceback
        result.add_detail(traceback.format_exc())

    result.duration = time.time() - start_time
    return result


# ============================================================
# MCP 协议测试
# ============================================================

class MCPProtocolTests:
    """MCP协议测试套件"""

    def __init__(self):
        self.suite = TestSuite("MCP 协议测试")

    async def run_all(self) -> bool:
        """运行所有测试"""
        print("\n🧪 开始 MCP 协议测试...")

        self.suite.add_result(await run_test(
            self.test_host_creation, "Host创建与启动"
        ))
        self.suite.add_result(await run_test(
            self.test_server_registration, "Server注册"
        ))
        self.suite.add_result(await run_test(
            self.test_tool_discovery, "工具发现"
        ))
        self.suite.add_result(await run_test(
            self.test_client_connection, "Client连接"
        ))
        self.suite.add_result(await run_test(
            self.test_heartbeat, "心跳机制"
        ))

        return self.suite.print_summary()

    async def test_host_creation(self, result: TestResult):
        """测试Host创建"""
        host = MCPFactory.create_host("test-host")
        await host.start()

        result.add_detail(f"Host ID: {host.host_id}")
        result.add_detail(f"初始服务器数: {len(host.servers)}")
        result.add_detail(f"初始工具数: {len(host.tools)}")

        assert host.host_id == "test-host"
        assert host._running == True

        await host.stop()

    async def test_server_registration(self, result: TestResult):
        """测试服务器注册"""
        host = MCPFactory.create_host("test-host")
        await host.start()

        server = MCPFactory.create_server(
            "test-server", "测试服务器", "localhost", 8001, host
        )

        # 注册测试工具
        tool = MCPTool(
            name="test_tool",
            description="测试工具",
            category="test",
            input_schema={"type": "object"},
            output_schema={"type": "object"}
        )

        await host.register_server(
            MCPServerInfo("test-server", "测试服务器", "localhost", 8001),
            [tool]
        )

        result.add_detail(f"注册后服务器数: {len(host.servers)}")
        result.add_detail(f"注册后工具数: {len(host.tools)}")

        assert "test-server" in host.servers
        assert "test_tool" in host.tools

        await host.stop()

    async def test_tool_discovery(self, result: TestResult):
        """测试工具发现"""
        from mcp_protocol.mcp_protocol import MCPServerInfo

        host = MCPFactory.create_host("test-host")
        await host.start()

        # 注册医疗工具
        tools = [
            MCPTool("medical_knowledge_query", "医学知识查询", "medical", {}, {}),
            MCPTool("hospital_department_query", "科室查询", "hospital", {}, {}),
            MCPTool("drug_database_query", "药品查询", "drug", {}, {}),
            MCPTool("appointment_booking", "预约挂号", "appointment", {}, {}),
        ]

        server_info = MCPServerInfo("medical-server", "医疗服务器", "localhost", 8001)
        await host.register_server(server_info, tools)

        # 发现所有工具
        all_tools = await host.discover_tools()
        result.add_detail(f"发现工具数: {len(all_tools)}")

        # 按类别发现
        medical_tools = await host.discover_tools("medical")
        result.add_detail(f"医疗类工具数: {len(medical_tools)}")

        assert len(all_tools) == 4
        assert len(medical_tools) == 1

        await host.stop()

    async def test_client_connection(self, result: TestResult):
        """测试Client连接"""
        host = MCPFactory.create_host("test-host")
        await host.start()

        client = MCPClient("test-client", host)
        await client.start()

        result.add_detail(f"Client ID: {client.client_id}")
        result.add_detail(f"Client运行状态: {client._running}")

        # 列出工具
        tools = await client.list_tools()
        result.add_detail(f"Client可访问工具数: {len(tools)}")

        assert client._running == True

        await client.stop()
        await host.stop()

    async def test_heartbeat(self, result: TestResult):
        """测试心跳机制"""
        host = MCPFactory.create_host("test-host")
        await host.start()

        server = MCPFactory.create_server(
            "test-server", "测试服务器", "localhost", 8001, host
        )
        await server.start()

        # 等待心跳发送
        await asyncio.sleep(2)

        # 检查服务器状态
        server_info = await host.get_server("test-server")
        if server_info:
            result.add_detail(f"服务器状态: {server_info.status}")
            result.add_detail(f"最后心跳: {server_info.last_heartbeat}")

        await server.stop()
        await host.stop()


# ============================================================
# MCP 工具测试
# ============================================================

class MCPToolTests:
    """MCP工具测试套件"""

    def __init__(self):
        self.suite = TestSuite("MCP 工具测试")

    async def run_all(self) -> bool:
        """运行所有测试"""
        print("\n🧪 开始 MCP 工具测试...")

        self.suite.add_result(await run_test(
            self.test_medical_knowledge_query, "医学知识查询工具"
        ))
        self.suite.add_result(await run_test(
            self.test_hospital_department_query, "医院科室查询工具"
        ))
        self.suite.add_result(await run_test(
            self.test_drug_database_query, "药品数据库查询工具"
        ))
        self.suite.add_result(await run_test(
            self.test_appointment_booking, "预约挂号工具"
        ))

        return self.suite.print_summary()

    async def test_medical_knowledge_query(self, result: TestResult):
        """测试医学知识查询"""
        handler = MedicalKnowledgeHandler()

        # 测试症状查询
        response = await handler.execute({
            "query_type": "symptom",
            "keyword": "头痛"
        })

        result.add_detail(f"查询成功: {response.get('success')}")
        result.add_detail(f"症状: {response.get('keyword')}")

        if response.get('success'):
            data = response.get('data', {})
            result.add_detail(f"描述: {data.get('description')[:50]}...")
            result.add_detail(f"常见原因数: {len(data.get('common_causes', []))}")
            result.add_detail(f"红旗征数: {len(data.get('red_flags', []))}")

        assert response.get('success') == True
        assert 'data' in response

    async def test_hospital_department_query(self, result: TestResult):
        """测试医院科室查询"""
        handler = HospitalDepartmentHandler()

        # 测试症状推荐
        response = await handler.execute({
            "query_type": "by_symptom",
            "symptom": "头痛"
        })

        result.add_detail(f"查询成功: {response.get('success')}")
        result.add_detail(f"推荐数: {len(response.get('recommendations', []))}")

        if response.get('success'):
            for rec in response.get('recommendations', [])[:2]:
                result.add_detail(f"  - {rec['symptom']} -> {rec['department']}")

        assert response.get('success') == True

    async def test_drug_database_query(self, result: TestResult):
        """测试药品数据库查询"""
        handler = DrugDatabaseHandler()

        # 测试药品信息查询
        response = await handler.execute({
            "query_type": "info",
            "drug_name": "阿莫西林"
        })

        result.add_detail(f"查询成功: {response.get('success')}")
        result.add_detail(f"药品: {response.get('drug_name')}")

        if response.get('success'):
            info = response.get('info', {})
            result.add_detail(f"分类: {info.get('category')}")
            result.add_detail(f"副作用数: {len(info.get('side_effects', []))}")

        assert response.get('success') == True

    async def test_appointment_booking(self, result: TestResult):
        """测试预约挂号"""
        handler = AppointmentBookingHandler()

        # 测试查询号源
        response = await handler.execute({
            "action": "query_availability",
            "department": "内科"
        })

        result.add_detail(f"查询成功: {response.get('success')}")
        result.add_detail(f"医生数: {len(response.get('doctors', []))}")

        if response.get('success'):
            for doctor in response.get('doctors', [])[:2]:
                result.add_detail(f"  - {doctor['name']} ({doctor['title']})")

        assert response.get('success') == True


# ============================================================
# Agent 测试
# ============================================================

class AgentTests:
    """Agent测试套件"""

    def __init__(self, agent: MedicalAgent):
        self.agent = agent
        self.suite = TestSuite("Agent 测试")

    async def run_all(self) -> bool:
        """运行所有测试"""
        print("\n🧪 开始 Agent 测试...")

        self.suite.add_result(await run_test(
            self.test_intent_classification, "意图分类测试"
        ))
        self.suite.add_result(await run_test(
            self.test_multi_turn_dialogue, "多轮对话测试"
        ))
        self.suite.add_result(await run_test(
            self.test_context_management, "上下文管理测试"
        ))
        self.suite.add_result(await run_test(
            self.test_symptom_analyzer, "症状分析Skill测试"
        ))
        self.suite.add_result(await run_test(
            self.test_department_recommender, "科室推荐Skill测试"
        ))
        self.suite.add_result(await run_test(
            self.test_medication_advisor, "用药咨询Skill测试"
        ))

        return self.suite.print_summary()

    async def test_intent_classification(self, result: TestResult):
        """测试意图分类"""
        test_cases = [
            ("我头痛好几天了", IntentType.SYMPTOM_INQUIRY),
            ("头痛挂什么科", IntentType.DEPARTMENT_QUERY),
            ("阿莫西林怎么吃", IntentType.MEDICATION_CONSULT),
            ("我想挂个号", IntentType.APPOINTMENT),
            ("怎么预防高血压", IntentType.HEALTH_EDUCATION),
            ("你好", IntentType.GREETING),
        ]

        correct = 0
        for text, expected_intent in test_cases:
            intent_result = await self.agent.classifier.classify(
                text,
                DialogueContext("test", "test-user")
            )

            if intent_result.intent == expected_intent:
                correct += 1
                result.add_detail(f"✓ '{text}' -> {intent_result.intent.value} ({intent_result.confidence:.2f})")
            else:
                result.add_detail(f"✗ '{text}' -> {intent_result.intent.value} (期望: {expected_intent.value})")

        accuracy = correct / len(test_cases)
        result.add_detail(f"准确率: {accuracy:.1%} ({correct}/{len(test_cases)})")

        assert accuracy >= 0.8

    async def test_multi_turn_dialogue(self, result: TestResult):
        """测试多轮对话"""
        session_id = "test-multi-turn"

        # 第一轮
        response1 = await self.agent.process(
            "我头痛",
            session_id=session_id
        )
        result.add_detail(f"第1轮: 用户='我头痛', 响应长度={len(response1)}")

        # 第二轮（补充信息）
        response2 = await self.agent.process(
            "已经三天了",
            session_id=session_id
        )
        result.add_detail(f"第2轮: 用户='已经三天了', 响应长度={len(response2)}")

        context = self.agent.get_context(session_id)
        result.add_detail(f"对话轮数: {context.turn_count}")
        result.add_detail(f"累积实体: {context.accumulated_entities}")

        assert context.turn_count == 2

    async def test_context_management(self, result: TestResult):
        """测试上下文管理"""
        session_id = "test-context"

        # 添加一些对话
        await self.agent.process("你好", session_id=session_id)
        await self.agent.process("我头痛", session_id=session_id)

        context = self.agent.get_context(session_id)
        result.add_detail(f"会话ID: {context.session_id}")
        result.add_detail(f"用户ID: {context.user_id}")
        result.add_detail(f"对话轮数: {len(context.history)}")

        # 清除会话
        self.agent.clear_context(session_id)
        cleared_context = self.agent.get_context(session_id)
        result.add_detail(f"清除后会话存在: {cleared_context is not None}")

        assert cleared_context is None

    async def test_symptom_analyzer(self, result: TestResult):
        """测试症状分析Skill"""
        from agent.medical_agent import SkillRequest, IntentType

        request = SkillRequest(
            skill_name="symptom-analyzer",
            intent=IntentType.SYMPTOM_INQUIRY,
            entities={"symptom": "头痛", "duration": "3天"},
            context=DialogueContext("test", "user"),
            metadata={"user_input": "我头痛三天了"}
        )

        response = await self.agent.skill_invoker.invoke(request)

        result.add_detail(f"响应成功: {response.success}")
        result.add_detail(f"响应长度: {len(response.content)}")
        result.add_detail(f"包含免责声明: {'免责声明' in response.content}")

        assert response.success == True
        assert '免责声明' in response.content

    async def test_department_recommender(self, result: TestResult):
        """测试科室推荐Skill"""
        from agent.medical_agent import SkillRequest, IntentType

        request = SkillRequest(
            skill_name="department-recommender",
            intent=IntentType.DEPARTMENT_QUERY,
            entities={"query": "头痛"},
            context=DialogueContext("test", "user"),
            metadata={}
        )

        response = await self.agent.skill_invoker.invoke(request)

        result.add_detail(f"响应成功: {response.success}")
        result.add_detail(f"响应包含科室: {'神经内科' in response.content or '科室' in response.content}")

        assert response.success == True

    async def test_medication_advisor(self, result: TestResult):
        """测试用药咨询Skill"""
        from agent.medical_agent import SkillRequest, IntentType

        request = SkillRequest(
            skill_name="medication-advisor",
            intent=IntentType.MEDICATION_CONSULT,
            entities={"drug_name": "阿莫西林", "query_type": "info"},
            context=DialogueContext("test", "user"),
            metadata={}
        )

        response = await self.agent.skill_invoker.invoke(request)

        result.add_detail(f"响应成功: {response.success}")
        result.add_detail(f"包含药品名: {'阿莫西林' in response.content}")
        result.add_detail(f"包含用法: {'用法' in response.content or '用量' in response.content}")

        assert response.success == True


# ============================================================
# 端到端测试
# ============================================================

class E2ETests:
    """端到端测试套件"""

    def __init__(self, agent: MedicalAgent):
        self.agent = agent
        self.suite = TestSuite("端到端测试")

    async def run_all(self) -> bool:
        """运行所有测试"""
        print("\n🧪 开始端到端测试...")

        self.suite.add_result(await run_test(
            self.test_complete_dialogue_flow, "完整对话流程"
        ))
        self.suite.add_result(await run_test(
            self.test_concurrent_sessions, "并发会话测试"
        ))
        self.suite.add_result(await run_test(
            self.test_error_handling, "错误处理测试"
        ))

        return self.suite.print_summary()

    async def test_complete_dialogue_flow(self, result: TestResult):
        """测试完整对话流程"""
        session_id = "test-e2e-flow"

        dialogues = [
            ("你好", "问候"),
            ("我头痛好几天了", "症状咨询"),
            ("头痛应该挂什么科", "科室查询"),
            ("阿莫西林怎么吃", "用药咨询"),
        ]

        for user_input, expected_type in dialogues:
            response = await self.agent.process(user_input, session_id=session_id)
            result.add_detail(f"✓ '{user_input}' -> {expected_type} (响应长度: {len(response)})")

        context = self.agent.get_context(session_id)
        result.add_detail(f"总对话轮数: {context.turn_count}")

        assert context.turn_count == len(dialogues)

    async def test_concurrent_sessions(self, result: TestResult):
        """测试并发会话"""
        sessions = ["session-1", "session-2", "session-3"]

        # 并发处理多个会话
        tasks = [
            self.agent.process("你好", session_id=s)
            for s in sessions
        ]

        responses = await asyncio.gather(*tasks)

        for i, (session, response) in enumerate(zip(sessions, responses)):
            result.add_detail(f"会话 {session}: 响应长度={len(response)}")

        # 验证每个会话独立
        for session in sessions:
            ctx = self.agent.get_context(session)
            result.add_detail(f"会话 {session} 轮数: {ctx.turn_count}")
            assert ctx.turn_count == 1

    async def test_error_handling(self, result: TestResult):
        """测试错误处理"""
        # 测试未知输入
        response = await self.agent.process(" xyzabc ")
        result.add_detail(f"未知输入响应: {len(response)} 字符")
        result.add_detail(f"包含提示: {'理解' in response or '换个说法' in response}")

        # 测试空输入
        response2 = await self.agent.process("")
        result.add_detail(f"空输入响应: {len(response2)} 字符")


# ============================================================
# 主测试运行器
# ============================================================

async def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("🏥 医疗智能助手 - 全面功能测试")
    print("="*70)

    # 初始化环境
    print("\n📦 初始化测试环境...")

    host = MCPFactory.create_host("test-mcp-host")
    await host.start()

    from mcp_tools.medical_tools import create_medical_mcp_server
    from mcp_protocol.mcp_protocol import MCPClient

    mcp_server = await create_medical_mcp_server(host)
    await mcp_server.start()

    mcp_client = MCPClient("test-agent-client", host)
    await mcp_client.start()

    agent = MedicalAgent(mcp_client=mcp_client)
    await agent.start()

    print("✓ 测试环境初始化完成")

    # 运行测试套件
    all_passed = True

    # MCP协议测试
    mcp_tests = MCPProtocolTests()
    all_passed &= await mcp_tests.run_all()

    # MCP工具测试
    tool_tests = MCPToolTests()
    all_passed &= await tool_tests.run_all()

    # Agent测试
    agent_tests = AgentTests(agent)
    all_passed &= await agent_tests.run_all()

    # 端到端测试
    e2e_tests = E2ETests(agent)
    all_passed &= await e2e_tests.run_all()

    # 清理
    print("\n🧹 清理测试环境...")
    await agent.stop()
    await mcp_client.stop()
    await mcp_server.stop()
    await host.stop()
    print("✓ 清理完成")

    # 总体结果
    print("\n" + "="*70)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("❌ 部分测试失败，请检查详细信息")
    print("="*70 + "\n")

    return all_passed


# ============================================================
# 单独运行测试
# ============================================================

async def run_mcp_tests_only():
    """仅运行MCP测试"""
    tests = MCPProtocolTests()
    await tests.run_all()


async def run_agent_tests_only():
    """仅运行Agent测试"""
    from agent.medical_agent import MedicalAgent
    from mcp_protocol.mcp_protocol import MCPClient

    # 使用mock MCP client
    agent = MedicalAgent(mcp_client=None)
    await agent.start()

    tests = AgentTests(agent)
    await tests.run_all()

    await agent.stop()


async def run_e2e_demo():
    """Run end-to-end demo"""
    from agent.medical_agent import MedicalAgent
    from mcp_protocol.mcp_protocol import MCPClient, MCPFactory
    from mcp_tools.medical_tools import create_medical_mcp_server

    print("\n" + "="*70)
    print("[Medical AI Assistant] End-to-End Demo")
    print("="*70 + "\n")

    # Initialize
    host = MCPFactory.create_host("demo-mcp-host")
    await host.start()

    mcp_server = await create_medical_mcp_server(host)
    await mcp_server.start()

    mcp_client = MCPClient("demo-client", host)
    await mcp_client.start()

    agent = MedicalAgent(mcp_client=mcp_client)
    await agent.start()

    # Demo dialogues
    demo_dialogues = [
        "Hello",
        "I have a headache for several days",
        "Which department should I visit?",
        "How to take amoxicillin?",
        "How to prevent high blood pressure?"
    ]

    for user_input in demo_dialogues:
        print(f"[User] {user_input}")
        response = await agent.process(user_input, session_id="demo-session")
        print(f"[Agent] {response[:200]}...")
        print("-" * 70)
        await asyncio.sleep(0.5)

    # Cleanup
    await agent.stop()
    await mcp_client.stop()
    await mcp_server.stop()
    await host.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="医疗智能助手测试")
    parser.add_argument("--suite", choices=["all", "mcp", "agent", "demo"],
                        default="all", help="测试套件")
    args = parser.parse_args()

    if args.suite == "all":
        asyncio.run(run_all_tests())
    elif args.suite == "mcp":
        asyncio.run(run_mcp_tests_only())
    elif args.suite == "agent":
        asyncio.run(run_agent_tests_only())
    elif args.suite == "demo":
        asyncio.run(run_e2e_demo())
