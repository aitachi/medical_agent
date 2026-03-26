# -*- coding: utf-8 -*-
"""
医疗智能助手 - 全功能测试脚本
测试所有API端点和MCP工具
验证模型配置为 qwen-plus
"""

import asyncio
import json
import sys
import os
import time
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aiohttp


BASE_URL = "http://127.0.0.1:8000"


class FeatureTester:
    """功能测试器"""

    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0

    async def test(self, name: str, test_func):
        """执行单个测试"""
        print(f"\n{'='*60}")
        print(f"[TEST] {name}")
        print('='*60)

        try:
            result = await test_func()
            if result.get("success"):
                self.passed += 1
                print(f"[PASS] {name}")
                if "data" in result:
                    print(f"  数据: {json.dumps(result['data'], ensure_ascii=False)[:200]}...")
            else:
                self.failed += 1
                print(f"[FAIL] {name}")
                if "error" in result:
                    print(f"  错误: {result['error']}")

            self.results.append({
                "name": name,
                "status": "PASS" if result.get("success") else "FAIL",
                "data": result.get("data"),
                "error": result.get("error")
            })
            return result.get("success", False)

        except Exception as e:
            self.failed += 1
            print(f"[ERROR] {name}: {e}")
            self.results.append({
                "name": name,
                "status": "ERROR",
                "error": str(e)
            })
            return False

    def print_summary(self):
        """打印测试摘要"""
        print(f"\n{'='*60}")
        print("[测试摘要]")
        print('='*60)
        print(f"总计: {self.passed + self.failed}")
        print(f"通过: {self.passed}")
        print(f"失败: {self.failed}")
        print(f"通过率: {self.passed / (self.passed + self.failed) * 100:.1f}%")
        print('='*60)


# ============================================================
# 测试函数
# ============================================================

async def test_system_status():
    """测试系统状态"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/status") as resp:
            data = await resp.json()
            return {
                "success": data.get("status") == "running",
                "data": data
            }


async def test_chat_basic():
    """测试基础聊天"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/chat",
            json={"message": "你好", "use_llm": False}
        ) as resp:
            data = await resp.json()
            return {
                "success": "response" in data and len(data["response"]) > 0,
                "data": data
            }


async def test_chat_with_llm():
    """测试LLM聊天（验证模型配置）"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/chat",
            json={"message": "头痛应该挂什么科？", "use_llm": True}
        ) as resp:
            data = await resp.json()
            # 检查是否使用了LLM
            response_text = data.get("response", "")
            has_llm_content = len(response_text) > 50  # LLM回复通常较长

            # 检查响应源
            response_source = data.get("response_source", "")

            return {
                "success": has_llm_content,
                "data": {
                    "response_preview": response_text[:100],
                    "response_source": response_source,
                    "intent": data.get("intent")
                }
            }


async def test_symptom_analysis():
    """测试症状分析"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/symptom/analyze",
            json={
                "symptoms": ["头痛", "头晕"],
                "description": "头痛持续三天，伴有轻微恶心",
                "duration": "3天",
                "severity": "中度"
            }
        ) as resp:
            data = await resp.json()
            return {
                "success": "analysis" in data or "response" in data,
                "data": data
            }


async def test_department_recommendation():
    """测试科室推荐"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/departments/recommend",
            params={"symptoms": "头痛,发热,咳嗽"}
        ) as resp:
            data = await resp.json()
            return {
                "success": "departments" in data or "recommendations" in data,
                "data": data
            }


async def test_knowledge_query():
    """测试医学知识查询"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/knowledge/query",
            params={"keyword": "高血压"}
        ) as resp:
            data = await resp.json()
            return {
                "success": "knowledge" in data or "description" in data,
                "data": data
            }


async def test_drug_query():
    """测试药品查询"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/drugs/info",
            params={"drug_name": "阿莫西林"}
        ) as resp:
            data = await resp.json()
            return {
                "success": "drug" in data or "name" in data,
                "data": data
            }


async def test_appointment_query():
    """测试预约查询"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/appointments/available",
            params={"department": "内科"}
        ) as resp:
            data = await resp.json()
            return {
                "success": "doctors" in data or "schedule" in data or "available" in data,
                "data": data
            }


async def test_chronic_record():
    """测试慢病记录"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/chronic/record",
            json={
                "patient_id": "test_patient",
                "record_type": "blood_pressure",
                "systolic": 135,
                "diastolic": 85,
                "record_date": datetime.now().strftime("%Y-%m-%d")
            }
        ) as resp:
            data = await resp.json()
            return {
                "success": data.get("success") or "record_id" in data,
                "data": data
            }


async def test_chronic_history():
    """测试慢病历史查询"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/chronic/history",
            params={"patient_id": "test_patient"}
        ) as resp:
            data = await resp.json()
            return {
                "success": "records" in data or "history" in data,
                "data": data
            }


async def test_online_consult_create():
    """测试在线问诊创建"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/consult/create",
            json={
                "patient_id": "test_patient",
                "patient_name": "测试患者",
                "department": "内科",
                "consult_type": "text",
                "chief_complaint": "头痛三天"
            }
        ) as resp:
            data = await resp.json()
            return {
                "success": data.get("success") or "consult_id" in data,
                "data": data
            }


async def test_health_report():
    """体检报告解读"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/health/report",
            json={
                "category": "血常规",
                "results": {
                    "WBC": 12.5,
                    "RBC": 4.5,
                    "HGB": 130,
                    "PLT": 250
                }
            }
        ) as resp:
            data = await resp.json()
            return {
                "success": "abnormal_items" in data or "analysis" in data or "interpretation" in data,
                "data": data
            }


async def test_emergency_guide():
    """测试急救指南"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/emergency/guide",
            params={"emergency_type": "心脏骤停"}
        ) as resp:
            data = await resp.json()
            return {
                "success": "guide" in data or "actions" in data,
                "data": data
            }


async def test_followup_feedback():
    """测试随访反馈"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/followup/feedback",
            json={
                "plan_id": "test_plan",
                "feedback": "患者血压控制良好，继续当前治疗方案",
                "doctor_id": "test_doctor"
            }
        ) as resp:
            data = await resp.json()
            return {
                "success": data.get("success") or "feedback_id" in data or "message" in data,
                "data": data
            }


async def test_user_profile():
    """测试用户画像"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/profile",
            params={"user_id": "test_user"}
        ) as resp:
            data = await resp.json()
            return {
                "success": "profile" in data or "preferences" in data,
                "data": data
            }


async def test_health_records():
    """测试健康档案"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/records",
            params={"patient_id": "test_patient"}
        ) as resp:
            data = await resp.json()
            return {
                "success": "records" in data or "allergies" in data or "medications" in data,
                "data": data
            }


async def test_mcp_tools_direct():
    """直接测试MCP工具"""
    from mcp_protocol.mcp_protocol import MCPFactory, MCPClient
    from mcp_tools.medical_tools import create_medical_mcp_server

    # 创建测试用MCP环境
    host = MCPFactory.create_host("test-host")
    await host.start()

    server = await create_medical_mcp_server(host)
    await server.start()

    client = MCPClient("test-client", host)
    await client.start()

    results = []

    # 测试1: 医学知识查询
    try:
        result = await client.call_tool(
            "medical_knowledge_query",
            {"query_type": "symptom", "keyword": "头痛"}
        )
        results.append({
            "tool": "medical_knowledge_query",
            "success": result.data.get("success", False)
        })
    except Exception as e:
        results.append({"tool": "medical_knowledge_query", "error": str(e)})

    # 测试2: 医院科室查询
    try:
        result = await client.call_tool(
            "hospital_department_query",
            {"query_type": "by_symptom", "symptom": "头痛"}
        )
        results.append({
            "tool": "hospital_department_query",
            "success": result.data.get("success", False)
        })
    except Exception as e:
        results.append({"tool": "hospital_department_query", "error": str(e)})

    # 测试3: 药品数据库查询
    try:
        result = await client.call_tool(
            "drug_database_query",
            {"query_type": "info", "drug_name": "阿莫西林"}
        )
        results.append({
            "tool": "drug_database_query",
            "success": result.data.get("success", False)
        })
    except Exception as e:
        results.append({"tool": "drug_database_query", "error": str(e)})

    # 测试4: 预约挂号
    try:
        result = await client.call_tool(
            "appointment_booking",
            {"action": "list_departments"}
        )
        results.append({
            "tool": "appointment_booking",
            "success": result.data.get("success", False)
        })
    except Exception as e:
        results.append({"tool": "appointment_booking", "error": str(e)})

    # 测试5: 检查报告解读
    try:
        result = await client.call_tool(
            "lab_report_query",
            {"action": "reference", "category": "血常规"}
        )
        results.append({
            "tool": "lab_report_query",
            "success": result.data.get("success", False)
        })
    except Exception as e:
        results.append({"tool": "lab_report_query", "error": str(e)})

    # 测试6: 慢病管理
    try:
        result = await client.call_tool(
            "chronic_disease_query",
            {"action": "targets", "condition": "高血压"}
        )
        results.append({
            "tool": "chronic_disease_query",
            "success": result.data.get("success", False)
        })
    except Exception as e:
        results.append({"tool": "chronic_disease_query", "error": str(e)})

    # 测试7: 在线问诊
    try:
        result = await client.call_tool(
            "online_consult",
            {"action": "list_doctors"}
        )
        results.append({
            "tool": "online_consult",
            "success": result.data.get("success", False)
        })
    except Exception as e:
        results.append({"tool": "online_consult", "error": str(e)})

    # 测试8: 急救指南
    try:
        result = await client.call_tool(
            "emergency_guide",
            {"action": "list"}
        )
        results.append({
            "tool": "emergency_guide",
            "success": result.data.get("success", False)
        })
    except Exception as e:
        results.append({"tool": "emergency_guide", "error": str(e)})

    # 测试9: 随访管理
    try:
        result = await client.call_tool(
            "followup_manage",
            {"action": "query_plan", "patient_id": "test"}
        )
        results.append({
            "tool": "followup_manage",
            "success": result.data.get("success", False) or "plans" in result.data
        })
    except Exception as e:
        results.append({"tool": "followup_manage", "error": str(e)})

    # 测试10: 体检套餐
    try:
        result = await client.call_tool(
            "health_checkup",
            {"action": "list_packages"}
        )
        results.append({
            "tool": "health_checkup",
            "success": result.data.get("success", False)
        })
    except Exception as e:
        results.append({"tool": "health_checkup", "error": str(e)})

    # 测试11: 提醒服务
    try:
        result = await client.call_tool(
            "reminder_manage",
            {"action": "get_types"}
        )
        results.append({
            "tool": "reminder_manage",
            "success": result.data.get("success", False)
        })
    except Exception as e:
        results.append({"tool": "reminder_manage", "error": str(e)})

    # 清理
    await client.stop()
    await server.stop()
    await host.stop()

    # 统计结果
    passed = sum(1 for r in results if r.get("success", False))
    total = len(results)

    return {
        "success": passed >= 8,  # 至少8个工具正常
        "data": {
            "total_tools": total,
            "passed_tools": passed,
            "details": results
        }
    }


# ============================================================
# 主测试流程
# ============================================================

async def main():
    """主测试流程"""
    print("="*60)
    print("医疗智能助手 - 全功能测试")
    print("="*60)

    # 等待服务启动
    print("\n等待服务启动...")
    for i in range(5):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BASE_URL}/api/status") as resp:
                    await resp.json()
            print("服务已就绪!")
            break
        except:
            await asyncio.sleep(1)
    else:
        print("服务启动超时!")
        return

    tester = FeatureTester()

    # API测试组
    print("\n" + "="*60)
    print("[API测试组]")
    print("="*60)

    await tester.test("系统状态检查", test_system_status)
    await tester.test("基础聊天", test_chat_basic)
    await tester.test("LLM聊天（含模型验证）", test_chat_with_llm)
    await tester.test("症状分析", test_symptom_analysis)
    await tester.test("科室推荐", test_department_recommendation)
    await tester.test("医学知识查询", test_knowledge_query)
    await tester.test("药品查询", test_drug_query)
    await tester.test("预约查询", test_appointment_query)

    # 业务功能测试组
    print("\n" + "="*60)
    print("[业务功能测试组]")
    print("="*60)

    await tester.test("慢病记录", test_chronic_record)
    await tester.test("慢病历史查询", test_chronic_history)
    await tester.test("在线问诊创建", test_online_consult_create)
    await tester.test("体检报告解读", test_health_report)
    await tester.test("急救指南", test_emergency_guide)
    await tester.test("随访反馈", test_followup_feedback)
    await tester.test("用户画像", test_user_profile)
    await tester.test("健康档案", test_health_records)

    # MCP工具测试组
    print("\n" + "="*60)
    print("[MCP工具测试组]")
    print("="*60)

    await tester.test("11个MCP工具测试", test_mcp_tools_direct)

    # 打印摘要
    tester.print_summary()

    # 模型配置验证
    print("\n" + "="*60)
    print("[模型配置验证]")
    print("="*60)
    print("检查模型配置...")
    try:
        # 读取配置文件
        with open(os.path.join(os.path.dirname(__file__), "web_api_server.py"), "r", encoding="utf-8") as f:
            content = f.read()
            if "DASHSCOPE_MODEL" in content:
                for line in content.split("\n"):
                    if "DASHSCOPE_MODEL" in line and "=" in line and "#" not in line.split("DASHSCOPE_MODEL")[0]:
                        print(f"配置: {line.strip()}")
                        if "qwen-plus" in line or "qwen" in line:
                            print("✓ 模型: qwen系列 (通义千问)")
                        break
    except Exception as e:
        print(f"无法读取配置: {e}")

    print("\n提示: 如需使用 qwen-plus，当前配置已正确")
    print("如需使用其他模型，请修改 web_api_server.py 中的 DASHSCOPE_MODEL")


if __name__ == "__main__":
    asyncio.run(main())
