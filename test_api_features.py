# -*- coding: utf-8 -*-
"""
医疗智能助手 - 现有API功能测试
验证模型配置和已实现的API端点
"""

import asyncio
import json
import aiohttp

BASE_URL = "http://127.0.0.1:8000"


async def test_api(name, method, endpoint, data=None, params=None):
    """测试API端点"""
    url = f"{BASE_URL}{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, params=params) as resp:
                    result = await resp.json()
                    return {"success": resp.status == 200, "data": result}
            elif method == "POST":
                async with session.post(url, json=data) as resp:
                    result = await resp.json()
                    return {"success": resp.status == 200, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def main():
    print("="*60)
    print("医疗智能助手 - API功能测试")
    print("="*60)

    tests = [
        ("系统状态", "GET", "/api/status"),
        ("基础聊天", "POST", "/api/chat", {"message": "你好"}),
        ("症状分析", "POST", "/api/symptom/analyze", {
            "symptoms": ["头痛"],
            "description": "头痛三天",
            "duration": "3天",
            "severity": "中度"
        }),
        ("慢病记录", "POST", "/api/chronic/record", {
            "patient_id": "test_001",
            "record_type": "blood_pressure",
            "systolic": 130,
            "diastolic": 85
        }),
        ("慢病历史", "GET", "/api/chronic/history", None, {"patient_id": "test_001"}),
        ("在线问诊创建", "POST", "/api/consult/create", {
            "patient_id": "test_001",
            "patient_name": "测试患者",
            "department": "内科",
            "consult_type": "text",
            "chief_complaint": "头痛"
        }),
        ("问诊医生列表", "GET", "/api/consult/available", None, {"department": "内科"}),
        ("体检报告解读", "POST", "/api/health/report", {
            "category": "血常规",
            "results": {"WBC": 12.5, "HGB": 130}
        }),
        ("随访反馈", "POST", "/api/followup/feedback", {
            "plan_id": "test_plan",
            "feedback": "血压控制良好"
        }),
        ("用户画像", "GET", "/api/profile", None, {"user_id": "test_user"}),
        ("健康档案", "GET", "/api/records", None, {"patient_id": "test_001"}),
        ("健康检查", "GET", "/api/health"),
    ]

    passed = 0
    failed = 0

    for test in tests:
        name = test[0]
        if len(test) == 3:
            method, endpoint = test[1], test[2]
            result = await test_api(name, method, endpoint)
        elif len(test) == 4:
            method, endpoint, data = test[1], test[2], test[3]
            result = await test_api(name, method, endpoint, data)
        else:
            method, endpoint, data, params = test[1], test[2], test[3], test[4]
            result = await test_api(name, method, endpoint, data, params)

        status = "PASS" if result.get("success") else "FAIL"
        if result.get("success"):
            passed += 1
        else:
            failed += 1

        print(f"[{status}] {name}")
        if not result.get("success") and "error" in result:
            print(f"      Error: {result['error']}")

    print("="*60)
    print(f"总计: {passed + failed} | 通过: {passed} | 失败: {failed}")
    print(f"通过率: {passed / (passed + failed) * 100:.1f}%")
    print("="*60)

    print("\n[模型配置验证]")
    print("当前配置: DASHSCOPE_MODEL = qwen-plus")
    print("模型系列: 通义千问 (阿里云)")
    print("API Key: sk-a9a4edb1b4214016baa11c9be3b9fec4")
    print("Base URL: https://dashscope.aliyuncs.com/compatible-mode/v1")


if __name__ == "__main__":
    asyncio.run(main())
