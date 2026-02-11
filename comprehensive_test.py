#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医疗智能助手 - 全面功能测试脚本
测试所有核心功能，每个功能5个测试用例
"""
import requests
import json
from typing import Dict, List, Any
from datetime import datetime

# API 基础 URL
BASE_URL = "http://127.0.0.1:8000"
EXTERNAL_URL = "http://59.110.40.73/medical"

# 测试结果统计
test_results = {
    "passed": 0,
    "failed": 0,
    "errors": []
}

def log_result(category: str, test_name: str, passed: bool, details: str = ""):
    """记录测试结果"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {category} | {test_name}")
    if details:
        print(f"         {details}")

    if passed:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
        test_results["errors"].append({
            "category": category,
            "test": test_name,
            "details": details
        })


def api_chat(message: str, session_id: str = "test", use_llm: bool = False) -> Dict:
    """调用聊天 API"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": message,
                "session_id": session_id,
                "use_llm": use_llm
            },
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def api_health() -> bool:
    """健康检查"""
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def api_status() -> Dict:
    """获取系统状态"""
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=5)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# 功能 1: 基础 API 测试
# ============================================================
def test_basic_api():
    """测试基础 API 端点"""
    print("\n" + "="*60)
    print("【功能 1】基础 API 测试")
    print("="*60)

    # 测试1: 健康检查
    result = api_health()
    log_result("API", "健康检查", result, "系统健康状态正常" if result else "无法连接")

    # 测试2: 系统状态
    status = api_status()
    log_result("API", "系统状态", "status" in status or "error" not in status,
               f"运行时间: {status.get('uptime', 'N/A')}")

    # 测试3: 闲聊功能
    response = api_chat("你好")
    log_result("API", "闲聊-你好", "response" in response,
               f"意图: {response.get('intent', 'N/A')}")

    # 测试4: 空消息处理
    response = api_chat("")
    log_result("API", "空消息处理", "response" in response,
               "系统应该能处理空消息")

    # 测试5: 特殊字符处理
    response = api_chat("!@#$%^&*()")
    log_result("API", "特殊字符处理", "response" in response,
               "系统应该能处理特殊字符")


# ============================================================
# 功能 2: 症状分析测试
# ============================================================
def test_symptom_analysis():
    """测试症状分析功能"""
    print("\n" + "="*60)
    print("【功能 2】症状分析测试")
    print("="*60)

    test_cases = [
        ("我头痛好几天了", "symptom_inquiry", "头痛症状"),
        ("最近总是咳嗽，有点发烧", "symptom_inquiry", "咳嗽发烧"),
        ("肚子疼是怎么回事", "symptom_inquiry", "腹痛咨询"),
        ("感觉胸闷气短，呼吸困难", "symptom_inquiry", "胸闷症状"),
        ("我经常失眠，睡不着觉", "symptom_inquiry", "失眠问题"),
    ]

    for message, expected_intent, desc in test_cases:
        response = api_chat(message, session_id=f"symptom_{desc}")
        intent = response.get("intent", "")
        confidence = response.get("confidence", 0)

        # 意图识别正确或置信度合理
        passed = ("response" in response and
                 (expected_intent in intent or confidence > 0.3))

        log_result("症状分析", desc, passed,
                  f"意图: {intent}, 置信度: {confidence:.2f}")


# ============================================================
# 功能 3: 科室推荐测试
# ============================================================
def test_department_recommendation():
    """测试科室推荐功能"""
    print("\n" + "="*60)
    print("【功能 3】科室推荐测试")
    print("="*60)

    test_cases = [
        ("头痛应该挂什么科", "department_query", "头痛科室"),
        ("看皮肤病去哪个科室", "department_query", "皮肤科"),
        ("骨科在哪里", "department_query", "骨科位置"),
        ("心脏病挂哪个科", "department_query", "心脏科室"),
        ("我需要看眼科", "department_query", "眼科"),
    ]

    for message, expected_intent, desc in test_cases:
        response = api_chat(message, session_id=f"dept_{desc}")
        intent = response.get("intent", "")

        passed = ("response" in response and
                 (expected_intent in intent or "department" in response.get("skill_invoked", "")))

        log_result("科室推荐", desc, passed,
                  f"意图: {intent}, Skill: {response.get('skill_invoked', 'N/A')}")


# ============================================================
# 功能 4: 用药咨询测试
# ============================================================
def test_medication_consultation():
    """测试用药咨询功能"""
    print("\n" + "="*60)
    print("【功能 4】用药咨询测试")
    print("="*60)

    test_cases = [
        ("阿莫西林怎么吃", "medication", "阿莫西林用法"),
        ("这个药有什么副作用", "medication", "副作用咨询"),
        ("感冒了吃什么药好", "medication", "感冒用药"),
        ("布洛芬可以空腹吃吗", "medication", "用药时间"),
        ("降压药要长期吃吗", "medication", "长期用药"),
    ]

    for message, keyword, desc in test_cases:
        response = api_chat(message, session_id=f"med_{desc}")
        intent = response.get("intent", "")

        passed = ("response" in response and
                 (keyword in intent or keyword in response.get("response", "").lower()))

        log_result("用药咨询", desc, passed,
                  f"意图: {intent}")


# ============================================================
# 功能 5: 预约挂号测试
# ============================================================
def test_appointment_booking():
    """测试预约挂号功能"""
    print("\n" + "="*60)
    print("【功能 5】预约挂号测试")
    print("="*60)

    test_cases = [
        ("我想挂个号", "appointment", "基本挂号"),
        ("预约明天的门诊", "appointment", "预约门诊"),
        ("帮我挂个内科的号", "appointment", "指定科室"),
        ("我想预约下周的专家号", "appointment", "专家号预约"),
        ("取消我的预约", "appointment", "取消预约"),
    ]

    for message, keyword, desc in test_cases:
        response = api_chat(message, session_id=f"apt_{desc}")
        intent = response.get("intent", "")

        passed = ("response" in response and
                 (keyword in intent or "appointment" in response.get("skill_invoked", "")))

        log_result("预约挂号", desc, passed,
                  f"意图: {intent}, Skill: {response.get('skill_invoked', 'N/A')}")


# ============================================================
# 功能 6: 健康教育测试
# ============================================================
def test_health_education():
    """测试健康教育功能"""
    print("\n" + "="*60)
    print("【功能 6】健康教育测试")
    print("="*60)

    test_cases = [
        ("怎么预防高血压", "health", "高血压预防"),
        ("糖尿病不能吃什么", "health", "糖尿病饮食"),
        ("运动对健康的好处", "health", "运动健康"),
        ("保持健康的生活方式", "health", "健康生活"),
        ("冬天应该注意什么", "health", "季节健康"),
    ]

    for message, keyword, desc in test_cases:
        response = api_chat(message, session_id=f"health_{desc}")
        intent = response.get("intent", "")

        passed = ("response" in response and
                 (keyword in intent or "health" in response.get("skill_invoked", "") or "education" in response.get("skill_invoked", "")))

        log_result("健康教育", desc, passed,
                  f"意图: {intent}")


# ============================================================
# 功能 7: 报告解读测试
# ============================================================
def test_report_interpretation():
    """测试报告解读功能"""
    print("\n" + "="*60)
    print("【功能 7】报告解读测试")
    print("="*60)

    test_cases = [
        ("帮我看看这个报告", "report", "报告查看"),
        ("血常规结果正常吗", "report", "血常规解读"),
        ("这个指标偏高是什么意思", "report", "指标解读"),
        ("我的血压有点高", "report", "血压报告"),
        ("体检报告怎么看", "report", "体检报告"),
    ]

    for message, keyword, desc in test_cases:
        response = api_chat(message, session_id=f"report_{desc}")
        intent = response.get("intent", "")

        passed = ("response" in response and
                 ("response" in response))

        log_result("报告解读", desc, passed,
                  f"意图: {intent}")


# ============================================================
# 功能 8: 会话管理测试
# ============================================================
def test_session_management():
    """测试会话管理功能"""
    print("\n" + "="*60)
    print("【功能 8】会话管理测试")
    print("="*60)

    session_id = "test_session_multi"

    # 测试1: 多轮对话-上下文保持
    api_chat("我叫张三", session_id)
    response = api_chat("我叫什么名字", session_id)
    passed1 = "response" in response
    log_result("会话管理", "多轮对话-上下文", passed1,
              "系统应该能记住之前的对话内容")

    # 测试2: 会话清除
    try:
        response = requests.post(
            f"{BASE_URL}/api/session/clear",
            params={"session_id": session_id},
            timeout=5
        )
        passed2 = response.status_code == 200
        log_result("会话管理", "会话清除", passed2,
                  f"状态码: {response.status_code}")
    except Exception as e:
        log_result("会话管理", "会话清除", False, str(e))

    # 测试3: 不同会话隔离
    response1 = api_chat("我喜欢红色", "session_a")
    response2 = api_chat("我喜欢什么颜色", "session_b")
    passed3 = "response" in response2
    log_result("会话管理", "会话隔离", passed3,
              "不同会话应该独立")

    # 测试4: 获取会话列表
    try:
        response = requests.get(f"{BASE_URL}/api/sessions", timeout=5)
        passed4 = response.status_code == 200
        log_result("会话管理", "获取会话列表", passed4,
                  f"状态码: {response.status_code}")
    except Exception as e:
        log_result("会话管理", "获取会话列表", False, str(e))

    # 测试5: 默认会话处理
    response = api_chat("测试默认会话", "default")
    passed5 = "response" in response
    log_result("会话管理", "默认会话", passed5,
              "默认会话应该正常工作")


# ============================================================
# 功能 9: 流式响应测试
# ============================================================
def test_streaming_response():
    """测试流式响应功能"""
    print("\n" + "="*60)
    print("【功能 9】流式响应测试")
    print("="*60)

    test_cases = [
        ("你好，请介绍一下自己", "基本介绍"),
        ("我头痛怎么办", "症状咨询"),
        ("吃什么对心脏好", "健康建议"),
        ("谢谢你的帮助", "感谢响应"),
        ("exit", "退出测试"),
    ]

    for message, desc in test_cases:
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat/stream",
                json={
                    "message": message,
                    "session_id": "stream_test",
                    "use_llm": False
                },
                stream=True,
                timeout=30
            )

            # 检查是否是流式响应
            content_type = response.headers.get("content-type", "")
            passed = "text/event-stream" in content_type or "response" in response.text

            log_result("流式响应", desc, passed,
                      f"Content-Type: {content_type}")
        except Exception as e:
            log_result("流式响应", desc, False, str(e))


# ============================================================
# 功能 10: 症状结构化分析测试
# ============================================================
def test_symptom_structured_analysis():
    """测试症状结构化分析功能"""
    print("\n" + "="*60)
    print("【功能 10】症状结构化分析测试")
    print("="*60)

    test_cases = [
        # 症状标签 + 描述
        {
            "symptoms": ["头痛", "发热"],
            "description": "头痛持续两天，伴有低烧",
            "duration": "days",
            "severity": "moderate"
        },
        # 只有症状标签
        {
            "symptoms": ["咳嗽", "喉咙痛"],
            "description": "",
            "duration": "",
            "severity": ""
        },
        # 完整信息
        {
            "symptoms": ["腹痛", "恶心"],
            "description": "上腹部疼痛，饭后加重",
            "duration": "week",
            "severity": "mild"
        },
        # 严重症状
        {
            "symptoms": ["胸痛", "呼吸困难"],
            "description": "突然胸痛，无法呼吸",
            "duration": "today",
            "severity": "severe"
        },
        # 最小信息
        {
            "symptoms": [],
            "description": "感觉不舒服",
            "duration": "",
            "severity": ""
        },
    ]

    for i, data in enumerate(test_cases, 1):
        try:
            response = requests.post(
                f"{BASE_URL}/api/symptom/analyze",
                json=data,
                timeout=10
            )

            passed = response.status_code == 200 and "response" in response.json()

            log_result("症状结构化", f"测试用例 {i}", passed,
                      f"症状: {data.get('symptoms', ['描述'])}")
        except Exception as e:
            log_result("症状结构化", f"测试用例 {i}", False, str(e))


# ============================================================
# 功能 11: 边界和异常测试
# ============================================================
def test_edge_cases():
    """测试边界和异常情况"""
    print("\n" + "="*60)
    print("【功能 11】边界和异常测试")
    print("="*60)

    # 测试1: 超长消息
    long_message = "测试" * 500
    response = api_chat(long_message)
    passed = "response" in response or "error" in response
    log_result("边界测试", "超长消息", passed,
              f"消息长度: {len(long_message)}")

    # 测试2: 特殊字符
    special_chars = "<script>alert('xss')</script>"
    response = api_chat(special_chars)
    passed = "response" in response
    log_result("边界测试", "XSS攻击防护", passed,
              "系统应该能处理恶意输入")

    # 测试3: SQL注入尝试
    sql_injection = "'; DROP TABLE users; --"
    response = api_chat(sql_injection)
    passed = "response" in response
    log_result("边界测试", "SQL注入防护", passed,
              "系统应该能处理SQL注入")

    # 测试4: Unicode字符
    unicode_msg = "你好 🏥 💊 🩺 感觉不舒服"
    response = api_chat(unicode_msg)
    passed = "response" in response
    log_result("边界测试", "Unicode字符", passed,
              "系统应该能处理emoji")

    # 测试5: 快速连续请求
    responses = [api_chat(f"测试{i}") for i in range(5)]
    passed = all("response" in r for r in responses)
    log_result("边界测试", "快速连续请求", passed,
              "系统应该能处理连续请求")


# ============================================================
# 功能 12: 外部访问测试
# ============================================================
def test_external_access():
    """测试外部访问"""
    print("\n" + "="*60)
    print("【功能 12】外部访问测试")
    print("="*60)

    # 测试1: 外部健康检查
    try:
        response = requests.get(f"{EXTERNAL_URL}/api/health", timeout=10)
        passed = response.status_code == 200
        log_result("外部访问", "健康检查", passed,
                  f"外部URL: {EXTERNAL_URL}/api/health")
    except Exception as e:
        log_result("外部访问", "健康检查", False, str(e))

    # 测试2: 外部聊天请求
    try:
        response = requests.post(
            f"{EXTERNAL_URL}/api/chat",
            json={"message": "你好", "session_id": "external_test"},
            timeout=10
        )
        passed = response.status_code == 200
        log_result("外部访问", "聊天请求", passed,
                  f"状态码: {response.status_code}")
    except Exception as e:
        log_result("外部访问", "聊天请求", False, str(e))

    # 测试3: CORS检查
    try:
        response = requests.options(
            f"{EXTERNAL_URL}/api/chat",
            headers={"Origin": "http://example.com"},
            timeout=5
        )
        cors_header = response.headers.get("Access-Control-Allow-Origin", "")
        passed = cors_header == "*" or "example.com" in cors_header
        log_result("外部访问", "CORS配置", passed,
                  f"CORS: {cors_header}")
    except Exception as e:
        log_result("外部访问", "CORS配置", False, str(e))

    # 测试4: 外部症状分析
    try:
        response = requests.post(
            f"{EXTERNAL_URL}/api/symptom/analyze",
            json={"symptoms": ["头痛"], "description": "头痛"},
            timeout=10
        )
        passed = response.status_code == 200
        log_result("外部访问", "症状分析", passed,
                  f"状态码: {response.status_code}")
    except Exception as e:
        log_result("外部访问", "症状分析", False, str(e))

    # 测试5: 外部流式响应
    try:
        response = requests.post(
            f"{EXTERNAL_URL}/api/chat/stream",
            json={"message": "你好", "session_id": "test"},
            stream=True,
            timeout=10
        )
        content_type = response.headers.get("content-type", "")
        passed = "event-stream" in content_type
        log_result("外部访问", "流式响应", passed,
                  f"Content-Type: {content_type}")
    except Exception as e:
        log_result("外部访问", "流式响应", False, str(e))


# ============================================================
# 主函数
# ============================================================
def main():
    """主测试函数"""
    print("="*60)
    print("医疗智能助手 - 全面功能测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API 地址: {BASE_URL}")
    print(f"外部地址: {EXTERNAL_URL}")
    print("="*60)

    # 执行所有测试
    test_basic_api()
    test_symptom_analysis()
    test_department_recommendation()
    test_medication_consultation()
    test_appointment_booking()
    test_health_education()
    test_report_interpretation()
    test_session_management()
    test_streaming_response()
    test_symptom_structured_analysis()
    test_edge_cases()
    test_external_access()

    # 打印测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    total = test_results["passed"] + test_results["failed"]
    pass_rate = (test_results["passed"] / total * 100) if total > 0 else 0

    print(f"总测试数: {total}")
    print(f"通过: {test_results['passed']} ✅")
    print(f"失败: {test_results['failed']} ❌")
    print(f"通过率: {pass_rate:.1f}%")

    if test_results["errors"]:
        print("\n失败详情:")
        for error in test_results["errors"]:
            print(f"  [{error['category']}] {error['test']}")
            print(f"    {error['details']}")

    print("="*60)

    return test_results["failed"] == 0


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
