#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医疗智能助手 - 页面跳转功能全面测试
测试每个功能页面的跳转是否正常工作
"""

import requests
import json
import time
from typing import Dict, List, Tuple

# API 配置
BASE_URL = "http://127.0.0.1:8000"
EXTERNAL_URL = "http://59.110.40.73/medical"

# 页面映射
PAGE_MAPPING = {
    "symptom_inquiry": {"page_id": "page-symptom", "page_name": "症状咨询", "icon": "🔍"},
    "department_query": {"page_id": "page-department", "page_name": "科室推荐", "icon": "🏥"},
    "medication_consult": {"page_id": "page-medication", "page_name": "用药咨询", "icon": "💊"},
    "appointment": {"page_id": "page-appointment", "page_name": "预约挂号", "icon": "📅"},
    "health_education": {"page_id": "page-health", "page_name": "健康教育", "icon": "📚"},
    "report_interpret": {"page_id": "page-report", "page_name": "报告解读", "icon": "📋"},
    "my_appointment": {"page_id": "page-myappointment", "page_name": "预约查询", "icon": "📋"},
    "followup": {"page_id": "page-followup", "page_name": "随访管理", "icon": "📝"},
    "records": {"page_id": "page-records", "page_name": "治疗档案", "icon": "📂"},
}

# 测试用例定义
TEST_CASES = [
    # 症状咨询页面
    {
        "page": "症状咨询",
        "page_id": "page-symptom",
        "tests": [
            "我头痛好几天了，感觉很难受",
            "最近总是咳嗽，有点发烧",
            "感觉胸闷气短，呼吸不畅"
        ]
    },
    # 科室推荐页面
    {
        "page": "科室推荐",
        "page_id": "page-department",
        "tests": [
            "头痛应该挂什么科",
            "看皮肤病去哪个科室",
            "心脏病挂哪个科"
        ]
    },
    # 用药咨询页面
    {
        "page": "用药咨询",
        "page_id": "page-medication",
        "tests": [
            "阿莫西林怎么吃",
            "这个药有什么副作用",
            "感冒了吃什么药好"
        ]
    },
    # 预约挂号页面
    {
        "page": "预约挂号",
        "page_id": "page-appointment",
        "tests": [
            "我想挂个号",
            "预约明天的门诊",
            "帮我挂个内科的号"
        ]
    },
    # 健康教育页面
    {
        "page": "健康教育",
        "page_id": "page-health",
        "tests": [
            "怎么预防高血压",
            "糖尿病不能吃什么",
            "运动对健康的好处"
        ]
    },
    # 报告解读页面
    {
        "page": "报告解读",
        "page_id": "page-report",
        "tests": [
            "帮我看看这个报告",
            "血常规结果正常吗",
            "这个指标偏高是什么意思"
        ]
    },
    # 预约查询页面
    {
        "page": "预约查询",
        "page_id": "page-myappointment",
        "tests": [
            "我想查询我的预约",
            "查看我的挂号记录",
            "我的预约状态是什么"
        ]
    },
    # 随访管理页面
    {
        "page": "随访管理",
        "page_id": "page-followup",
        "tests": [
            "我要添加随访记录",
            "查看患者随访情况",
            "预约随访时间"
        ]
    },
    # 治疗档案页面
    {
        "page": "治疗档案",
        "page_id": "page-records",
        "tests": [
            "我要查看我的病历",
            "我的治疗档案在哪里",
            "查询就诊记录"
        ]
    },
]


def test_chat_api(message: str) -> Dict:
    """测试聊天 API"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": message, "session_id": f"test_{int(time.time())}", "use_llm": False},
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def test_stream_api(message: str) -> Dict:
    """测试流式 API 中的页面推荐事件"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat/stream",
            json={"message": message, "session_id": f"test_{int(time.time())}", "use_llm": False},
            stream=True,
            timeout=10
        )

        # 读取所有事件
        events = []
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    try:
                        event = json.loads(line[6:])
                        events.append(event)
                    except:
                        pass

        # 查找 page_suggestion 事件
        for event in events:
            if event.get('type') == 'page_suggestion':
                return {"has_suggestion": True, "page_info": event.get('page_info')}

        return {"has_suggestion": False, "page_info": None, "events_count": len(events)}
    except Exception as e:
        return {"error": str(e)}


def run_comprehensive_test():
    """运行全面测试"""
    print("=" * 80)
    print("医疗智能助手 - 页面跳转功能全面测试")
    print("=" * 80)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API 地址: {BASE_URL}")
    print(f"外部地址: {EXTERNAL_URL}")
    print("=" * 80)

    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    issues = []

    for page_config in TEST_CASES:
        page_name = page_config["page"]
        page_id = page_config["page_id"]
        tests = page_config["tests"]

        print(f"\n{'=' * 80}")
        print(f"📄 测试页面: {page_name} ({page_id})")
        print(f"{'=' * 80}")

        page_passed = 0
        page_failed = 0

        for i, test_message in enumerate(tests, 1):
            total_tests += 1
            print(f"\n  测试 {i}/3: \"{test_message}\"")
            print("-" * 60)

            # 测试流式 API
            stream_result = test_stream_api(test_message)

            if "error" in stream_result:
                print(f"  ❌ 错误: {stream_result['error']}")
                page_failed += 1
                failed_tests += 1
                issues.append({
                    "page": page_name,
                    "test": test_message,
                    "error": stream_result['error']
                })
                continue

            has_suggestion = stream_result.get("has_suggestion", False)
            page_info = stream_result.get("page_info")

            # 验证结果
            expected_page_id = page_id
            actual_page_id = page_info.get("page_id") if page_info else None

            if has_suggestion and actual_page_id == expected_page_id:
                print(f"  ✅ PASS - 正确推荐页面")
                print(f"     页面ID: {actual_page_id}")
                print(f"     页面名称: {page_info.get('page_name')}")
                print(f"     页面图标: {page_info.get('page_icon')}")
                print(f"     描述: {page_info.get('description')}")
                page_passed += 1
                passed_tests += 1
            elif has_suggestion:
                print(f"  ⚠️  部分匹配 - 推荐了其他页面")
                print(f"     期望: {expected_page_id}")
                print(f"     实际: {actual_page_id}")
                page_failed += 1
                failed_tests += 1
                issues.append({
                    "page": page_name,
                    "test": test_message,
                    "error": f"页面不匹配: 期望 {expected_page_id}, 实际 {actual_page_id}"
                })
            else:
                print(f"  ❌ FAIL - 无页面推荐")
                print(f"     事件数: {stream_result.get('events_count', 0)}")
                page_failed += 1
                failed_tests += 1
                issues.append({
                    "page": page_name,
                    "test": test_message,
                    "error": "无页面推荐"
                })

        # 页面汇总
        print(f"\n  📊 页面汇总: {page_name}")
        print(f"     通过: {page_passed}/3")
        print(f"     失败: {page_failed}/3")
        if page_passed == 3:
            print(f"     状态: ✅ 全部通过")
        elif page_passed > 0:
            print(f"     状态: ⚠️  部分通过")
        else:
            print(f"     状态: ❌ 全部失败")

    # 测试汇总
    print(f"\n{'=' * 80}")
    print("📊 测试汇总")
    print(f"{'=' * 80}")
    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests} ✅")
    print(f"失败: {failed_tests} ❌")
    print(f"通过率: {(passed_tests/total_tests*100):.1f}%")

    if issues:
        print(f"\n❌ 失败详情:")
        for issue in issues:
            print(f"  [{issue['page']}] \"{issue['test']}\"")
            print(f"    错误: {issue['error']}")

    print(f"{'=' * 80}")

    return failed_tests == 0


if __name__ == "__main__":
    import sys
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
