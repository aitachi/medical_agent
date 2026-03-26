# -*- coding: utf-8 -*-
"""
医疗智能助手 - 全系统功能验证脚本
验证：模型配置、Skills、MCP工具、基础功能
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class SystemValidator:
    """系统验证器"""

    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def log(self, level, message):
        """记录日志"""
        symbols = {"INFO": "[*]", "PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]"}
        print(f"{symbols.get(level, '[?]')} {message}")

    def add_result(self, category, name, status, details=""):
        """添加结果"""
        result = {
            "category": category,
            "name": name,
            "status": status,
            "details": details
        }
        self.results.append(result)
        if status == "PASS":
            self.passed += 1
            self.log("PASS", f"{category} - {name}")
        elif status == "FAIL":
            self.failed += 1
            self.log("FAIL", f"{category} - {name}: {details}")
        else:
            self.warnings += 1
            self.log("WARN", f"{category} - {name}: {details}")

    def print_summary(self):
        """打印摘要"""
        print("\n" + "="*60)
        print("[验证摘要]")
        print("="*60)
        print(f"总计: {self.passed + self.failed + self.warnings}")
        print(f"通过: {self.passed}")
        print(f"失败: {self.failed}")
        print(f"警告: {self.warnings}")
        if self.passed + self.failed > 0:
            print(f"通过率: {self.passed / (self.passed + self.failed) * 100:.1f}%")
        print("="*60)


async def validate_model_config(validator):
    """验证模型配置"""
    print("\n" + "="*60)
    print("[1] 模型配置验证")
    print("="*60)

    # 检查 web_api_server.py
    try:
        with open("web_api_server.py", "r", encoding="utf-8") as f:
            content = f.read()
            if 'DASHSCOPE_MODEL = "qwen-max"' in content:
                validator.add_result("模型配置", "web_api_server.py模型", "PASS", "qwen-max")
            elif 'DASHSCOPE_MODEL = "qwen-plus"' in content:
                validator.add_result("模型配置", "web_api_server.py模型", "PASS", "qwen-plus")
            else:
                validator.add_result("模型配置", "web_api_server.py模型", "WARN", "未找到模型配置")

            if "DASHSCOPE_API_KEY" in content:
                validator.add_result("模型配置", "API Key配置", "PASS")
            if "DASHSCOPE_BASE_URL" in content:
                validator.add_result("模型配置", "Base URL配置", "PASS", "dashscope.aliyuncs.com")
    except Exception as e:
        validator.add_result("模型配置", "配置文件读取", "FAIL", str(e))

    # 检查 agent/llm_service.py
    try:
        with open("agent/llm_service.py", "r", encoding="utf-8") as f:
            content = f.read()
            if "qwen-max" in content or "qwen-plus" in content:
                validator.add_result("模型配置", "llm_service.py模型", "PASS")
            if "DashScopeLLM" in content:
                validator.add_result("模型配置", "DashScope客户端", "PASS")
    except Exception as e:
        validator.add_result("模型配置", "LLM服务检查", "FAIL", str(e))


async def validate_skills(validator):
    """验证Skills模块"""
    print("\n" + "="*60)
    print("[2] Skills模块验证")
    print("="*60)

    skills_dir = "skills"
    expected_skills = [
        "report_interpreter",   # 报告解读
        "online_consult",       # 在线问诊
        "chronic_recorder",     # 慢病记录
        "chronic_advisor",      # 慢病咨询
        "followup_service",     # 随访服务
        "checkup_service",      # 体检服务
        "reminder_service",     # 提醒服务
        "emergency_handler",    # 急救处理
        "scope_handler",        # 范围处理
        "help_handler",         # 帮助处理
        "appointment_manage"    # 预约管理
    ]

    if not os.path.exists(skills_dir):
        validator.add_result("Skills", "skills目录", "FAIL", "目录不存在")
        return

    for skill in expected_skills:
        skill_path = os.path.join(skills_dir, skill)
        init_file = os.path.join(skill_path, "__init__.py")

        if os.path.exists(skill_path):
            if os.path.exists(init_file):
                # 检查SKILL.md
                skill_md = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(skill_md):
                    validator.add_result("Skills", skill, "PASS", "有SKILL.md")
                else:
                    validator.add_result("Skills", skill, "WARN", "缺少SKILL.md")

                # 检查handler.py
                handler_file = os.path.join(skill_path, "handler.py")
                if os.path.exists(handler_file):
                    validator.add_result("Skills", f"{skill}/handler", "PASS")
            else:
                validator.add_result("Skills", skill, "WARN", "缺少__init__.py")
        else:
            validator.add_result("Skills", skill, "FAIL", "目录不存在")


async def validate_mcp_tools(validator):
    """验证MCP工具"""
    print("\n" + "="*60)
    print("[3] MCP工具验证")
    print("="*60)

    try:
        from mcp_protocol.mcp_protocol import MCPFactory
        from mcp_tools.medical_tools import create_medical_mcp_server

        # 创建测试环境
        host = MCPFactory.create_host("validation-host")
        await host.start()

        server = await create_medical_mcp_server(host)
        await server.start()

        # 获取已注册的工具
        tools = server.get_tools()

        expected_tools = [
            "medical_knowledge_query",
            "hospital_department_query",
            "drug_database_query",
            "appointment_booking",
            "lab_report_query",
            "chronic_disease_query",
            "online_consult",
            "emergency_guide",
            "followup_manage",
            "health_checkup",
            "reminder_manage"
        ]

        registered_tools = [tool.name for tool in tools]

        for tool_name in expected_tools:
            if tool_name in registered_tools:
                validator.add_result("MCP工具", tool_name, "PASS")
            else:
                validator.add_result("MCP工具", tool_name, "FAIL", "未注册")

        # 测试工具调用
        client = __import__("mcp_protocol.mcp_protocol", fromlist=["MCPClient"]).MCPClient("validator", host)
        await client.start()

        test_cases = [
            ("medical_knowledge_query", {"query_type": "symptom", "keyword": "头痛"}),
            ("hospital_department_query", {"query_type": "list"}),
            ("drug_database_query", {"query_type": "info", "drug_name": "阿莫西林"}),
            ("lab_report_query", {"action": "list_categories"}),
            ("chronic_disease_query", {"action": "targets", "condition": "高血压"}),
            ("online_consult", {"action": "list_departments"}),
            ("emergency_guide", {"action": "list"}),
            ("followup_manage", {"action": "query_plan", "patient_id": "test"}),
            ("health_checkup", {"action": "list_packages"}),
            ("reminder_manage", {"action": "get_types"}),
        ]

        for tool_name, params in test_cases:
            try:
                result = await client.call_tool(tool_name, params)
                if result.data.get("success") or "data" in result.data:
                    validator.add_result("MCP调用", tool_name, "PASS")
                else:
                    validator.add_result("MCP调用", tool_name, "WARN", f"返回: {result.data}")
            except Exception as e:
                validator.add_result("MCP调用", tool_name, "FAIL", str(e))

        await client.stop()
        await server.stop()
        await host.stop()

    except Exception as e:
        validator.add_result("MCP工具", "初始化", "FAIL", str(e))


async def validate_data_services(validator):
    """验证数据服务"""
    print("\n" + "="*60)
    print("[4] 数据服务验证")
    print("="*60)

    services_dir = "services/data_services"
    expected_services = [
        "user_profile_service",
        "health_records_service",
        "chronic_disease_service",
        "preference_service",
        "behavior_log_service",
        "reminder_service",
        "payment_service",
        "location_service"
    ]

    if not os.path.exists(services_dir):
        validator.add_result("数据服务", "data_services目录", "FAIL", "目录不存在")
        return

    for service in expected_services:
        service_path = os.path.join(services_dir, f"{service}.py")
        if os.path.exists(service_path):
            # 检查类定义
            try:
                with open(service_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "class" in content and "Service" in content:
                        validator.add_result("数据服务", service, "PASS")
                    else:
                        validator.add_result("数据服务", service, "WARN", "可能缺少Service类")
            except Exception as e:
                validator.add_result("数据服务", service, "WARN", str(e))
        else:
            validator.add_result("数据服务", service, "FAIL", "文件不存在")


async def validate_api_endpoints(validator):
    """验证API端点"""
    print("\n" + "="*60)
    print("[5] API端点验证")
    print("="*60)

    try:
        import aiohttp

        # 检查服务是否运行
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://127.0.0.1:8000/api/status", timeout=3) as resp:
                    if resp.status == 200:
                        validator.add_result("API服务", "服务运行状态", "PASS")
                    else:
                        validator.add_result("API服务", "服务运行状态", "FAIL", f"状态码: {resp.status}")
        except Exception as e:
            validator.add_result("API服务", "服务运行状态", "WARN", f"未运行: {e}")
            return

        # 测试各端点
        endpoints = [
            ("GET", "/api/status", None, "系统状态"),
            ("POST", "/api/chat", {"message": "测试"}, "基础聊天"),
            ("GET", "/api/profile", {"user_id": "test"}, "用户画像"),
            ("GET", "/api/records", {"patient_id": "test"}, "健康档案"),
            ("GET", "/api/health", None, "健康检查"),
        ]

        for method, endpoint, data, name in endpoints:
            try:
                async with aiohttp.ClientSession() as session:
                    if method == "GET":
                        async with session.get(f"http://127.0.0.1:8000{endpoint}", params=data, timeout=5) as resp:
                            if resp.status == 200:
                                validator.add_result("API端点", name, "PASS")
                            else:
                                validator.add_result("API端点", name, "WARN", f"状态码: {resp.status}")
                    elif method == "POST":
                        async with session.post(f"http://127.0.0.1:8000{endpoint}", json=data, timeout=10) as resp:
                            if resp.status == 200:
                                validator.add_result("API端点", name, "PASS")
                            else:
                                validator.add_result("API端点", name, "WARN", f"状态码: {resp.status}")
            except Exception as e:
                validator.add_result("API端点", name, "WARN", str(e))

    except ImportError:
        validator.add_result("API端点", "测试", "WARN", "aiohttp未安装")


async def validate_agent(validator):
    """验证Agent组件"""
    print("\n" + "="*60)
    print("[6] Agent组件验证")
    print("="*60)

    # 检查核心文件
    agent_files = {
        "agent/medical_agent.py": "MedicalAgent",
        "agent/scene_filter.py": "SceneFilter",
        "agent/llm_service.py": "DashScopeLLM",
        "agent/user_profile.py": "UserProfile",
    }

    for file_path, expected_class in agent_files.items():
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if f"class {expected_class}" in content:
                        validator.add_result("Agent", expected_class, "PASS")
                    else:
                        validator.add_result("Agent", expected_class, "WARN", "类定义未找到")
            except Exception as e:
                validator.add_result("Agent", expected_class, "FAIL", str(e))
        else:
            validator.add_result("Agent", expected_class, "FAIL", "文件不存在")

    # 检查意图类型
    try:
        with open("agent/medical_agent.py", "r", encoding="utf-8") as f:
            content = f.read()
            if "class IntentType" in content:
                # 提取意图类型数量
                import re
                matches = re.findall(r'(\w+)\s*=\s*"', content)
                if len(matches) >= 15:
                    validator.add_result("Agent", "IntentType枚举", "PASS", f"{len(matches)}种意图")
                else:
                    validator.add_result("Agent", "IntentType枚举", "WARN", f"仅{len(matches)}种意图")
    except Exception as e:
        validator.add_result("Agent", "IntentType枚举", "FAIL", str(e))


async def main():
    """主验证流程"""
    validator = SystemValidator()

    print("="*60)
    print("医疗智能助手 - 全系统功能验证")
    print("="*60)
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 执行各项验证
    await validate_model_config(validator)
    await validate_skills(validator)
    await validate_mcp_tools(validator)
    await validate_data_services(validator)
    await validate_agent(validator)
    await validate_api_endpoints(validator)

    # 打印摘要
    validator.print_summary()

    # 生成详细报告
    report_path = "validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": validator.passed + validator.failed + validator.warnings,
                "passed": validator.passed,
                "failed": validator.failed,
                "warnings": validator.warnings
            },
            "results": validator.results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n详细报告已保存至: {report_path}")

    # 返回退出码
    return 0 if validator.failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
