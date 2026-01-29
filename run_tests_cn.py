# -*- coding: utf-8 -*-
"""
Full functional test for Medical AI Assistant (Chinese)
"""
import asyncio
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_protocol.mcp_protocol import MCPFactory, MCPClient
from mcp_tools.medical_tools import create_medical_mcp_server
from agent.medical_agent import MedicalAgent, IntentType, DialogueContext


async def test_mcp_tools():
    """Test MCP tools"""
    print("=" * 60)
    print("MCP Tools Test")
    print("=" * 60)

    from mcp_tools.medical_tools import (
        MedicalKnowledgeHandler,
        HospitalDepartmentHandler,
        DrugDatabaseHandler,
        AppointmentBookingHandler
    )

    # Test 1: Medical Knowledge
    print("\n[TEST 1] Medical Knowledge Query")
    handler = MedicalKnowledgeHandler()
    result = await handler.execute({
        "query_type": "symptom",
        "keyword": "头痛"
    })
    print(f"Success: {result.get('success')}")
    if result.get('success'):
        data = result.get('data', {})
        print(f"Description exists: {bool(data.get('description'))}")
        print(f"Common causes: {len(data.get('common_causes', []))} items")
        print(f"Red flags: {len(data.get('red_flags', []))} items")
        print(f"Department: {data.get('department', 'N/A')}")
    assert result.get('success') == True
    print("Status: PASS")

    # Test 2: Hospital Department
    print("\n[TEST 2] Hospital Department Query")
    handler = HospitalDepartmentHandler()
    result = await handler.execute({
        "query_type": "by_symptom",
        "symptom": "头痛"
    })
    print(f"Success: {result.get('success')}")
    if result.get('success'):
        print(f"Recommendations: {len(result.get('recommendations', []))} items")
    assert result.get('success') == True
    print("Status: PASS")

    # Test 3: Drug Database
    print("\n[TEST 3] Drug Database Query")
    handler = DrugDatabaseHandler()
    result = await handler.execute({
        "query_type": "info",
        "drug_name": "阿莫西林"
    })
    print(f"Success: {result.get('success')}")
    if result.get('success'):
        info = result.get('info', {})
        print(f"Category: {info.get('category', 'N/A')}")
    assert result.get('success') == True
    print("Status: PASS")

    # Test 4: Appointment Booking
    print("\n[TEST 4] Appointment Booking")
    handler = AppointmentBookingHandler()
    result = await handler.execute({
        "action": "list_departments"
    })
    print(f"Success: {result.get('success')}")
    if result.get('success'):
        depts = result.get('departments', [])
        print(f"Departments: {len(depts)} items")
    assert result.get('success') == True
    print("Status: PASS")


async def test_intent_classification():
    """Test intent classification"""
    print("\n" + "=" * 60)
    print("Intent Classification Test")
    print("=" * 60)

    from agent.medical_agent import IntentClassifier

    classifier = IntentClassifier()

    test_cases = [
        ("我头痛好几天了", IntentType.SYMPTOM_INQUIRY),
        ("头痛挂什么科", IntentType.DEPARTMENT_QUERY),
        ("阿莫西林怎么吃", IntentType.MEDICATION_CONSULT),
        ("我想挂个号", IntentType.APPOINTMENT),
        ("怎么预防高血压", IntentType.HEALTH_EDUCATION),
        ("你好", IntentType.GREETING),
    ]

    correct = 0
    for text, expected in test_cases:
        result = await classifier.classify(text, DialogueContext("test", "user"))
        status = "PASS" if result.intent == expected else "FAIL"
        if result.intent == expected:
            correct += 1
        print(f"[{status}] '{text}' -> {result.intent.value} ({result.confidence:.2f})")

    accuracy = correct / len(test_cases) * 100
    print(f"\nAccuracy: {accuracy:.1f}% ({correct}/{len(test_cases)})")
    assert accuracy >= 80, "Intent classification accuracy too low"
    print("Status: PASS")


async def test_agent():
    """Test Agent"""
    print("\n" + "=" * 60)
    print("Agent Test")
    print("=" * 60)

    # Initialize
    host = MCPFactory.create_host("test-mcp-host")
    await host.start()
    print("Host started")

    mcp_server = await create_medical_mcp_server(host)
    await mcp_server.start()
    print(f"MCP Server started with {len(host.tools)} tools")

    mcp_client = MCPClient("test-client", host)
    await mcp_client.start()
    print("MCP Client started")

    agent = MedicalAgent(mcp_client=mcp_client)
    await agent.start()
    print("Agent started")

    # Test dialogues
    dialogues = [
        "你好",
        "我头痛好几天了",
        "头痛挂什么科",
        "阿莫西林怎么吃",
    ]

    print("\nProcessing test dialogues:")
    for i, user_input in enumerate(dialogues, 1):
        response = await agent.process(user_input, session_id="test-session")
        print(f"\n[{i}] User: {user_input}")
        print(f"    Response length: {len(response)} chars")
        print(f"    Has disclaimer: {'disclaimer' in response or 'disclaimer' in response.lower() or '免责' in response or '声明' in response}")

    # Check context
    context = agent.get_context("test-session")
    print(f"\nDialogue turns: {context.turn_count}")
    assert context.turn_count == len(dialogues)

    # Cleanup
    await agent.stop()
    await mcp_client.stop()
    await mcp_server.stop()
    await host.stop()
    print("\nStatus: PASS")


async def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Medical AI Assistant - Full Test Suite")
    print("=" * 60)

    try:
        await test_mcp_tools()
        await test_intent_classification()
        await test_agent()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
