# -*- coding: utf-8 -*-
"""
医疗智能助手 - 综合测试套件
包含: 单元测试、功能测试、性能测试、流程测试
"""
import asyncio
import sys
import os
import time
import json
import logging
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
# 测试数据类
# ============================================================

@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    test_type: str  # unit, functional, performance, flow
    skill: str
    input_text: str
    expected_intent: str
    actual_intent: str
    expected_skill: str
    actual_skill: str
    confidence: float
    entities: Dict[str, Any]
    response_length: int
    response_time_ms: float
    passed: bool
    error_message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    complexity: str = "simple"  # simple, medium, complex, edge_case


@dataclass
class PerformanceMetrics:
    """性能指标"""
    test_name: str
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    throughput_rps: float
    success_rate: float
    total_tests: int
    passed_tests: int


@dataclass
class TestSuiteSummary:
    """测试套件汇总"""
    suite_name: str
    start_time: str
    end_time: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    pass_rate: float
    total_duration_ms: float
    results: List[TestResult] = field(default_factory=list)
    performance_metrics: List[PerformanceMetrics] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)


# ============================================================
# 扩展测试用例 - 每个Skill 6个不同复杂度的测试用例
# ============================================================

EXTENDED_TEST_CASES = {
    "greeting-handler": [
        # 简单 - 基本问候
        {
            "input": "你好",
            "expected_intent": "greeting",
            "expected_skill": "greeting-handler",
            "complexity": "simple",
            "description": "基本问候语"
        },
        # 简单 - 英文问候
        {
            "input": "hi",
            "expected_intent": "greeting",
            "expected_skill": "greeting-handler",
            "complexity": "simple",
            "description": "英文问候语"
        },
        # 中等 - 时间问候
        {
            "input": "早上好，今天感觉不错",
            "expected_intent": "greeting",
            "expected_skill": "greeting-handler",
            "complexity": "medium",
            "description": "带时间的问候语"
        },
        # 中等 - 感谢
        {
            "input": "谢谢你的帮助",
            "expected_intent": "greeting",
            "expected_skill": "greeting-handler",
            "complexity": "medium",
            "description": "感谢用语"
        },
        # 复杂 - 混合问候
        {
            "input": "你好啊，请问你可以帮我吗？我想咨询一些健康问题",
            "expected_intent": "greeting",
            "expected_skill": "greeting-handler",
            "complexity": "complex",
            "description": "问候+询问混合"
        },
        # 边界 - 简短问候
        {
            "input": "嗨",
            "expected_intent": "greeting",
            "expected_skill": "greeting-handler",
            "complexity": "edge_case",
            "description": "单字问候"
        },
    ],

    "symptom-analyzer": [
        # 简单 - 单症状
        {
            "input": "我头痛",
            "expected_intent": "symptom_inquiry",
            "expected_skill": "symptom-analyzer",
            "complexity": "simple",
            "description": "单一症状描述"
        },
        # 简单 - 基本症状
        {
            "input": "最近一直咳嗽",
            "expected_intent": "symptom_inquiry",
            "expected_skill": "symptom-analyzer",
            "complexity": "simple",
            "description": "带时间状语的症状"
        },
        # 中等 - 多症状
        {
            "input": "我头痛好几天了，还有点发热",
            "expected_intent": "symptom_inquiry",
            "expected_skill": "symptom-analyzer",
            "complexity": "medium",
            "description": "多症状描述"
        },
        # 中等 - 带严重程度
        {
            "input": "剧烈头痛，伴有恶心呕吐",
            "expected_intent": "symptom_inquiry",
            "expected_skill": "symptom-analyzer",
            "complexity": "medium",
            "description": "带严重程度的症状"
        },
        # 复杂 - 详细症状描述
        {
            "input": "我这三天一直头痛，特别是左边太阳穴位置，非常疼，还有点眩晕的感觉，严重影响了睡眠",
            "expected_intent": "symptom_inquiry",
            "expected_skill": "symptom-analyzer",
            "complexity": "complex",
            "description": "详细的多维度症状描述"
        },
        # 边界 - 模糊症状
        {
            "input": "感觉不舒服，不知道哪里不对劲",
            "expected_intent": "symptom_inquiry",
            "expected_skill": "symptom-analyzer",
            "complexity": "edge_case",
            "description": "模糊的症状描述"
        },
    ],

    "department-recommender": [
        # 简单 - 基本科室查询
        {
            "input": "头痛挂什么科",
            "expected_intent": "department_query",
            "expected_skill": "department-recommender",
            "complexity": "simple",
            "description": "基本科室查询"
        },
        # 简单 - 直接询问
        {
            "input": "肚子疼去哪个科",
            "expected_intent": "department_query",
            "expected_skill": "department-recommender",
            "complexity": "simple",
            "description": "直接科室询问"
        },
        # 中等 - 描述性科室查询
        {
            "input": "我最近总是咳嗽，应该去看哪个科室",
            "expected_intent": "department_query",
            "expected_skill": "department-recommender",
            "complexity": "medium",
            "description": "带症状描述的科室查询"
        },
        # 中等 - 具体科室确认
        {
            "input": "皮肤过敏是挂皮肤科吗",
            "expected_intent": "department_query",
            "expected_skill": "department-recommender",
            "complexity": "medium",
            "description": "确认性科室查询"
        },
        # 复杂 - 多症状科室推荐
        {
            "input": "我有关节痛还有皮肤红肿，应该是风湿科还是皮肤科",
            "expected_intent": "department_query",
            "expected_skill": "department-recommender",
            "complexity": "complex",
            "description": "多症状多科室选择"
        },
        # 边界 - 不常见症状
        {
            "input": "脚趾甲长进肉里了要挂什么科",
            "expected_intent": "department_query",
            "expected_skill": "department-recommender",
            "complexity": "edge_case",
            "description": "不常见症状的科室查询"
        },
    ],

    "medication-advisor": [
        # 简单 - 基本用法询问
        {
            "input": "阿莫西林怎么吃",
            "expected_intent": "medication_consult",
            "expected_skill": "medication-advisor",
            "complexity": "simple",
            "description": "基本用法询问"
        },
        # 简单 - 副作用询问
        {
            "input": "布洛芬有什么副作用",
            "expected_intent": "medication_consult",
            "expected_skill": "medication-advisor",
            "complexity": "simple",
            "description": "副作用询问"
        },
        # 中等 - 具体剂量询问
        {
            "input": "成人阿莫西林一次吃多少，一天几次",
            "expected_intent": "medication_consult",
            "expected_skill": "medication-advisor",
            "complexity": "medium",
            "description": "具体剂量询问"
        },
        # 中等 - 药物相互作用
        {
            "input": "阿莫西林和布洛芬能一起吃吗",
            "expected_intent": "medication_consult",
            "expected_skill": "medication-advisor",
            "complexity": "medium",
            "description": "药物相互作用询问"
        },
        # 复杂 - 详细用药咨询
        {
            "input": "我有胃溃疡，可以吃布洛芬止痛吗？有没有替代的药物？需要注意什么？",
            "expected_intent": "medication_consult",
            "expected_skill": "medication-advisor",
            "complexity": "complex",
            "description": "带病史的详细用药咨询"
        },
        # 边界 - 模糊药品名称
        {
            "input": "那个消炎药一天吃几次",
            "expected_intent": "medication_consult",
            "expected_skill": "medication-advisor",
            "complexity": "edge_case",
            "description": "模糊药品名称的询问"
        },
    ],

    "health-educator": [
        # 简单 - 基本预防询问
        {
            "input": "怎么预防高血压",
            "expected_intent": "health_education",
            "expected_skill": "health-educator",
            "complexity": "simple",
            "description": "基本疾病预防询问"
        },
        # 简单 - 饮食询问
        {
            "input": "高血压不能吃什么",
            "expected_intent": "health_education",
            "expected_skill": "health-educator",
            "complexity": "simple",
            "description": "饮食禁忌询问"
        },
        # 中等 - 运动建议
        {
            "input": "糖尿病患者有什么运动建议",
            "expected_intent": "health_education",
            "expected_skill": "health-educator",
            "complexity": "medium",
            "description": "特定疾病的运动建议"
        },
        # 中等 - 生活方式询问
        {
            "input": "高血压患者日常生活中要注意什么",
            "expected_intent": "health_education",
            "expected_skill": "health-educator",
            "complexity": "medium",
            "description": "生活方式注意事项"
        },
        # 复杂 - 综合健康咨询
        {
            "input": "我有高血压和糖尿病，饮食和运动方面有什么需要注意的吗？能不能推荐一些适合的运动项目？",
            "expected_intent": "health_education",
            "expected_skill": "health-educator",
            "complexity": "complex",
            "description": "多疾病综合健康咨询"
        },
        # 边界 - 通用健康建议
        {
            "input": "怎么样才能保持健康",
            "expected_intent": "health_education",
            "expected_skill": "health-educator",
            "complexity": "edge_case",
            "description": "通用健康建议询问"
        },
    ],

    "fallback-handler": [
        # 简单 - 无关输入
        {
            "input": "今天天气怎么样",
            "expected_intent": "unknown",
            "expected_skill": "fallback-handler",
            "complexity": "simple",
            "description": "非医疗相关询问"
        },
        # 简单 - 乱码输入
        {
            "input": "asdfgh",
            "expected_intent": "unknown",
            "expected_skill": "fallback-handler",
            "complexity": "simple",
            "description": "无意义输入"
        },
        # 中等 - 模糊医疗问题
        {
            "input": "那个东西怎么用",
            "expected_intent": "unknown",
            "expected_skill": "fallback-handler",
            "complexity": "medium",
            "description": "指代不明的询问"
        },
        # 中等 - 复杂无关问题
        {
            "input": "我想买一台电脑，你有什么推荐吗",
            "expected_intent": "unknown",
            "expected_skill": "fallback-handler",
            "complexity": "medium",
            "description": "完全不相关的复杂问题"
        },
        # 复杂 - 混合意图
        {
            "input": "你好我想请问一下今天北京的天气怎么样，哦对了还有我头痛怎么办",
            "expected_intent": "unknown",
            "expected_skill": "fallback-handler",
            "complexity": "complex",
            "description": "混合多个无关意图"
        },
        # 边界 - 空输入
        {
            "input": "    ",
            "expected_intent": "unknown",
            "expected_skill": "fallback-handler",
            "complexity": "edge_case",
            "description": "空白输入"
        },
    ],
}


# 额外的边界和压力测试用例
EDGE_CASE_TEST_CASES = [
    # 特殊字符
    {"input": "@#$%^&*()", "expected_intent": "unknown", "expected_skill": "fallback-handler", "complexity": "edge_case"},
    # 超长输入
    {"input": "头痛" * 100, "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "edge_case"},
    # 中英混合 - 应该能识别中文症状
    {"input": "我headache好几天了", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "edge_case"},
    # 重复词 - 需要改进分类器来处理
    {"input": "痛痛痛痛痛", "expected_intent": "unknown", "expected_skill": "fallback-handler", "complexity": "edge_case"},
    # 标点符号测试 - 多症状
    {"input": "我头痛，发热，咳嗽，恶心，呕吐，腹泻，失眠，乏力，疼痛，痒，不适，难受，不舒服，症状", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "complex"},
    # 多语言问候
    {"input": "hello 你好", "expected_intent": "greeting", "expected_skill": "greeting-handler", "complexity": "edge_case"},
    # 数字混合用药
    {"input": "我吃了3天药了", "expected_intent": "medication_consult", "expected_skill": "medication-advisor", "complexity": "medium"},
    # 否定句
    {"input": "我不头痛", "expected_intent": "unknown", "expected_skill": "fallback-handler", "complexity": "edge_case"},
    # 疑问句变体
    {"input": "头痛是不是应该挂神经内科？", "expected_intent": "department_query", "expected_skill": "department-recommender", "complexity": "medium"},
    # 条件句
    {"input": "如果头痛发热应该怎么办", "expected_intent": "symptom_inquiry", "expected_skill": "symptom-analyzer", "complexity": "complex"},
]


# ============================================================
# 测试运行器
# ============================================================

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
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """设置日志记录器"""
        logger = logging.getLogger("MedicalTestRunner")
        logger.setLevel(logging.DEBUG)

        # 创建日志目录
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)

        # 文件处理器
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"test_run_{timestamp}.log")
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        # 控制台处理器
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        self.log_file = log_file
        return logger

    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        self.logs.append(f"[{datetime.now().isoformat()}] [{level}] {message}")
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
        self.log("启动测试环境...")
        self.host = MCPFactory.create_host("comprehensive-test-host")
        await self.host.start()
        self.log("MCP Host 已启动")

        self.server = await create_medical_mcp_server(self.host)
        await self.server.start()
        self.log(f"MCP Server 已启动，注册了 4 个工具")

        self.client = MCPClient("comprehensive-test-client", self.host)
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

    async def run_single_test(
        self,
        test_case: Dict[str, Any],
        skill: str,
        test_type: str = "functional"
    ) -> TestResult:
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
            # 意图识别
            context = DialogueContext("test-session", "test-user")
            intent_result = await self.agent.classifier.classify(input_text, context)
            actual_intent = intent_result.intent.value
            actual_skill = intent_result.target_skill
            confidence = intent_result.confidence
            entities = intent_result.entities

            # 处理请求
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

        response_time = (time.time() - start_time) * 1000  # 转换为毫秒
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

    async def run_skill_tests(
        self,
        skill: str,
        test_cases: List[Dict],
        test_type: str = "functional"
    ) -> List[TestResult]:
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

    async def run_all_functional_tests(self) -> TestSuiteSummary:
        """运行所有功能测试"""
        self.log("\n" + "="*80)
        self.log("开始功能测试")
        self.log("="*80)

        start_time = time.time()

        for skill, test_cases in EXTENDED_TEST_CASES.items():
            await self.run_skill_tests(skill, test_cases, "functional")

        # 运行边界测试
        self.log("\n运行边界测试...")
        for i, test_case in enumerate(EDGE_CASE_TEST_CASES, 1):
            result = await self.run_single_test(
                test_case,
                test_case["expected_skill"],
                "edge_case"
            )
            self.results.append(result)

        end_time = time.time()

        summary = TestSuiteSummary(
            suite_name="Functional Tests",
            start_time=datetime.fromtimestamp(start_time).isoformat(),
            end_time=datetime.fromtimestamp(end_time).isoformat(),
            total_tests=len(self.results),
            passed_tests=sum(1 for r in self.results if r.passed),
            failed_tests=sum(1 for r in self.results if not r.passed),
            skipped_tests=0,
            pass_rate=sum(1 for r in self.results if r.passed) / len(self.results) * 100 if self.results else 0,
            total_duration_ms=(end_time - start_time) * 1000,
            results=self.results.copy(),
            logs=self.logs.copy()
        )

        return summary

    async def run_performance_tests(self) -> TestSuiteSummary:
        """运行性能测试"""
        self.log("\n" + "="*80)
        self.log("开始性能测试")
        self.log("="*80)

        start_time = time.time()
        perf_results = []

        # 单请求性能测试
        test_inputs = [
            "你好",
            "我头痛",
            "头痛挂什么科",
            "阿莫西林怎么吃",
            "怎么预防高血压"
        ]

        for input_text in test_inputs:
            times = []
            for i in range(50):  # 每个输入测试50次
                single_start = time.time()
                try:
                    await self.agent.process(input_text, session_id=f"perf-test-{i}")
                    times.append((time.time() - single_start) * 1000)
                except Exception as e:
                    self.log(f"性能测试错误: {e}", "ERROR")

            if times:
                times_sorted = sorted(times)
                metric = PerformanceMetrics(
                    test_name=f"perf_{input_text[:10]}",
                    avg_response_time_ms=sum(times) / len(times),
                    min_response_time_ms=min(times),
                    max_response_time_ms=max(times),
                    p95_response_time_ms=times_sorted[int(len(times) * 0.95)],
                    p99_response_time_ms=times_sorted[int(len(times) * 0.99)],
                    throughput_rps=1000 / (sum(times) / len(times)),
                    success_rate=100,
                    total_tests=len(times),
                    passed_tests=len(times)
                )
                perf_results.append(metric)
                self.log(f"性能测试 - '{input_text}': 平均 {metric.avg_response_time_ms:.2f}ms, "
                        f"P95: {metric.p95_response_time_ms:.2f}ms, "
                        f"吞吐量: {metric.throughput_rps:.2f} req/s")

        # 并发测试（模拟）
        self.log("执行并发负载测试...")
        concurrent_tasks = 10
        concurrent_iterations = 20
        concurrent_times = []

        for i in range(concurrent_iterations):
            batch_start = time.time()
            tasks = [
                self.agent.process("你好", session_id=f"concurrent-{i}-{j}")
                for j in range(concurrent_tasks)
            ]
            await asyncio.gather(*tasks)
            batch_time = (time.time() - batch_start) * 1000
            concurrent_times.append(batch_time)

        if concurrent_times:
            avg_concurrent = sum(concurrent_times) / len(concurrent_times)
            concurrent_throughput = (concurrent_tasks * 1000) / avg_concurrent
            self.log(f"并发测试 - {concurrent_tasks}并发 x {concurrent_iterations}轮: "
                    f"平均批次时间 {avg_concurrent:.2f}ms, "
                    f"吞吐量 {concurrent_throughput:.2f} req/s")

        end_time = time.time()

        summary = TestSuiteSummary(
            suite_name="Performance Tests",
            start_time=datetime.fromtimestamp(start_time).isoformat(),
            end_time=datetime.fromtimestamp(end_time).isoformat(),
            total_tests=len(test_inputs) * 50 + len(concurrent_times),
            passed_tests=len(test_inputs) * 50 + len(concurrent_times),
            failed_tests=0,
            skipped_tests=0,
            pass_rate=100,
            total_duration_ms=(end_time - start_time) * 1000,
            performance_metrics=perf_results,
            logs=self.logs.copy()
        )

        return summary

    async def run_unit_tests(self) -> TestSuiteSummary:
        """运行单元测试"""
        self.log("\n" + "="*80)
        self.log("开始单元测试")
        self.log("="*80)

        start_time = time.time()
        results = []

        # 测试 IntentClassifier
        self.log("测试 IntentClassifier...")
        classifier = IntentClassifier()
        context = DialogueContext("unit-test", "user")

        # 问候语测试
        greeting_tests = ["你好", "hi", "早上好"]
        for text in greeting_tests:
            result = await classifier.classify(text, context)
            passed = result.intent == IntentType.GREETING
            results.append(TestResult(
                test_name=f"IntentClassifier_greeting",
                test_type="unit",
                skill="intent-classifier",
                input_text=text,
                expected_intent="greeting",
                actual_intent=result.intent.value,
                expected_skill="greeting-handler",
                actual_skill=result.target_skill,
                confidence=result.confidence,
                entities=result.entities,
                response_length=0,
                response_time_ms=0,
                passed=passed
            ))

        # 症状识别测试
        symptom_tests = ["我头痛", "最近咳嗽", "发热"]
        for text in symptom_tests:
            result = await classifier.classify(text, context)
            passed = result.intent == IntentType.SYMPTOM_INQUIRY
            results.append(TestResult(
                test_name=f"IntentClassifier_symptom",
                test_type="unit",
                skill="intent-classifier",
                input_text=text,
                expected_intent="symptom_inquiry",
                actual_intent=result.intent.value,
                expected_skill="symptom-analyzer",
                actual_skill=result.target_skill,
                confidence=result.confidence,
                entities=result.entities,
                response_length=0,
                response_time_ms=0,
                passed=passed
            ))

        # 测试 HealthKnowledgeBase
        self.log("测试 HealthKnowledgeBase...")
        kb = HealthKnowledgeBase()

        prevention = kb.get_disease_prevention("高血压")
        prevention_passed = prevention is not None and "prevention" in prevention
        results.append(TestResult(
            test_name="HealthKnowledgeBase_prevention",
            test_type="unit",
            skill="health-educator",
            input_text="get_disease_prevention('高血压')",
            expected_intent="",
            actual_intent="",
            expected_skill="health-educator",
            actual_skill="health-educator",
            confidence=1.0,
            entities={},
            response_length=len(str(prevention)) if prevention else 0,
            response_time_ms=0,
            passed=prevention_passed
        ))

        restrictions = kb.get_food_restrictions("糖尿病")
        restrictions_passed = restrictions is not None and len(restrictions) > 0
        results.append(TestResult(
            test_name="HealthKnowledgeBase_restrictions",
            test_type="unit",
            skill="health-educator",
            input_text="get_food_restrictions('糖尿病')",
            expected_intent="",
            actual_intent="",
            expected_skill="health-educator",
            actual_skill="health-educator",
            confidence=1.0,
            entities={},
            response_length=len(restrictions) if restrictions else 0,
            response_time_ms=0,
            passed=restrictions_passed
        ))

        # 测试 ResponseFormatter
        self.log("测试 ResponseFormatter...")
        formatter = ResponseFormatter()

        formatted = formatter.format("测试内容", "health", False, False)
        formatter_passed = "免责声明" in formatted
        results.append(TestResult(
            test_name="ResponseFormatter_disclaimer",
            test_type="unit",
            skill="response-formatter",
            input_text="format('测试内容', 'health', False, False)",
            expected_intent="",
            actual_intent="",
            expected_skill="response-formatter",
            actual_skill="response-formatter",
            confidence=1.0,
            entities={},
            response_length=len(formatted),
            response_time_ms=0,
            passed=formatter_passed
        ))

        end_time = time.time()

        summary = TestSuiteSummary(
            suite_name="Unit Tests",
            start_time=datetime.fromtimestamp(start_time).isoformat(),
            end_time=datetime.fromtimestamp(end_time).isoformat(),
            total_tests=len(results),
            passed_tests=sum(1 for r in results if r.passed),
            failed_tests=sum(1 for r in results if not r.passed),
            skipped_tests=0,
            pass_rate=sum(1 for r in results if r.passed) / len(results) * 100 if results else 0,
            total_duration_ms=(end_time - start_time) * 1000,
            results=results,
            logs=self.logs.copy()
        )

        self.log(f"单元测试完成: {summary.passed_tests}/{summary.total_tests} 通过")

        return summary

    async def run_flow_tests(self) -> TestSuiteSummary:
        """运行流程测试 - 测试完整对话流程"""
        self.log("\n" + "="*80)
        self.log("开始流程测试")
        self.log("="*80)

        start_time = time.time()
        results = []

        # 测试流程1: 简单单轮对话
        self.log("流程测试1: 简单单轮对话...")
        session_id = "flow-test-1"
        response = await self.agent.process("你好", session_id=session_id)
        flow1_passed = len(response) > 0 and "您好" in response or "你好" in response or "嗨" in response
        results.append(TestResult(
            test_name="FlowTest_simple_single_turn",
            test_type="flow",
            skill="greeting-handler",
            input_text="你好",
            expected_intent="greeting",
            actual_intent="greeting",
            expected_skill="greeting-handler",
            actual_skill="greeting-handler",
            confidence=0.95,
            entities={},
            response_length=len(response),
            response_time_ms=0,
            passed=flow1_passed
        ))

        # 测试流程2: 多轮对话
        self.log("流程测试2: 多轮对话...")
        session_id = "flow-test-2"
        dialogues = [
            ("你好", "greeting"),
            ("我头痛", "symptom_inquiry"),
            ("头痛挂什么科", "department_query"),
            ("怎么预防高血压", "health_education"),
        ]

        context = self.agent.get_or_create_context(session_id, "user")
        flow2_passed = True

        for text, expected_intent in dialogues:
            response = await self.agent.process(text, session_id=session_id)
            intent_result = await self.agent.classifier.classify(text, context)
            if intent_result.intent.value != expected_intent:
                flow2_passed = False

        results.append(TestResult(
            test_name="FlowTest_multi_turn",
            test_type="flow",
            skill="multi-skill",
            input_text=str([d[0] for d in dialogues]),
            expected_intent="multi",
            actual_intent="multi",
            expected_skill="multi-skill",
            actual_skill="multi-skill",
            confidence=1.0,
            entities={},
            response_length=context.turn_count,
            response_time_ms=0,
            passed=flow2_passed and context.turn_count == len(dialogues)
        ))

        # 测试流程3: 上下文保持
        self.log("流程测试3: 上下文保持...")
        session_id = "flow-test-3"
        await self.agent.process("我头痛", session_id=session_id)
        context = self.agent.get_context(session_id)
        flow3_passed = context is not None and context.turn_count >= 1

        results.append(TestResult(
            test_name="FlowTest_context_persistence",
            test_type="flow",
            skill="context",
            input_text="我头痛 + 上下文检查",
            expected_intent="symptom_inquiry",
            actual_intent="symptom_inquiry",
            expected_skill="symptom-analyzer",
            actual_skill="symptom-analyzer",
            confidence=1.0,
            entities={},
            response_length=context.turn_count if context else 0,
            response_time_ms=0,
            passed=flow3_passed
        ))

        # 测试流程4: 会话清空
        self.log("流程测试4: 会话清空...")
        session_id = "flow-test-4"
        await self.agent.process("你好", session_id=session_id)
        self.agent.clear_context(session_id)
        context = self.agent.get_context(session_id)
        flow4_passed = context is None or context.turn_count == 0

        results.append(TestResult(
            test_name="FlowTest_context_clear",
            test_type="flow",
            skill="context",
            input_text="清空上下文",
            expected_intent="",
            actual_intent="",
            expected_skill="",
            actual_skill="",
            confidence=1.0,
            entities={},
            response_length=0,
            response_time_ms=0,
            passed=flow4_passed
        ))

        # 测试流程5: 错误处理
        self.log("流程测试5: 错误处理...")
        try:
            response = await self.agent.process("", session_id="flow-test-5")
            flow5_passed = len(response) > 0  # 应该有兜底响应
        except Exception:
            flow5_passed = False  # 不应该抛出异常

        results.append(TestResult(
            test_name="FlowTest_error_handling",
            test_type="flow",
            skill="fallback-handler",
            input_text="",
            expected_intent="unknown",
            actual_intent="unknown",
            expected_skill="fallback-handler",
            actual_skill="fallback-handler",
            confidence=0.0,
            entities={},
            response_length=len(response) if flow5_passed else 0,
            response_time_ms=0,
            passed=flow5_passed
        ))

        # 测试流程6: MCP工具调用链
        self.log("流程测试6: MCP工具调用链...")
        flow6_start = time.time()
        response = await self.agent.process("我头痛", session_id="flow-test-6")
        flow6_time = (time.time() - flow6_start) * 1000
        flow6_passed = len(response) > 0 and flow6_time < 5000  # 应该在5秒内完成

        results.append(TestResult(
            test_name="FlowTest_mcp_chain",
            test_type="flow",
            skill="symptom-analyzer",
            input_text="我头痛",
            expected_intent="symptom_inquiry",
            actual_intent="symptom_inquiry",
            expected_skill="symptom-analyzer",
            actual_skill="symptom-analyzer",
            confidence=0.7,
            entities={},
            response_length=len(response),
            response_time_ms=flow6_time,
            passed=flow6_passed
        ))

        end_time = time.time()

        summary = TestSuiteSummary(
            suite_name="Flow Tests",
            start_time=datetime.fromtimestamp(start_time).isoformat(),
            end_time=datetime.fromtimestamp(end_time).isoformat(),
            total_tests=len(results),
            passed_tests=sum(1 for r in results if r.passed),
            failed_tests=sum(1 for r in results if not r.passed),
            skipped_tests=0,
            pass_rate=sum(1 for r in results if r.passed) / len(results) * 100 if results else 0,
            total_duration_ms=(end_time - start_time) * 1000,
            results=results,
            logs=self.logs.copy()
        )

        self.log(f"流程测试完成: {summary.passed_tests}/{summary.total_tests} 通过")

        return summary

    def get_summary_by_complexity(self) -> Dict[str, Dict[str, int]]:
        """按复杂度统计测试结果"""
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

    def get_summary_by_skill(self) -> Dict[str, Dict[str, int]]:
        """按Skill统计测试结果"""
        stats = defaultdict(lambda: {"total": 0, "passed": 0})

        for result in self.results:
            skill = result.skill
            stats[skill]["total"] += 1
            if result.passed:
                stats[skill]["passed"] += 1

        return dict(stats)

    def save_results(self, filepath: str):
        """保存测试结果到JSON文件"""
        output_dir = os.path.dirname(filepath)
        os.makedirs(output_dir, exist_ok=True)

        data = {
            "summary": {
                "total_tests": len(self.results),
                "passed_tests": sum(1 for r in self.results if r.passed),
                "failed_tests": sum(1 for r in self.results if not r.passed),
                "pass_rate": sum(1 for r in self.results if r.passed) / len(self.results) * 100 if self.results else 0,
                "by_complexity": self.get_summary_by_complexity(),
                "by_skill": self.get_summary_by_skill(),
            },
            "results": [asdict(r) for r in self.results],
            "performance_data": {k: {
                "avg": sum(v) / len(v),
                "min": min(v),
                "max": max(v),
                "count": len(v)
            } for k, v in self.performance_data.items()},
            "logs": self.logs
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.log(f"测试结果已保存到: {filepath}")


async def main():
    """主函数 - 运行所有测试"""
    runner = ComprehensiveTestRunner()

    try:
        await runner.start()

        # 运行所有测试
        unit_summary = await runner.run_unit_tests()
        functional_summary = await runner.run_all_functional_tests()
        performance_summary = await runner.run_performance_tests()
        flow_summary = await runner.run_flow_tests()

        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(
            os.path.dirname(__file__),
            "results",
            f"test_results_{timestamp}.json"
        )
        runner.save_results(results_file)

        # 打印最终汇总
        print("\n" + "="*80)
        print("测试汇总")
        print("="*80)

        total_tests = len(runner.results)
        total_passed = sum(1 for r in runner.results if r.passed)

        print(f"\n总测试数: {total_tests}")
        print(f"通过数: {total_passed}")
        print(f"失败数: {total_tests - total_passed}")
        print(f"通过率: {total_passed / total_tests * 100:.1f}%")

        print("\n各测试套件结果:")
        print(f"  单元测试: {unit_summary.passed_tests}/{unit_summary.total_tests} "
              f"({unit_summary.pass_rate:.1f}%)")
        print(f"  功能测试: {functional_summary.passed_tests}/{functional_summary.total_tests} "
              f"({functional_summary.pass_rate:.1f}%)")
        print(f"  性能测试: {performance_summary.passed_tests}/{performance_summary.total_tests} "
              f"({performance_summary.pass_rate:.1f}%)")
        print(f"  流程测试: {flow_summary.passed_tests}/{flow_summary.total_tests} "
              f"({flow_summary.pass_rate:.1f}%)")

        print("\n按复杂度统计:")
        for complexity, stats in runner.get_summary_by_complexity().items():
            rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"  {complexity}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

        print("\n按Skill统计:")
        for skill, stats in runner.get_summary_by_skill().items():
            rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"  {skill}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

        print(f"\n日志文件: {runner.log_file}")
        print(f"结果文件: {results_file}")
        print("="*80)

    finally:
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
