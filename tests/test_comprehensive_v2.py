# -*- coding: utf-8 -*-
"""
医疗智能助手 - 完整测试套件 V2
修复所有bug，增加测试用例
"""
import asyncio
import sys
import os
import time
import json
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_protocol.mcp_protocol import MCPFactory, MCPClient
from mcp_tools.medical_tools import create_medical_mcp_server
from agent.medical_agent import (
    MedicalAgent, IntentType, IntentClassifier,
    HealthKnowledgeBase, ResponseFormatter, DialogueContext,
    SkillRequest, SkillResponse
)


# ============================================================
# 扩展测试用例 - 每个Skill 8个测试用例
# ============================================================

EXTENDED_TEST_CASES_V2 = {
    "greeting-handler": [
        # 简单
        {"input": "你好", "expected_intent": "greeting", "expected_skill": "greeting-handler", "complexity": "simple"},
        {"input": "hi", "expected_intent": "greeting", "expected_skill": "greeting-handler", "complexity": "simple"},
        {"input": "嗨", "expected_intent": "greeting", "expected_skill": "greeting-handler", "complexity": "simple"},
        # 中等
        {"input": "早上好", "expected_intent": "greeting", "expected_skill": "greeting-handler", "complexity": "medium"},
        {"input": "下午好", "expected_intent": "greeting", "expected_skill": "greeting-handler", "complexity": "medium"},
        # 复杂
        {"input": "你好啊，请问可以帮我吗？", "expected_intent": "greeting", "expected_skill": "greeting-handler", "complexity": "complex"},
        # 边界
        {"input": "hello 你好", "expected_intent": "greeting", "expected_skill": "greeting-handler", "complexity": "edge_case"},
        {"input": "您好，我想咨询健康问题", "expected_intent": "greeting", "expected_skill": "greeting-handler", "complexity": "edge_case"},
    ],

    "symptom-analyzer": [
        # 简单
        {"input": "我头痛", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "simple"},
        {"input": "最近一直咳嗽", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "simple"},
        {"input": "感觉有点发热", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "simple"},
        # 中等
        {"input": "我头痛好几天了", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "medium"},
        {"input": "最近胃不舒服，感觉恶心", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "medium"},
        {"input": "剧烈头痛，伴有恶心呕吐", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "medium"},
        # 复杂
        {"input": "我这三天一直头痛，特别是左边太阳穴位置，非常疼", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "complex"},
        {"input": "我头痛、发热，还有点咳嗽，很难受", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "complex"},
        # 边界
        {"input": "我头痛好几天了，非常不舒服", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "edge_case"},
    ],

    "department-recommender": [
        # 简单
        {"input": "头痛挂什么科", "expected_intent": "department_query", "expected_skill": "department-recommender", "complexity": "simple"},
        {"input": "肚子疼去哪个科", "expected_intent": "department_query", "expected_skill": "department-recommender", "complexity": "simple"},
        {"input": "皮肤过敏看什么科", "expected_intent": "department_query", "expected_skill": "department-recommender", "complexity": "simple"},
        # 中等
        {"input": "我最近总是咳嗽，应该去看哪个科室", "expected_intent": "department_query", "expected_skill": "department-recommender", "complexity": "medium"},
        {"input": "头痛是不是应该挂神经内科？", "expected_intent": "department_query", "expected_skill": "department-recommender", "complexity": "medium"},
        {"input": "我关节痛还有皮肤红肿，应该挂什么科", "expected_intent": "department_query", "expected_skill": "department-recommender", "complexity": "medium"},
        # 复杂
        {"input": "我有高血压和糖尿病，应该去哪个科室复查", "expected_intent": "department_query", "expected_skill": "department-recommender", "complexity": "complex"},
        {"input": "我头痛、恶心，还有视力模糊，这是要看神经科还是眼科", "expected_intent": "department_query", "expected_skill": "department-recommender", "complexity": "complex"},
        # 边界
        {"input": "脚趾甲长进肉里了，要挂什么科", "expected_intent": "department_query", "expected_skill": "department-recommender", "complexity": "edge_case"},
    ],

    "medication-advisor": [
        # 简单
        {"input": "阿莫西林怎么吃", "expected_intent": "medication_consult", "expected_skill": "medication-advisor", "complexity": "simple"},
        {"input": "布洛芬有什么副作用", "expected_intent": "medication_consult", "expected_skill": "medication-advisor", "complexity": "simple"},
        {"input": "感冒药一天几次", "expected_intent": "medication_consult", "expected_skill": "medication-advisor", "complexity": "simple"},
        # 中等
        {"input": "成人阿莫西林一次吃多少", "expected_intent": "medication_consult", "expected_skill": "medication-advisor", "complexity": "medium"},
        {"input": "阿莫西林和布洛芬能一起吃吗", "expected_intent": "medication_consult", "expected_skill": "medication-advisor", "complexity": "medium"},
        {"input": "我有胃溃疡，可以吃布洛芬吗", "expected_intent": "medication_consult", "expected_skill": "medication-advisor", "complexity": "medium"},
        # 复杂
        {"input": "我正在服用降压药，可以同时吃感冒药吗？有什么禁忌？", "expected_intent": "medication_consult", "expected_skill": "medication-advisor", "complexity": "complex"},
        {"input": "孕妇可以吃感冒药吗？有哪些药物是需要避免的？", "expected_intent": "medication_consult", "expected_skill": "medication-advisor", "complexity": "complex"},
        # 边界
        {"input": "我吃了3天药了，但是症状没好转", "expected_intent": "medication_consult", "expected_skill": "medication-advisor", "complexity": "edge_case"},
    ],

    "health-educator": [
        # 简单
        {"input": "怎么预防高血压", "expected_intent": "health_education", "expected_skill": "health-educator", "complexity": "simple"},
        {"input": "高血压不能吃什么", "expected_intent": "health_education", "expected_skill": "health-educator", "complexity": "simple"},
        {"input": "有什么运动建议", "expected_intent": "health_education", "expected_skill": "health-educator", "complexity": "simple"},
        # 中等
        {"input": "糖尿病患者有什么运动建议", "expected_intent": "health_education", "expected_skill": "health-educator", "complexity": "medium"},
        {"input": "高血压患者日常生活中要注意什么", "expected_intent": "health_education", "expected_skill": "health-educator", "complexity": "medium"},
        {"input": "怎么预防感冒", "expected_intent": "health_education", "expected_skill": "health-educator", "complexity": "medium"},
        # 复杂
        {"input": "我有高血压和糖尿病，饮食和运动方面有什么需要注意的？", "expected_intent": "health_education", "expected_skill": "health-educator", "complexity": "complex"},
        {"input": "预防心血管疾病需要采取哪些措施？", "expected_intent": "health_education", "expected_skill": "health-educator", "complexity": "complex"},
        # 边界
        {"input": "怎么样才能保持健康的生活方式", "expected_intent": "health_education", "expected_skill": "health-educator", "complexity": "edge_case"},
    ],

    "fallback-handler": [
        # 简单 - 无关输入
        {"input": "今天天气怎么样", "expected_intent": "unknown", "expected_skill": "fallback-handler", "complexity": "simple"},
        {"input": "asdfgh", "expected_intent": "unknown", "expected_skill": "fallback-handler", "complexity": "simple"},
        # 中等 - 模糊输入
        {"input": "那个东西怎么用", "expected_intent": "unknown", "expected_skill": "fallback-handler", "complexity": "medium"},
        {"input": "我想买一台电脑", "expected_intent": "unknown", "expected_skill": "fallback-handler", "complexity": "medium"},
        # 复杂 - 否定句
        {"input": "我不头痛也不痛", "expected_intent": "unknown", "expected_skill": "fallback-handler", "complexity": "complex"},
        {"input": "我没病，身体很好", "expected_intent": "unknown", "expected_skill": "fallback-handler", "complexity": "complex"},
        # 边界 - 特殊字符和空输入
        {"input": "@#$%^&*()", "expected_intent": "unknown", "expected_skill": "fallback-handler", "complexity": "edge_case"},
        {"input": "    ", "expected_intent": "unknown", "expected_skill": "fallback-handler", "complexity": "edge_case"},
    ],
}


# 额外的边界测试用例
EDGE_CASE_TEST_CASES_V2 = [
    {"input": "头痛" * 100, "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "edge_case"},
    {"input": "我headache好几天了", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "edge_case"},
    {"input": "痛痛痛痛痛", "expected_intent": "unknown", "expected_skill": "fallback-handler", "complexity": "edge_case"},
    {"input": "我头痛，发热，咳嗽，恶心，呕吐，腹泻，失眠，乏力", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "edge_case"},
    {"input": "如果头痛发热应该怎么办", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "edge_case"},
]


# ============================================================
# 测试运行器
# ============================================================

@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    test_type: str
    skill: str
    input_text: str
    expected_intent: str
    actual_intent: str
    expected_skill: str
    actual_skill: str
    confidence: float
    entities: dict
    response_length: int
    response_time_ms: float
    passed: bool
    error_message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    complexity: str = "simple"


class ComprehensiveTestRunner:
    """综合测试运行器"""

    def __init__(self):
        self.host = None
        self.server = None
        self.client = None
        self.agent = None
        self.results: List[TestResult] = []
        self.performance_data: Dict[str, List[float]] = defaultdict(list)
        self.logs: List[str] = []
        self.logger = None  # Will be initialized in start()

    def _setup_logger(self):
        """设置日志"""
        logger = logging.getLogger("MedicalTestRunner")
        logger.setLevel(logging.DEBUG)

        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"test_run_{timestamp}.log")
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        self.log_file = log_file
        return logger

    def log(self, message: str, level: str = "INFO"):
        self.logs.append(f"[{datetime.now().isoformat()}] [{level}] {message}")
        if self.logger is None:
            return
        if level == "DEBUG":
            self.logger.debug(message)
        elif level == "WARNING":
            self.logger.warning(message)
        elif level == "ERROR":
            self.logger.error(message)
        else:
            self.logger.info(message)

    async def start(self):
        """启动测试环境"""
        # Initialize logger first
        if self.logger is None:
            self.logger = self._setup_logger()
        self.log("启动测试环境...")
        self.host = MCPFactory.create_host("test-v2-host")
        await self.host.start()
        self.log("MCP Host 已启动")

        self.server = await create_medical_mcp_server(self.host)
        await self.server.start()
        self.log(f"MCP Server 已启动，注册了 4 个工具")

        self.client = MCPClient("test-v2-client", self.host)
        await self.client.start()
        self.log("MCP Client 已启动")

        self.agent = MedicalAgent(mcp_client=self.client)
        await self.agent.start()
        self.log("MedicalAgent 已启动")

    async def stop(self):
        """停止测试环境"""
        self.log("停止测试环境...")
        if self.agent:
            await self.agent.stop()
        if self.client:
            await self.client.stop()
        if self.server:
            await self.server.stop()
        if self.host:
            await self.host.stop()
        self.log("测试环境已停止")

    async def run_single_test(self, test_case: Dict, skill: str, test_type: str = "functional") -> TestResult:
        """运行单个测试"""
        input_text = test_case["input"]
        expected_intent = test_case.get("expected_intent", "")
        expected_skill = test_case.get("expected_skill", skill)
        complexity = test_case.get("complexity", "simple")

        self.log(f"运行测试 - Skill: {skill}, 输入: '{input_text[:30]}...', 复杂度: {complexity}")

        start_time = time.time()
        error_msg = ""
        passed = False
        actual_intent = ""
        actual_skill = ""
        confidence = 0.0
        entities = {}
        response_length = 0

        try:
            context = DialogueContext("test-session", "test-user")
            intent_result = await self.agent.classifier.classify(input_text, context)
            actual_intent = intent_result.intent.value
            actual_skill = intent_result.target_skill
            confidence = intent_result.confidence
            entities = intent_result.entities

            response = await self.agent.process(input_text, session_id="test-session")
            response_length = len(response)

            # 验证结果
            skill_match = actual_skill == expected_skill
            intent_match = actual_intent == expected_intent if expected_intent else True

            passed = skill_match and intent_match

            if not skill_match:
                error_msg = f"Skill不匹配: 预期 {expected_skill}, 实际 {actual_skill}"
            elif not intent_match:
                error_msg = f"意图不匹配: 预期 {expected_intent}, 实际 {actual_intent}"

        except Exception as e:
            error_msg = str(e)
            self.log(f"测试出错: {error_msg}", "ERROR")

        response_time = (time.time() - start_time) * 1000
        self.performance_data[skill].append(response_time)

        result = TestResult(
            test_name=f"{skill}_{complexity}",
            test_type=test_type,
            skill=skill,
            input_text=input_text,
            expected_intent=expected_intent,
            actual_intent=actual_intent,
            expected_skill=expected_skill,
            actual_skill=actual_skill,
            confidence=confidence,
            entities=entities,
            response_length=response_length,
            response_time_ms=response_time,
            passed=passed,
            error_message=error_msg,
            complexity=complexity
        )

        self.log(f"测试结果 - {'PASS' if passed else 'FAIL'}, 响应时间: {response_time:.2f}ms")
        return result

    async def run_skill_tests(self, skill: str, test_cases: List[Dict], test_type: str = "functional") -> List[TestResult]:
        """运行某个Skill的所有测试"""
        self.log(f"\n{'='*60}")
        self.log(f"开始测试 Skill: {skill} ({test_type})")
        self.log(f"{'='*60}")

        results = []
        for i, test_case in enumerate(test_cases, 1):
            result = await self.run_single_test(test_case, skill, test_type)
            results.append(result)
            self.results.append(result)

        passed = sum(1 for r in results if r.passed)
        self.log(f"{skill} 测试完成: {passed}/{len(results)} 通过")

        return results

    async def run_all_functional_tests(self) -> Dict:
        """运行所有功能测试"""
        self.log("\n" + "="*80)
        self.log("开始功能测试")
        self.log("="*80)

        start_time = time.time()

        for skill, test_cases in EXTENDED_TEST_CASES_V2.items():
            await self.run_skill_tests(skill, test_cases, "functional")

        # 运行边界测试
        self.log("\n运行边界测试...")
        for test_case in EDGE_CASE_TEST_CASES_V2:
            result = await self.run_single_test(test_case, test_case["expected_skill"], "edge_case")
            self.results.append(result)

        end_time = time.time()

        return {
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "total_duration_ms": (end_time - start_time) * 1000,
        }

    async def run_performance_tests(self) -> Dict:
        """运行性能测试"""
        self.log("\n" + "="*80)
        self.log("开始性能测试")
        self.log("="*80)

        start_time = time.time()

        test_inputs = [
            "你好",
            "我头痛",
            "头痛挂什么科",
            "阿莫西林怎么吃",
            "怎么预防高血压",
        ]

        for input_text in test_inputs:
            times = []
            for i in range(50):
                single_start = time.time()
                try:
                    await self.agent.process(input_text, session_id=f"perf-{i}")
                    times.append((time.time() - single_start) * 1000)
                except Exception as e:
                    self.log(f"性能测试错误: {e}", "ERROR")

            if times:
                times_sorted = sorted(times)
                self.log(f"性能测试 - '{input_text}': 平均 {np.mean(times):.2f}ms, "
                        f"P95: {times_sorted[int(len(times)*0.95)]:.2f}ms")

        # 并发测试
        concurrent_tasks = 10
        concurrent_iterations = 20
        for i in range(concurrent_iterations):
            batch_start = time.time()
            tasks = [
                self.agent.process("你好", session_id=f"concurrent-{i}-{j}")
                for j in range(concurrent_tasks)
            ]
            await asyncio.gather(*tasks)
            batch_time = (time.time() - batch_start) * 1000
            self.log(f"并发批次 {i+1}: {concurrent_tasks}请求, 耗时 {batch_time:.2f}ms")

        end_time = time.time()

        return {
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "total_duration_ms": (end_time - start_time) * 1000,
        }

    async def run_unit_tests(self) -> Dict:
        """运行单元测试"""
        self.log("\n" + "="*80)
        self.log("开始单元测试")
        self.log("="*80)

        start_time = time.time()
        results = []

        # IntentClassifier 测试
        classifier = IntentClassifier()
        context = DialogueContext("unit-test", "user")

        greeting_tests = [
            ("你好", IntentType.GREETING),
            ("hi", IntentType.GREETING),
            ("早上好", IntentType.GREETING),
        ]
        for text, expected in greeting_tests:
            result = await classifier.classify(text, context)
            passed = result.intent == expected
            results.append(TestResult(
                test_name=f"IntentClassifier_greeting",
                test_type="unit", skill="intent-classifier",
                input_text=text, expected_intent=expected.value,
                actual_intent=result.intent.value,
                expected_skill="greeting-handler", actual_skill=result.target_skill,
                confidence=result.confidence, entities=result.entities,
                response_length=0, response_time_ms=0, passed=passed
            ))

        symptom_tests = [
            ("我头痛", IntentType.SYMPTOM_INQUIRY),
            ("最近咳嗽", IntentType.SYMPTOM_INQUIRY),
            ("头痛挂什么科", IntentType.DEPARTMENT_QUERY),
            ("阿莫西林怎么吃", IntentType.MEDICATION_CONSULT),
            ("怎么预防高血压", IntentType.HEALTH_EDUCATION),
        ]
        for text, expected in symptom_tests:
            result = await classifier.classify(text, context)
            passed = result.intent == expected
            results.append(TestResult(
                test_name=f"IntentClassifier_{expected.value}",
                test_type="unit", skill="intent-classifier",
                input_text=text, expected_intent=expected.value,
                actual_intent=result.intent.value,
                expected_skill="", actual_skill=result.target_skill,
                confidence=result.confidence, entities=result.entities,
                response_length=0, response_time_ms=0, passed=passed
            ))

        end_time = time.time()

        return {
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "total_duration_ms": (end_time - start_time) * 1000,
            "results": results,
        }

    async def run_flow_tests(self) -> Dict:
        """运行流程测试"""
        self.log("\n" + "="*80)
        self.log("开始流程测试")
        self.log("="*80)

        start_time = time.time()
        results = []

        # 测试1: 单轮对话
        response = await self.agent.process("你好", session_id="flow-test-1")
        results.append(TestResult(
            test_name="FlowTest_single_turn",
            test_type="flow", skill="greeting-handler",
            input_text="你好", expected_intent="greeting",
            actual_intent="greeting", expected_skill="greeting-handler",
            actual_skill="greeting-handler", confidence=0.95,
            entities={}, response_length=len(response), response_time_ms=0,
            passed=len(response) > 0 and ("您好" in response or "你好" in response or "嗨" in response)
        ))

        # 测试2: 多轮对话
        session_id = "flow-test-2"
        dialogues = [
            ("你好", "greeting"),
            ("我头痛", "symptom_inquiry"),
            ("头痛挂什么科", "department_query"),
        ]
        for text, expected in dialogues:
            await self.agent.process(text, session_id=session_id)

        context = self.agent.get_context(session_id)
        results.append(TestResult(
            test_name="FlowTest_multi_turn",
            test_type="flow", skill="multi-skill",
            input_text=str([d[0] for d in dialogues]),
            expected_intent="multi", actual_intent="multi",
            expected_skill="multi-skill", actual_skill="multi-skill",
            confidence=1.0, entities={}, response_length=context.turn_count,
            response_time_ms=0, passed=context.turn_count == len(dialogues)
        ))

        # 测试3: 上下文保持
        session_id = "flow-test-3"
        await self.agent.process("我头痛", session_id=session_id)
        context = self.agent.get_context(session_id)
        results.append(TestResult(
            test_name="FlowTest_context",
            test_type="flow", skill="context",
            input_text="上下文测试", expected_intent="",
            actual_intent="", expected_skill="",
            actual_skill="", confidence=1.0, entities={},
            response_length=context.turn_count if context else 0,
            response_time_ms=0, passed=context is not None and context.turn_count >= 1
        ))

        # 测试4: 会话清空
        session_id = "flow-test-4"
        await self.agent.process("你好", session_id=session_id)
        self.agent.clear_context(session_id)
        context = self.agent.get_context(session_id)
        results.append(TestResult(
            test_name="FlowTest_clear",
            test_type="flow", skill="context",
            input_text="清空上下文", expected_intent="",
            actual_intent="", expected_skill="",
            actual_skill="", confidence=1.0, entities={},
            response_length=0, response_time_ms=0,
            passed=context is None or context.turn_count == 0
        ))

        end_time = time.time()

        return {
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "total_duration_ms": (end_time - start_time) * 1000,
            "results": results,
        }

    def get_summary(self) -> Dict:
        """获取测试汇总"""
        return {
            "total_tests": len(self.results),
            "passed_tests": sum(1 for r in self.results if r.passed),
            "failed_tests": sum(1 for r in self.results if not r.passed),
            "pass_rate": sum(1 for r in self.results if r.passed) / len(self.results) * 100 if self.results else 0,
            "by_skill": self._get_summary_by_skill(),
            "by_complexity": self._get_summary_by_complexity(),
        }

    def _get_summary_by_skill(self) -> Dict[str, Dict[str, int]]:
        stats = defaultdict(lambda: {"total": 0, "passed": 0})
        for result in self.results:
            skill = result.skill
            stats[skill]["total"] += 1
            if result.passed:
                stats[skill]["passed"] += 1
        return dict(stats)

    def _get_summary_by_complexity(self) -> Dict[str, Dict[str, int]]:
        stats = {
            "simple": {"total": 0, "passed": 0},
            "medium": {"total": 0, "passed": 0},
            "complex": {"total": 0, "passed": 0},
            "edge_case": {"total": 0, "passed": 0}
        }
        for result in self.results:
            complexity = result.complexity
            if complexity in stats:
                stats[complexity]["total"] += 1
                if result.passed:
                    stats[complexity]["passed"] += 1
        return stats

    def save_results(self, filepath: str):
        """保存测试结果"""
        output_dir = os.path.dirname(filepath)
        os.makedirs(output_dir, exist_ok=True)

        data = {
            "summary": self.get_summary(),
            "results": [asdict(r) for r in self.results],
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.log(f"测试结果已保存到: {filepath}")

    def print_summary(self):
        """打印测试汇总"""
        summary = self.get_summary()

        print("\n" + "="*80)
        print("测试汇总")
        print("="*80)

        print(f"\n总测试数: {summary['total_tests']}")
        print(f"通过数: {summary['passed_tests']}")
        print(f"失败数: {summary['failed_tests']}")
        print(f"通过率: {summary['pass_rate']:.1f}%")

        print("\n按Skill统计:")
        for skill, stats in summary['by_skill'].items():
            rate = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"  {skill}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

        print("\n按复杂度统计:")
        for comp, stats in summary['by_complexity'].items():
            rate = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"  {comp}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

        print("\n" + "="*80)


async def main():
    """主函数"""
    runner = ComprehensiveTestRunner()

    try:
        await runner.start()

        # 运行所有测试
        await runner.run_all_functional_tests()

        # 打印汇总
        runner.print_summary()

        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(
            os.path.dirname(__file__),
            "tests", "results",
            f"test_results_{timestamp}.json"
        )
        runner.save_results(results_file)

        print(f"\n结果文件: {results_file}")

    finally:
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
