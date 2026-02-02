# -*- coding: utf-8 -*-
"""
全栈集成测试 - 前端后端联调测试
测试所有功能的正确命中和使用
"""

import asyncio
import sys
import os
import json
import requests
from datetime import datetime
from typing import Dict, List
import time
import subprocess
import signal

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FullStackIntegrationTester:
    """全栈集成测试器"""

    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.server_process = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "server_status": {},
            "api_tests": {},
            "intent_coverage": {},
            "functional_tests": {},
            "errors": []
        }

    def start_server(self):
        """启动Web服务器"""
        print("\n" + "=" * 70)
        print("启动Web服务器...")
        print("=" * 70)

        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        python_exe = r"C:\Users\ASUS\miniconda3\envs\agent\python.exe"
        server_script = os.path.join(project_root, "web_api_server.py")

        # 构建命令
        cmd_list = [python_exe, server_script, "--host", "127.0.0.1", "--port", "8000"]

        self.server_process = subprocess.Popen(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )

        # 等待服务器启动
        print("等待服务器启动...")
        for i in range(30):
            try:
                response = requests.get(f"{self.base_url}/api/health", timeout=1)
                if response.status_code == 200:
                    print(f"服务器已启动 (耗时: {(i+1)*0.5}秒)")
                    self.results["server_status"]["startup_time"] = f"{(i+1)*0.5}秒"
                    return True
            except:
                time.sleep(0.5)

        print("服务器启动超时")
        return False

    def stop_server(self):
        """停止Web服务器"""
        if self.server_process:
            print("\n停止服务器...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except:
                self.server_process.kill()
            print("服务器已停止")

    def test_health_check(self):
        """测试健康检查端点"""
        print("\n" + "-" * 70)
        print("测试1: 健康检查")
        print("-" * 70)

        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            data = response.json()

            print(f"状态: {data['status']}")
            print(f"运行时间: {data['uptime']}")
            print(f"时间戳: {data['timestamp']}")

            self.results["api_tests"]["health_check"] = {
                "status": "pass",
                "http_code": response.status_code
            }
            return True

        except Exception as e:
            print(f"失败: {e}")
            self.results["api_tests"]["health_check"] = {"status": "fail", "error": str(e)}
            self.results["errors"].append(f"健康检查失败: {e}")
            return False

    def test_system_status(self):
        """测试系统状态端点"""
        print("\n" + "-" * 70)
        print("测试2: 系统状态")
        print("-" * 70)

        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=5)
            data = response.json()

            print(f"服务状态: {data['status']}")
            print(f"运行时间: {data['uptime']}")
            print(f"活跃会话数: {data['active_sessions']}")
            print(f"总请求数: {data['total_requests']}")
            print(f"分类器类型: {data['classifier_type']}")

            self.results["api_tests"]["system_status"] = {
                "status": "pass",
                "http_code": response.status_code,
                "data": data
            }
            return True

        except Exception as e:
            print(f"失败: {e}")
            self.results["api_tests"]["system_status"] = {"status": "fail", "error": str(e)}
            self.results["errors"].append(f"系统状态失败: {e}")
            return False

    def test_chat_endpoint(self):
        """测试聊天端点"""
        print("\n" + "-" * 70)
        print("测试3: 聊天端点")
        print("-" * 70)

        test_cases = [
            ("问候测试", "你好", "greeting"),
            ("症状咨询", "我头痛好几天了", "symptom_inquiry"),
            ("科室查询", "头痛挂什么科", "department_query"),
            ("用药咨询", "阿莫西林怎么吃", "medication_consult"),
            ("健康教育", "怎么预防高血压", "health_education"),
            ("预约挂号", "我想挂号", "appointment"),
            ("复杂表达", "我最近一直咳嗽，而且有点发烧，应该挂什么科？", "symptom_inquiry"),
            ("模糊表达", "不舒服", "unknown"),
        ]

        results = {
            "total": len(test_cases),
            "pass": 0,
            "fail": 0,
            "details": []
        }

        intent_names = {
            "symptom_inquiry": "症状咨询",
            "department_query": "科室查询",
            "medication_consult": "用药咨询",
            "appointment": "预约挂号",
            "health_education": "健康教育",
            "greeting": "问候",
            "unknown": "未知"
        }

        for name, message, expected_intent in test_cases:
            try:
                time.sleep(0.2)  # Add delay between requests
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json={"message": message, "session_id": "test_session", "user_id": "test_user"},
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    detected_intent = data.get('intent', '')
                    confidence = data.get('confidence', 0)

                    # 检查意图是否正确
                    is_correct = detected_intent == expected_intent
                    if is_correct:
                        results["pass"] += 1
                    else:
                        results["fail"] += 1

                    intent_name = intent_names.get(detected_intent, detected_intent)
                    expected_name = intent_names.get(expected_intent, expected_intent)

                    status = "[PASS]" if is_correct else "[FAIL]"

                    print(f"{status} {name}: '{message}'")
                    print(f"     预期意图: {expected_name}, 检测到: {intent_name}, 置信度: {confidence:.4f}")

                    results["details"].append({
                        "name": name,
                        "message": message,
                        "expected": expected_intent,
                        "detected": detected_intent,
                        "correct": is_correct,
                        "confidence": confidence,
                        "response_length": len(data.get('response', ''))
                    })
                else:
                    print(f"[FAIL] {name}: HTTP {response.status_code}")
                    results["fail"] += 1
                    self.results["errors"].append(f"{name}: HTTP {response.status_code}")

            except Exception as e:
                print(f"[ERROR] {name}: {e}")
                results["fail"] += 1
                self.results["errors"].append(f"{name}: {e}")

        accuracy = results["pass"] / results["total"] * 100
        print(f"\n聊天端点准确率: {accuracy:.2f}% ({results['pass']}/{results['total']})")

        self.results["api_tests"]["chat"] = results
        return accuracy

    def test_all_intents(self):
        """测试所有意图类型的覆盖"""
        print("\n" + "-" * 70)
        print("测试4: 意图类型覆盖测试")
        print("-" * 70)

        intent_tests = {
            "symptom_inquiry": [
                "我头痛",
                "最近一直咳嗽",
                "肚子疼怎么办",
                "胸闷气短",
                "发烧38度"
            ],
            "department_query": [
                "头痛挂什么科",
                "肚子疼去哪个科",
                "咳嗽看什么科"
            ],
            "medication_consult": [
                "阿莫西林怎么吃",
                "布洛芬副作用",
                "感冒药能一起吃吗"
            ],
            "appointment": [
                "我想挂号",
                "预约专家门诊",
                "帮我排号"
            ],
            "health_education": [
                "怎么预防高血压",
                "糖尿病不能吃什么",
                "有什么运动建议"
            ],
            "greeting": [
                "你好",
                "您好",
                "谢谢",
                "再见"
            ],
            "unknown": [
                "今天天气",
                "不痛",
                "那个那个"
            ]
        }

        results = {
            "total_intents": len(intent_tests),
            "tested_samples": 0,
            "by_intent": {}
        }

        intent_names = {
            "symptom_inquiry": "症状咨询",
            "department_query": "科室查询",
            "medication_consult": "用药咨询",
            "appointment": "预约挂号",
            "health_education": "健康教育",
            "greeting": "问候",
            "unknown": "未知"
        }

        overall_correct = 0
        overall_total = 0

        for intent, messages in intent_tests.items():
            intent_results = {"correct": 0, "total": len(messages)}

            for message in messages:
                try:
                    time.sleep(0.2)  # Add delay between requests
                    response = requests.post(
                        f"{self.base_url}/api/chat",
                        json={"message": message, "session_id": f"test_{intent}", "user_id": "test"},
                        timeout=30
                    )

                    if response.status_code == 200:
                        data = response.json()
                        detected = data.get('intent', '')
                        if detected == intent:
                            intent_results["correct"] += 1
                            overall_correct += 1
                        overall_total += 1
                except:
                    pass

            intent_results["accuracy"] = intent_results["correct"] / intent_results["total"] * 100
            results["by_intent"][intent] = intent_results

            intent_name = intent_names.get(intent, intent)
            print(f"{intent_name}: {intent_results['accuracy']:.1f}% ({intent_results['correct']}/{intent_results['total']})")

        results["overall_accuracy"] = overall_correct / overall_total * 100 if overall_total > 0 else 0
        results["tested_samples"] = overall_total

        print(f"\n整体意图识别准确率: {results['overall_accuracy']:.2f}%")

        self.results["intent_coverage"] = results
        return results

    def test_response_quality(self):
        """测试响应质量"""
        print("\n" + "-" * 70)
        print("测试5: 响应质量检查")
        print("-" * 70)

        quality_tests = [
            ("症状咨询", "我头痛"),
            ("科室查询", "头痛挂什么科"),
            ("用药咨询", "阿莫西林怎么吃"),
            ("健康教育", "怎么预防高血压"),
            ("问候", "你好"),
        ]

        results = []

        for name, message in quality_tests:
            try:
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json={"message": message, "session_id": "quality_test", "user_id": "test"},
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    resp_text = data.get('response', '')
                    has_content = len(resp_text) > 50
                    has_disclaimer = '免责' in resp_text or 'disclaimer' in resp_text.lower()

                    results.append({
                        "name": name,
                        "message": message,
                        "response_length": len(resp_text),
                        "has_content": has_content,
                        "has_disclaimer": has_disclaimer,
                        "status": "pass" if has_content else "fail"
                    })

                    status = "[OK]" if has_content else "[--]"
                    print(f"{status} {name}: 响应长度={len(resp_text)}, 含免责声明={has_disclaimer}")

            except Exception as e:
                print(f"[ERROR] {name}: {e}")
                results.append({"name": name, "status": "error", "error": str(e)})

        self.results["functional_tests"]["response_quality"] = results
        return all(r.get("status") == "pass" for r in results)

    def test_session_management(self):
        """测试会话管理"""
        print("\n" + "-" * 70)
        print("测试6: 会话管理")
        print("-" * 70)

        try:
            # 发送消息创建会话
            requests.post(
                f"{self.base_url}/api/chat",
                json={"message": "你好", "session_id": "session_test", "user_id": "test"},
                timeout=5
            )

            # 获取会话列表
            response = requests.get(f"{self.base_url}/api/sessions", timeout=30)
            if response.status_code == 200:
                sessions = response.json().get("sessions", [])
                print(f"活跃会话数: {len(sessions)}")
                self.results["api_tests"]["sessions"] = {"status": "pass", "count": len(sessions)}
                return True

        except Exception as e:
            print(f"失败: {e}")
            self.results["api_tests"]["sessions"] = {"status": "fail", "error": str(e)}
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 70)
        print("全栈集成测试")
        print("=" * 70)

        # 启动服务器
        if not self.start_server():
            print("\n服务器启动失败，无法继续测试")
            return False

        try:
            # 运行所有测试
            tests = [
                ("健康检查", self.test_health_check),
                ("系统状态", self.test_system_status),
                ("聊天端点", self.test_chat_endpoint),
                ("意图覆盖", self.test_all_intents),
                ("响应质量", self.test_response_quality),
                ("会话管理", self.test_session_management),
            ]

            for test_name, test_func in tests:
                try:
                    test_func()
                except Exception as e:
                    print(f"\n[错误] {test_name} 测试失败: {e}")
                    self.results["errors"].append(f"{test_name}: {e}")

        finally:
            self.stop_server()

        return self.print_summary()

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 70)
        print("测试摘要报告")
        print("=" * 70)

        print(f"\n测试时间: {self.results['timestamp']}")

        # API测试结果
        api_tests = self.results.get("api_tests", {})
        print(f"\nAPI端点测试:")
        for endpoint, result in api_tests.items():
            if isinstance(result, dict) and "status" in result:
                status = result["status"]
                icon = "[PASS]" if status == "pass" else "[FAIL]"
                print(f"  {icon} {endpoint}: {status}")

        # 聊天端点详情
        if "chat" in api_tests:
            chat_result = api_tests["chat"]
            print(f"\n聊天端点详情:")
            print(f"  准确率: {chat_result.get('pass', 0)}/{chat_result.get('total', 0)} "
                  f"({chat_result.get('pass', 0)/max(chat_result.get('total', 1), 0)*100:.1f}%)")

        # 意图覆盖
        if "intent_coverage" in self.results:
            cov = self.results["intent_coverage"]
            print(f"\n意图覆盖测试:")
            print(f"  整体准确率: {cov.get('overall_accuracy', 0):.2f}%")
            print(f"  测试样本数: {cov.get('tested_samples', 0)}")

        # 功能测试
        func_tests = self.results.get("functional_tests", {})
        if "response_quality" in func_tests:
            print(f"\n响应质量测试:")
            passed = sum(1 for r in func_tests["response_quality"] if r.get("status") == "pass")
            total = len(func_tests["response_quality"])
            print(f"  通过率: {passed}/{total} ({passed/total*100:.0f}%)")

        # 错误
        if self.results["errors"]:
            print(f"\n错误数量: {len(self.results['errors'])}")
            for error in self.results["errors"][:10]:
                print(f"  - {error}")

        # 总体评估
        all_passed = (
            all(r.get("status") == "pass" for r in api_tests.values() if isinstance(r, dict))
            and len(self.results["errors"]) == 0
        )

        print("\n" + "=" * 70)
        if all_passed:
            print("[SUCCESS] 所有测试通过！前后端集成正常！")
        else:
            print("[WARNING] 部分测试失败，请检查日志")
        print("=" * 70)

        return all_passed

    def save_report(self):
        """保存测试报告"""
        report_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tests"
        )
        os.makedirs(report_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(report_dir, f"fullstack_test_report_{timestamp}.json")

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n测试报告已保存: {report_path}")
        return report_path


async def main():
    """主函数"""
    tester = FullStackIntegrationTester()
    tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
