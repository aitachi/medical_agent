# -*- coding: utf-8 -*-
"""
Simple test runner for Medical AI Assistant
"""
import asyncio
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_protocol.mcp_protocol import MCPFactory, MCPClient
from mcp_tools.medical_tools import create_medical_mcp_server
from agent.medical_agent import MedicalAgent


async def run_quick_test():
    """Run a quick functional test"""

    print("=" * 60)
    print("Medical AI Assistant - Quick Test")
    print("=" * 60)

    # Step 1: Initialize MCP Host
    print("\n[1/5] Initializing MCP Host...")
    host = MCPFactory.create_host("test-mcp-host")
    await host.start()
    print("   Host started: " + host.host_id)

    # Step 2: Create and start MCP Server
    print("\n[2/5] Starting MCP Server...")
    mcp_server = await create_medical_mcp_server(host)
    await mcp_server.start()
    print("   Server started: medical-mcp-server")
    print("   Registered tools:")
    for tool_name in host.tools.keys():
        print(f"      - {tool_name}")

    # Step 3: Create MCP Client
    print("\n[3/5] Creating MCP Client...")
    mcp_client = MCPClient("test-agent-client", host)
    await mcp_client.start()
    print("   Client started")

    # Step 4: Create and start Agent
    print("\n[4/5] Starting Agent...")
    agent = MedicalAgent(mcp_client=mcp_client)
    await agent.start()
    print("   Agent started")

    # Step 5: Run test dialogues
    print("\n[5/5] Running test dialogues...")
    print("-" * 60)

    test_cases = [
        ("Hello", IntentType.GREETING),
        ("I have a headache", IntentType.SYMPTOM_INQUIRY),
        ("Which department for headache?", IntentType.DEPARTMENT_QUERY),
        ("How to take amoxicillin?", IntentType.MEDICATION_CONSULT),
    ]

    from agent.medical_agent import IntentType

    for user_input, expected_intent in test_cases:
        print(f"\nUser: {user_input}")

        # Classify intent
        intent_result = await agent.classifier.classify(
            user_input,
            agent.get_or_create_context("test-session", "test-user")
        )

        print(f"Intent: {intent_result.intent.value} (confidence: {intent_result.confidence:.2f})")
        print(f"Target Skill: {intent_result.target_skill}")
        print(f"Entities: {intent_result.entities}")

        # Process and get response
        response = await agent.process(user_input, session_id="test-session")
        print(f"Response: {response[:150]}...")

        # Verify intent
        if intent_result.intent == expected_intent:
            print("Status: PASS")
        else:
            print(f"Status: FAIL (expected: {expected_intent.value})")

        print("-" * 60)

    # Cleanup
    print("\n[Cleanup] Stopping services...")
    await agent.stop()
    await mcp_client.stop()
    await mcp_server.stop()
    await host.stop()
    print("All services stopped")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


async def test_mcp_tools():
    """Test MCP tools directly"""

    print("=" * 60)
    print("MCP Tools Direct Test")
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
        "keyword": "headache"
    })
    print(f"   Success: {result.get('success')}")
    if result.get('success'):
        data = result.get('data', {})
        print(f"   Description: {data.get('description', '')[:50]}...")
        print(f"   Common causes: {len(data.get('common_causes', []))} items")
        print(f"   Red flags: {len(data.get('red_flags', []))} items")

    # Test 2: Hospital Department
    print("\n[TEST 2] Hospital Department Query")
    handler = HospitalDepartmentHandler()
    result = await handler.execute({
        "query_type": "by_symptom",
        "symptom": "headache"
    })
    print(f"   Success: {result.get('success')}")
    if result.get('success'):
        for rec in result.get('recommendations', [])[:2]:
            print(f"   - {rec.get('symptom')}: {rec.get('department')}")

    # Test 3: Drug Database
    print("\n[TEST 3] Drug Database Query")
    handler = DrugDatabaseHandler()
    result = await handler.execute({
        "query_type": "info",
        "drug_name": "amoxicillin"
    })
    print(f"   Success: {result.get('success')}")
    if result.get('success'):
        info = result.get('info', {})
        print(f"   Category: {info.get('category', 'N/A')}")
        print(f"   Side effects: {len(info.get('side_effects', []))} items")

    # Test 4: Appointment Booking
    print("\n[TEST 4] Appointment Booking")
    handler = AppointmentBookingHandler()
    result = await handler.execute({
        "action": "list_departments"
    })
    print(f"   Success: {result.get('success')}")
    if result.get('success'):
        depts = result.get('departments', [])
        print(f"   Available departments: {depts}")

    print("\n" + "=" * 60)
    print("MCP Tools Test Complete!")
    print("=" * 60)


async def test_intent_classification():
    """Test intent classification"""

    print("=" * 60)
    print("Intent Classification Test")
    print("=" * 60)

    from agent.medical_agent import IntentClassifier, IntentType, DialogueContext

    classifier = IntentClassifier()

    test_cases = [
        ("I have a headache", IntentType.SYMPTOM_INQUIRY),
        ("Which department should I visit?", IntentType.DEPARTMENT_QUERY),
        ("How to take amoxicillin?", IntentType.MEDICATION_CONSULT),
        ("I want to make an appointment", IntentType.APPOINTMENT),
        ("How to prevent high blood pressure?", IntentType.HEALTH_EDUCATION),
        ("Hello", IntentType.GREETING),
    ]

    correct = 0
    for text, expected in test_cases:
        result = await classifier.classify(text, DialogueContext("test", "user"))
        status = "PASS" if result.intent == expected else "FAIL"
        if result.intent == expected:
            correct += 1
        print(f"\n[{status}] Input: {text}")
        print(f"   Expected: {expected.value}")
        print(f"   Got: {result.intent.value} (confidence: {result.confidence:.2f})")

    accuracy = correct / len(test_cases) * 100
    print("\n" + "=" * 60)
    print(f"Accuracy: {accuracy:.1f}% ({correct}/{len(test_cases)})")
    print("=" * 60)


async def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description="Medical AI Assistant Test Runner")
    parser.add_argument("--test", choices=["all", "mcp", "intent", "agent"],
                        default="all", help="Test to run")
    args = parser.parse_args()

    if args.test in ["all", "mcp"]:
        await test_mcp_tools()
        print()

    if args.test in ["all", "intent"]:
        await test_intent_classification()
        print()

    if args.test in ["all", "agent"]:
        await run_quick_test()


if __name__ == "__main__":
    asyncio.run(main())
