# -*- coding: utf-8 -*-
"""
医疗智能助手 Web API 服务器
使用 FastAPI 提供 REST API
集成阿里云 qwen-plus 大模型
"""

import asyncio
import sys
import os
import uvicorn
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict

# FastAPI imports
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_protocol.mcp_protocol import MCPFactory
from mcp_tools.medical_tools import create_medical_mcp_server
from agent.medical_agent import MedicalAgent
from mcp_protocol.mcp_protocol import MCPClient
from database.db_manager_sqlite import get_db
try:
    from agent.llm_service import init_llm_service, shutdown_llm_service, get_llm_service
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("[WARNING] LLM service not available, running in local mode only")

# 初始化数据库
db = get_db()
print("[INFO] Database initialized")


# ============================================================
# LLM 配置
# ============================================================

DASHSCOPE_API_KEY = "sk-a9a4edb1b4214016baa11c9be3b9fec4"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# 通义千问最新Plus模型 (qwen-plus 为通义千问2.5，qwen-max 为最强版本)
DASHSCOPE_MODEL = "qwen-max"  # 可选: qwen-turbo, qwen-plus, qwen-max, qwen-long


# ============================================================
# Pydantic 模型
# ============================================================

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: Optional[str] = "default"
    user_id: Optional[str] = "anonymous"
    use_llm: Optional[bool] = True  # 是否使用LLM增强响应


class SymptomAnalysisRequest(BaseModel):
    """症状分析请求"""
    symptoms: List[str] = []  # 症状标签列表
    description: str = ""  # 症状详细描述
    duration: str = ""  # 持续时间
    severity: str = ""  # 严重程度
    session_id: Optional[str] = "symptom_page"
    user_id: Optional[str] = "anonymous"


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    skill_invoked: Optional[str] = None
    timestamp: str
    suggested_page: Optional[Dict[str, str]] = None  # 页面跳转推荐
    candidate_pages: Optional[List[Dict[str, str]]] = None  # 候选页面列表（意图不明确时）


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    user_id: str
    message_count: int
    created_at: str
    last_activity: str


class SystemStatus(BaseModel):
    """系统状态"""
    status: str
    uptime: str
    active_sessions: int
    total_requests: int
    classifier_type: str


# ============================================================
# 新增 API 请求/响应模型
# ============================================================

class ChronicRecordRequest(BaseModel):
    """慢病记录请求"""
    user_id: str
    disease_type: str  # hypertension/diabetes/hyperlipidemia/coronary/copd等
    measure_data: dict  # 测量数据
    measure_time: str
    note: Optional[str] = None


class ChronicRecordResponse(BaseModel):
    """慢病记录响应"""
    record_id: str
    status: str  # normal/elevated/high
    trend: str  # stable/rising/falling
    alert: Optional[str] = None
    advice: List[str]


class ChronicHistoryResponse(BaseModel):
    """慢病历史响应"""
    user_id: str
    disease_type: str
    records: List[Dict]
    statistics: Dict


class ConsultCreateRequest(BaseModel):
    """在线问诊创建请求"""
    user_id: str
    consult_type: str  # text/video/phone
    department: Optional[str] = None
    doctor_id: Optional[str] = None
    symptom_desc: str
    images: Optional[List[str]] = None


class ConsultCreateResponse(BaseModel):
    """在线问诊创建响应"""
    consult_id: str
    status: str  # waiting/queued/active
    queue_position: int
    estimated_wait: int  # 预计等待时间（分钟）
    payment_info: Dict


class ReportInterpretRequest(BaseModel):
    """报告解读请求"""
    user_id: str
    report_type: str  # blood_test/urine_test/liver_function/kidney_function等
    report_data: Dict  # 报告数据
    images: Optional[List[str]] = None


class ReportInterpretResponse(BaseModel):
    """报告解读响应"""
    report_id: str
    summary: str
    abnormal_items: List[Dict]
    health_suggestions: List[str]
    follow_up: Optional[str] = None


class FollowupFeedbackRequest(BaseModel):
    """随访反馈请求"""
    user_id: str
    followup_id: Optional[str] = None
    feedback_type: str  # recovery/side_effect/medication/adverse_event等
    symptoms: List[str]
    medication_compliance: str  # good/partial/poor
    additional_notes: Optional[str] = None


class FollowupFeedbackResponse(BaseModel):
    """随访反馈响应"""
    feedback_id: str
    status: str
    assessment: str
    recommendations: List[str]
    next_followup_date: Optional[str] = None


class UserProfileResponse(BaseModel):
    """用户画像响应"""
    user_id: str
    basic_info: Dict
    health_tags: List[str]
    preferences: Dict
    behavior_stats: Dict
    risk_level: str


class HealthRecordsResponse(BaseModel):
    """健康档案响应"""
    user_id: str
    basic_info: Dict
    medical_history: List[Dict]
    allergy_history: List[str]
    medication_history: List[Dict]
    surgery_history: List[Dict]
    family_history: List[Dict]


# ============================================================
# 页面推荐映射
# ============================================================

def get_suggested_page(intent: str, confidence: float, message: str = "") -> Optional[Dict[str, str]]:
    """
    根据意图和置信度返回推荐页面

    Args:
        intent: 意图类型
        confidence: 置信度
        message: 用户原始消息（用于智能匹配）

    Returns:
        页面信息字典或None
    """
    # 不推荐跳转的意图
    if intent in ["greeting", "chitchat"]:
        return None

    # 智能匹配：根据消息内容覆盖意图推荐
    message_lower = message.lower()

    # 血糖/血压相关 -> 健康教育或症状咨询
    if any(kw in message_lower for kw in ["血糖升高", "血糖高", "血压升高", "血压高", "血糖突然", "血压突然"]):
        return {
            "page_id": "page-health",
            "page_name": "健康教育",
            "page_icon": "📚",
            "description": "获取健康知识科普和疾病预防建议"
        }

    # 预约查询相关关键词 -> my_appointment
    if any(kw in message_lower for kw in ["查询我的预约", "查看预约", "我的预约状态", "挂号记录", "我的挂号"]):
        return {
            "page_id": "page-myappointment",
            "page_name": "预约查询",
            "page_icon": "📋",
            "description": "查看和管理您的预约记录"
        }

    # 随访管理相关关键词 -> followup
    if any(kw in message_lower for kw in ["添加随访", "随访记录", "随访情况", "查看随访"]):
        return {
            "page_id": "page-followup",
            "page_name": "随访管理",
            "page_icon": "📝",
            "description": "管理患者随访记录和康复评估"
        }

    # 治疗档案相关关键词 -> records
    if any(kw in message_lower for kw in ["查看我的病历", "治疗档案", "我的档案", "就诊记录", "病历"]):
        return {
            "page_id": "page-records",
            "page_name": "治疗档案",
            "page_icon": "📂",
            "description": "查看完整的就诊历史和健康档案"
        }

    # 置信度过低时不推荐跳转
    if confidence < 0.3:
        return None

    page_mapping = {
        "symptom_inquiry": {
            "page_id": "page-symptom",
            "page_name": "症状咨询",
            "page_icon": "🔍",
            "description": "使用专业的症状分析工具，获取详细健康建议"
        },
        "department_query": {
            "page_id": "page-department",
            "page_name": "科室推荐",
            "page_icon": "🏥",
            "description": "智能匹配最合适的科室，快速找到对口的医生"
        },
        "medication_consult": {
            "page_id": "page-medication",
            "page_name": "用药咨询",
            "page_icon": "💊",
            "description": "查询药品用法、副作用和注意事项"
        },
        "appointment": {
            "page_id": "page-appointment",
            "page_name": "预约挂号",
            "page_icon": "📅",
            "description": "在线预约医生门诊，选择合适的时间段"
        },
        "health_education": {
            "page_id": "page-health",
            "page_name": "健康教育",
            "page_icon": "📚",
            "description": "获取健康知识科普和疾病预防建议"
        },
        "report_interpret": {
            "page_id": "page-report",
            "page_name": "报告解读",
            "page_icon": "📋",
            "description": "专业解读检查报告，了解各项指标含义"
        },
        "my_appointment": {
            "page_id": "page-myappointment",
            "page_name": "我的预约",
            "page_icon": "📋",
            "description": "查看和管理您的预约记录"
        },
        "followup": {
            "page_id": "page-followup",
            "page_name": "随访管理",
            "page_icon": "📝",
            "description": "管理患者随访记录和康复评估"
        },
        "records": {
            "page_id": "page-records",
            "page_name": "治疗档案",
            "page_icon": "📂",
            "description": "查看完整的就诊历史和健康档案"
        }
    }

    return page_mapping.get(intent)


def get_candidate_pages(alternatives: List[Dict], message: str = "") -> List[Dict[str, str]]:
    """
    根据候选意图列表返回候选页面列表

    Args:
        alternatives: 候选意图列表 [{"intent": "xxx", "confidence": 0.5}, ...]
        message: 用户原始消息

    Returns:
        候选页面列表，最多3个
    """
    # 不推荐跳转的意图
    excluded_intents = ["greeting", "unknown", "chitchat"]

    # 页面映射
    page_mapping = {
        "symptom_inquiry": {
            "page_id": "page-symptom",
            "page_name": "症状咨询",
            "page_icon": "🔍",
            "description": "使用专业的症状分析工具，获取详细健康建议"
        },
        "department_query": {
            "page_id": "page-department",
            "page_name": "科室推荐",
            "page_icon": "🏥",
            "description": "智能匹配最合适的科室，快速找到对口的医生"
        },
        "medication_consult": {
            "page_id": "page-medication",
            "page_name": "用药咨询",
            "page_icon": "💊",
            "description": "查询药品用法、副作用和注意事项"
        },
        "appointment": {
            "page_id": "page-appointment",
            "page_name": "预约挂号",
            "page_icon": "📅",
            "description": "在线预约医生门诊，选择合适的时间段"
        },
        "health_education": {
            "page_id": "page-health",
            "page_name": "健康教育",
            "page_icon": "📚",
            "description": "获取健康知识科普和疾病预防建议"
        },
        "report_interpret": {
            "page_id": "page-report",
            "page_name": "报告解读",
            "page_icon": "📋",
            "description": "专业解读检查报告，了解各项指标含义"
        },
        "my_appointment": {
            "page_id": "page-myappointment",
            "page_name": "我的预约",
            "page_icon": "📋",
            "description": "查看和管理您的预约记录"
        },
        "followup": {
            "page_id": "page-followup",
            "page_name": "随访管理",
            "page_icon": "📝",
            "description": "管理患者随访记录和康复评估"
        },
        "records": {
            "page_id": "page-records",
            "page_name": "治疗档案",
            "page_icon": "📂",
            "description": "查看完整的就诊历史和健康档案"
        }
    }

    candidate_pages = []
    seen_intents = set()

    for alt in alternatives[:5]:  # 最多看前5个
        intent = alt.get("intent", "")
        confidence = alt.get("confidence", 0)

        # 跳过排除的意图和低置信度
        if intent in excluded_intents or confidence < 0.2:
            continue

        # 跳过已添加的意图
        if intent in seen_intents:
            continue

        # 获取页面信息
        page_info = page_mapping.get(intent)
        if page_info:
            page_info["confidence"] = round(confidence * 100, 1)  # 添加置信度百分比
            candidate_pages.append(page_info)
            seen_intents.add(intent)

        # 最多返回3个
        if len(candidate_pages) >= 3:
            break

    return candidate_pages


def get_default_candidate_pages(existing_pages: List[Dict] = None) -> List[Dict[str, str]]:
    """
    获取默认的候选页面列表（当候选页面不足时使用）

    Args:
        existing_pages: 已有的候选页面列表

    Returns:
        默认候选页面列表
    """
    # 获取已有页面的 ID
    existing_ids = set()
    if existing_pages:
        existing_ids = {p.get("page_id") for p in existing_pages}

    # 默认页面列表（按常用程度排序）
    default_pages = [
        {
            "page_id": "page-symptom",
            "page_name": "症状咨询",
            "page_icon": "🔍",
            "description": "使用专业的症状分析工具，获取详细健康建议",
            "confidence": "推荐"
        },
        {
            "page_id": "page-health",
            "page_name": "健康教育",
            "page_icon": "📚",
            "description": "获取健康知识科普和疾病预防建议",
            "confidence": "推荐"
        },
        {
            "page_id": "page-appointment",
            "page_name": "预约挂号",
            "page_icon": "📅",
            "description": "在线预约医生门诊，选择合适的时间段",
            "confidence": "推荐"
        },
        {
            "page_id": "page-medication",
            "page_name": "用药咨询",
            "page_icon": "💊",
            "description": "查询药品用法、副作用和注意事项",
            "confidence": "推荐"
        },
        {
            "page_id": "page-department",
            "page_name": "科室推荐",
            "page_icon": "🏥",
            "description": "智能匹配最合适的科室，快速找到对口的医生",
            "confidence": "推荐"
        }
    ]

    # 过滤掉已有的页面
    result = [p for p in default_pages if p["page_id"] not in existing_ids]

    return result


# ============================================================
# FastAPI 应用
# ============================================================

app = FastAPI(
    title="医疗智能助手 API",
    description="基于MLP意图识别的医疗健康咨询助手",
    version="1.0.0",
    root_path="/medical"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局状态
class AppState:
    """应用状态"""
    def __init__(self):
        self.agent: Optional[MedicalAgent] = None
        self.host = None
        self.server = None
        self.client = None
        self.sessions: Dict[str, Dict] = {}
        self.start_time = datetime.now()
        self.request_count = 0
        self.llm_enabled = False
        self.llm_service = None

    @property
    def uptime(self) -> str:
        """获取运行时间"""
        delta = datetime.now() - self.start_time
        return str(delta)

    def get_active_session_count(self) -> int:
        """获取活跃会话数"""
        return len(self.sessions)

    def increment_request(self):
        """增加请求计数"""
        self.request_count += 1

state = AppState()


# ============================================================
# 生命周期管理
# ============================================================

@app.on_event("startup")
async def startup_event():
    """启动事件"""
    print("\n" + "=" * 60)
    print("医疗智能助手 Web API 正在启动...")
    print("=" * 60)

    # 创建MCP基础设施
    state.host = MCPFactory.create_host("web-api-host")
    await state.host.start()

    state.server = await create_medical_mcp_server(state.host)
    await state.server.start()

    state.client = MCPClient("web-api-client", state.host)
    await state.client.start()

    # 创建Agent
    state.agent = MedicalAgent(mcp_client=state.client)
    await state.agent.start()

    # 初始化LLM服务
    if LLM_AVAILABLE:
        try:
            state.llm_service = await init_llm_service(
                api_key=DASHSCOPE_API_KEY,
                base_url=DASHSCOPE_BASE_URL,
                model=DASHSCOPE_MODEL
            )
            state.llm_enabled = True
            print(f"[LLM] qwen-plus 大模型已启用")
        except Exception as e:
            print(f"[LLM] 初始化失败: {e}")
            print(f"[LLM] 将使用本地规则响应")
            state.llm_enabled = False
    else:
        state.llm_enabled = False
        print(f"[LLM] LLM服务不可用，使用本地规则响应")

    # 挂载静态文件目录
    static_dir = os.path.join(os.path.dirname(__file__), "frontend", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    print("\n[Medical AI Assistant] Web API Ready!")
    print(f"[LLM Enabled] {state.llm_enabled}")
    print("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    print("\n[Medical AI Assistant] Shutting down...")

    # 关闭LLM服务
    if LLM_AVAILABLE:
        await shutdown_llm_service()

    if state.agent:
        await state.agent.stop()
    if state.client:
        await state.client.stop()
    if state.server:
        await state.server.stop()
    if state.host:
        await state.host.stop()

    print("[Medical AI Assistant] Stopped")


# ============================================================
# 根路由 - 返回前端页面
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """返回前端页面"""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "frontend",
        "index.html"
    )
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>前端页面未找到，请确保 frontend/index.html 存在</h1>")


@app.get("/favicon.ico")
async def favicon():
    """返回favicon"""
    favicon_path = os.path.join(
        os.path.dirname(__file__),
        "frontend",
        "static",
        "favicon.svg"
    )
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/svg+xml")
    # 返回一个简单的SVG favicon
    svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="#667eea"/><text x="50" y="70" font-size="60" text-anchor="middle" fill="white">🏥</text></svg>'
    return HTMLResponse(content=svg_content, media_type="image/svg+xml")


# 专门功能页面路由
@app.get("/symptom.html", response_class=HTMLResponse)
async def symptom_page():
    """症状咨询页面"""
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "symptom.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>页面未找到</h1>")


@app.get("/department.html", response_class=HTMLResponse)
async def department_page():
    """科室推荐页面"""
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "department.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>页面未找到</h1>")


@app.get("/medication.html", response_class=HTMLResponse)
async def medication_page():
    """用药咨询页面"""
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "medication.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>页面未找到</h1>")


@app.get("/appointment.html", response_class=HTMLResponse)
async def appointment_page():
    """预约挂号页面"""
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "appointment.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>页面未找到</h1>")


@app.get("/health.html", response_class=HTMLResponse)
async def health_page():
    """健康教育页面"""
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "health.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>页面未找到</h1>")


# ============================================================
# API 端点
# ============================================================

@app.get("/api/status", response_model=SystemStatus)
async def get_status():
    """获取系统状态"""
    return SystemStatus(
        status="running",
        uptime=state.uptime,
        active_sessions=state.get_active_session_count(),
        total_requests=state.request_count,
        classifier_type=state.agent.classifier.classifier_type if state.agent else "none"
    )


async def stream_events(generator):
    """将异步生成器转换为SSE流"""
    try:
        async for event in generator:
            import json
            event_json = json.dumps(event, ensure_ascii=False)
            yield f"data: {event_json}\n\n"
    except Exception as e:
        error_event = {"type": "error", "content": str(e)}
        import json
        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天端点 - 返回SSE流"""
    state.increment_request()

    async def generate():
        try:
            context = state.agent.get_or_create_context(request.session_id, request.user_id)

            # 0. Query Rewrite - 查询重写
            rewrite_result = await state.agent.query_rewriter.rewrite(
                request.message,
                request.session_id,
                context
            )

            # 发送重写结果（如果发生了改变）
            if rewrite_result["changed"]:
                yield {
                    "type": "query_rewrite",
                    "original": rewrite_result["original"],
                    "rewritten": rewrite_result["rewritten"],
                    "reason": rewrite_result["reason"]
                }

            # 使用重写后的消息进行后续处理
            user_message = rewrite_result["rewritten"]

            # 1. 发送意图识别过程
            intent_result = await state.agent.classifier.classify(user_message, context)

            # 发送意图识别结果
            yield {
                "type": "intent_recognition",
                "intent": intent_result.intent.value,
                "confidence": intent_result.confidence,
                "confidence_percent": round(intent_result.confidence * 100, 2),
                "skill": intent_result.target_skill,
                "entities": intent_result.entities,
                "query_rewritten": rewrite_result["changed"]  # 标记是否重写
            }

            # 2. 如果使用MCP工具，发送工具调用信息
            if intent_result.target_skill in ["symptom-analyzer", "department-recommender", "medication-advisor"]:
                yield {
                    "type": "tool_call",
                    "tool": intent_result.target_skill,
                    "message": f"正在调用医疗知识库..."
                }

            # 3. 生成响应
            if request.use_llm and state.llm_enabled and state.llm_service and LLM_AVAILABLE:
                # 使用LLM流式生成
                async for event in state.llm_service.generate_response_stream(
                    user_message=user_message,
                    intent=intent_result.intent.value,
                    session_id=request.session_id
                ):
                    yield event
            else:
                # 使用本地Agent（传递原始用户消息以保持上下文）
                response = await state.agent.process(
                    request.message,  # 使用原始消息保持对话连贯性
                    request.session_id,
                    request.user_id
                )
                yield {
                    "type": "content",
                    "content": response
                }
                yield {"type": "done", "content": ""}

            # 4. 检查是否需要推荐页面跳转
            confidence = intent_result.confidence

            # 高置信度 (>= 0.5): 直接推荐单个页面
            if confidence >= 0.5:
                suggested_page = get_suggested_page(
                    intent_result.intent.value,
                    confidence,
                    request.message
                )
                if suggested_page:
                    yield {
                        "type": "page_suggestion",
                        "page_info": suggested_page
                    }
            # 中低置信度 (< 0.5): 返回候选页面列表让用户选择
            else:
                # 先检查是否有智能匹配的页面
                smart_match_page = get_suggested_page(
                    intent_result.intent.value,
                    confidence,
                    request.message
                )

                # 构建候选意图列表
                all_alternatives = [{"intent": intent_result.intent.value, "confidence": confidence}]
                if hasattr(intent_result, 'alternatives') and intent_result.alternatives:
                    all_alternatives.extend(intent_result.alternatives)

                candidate_pages = get_candidate_pages(all_alternatives, request.message)

                # 如果有智能匹配的页面，将其放在候选列表最前面
                if smart_match_page:
                    # 移除已存在的相同页面
                    candidate_pages = [p for p in candidate_pages if p.get("page_id") != smart_match_page.get("page_id")]
                    # 将智能匹配的页面放在最前面
                    smart_match_page["confidence"] = "智能匹配"
                    candidate_pages.insert(0, smart_match_page)

                # 如果候选页面少于3个，添加默认的常用页面
                if len(candidate_pages) < 3:
                    default_pages = get_default_candidate_pages(candidate_pages)
                    candidate_pages.extend(default_pages)
                    candidate_pages = candidate_pages[:3]  # 最多3个

                if len(candidate_pages) >= 2:
                    yield {
                        "type": "candidate_pages",
                        "pages": candidate_pages,
                        "message": "请问您需要以下哪项服务？"
                    }
                elif len(candidate_pages) == 1:
                    yield {
                        "type": "page_suggestion",
                        "page_info": candidate_pages[0]
                    }

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield {
                "type": "error",
                "content": str(e)
            }

    return StreamingResponse(
        stream_events(generate()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )


@app.post("/api/symptom/analyze")
async def analyze_symptom(request: SymptomAnalysisRequest):
    """
    症状分析专用端点（非流式）
    接收结构化的症状数据（标签、描述、持续时间、严重程度）
    生成针对性的医疗分析
    """
    state.increment_request()

    try:
        # 构建包含所有症状信息的详细消息
        symptom_info_parts = []

        if request.symptoms:
            symptom_info_parts.append(f"症状标签：{', '.join(request.symptoms)}")

        if request.description:
            symptom_info_parts.append(f"详细描述：{request.description}")

        if request.duration:
            duration_map = {
                "today": "今天刚开始",
                "days": "1-3天",
                "week": "约一周",
                "weeks": "超过一周",
                "month": "持续一个月以上"
            }
            duration_text = duration_map.get(request.duration, request.duration)
            symptom_info_parts.append(f"持续时间：{duration_text}")

        if request.severity:
            severity_map = {
                "mild": "轻微 - 可以忍受",
                "moderate": "中度 - 有些影响生活",
                "severe": "严重 - 难以忍受"
            }
            severity_text = severity_map.get(request.severity, request.severity)
            symptom_info_parts.append(f"严重程度：{severity_text}")

        # 组合所有信息
        detailed_message = " | ".join(symptom_info_parts)

        # 使用聊天端点处理
        chat_req = ChatRequest(
            message=f"请分析我的症状：{detailed_message}",
            session_id=request.session_id,
            user_id=request.user_id,
            use_llm=False  # 使用本地模式避免超时
        )

        # 调用聊天端点
        return await chat(chat_req)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/symptom/analyze/stream")
async def analyze_symptom_stream(request: SymptomAnalysisRequest):
    """
    症状分析专用端点（流式）
    接收结构化的症状数据（标签、描述、持续时间、严重程度）
    生成针对性的医疗分析
    """
    state.increment_request()

    async def generate():
        try:
            # 构建包含所有症状信息的详细消息
            symptom_info_parts = []

            if request.symptoms:
                symptom_info_parts.append(f"症状标签：{', '.join(request.symptoms)}")

            if request.description:
                symptom_info_parts.append(f"详细描述：{request.description}")

            if request.duration:
                duration_map = {
                    "today": "今天刚开始",
                    "days": "1-3天",
                    "week": "约一周",
                    "weeks": "超过一周",
                    "month": "持续一个月以上"
                }
                duration_text = duration_map.get(request.duration, request.duration)
                symptom_info_parts.append(f"持续时间：{duration_text}")

            if request.severity:
                severity_map = {
                    "mild": "轻微 - 可以忍受",
                    "moderate": "中度 - 有些影响生活",
                    "severe": "严重 - 难以忍受"
                }
                severity_text = severity_map.get(request.severity, request.severity)
                symptom_info_parts.append(f"严重程度：{severity_text}")

            # 组合所有信息
            detailed_message = " | ".join(symptom_info_parts)

            context = state.agent.get_or_create_context(request.session_id, request.user_id)

            # 0. Query Rewrite - 查询重写
            user_message = f"请分析我的症状：{detailed_message}"
            rewrite_result = await state.agent.query_rewriter.rewrite(
                user_message,
                request.session_id,
                context
            )

            # 发送重写结果（如果发生了改变）
            if rewrite_result["changed"]:
                yield {
                    "type": "query_rewrite",
                    "original": rewrite_result["original"],
                    "rewritten": rewrite_result["rewritten"],
                    "reason": rewrite_result["reason"]
                }

            # 使用重写后的消息进行后续处理
            user_message = rewrite_result["rewritten"]

            # 1. 发送意图识别过程
            intent_result = await state.agent.classifier.classify(user_message, context)

            # 发送意图识别结果
            yield {
                "type": "intent_recognition",
                "intent": intent_result.intent.value,
                "confidence": intent_result.confidence,
                "confidence_percent": round(intent_result.confidence * 100, 2),
                "skill": intent_result.target_skill,
                "entities": intent_result.entities,
                "query_rewritten": rewrite_result["changed"]
            }

            # 2. 如果使用MCP工具，发送工具调用信息
            if intent_result.target_skill in ["symptom-analyzer", "department-recommender", "medication-advisor"]:
                yield {
                    "type": "tool_call",
                    "tool": intent_result.target_skill,
                    "message": f"正在调用医疗知识库..."
                }

            # 3. 生成响应
            if state.llm_enabled and state.llm_service and LLM_AVAILABLE:
                # 使用LLM流式生成
                async for event in state.llm_service.generate_response_stream(
                    user_message=user_message,
                    intent=intent_result.intent.value,
                    session_id=request.session_id
                ):
                    yield event
            else:
                # 使用本地Agent
                response = await state.agent.process(
                    user_message,
                    request.session_id,
                    request.user_id
                )
                yield {
                    "type": "content",
                    "content": response
                }
                yield {"type": "done", "content": ""}

            # 4. 检查是否需要推荐页面跳转
            confidence = intent_result.confidence

            # 高置信度 (>= 0.5): 直接推荐单个页面
            if confidence >= 0.5:
                suggested_page = get_suggested_page(
                    intent_result.intent.value,
                    confidence,
                    request.message
                )
                if suggested_page:
                    yield {
                        "type": "page_suggestion",
                        "page_info": suggested_page
                    }
            # 中低置信度 (< 0.5): 返回候选页面列表让用户选择
            else:
                # 先检查是否有智能匹配的页面
                smart_match_page = get_suggested_page(
                    intent_result.intent.value,
                    confidence,
                    request.message
                )

                # 构建候选意图列表
                all_alternatives = [{"intent": intent_result.intent.value, "confidence": confidence}]
                if hasattr(intent_result, 'alternatives') and intent_result.alternatives:
                    all_alternatives.extend(intent_result.alternatives)

                candidate_pages = get_candidate_pages(all_alternatives, request.message)

                # 如果有智能匹配的页面，将其放在候选列表最前面
                if smart_match_page:
                    # 移除已存在的相同页面
                    candidate_pages = [p for p in candidate_pages if p.get("page_id") != smart_match_page.get("page_id")]
                    # 将智能匹配的页面放在最前面
                    smart_match_page["confidence"] = "智能匹配"
                    candidate_pages.insert(0, smart_match_page)

                # 如果候选页面少于3个，添加默认的常用页面
                if len(candidate_pages) < 3:
                    default_pages = get_default_candidate_pages(candidate_pages)
                    candidate_pages.extend(default_pages)
                    candidate_pages = candidate_pages[:3]  # 最多3个

                if len(candidate_pages) >= 2:
                    yield {
                        "type": "candidate_pages",
                        "pages": candidate_pages,
                        "message": "请问您需要以下哪项服务？"
                    }
                elif len(candidate_pages) == 1:
                    yield {
                        "type": "page_suggestion",
                        "page_info": candidate_pages[0]
                    }

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield {
                "type": "error",
                "content": str(e)
            }

    return StreamingResponse(
        stream_events(generate()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求"""
    import time
    start_time = time.time()
    state.increment_request()

    try:
        # 创建/获取会话
        db.create_session(request.session_id, request.user_id)

        # 记录用户消息
        db.add_message(
            session_id=request.session_id,
            message_type='user',
            content=request.message
        )

        # 获取意图信息（先用本地分类器）
        context = state.agent.get_or_create_context(request.session_id, request.user_id)
        intent_result = await state.agent.classifier.classify(request.message, context)

        # 根据请求决定是否使用LLM
        if request.use_llm and state.llm_enabled and state.llm_service and LLM_AVAILABLE:
            # 使用LLM生成响应
            response = await state.llm_service.generate_response(
                user_message=request.message,
                intent=intent_result.intent.value,
                session_id=request.session_id
            )
            response_source = "qwen-plus"
        else:
            # 使用本地Agent处理
            response = await state.agent.process(
                request.message,
                request.session_id,
                request.user_id
            )
            response_source = "local"

        # 记录助手响应
        processing_time = int((time.time() - start_time) * 1000)
        db.add_message(
            session_id=request.session_id,
            message_type='assistant',
            content=response,
            intent=intent_result.intent.value if intent_result else None,
            confidence=float(intent_result.confidence) if intent_result else None,
            skill_invoked=intent_result.target_skill if intent_result else None,
            processing_time_ms=processing_time
        )

        # 更新会话状态
        db.update_session(
            request.session_id,
            last_intent=intent_result.intent.value if intent_result else None
        )

        # 获取推荐页面或候选页面
        suggested_page = None
        candidate_pages = None
        confidence = intent_result.confidence if intent_result else 0

        # 高置信度 (>= 0.6): 直接推荐单个页面
        if confidence >= 0.6:
            suggested_page = get_suggested_page(
                intent_result.intent.value,
                confidence,
                request.message
            )
        # 中等置信度 (0.3-0.6): 返回候选页面列表
        elif confidence >= 0.3 and hasattr(intent_result, 'alternatives') and intent_result.alternatives:
            # 构建候选意图列表（包含主意图）
            all_alternatives = [{"intent": intent_result.intent.value, "confidence": confidence}]
            all_alternatives.extend(intent_result.alternatives)

            candidate_pages = get_candidate_pages(all_alternatives, request.message)

            # 如果只有一个候选，直接推荐
            if len(candidate_pages) == 1:
                suggested_page = candidate_pages[0]
                candidate_pages = None
        # 低置信度但有智能匹配
        elif confidence >= 0.3:
            suggested_page = get_suggested_page(
                intent_result.intent.value,
                confidence,
                request.message
            )

        return ChatResponse(
            response=response,
            intent=intent_result.intent.value if intent_result else None,
            confidence=intent_result.confidence if intent_result else None,
            skill_invoked=intent_result.target_skill if intent_result else None,
            timestamp=datetime.now().isoformat(),
            suggested_page=suggested_page,
            candidate_pages=candidate_pages
        )

    except Exception as e:
        import traceback
        traceback.print_exc()

        # 记录错误
        db.add_message(
            session_id=request.session_id,
            message_type='system',
            content=f"Error: {str(e)}",
            intent='error'
        )

        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/clear")
async def clear_session(session_id: str = "default"):
    """清除会话"""
    # 清除内存中的上下文
    if state.agent:
        state.agent.clear_context(session_id)
        if session_id in state.sessions:
            del state.sessions[session_id]

    # 同时清除数据库中的会话
    db.delete_session(session_id)

    return {"success": True, "message": "会话已清除"}


@app.get("/api/sessions")
async def get_sessions():
    """获取所有会话（从数据库）"""
    try:
        # 查询所有会话
        import sqlite3
        conn = sqlite3.connect('/root/medical_agent/data/medical_agent.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT session_id, user_id, status, last_intent,
                   message_count, created_at, updated_at
            FROM sessions
            ORDER BY updated_at DESC
            LIMIT 100
        """)
        rows = cursor.fetchall()
        conn.close()

        sessions = [dict(row) for row in rows]
        return {"sessions": sessions}
    except Exception as e:
        return {"sessions": [], "error": str(e)}


# ============================================================
# 新增 API 端点
# ============================================================

# ------------------------------------------------------------
# 1. 慢病记录接口
# ------------------------------------------------------------

@app.post("/api/chronic/record", response_model=ChronicRecordResponse)
async def record_chronic_data(request: ChronicRecordRequest):
    """
    记录慢病监测数据

    支持的疾病类型:
    - hypertension: 高血压 (measure_data: {systolic, diastolic, heart_rate})
    - diabetes: 糖尿病 (measure_data: {fpg, ppg})
    - hyperlipidemia: 高血脂 (measure_data: {tc, tg})
    - coronary: 冠心病 (measure_data: {symptoms, medication})
    - copd: 慢阻肺 (measure_data: {spo2, symptoms})
    """
    state.increment_request()

    try:
        import uuid
        record_id = f"CR{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"

        # 分析数据状态
        disease_type = request.disease_type.lower()
        measure_data = request.measure_data

        status = "normal"
        alert = None
        advice = []
        trend = "stable"

        # 高血压分析
        if disease_type == "hypertension":
            systolic = measure_data.get("systolic", 0)
            diastolic = measure_data.get("diastolic", 0)

            if systolic >= 180 or diastolic >= 110:
                status = "high"
                alert = "血压严重升高，请立即就医！"
                advice = [
                    "立即就医或拨打120",
                    "停止活动，静卧休息",
                    "如有降压药，按医嘱服用"
                ]
            elif systolic >= 140 or diastolic >= 90:
                status = "elevated"
                alert = "血压偏高，建议监测并咨询医生"
                advice = [
                    "按时服药，不要擅自停药",
                    "低盐饮食，每日食盐<6g",
                    "规律作息，避免熬夜",
                    "如持续偏高请及时就医"
                ]
            else:
                advice = [
                    "血压控制良好，继续保持",
                    "坚持健康生活方式",
                    "定期监测血压"
                ]

        # 糖尿病分析
        elif disease_type == "diabetes":
            fpg = measure_data.get("fpg", 0)  # 空腹血糖
            ppg = measure_data.get("ppg", 0)  # 餐后血糖

            if fpg >= 7.0 or ppg >= 11.1:
                status = "elevated"
                alert = "血糖偏高，请咨询医生调整用药"
                advice = [
                    "控制饮食，减少碳水化合物摄入",
                    "适当运动，饭后散步30分钟",
                    "按时服药或注射胰岛素",
                    "定期监测血糖"
                ]
            elif fpg < 3.9:
                status = "high"
                alert = "血糖过低，请立即补充糖分！"
                advice = [
                    "立即进食糖果、饼干等含糖食物",
                    "15分钟后复测血糖",
                    "如无好转请及时就医"
                ]
            else:
                advice = [
                    "血糖控制良好，继续保持",
                    "坚持饮食控制和运动",
                    "定期监测血糖"
                ]

        # 高血脂分析
        elif disease_type == "hyperlipidemia":
            tc = measure_data.get("tc", 0)  # 总胆固醇
            tg = measure_data.get("tg", 0)  # 甘油三酯

            if tc >= 6.2 or tg >= 2.3:
                status = "elevated"
                alert = "血脂偏高，建议咨询医生"
                advice = [
                    "低脂饮食，少吃动物内脏",
                    "增加运动，控制体重",
                    "戒烟限酒",
                    "按时服药"
                ]
            else:
                advice = [
                    "血脂控制良好",
                    "继续保持健康生活方式"
                ]

        # 其他疾病类型
        else:
            advice = [
                "记录已保存",
                "如有不适请及时就医",
                "遵医嘱用药"
            ]

        # 保存到数据库（这里可以扩展为持久化存储）
        # TODO: 添加到慢病数据库

        return ChronicRecordResponse(
            record_id=record_id,
            status=status,
            trend=trend,
            alert=alert,
            advice=advice
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"记录失败: {str(e)}")


# ------------------------------------------------------------
# 2. 慢病历史接口
# ------------------------------------------------------------

@app.get("/api/chronic/history", response_model=ChronicHistoryResponse)
async def get_chronic_history(
    user_id: str,
    disease_type: Optional[str] = None,
    days: Optional[int] = 30
):
    """
    获取慢病监测历史数据

    参数:
    - user_id: 用户ID
    - disease_type: 疾病类型（可选）
    - days: 查询天数（默认30天）
    """
    state.increment_request()

    try:
        # TODO: 从数据库查询实际历史记录
        # 这里返回模拟数据
        records = []
        statistics = {
            "avg_value": 0,
            "max_value": 0,
            "min_value": 0,
            "trend": "stable",
            "abnormal_count": 0,
            "total_records": 0
        }

        return ChronicHistoryResponse(
            user_id=user_id,
            disease_type=disease_type or "all",
            records=records,
            statistics=statistics
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


# ------------------------------------------------------------
# 3. 在线问诊接口
# ------------------------------------------------------------

@app.post("/api/consult/create", response_model=ConsultCreateResponse)
async def create_consultation(request: ConsultCreateRequest):
    """
    创建在线问诊单

    支持的问诊类型:
    - text: 图文问诊（24小时响应）
    - video: 视频问诊（即时）
    - phone: 电话问诊（预约回拨）
    """
    state.increment_request()

    try:
        import uuid
        consult_id = f"CONSULT{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"

        # 根据问诊类型确定等待时间
        estimated_wait_map = {
            "text": 60,  # 图文问诊：1小时内
            "video": 5,  # 视频问诊：5分钟内
            "phone": 30  # 电话问诊：30分钟内
        }
        estimated_wait = estimated_wait_map.get(request.consult_type, 30)

        # 模拟排队位置
        queue_position = 1

        # 支付信息
        payment_info = {
            "amount": 50 if request.consult_type == "text" else 100,
            "currency": "CNY",
            "status": "pending",
            "description": "在线问诊费用"
        }

        # 保存问诊记录到数据库
        # TODO: 添加到问诊数据库

        return ConsultCreateResponse(
            consult_id=consult_id,
            status="waiting",
            queue_position=queue_position,
            estimated_wait=estimated_wait,
            payment_info=payment_info
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建问诊失败: {str(e)}")


@app.get("/api/consult/available")
async def get_available_doctors(
    department: Optional[str] = None,
    consult_type: Optional[str] = "text"
):
    """获取可用医生列表"""
    state.increment_request()

    try:
        # 模拟医生数据
        doctors = [
            {
                "doctor_id": "DOC001",
                "name": "张医生",
                "title": "主任医师",
                "department": "内科",
                "specialty": "心血管疾病",
                "experience": "20年",
                "rating": 4.9,
                "available": True,
                "consult_price": {"text": 50, "video": 100, "phone": 80}
            },
            {
                "doctor_id": "DOC002",
                "name": "李医生",
                "title": "副主任医师",
                "department": "内分泌科",
                "specialty": "糖尿病、甲状腺疾病",
                "experience": "15年",
                "rating": 4.8,
                "available": True,
                "consult_price": {"text": 40, "video": 80, "phone": 60}
            }
        ]

        # 按科室过滤
        if department:
            doctors = [d for d in doctors if d["department"] == department]

        return {"doctors": doctors, "total": len(doctors)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


# ------------------------------------------------------------
# 4. 报告解读接口
# ------------------------------------------------------------

@app.post("/api/health/report", response_model=ReportInterpretResponse)
async def interpret_health_report(request: ReportInterpretRequest):
    """
    解读健康检查报告

    支持的报告类型:
    - blood_test: 血常规
    - urine_test: 尿常规
    - liver_function: 肝功能
    - kidney_function: 肾功能
    - blood_lipids: 血脂四项
    - blood_glucose: 血糖
    - thyroid_function: 甲状腺功能
    """
    state.increment_request()

    try:
        import uuid
        report_id = f"REPORT{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"

        # 解析报告数据
        abnormal_items = []
        summary = "您的检查报告整体情况如下"
        health_suggestions = []

        report_type = request.report_type.lower()
        report_data = request.report_data

        # 血常规解读
        if report_type == "blood_test":
            # 白细胞
            wbc = report_data.get("wbc", 0)
            if wbc > 10:
                abnormal_items.append({
                    "item": "白细胞(WBC)",
                    "value": wbc,
                    "unit": "10^9/L",
                    "status": "升高",
                    "meaning": "可能存在感染或炎症"
                })
            elif wbc < 4:
                abnormal_items.append({
                    "item": "白细胞(WBC)",
                    "value": wbc,
                    "unit": "10^9/L",
                    "status": "降低",
                    "meaning": "可能存在免疫功能低下"
                })

            # 血红蛋白
            hgb = report_data.get("hgb", 0)
            if hgb < 120:
                abnormal_items.append({
                    "item": "血红蛋白(HGB)",
                    "value": hgb,
                    "unit": "g/L",
                    "status": "降低",
                    "meaning": "可能存在贫血"
                })

            # 血小板
            plt = report_data.get("plt", 0)
            if plt < 100:
                abnormal_items.append({
                    "item": "血小板(PLT)",
                    "value": plt,
                    "unit": "10^9/L",
                    "status": "降低",
                    "meaning": "注意出血倾向"
                })

        # 血脂解读
        elif report_type == "blood_lipids":
            tc = report_data.get("tc", 0)
            tg = report_data.get("tg", 0)
            ldl = report_data.get("ldl", 0)

            if tc > 5.2:
                abnormal_items.append({
                    "item": "总胆固醇(TC)",
                    "value": tc,
                    "unit": "mmol/L",
                    "status": "升高",
                    "meaning": "心血管疾病风险增加"
                })

            if tg > 1.7:
                abnormal_items.append({
                    "item": "甘油三酯(TG)",
                    "value": tg,
                    "unit": "mmol/L",
                    "status": "升高",
                    "meaning": "需要注意饮食控制"
                })

            if ldl > 3.4:
                abnormal_items.append({
                    "item": "低密度脂蛋白(LDL-C)",
                    "value": ldl,
                    "unit": "mmol/L",
                    "status": "升高",
                    "meaning": "动脉粥样硬化风险增加"
                })

        # 肝功能解读
        elif report_type == "liver_function":
            alt = report_data.get("alt", 0)
            ast = report_data.get("ast", 0)

            if alt > 50:
                abnormal_items.append({
                    "item": "谷丙转氨酶(ALT)",
                    "value": alt,
                    "unit": "U/L",
                    "status": "升高",
                    "meaning": "可能存在肝细胞损伤"
                })

            if ast > 50:
                abnormal_items.append({
                    "item": "谷草转氨酶(AST)",
                    "value": ast,
                    "unit": "U/L",
                    "status": "升高",
                    "meaning": "可能存在肝脏或心肌损伤"
                })

        # 肾功能解读
        elif report_type == "kidney_function":
            creatinine = report_data.get("creatinine", 0)
            urea = report_data.get("urea", 0)

            if creatinine > 133:
                abnormal_items.append({
                    "item": "肌酐",
                    "value": creatinine,
                    "unit": "μmol/L",
                    "status": "升高",
                    "meaning": "可能存在肾功能损害"
                })

            if urea > 7.1:
                abnormal_items.append({
                    "item": "尿素",
                    "value": urea,
                    "unit": "mmol/L",
                    "status": "升高",
                    "meaning": "需要关注肾功能"
                })

        # 血糖解读
        elif report_type == "blood_glucose":
            fpg = report_data.get("fpg", 0)
            hba1c = report_data.get("hba1c", 0)

            if fpg >= 7.0:
                abnormal_items.append({
                    "item": "空腹血糖(FPG)",
                    "value": fpg,
                    "unit": "mmol/L",
                    "status": "升高",
                    "meaning": "可能存在糖尿病"
                })

            if hba1c >= 6.5:
                abnormal_items.append({
                    "item": "糖化血红蛋白(HbA1c)",
                    "value": hba1c,
                    "unit": "%",
                    "status": "升高",
                    "meaning": "近3个月血糖控制不佳"
                })

        # 生成总结
        if abnormal_items:
            summary = f"检查发现 {len(abnormal_items)} 项异常指标"
            health_suggestions = [
                "建议及时就医，咨询专科医生",
                "保持良好的生活习惯",
                "遵医嘱进行进一步检查",
                "定期复查相关指标"
            ]
        else:
            summary = "检查指标均在正常范围内"
            health_suggestions = [
                "继续保持健康的生活方式",
                "定期体检",
                "注意饮食均衡",
                "适量运动"
            ]

        return ReportInterpretResponse(
            report_id=report_id,
            summary=summary,
            abnormal_items=abnormal_items,
            health_suggestions=health_suggestions,
            follow_up="建议1-2周后复查" if abnormal_items else "按常规体检周期复查"
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"报告解读失败: {str(e)}")


# ------------------------------------------------------------
# 5. 随访反馈接口
# ------------------------------------------------------------

@app.post("/api/followup/feedback", response_model=FollowupFeedbackResponse)
async def submit_followup_feedback(request: FollowupFeedbackRequest):
    """
    提交随访反馈

    反馈类型:
    - recovery: 康复情况反馈
    - side_effect: 副作用反馈
    - medication: 用药情况反馈
    - adverse_event: 不良事件报告
    """
    state.increment_request()

    try:
        import uuid
        feedback_id = f"FOLLOWUP{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"

        # 分析反馈
        assessment = "感谢您的反馈"
        recommendations = []
        next_followup_date = None

        feedback_type = request.feedback_type.lower()

        # 康复情况评估
        if feedback_type == "recovery":
            if not request.symptoms:
                assessment = "您的情况正在好转"
                recommendations = [
                    "继续保持当前治疗方案",
                    "注意休息，避免劳累",
                    "定期复查"
                ]
            else:
                assessment = "您仍有症状需要关注"
                recommendations = [
                    "症状持续建议及时就医",
                    "按时服药",
                    "记录症状变化"
                ]

        # 副作用评估
        elif feedback_type == "side_effect":
            assessment = "您反馈的副作用已记录"
            recommendations = [
                "请勿擅自停药",
                "及时与主治医生联系",
                "严重副作用请立即就医"
            ]

        # 用药情况评估
        elif feedback_type == "medication":
            if request.medication_compliance == "good":
                assessment = "用药依从性良好"
                recommendations = [
                    "继续保持良好的用药习惯",
                    "定期复查"
                ]
            else:
                assessment = "用药依从性需要改善"
                recommendations = [
                    "建议设置用药提醒",
                    "按时规律服药非常重要",
                    "与医生讨论用药困难"
                ]

        # 不良事件报告
        elif feedback_type == "adverse_event":
            assessment = "您的不良事件报告已记录"
            recommendations = [
                "请立即停止相关用药",
                "尽快就医处理",
                "保留相关记录和药品"
            ]

        # 计算下次随访日期
        from datetime import timedelta
        next_followup_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        # 保存反馈到数据库
        # TODO: 添加到随访数据库

        return FollowupFeedbackResponse(
            feedback_id=feedback_id,
            status="recorded",
            assessment=assessment,
            recommendations=recommendations,
            next_followup_date=next_followup_date
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"提交反馈失败: {str(e)}")


# ------------------------------------------------------------
# 6. 用户画像接口
# ------------------------------------------------------------

@app.get("/api/profile", response_model=UserProfileResponse)
async def get_user_profile(user_id: str):
    """
    获取用户画像

    包含:
    - 基础信息: 年龄、性别、地区
    - 健康标签: 高血压、糖尿病等
    - 偏好: 常去医院、偏好医生
    - 行为统计: 咨询次数、挂号次数
    - 风险等级: 低/中/高
    """
    state.increment_request()

    try:
        # 尝试从profile_service获取数据
        try:
            from services.profile_service import get_profile_service
            profile_service = get_profile_service()
            profile = await profile_service.get_or_create_profile(user_id)

            # 转换为响应格式
            health_tags = profile.chronic_conditions if hasattr(profile, 'chronic_conditions') else []
            risk_level = "low"

            # 根据健康标签评估风险等级
            if len(health_tags) >= 3:
                risk_level = "high"
            elif len(health_tags) >= 1:
                risk_level = "medium"

            return UserProfileResponse(
                user_id=profile.user_id,
                basic_info=profile.basic_info if hasattr(profile, 'basic_info') else {},
                health_tags=health_tags,
                preferences=profile.preferences if hasattr(profile, 'preferences') else {},
                behavior_stats=profile.stats if hasattr(profile, 'stats') else {},
                risk_level=risk_level
            )
        except Exception as profile_error:
            # 如果profile_service不可用，返回默认画像
            import traceback
            traceback.print_exc()

            return UserProfileResponse(
                user_id=user_id,
                basic_info={},
                health_tags=[],
                preferences={},
                behavior_stats={},
                risk_level="low"
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取用户画像失败: {str(e)}")


@app.post("/api/profile/update")
async def update_user_profile(user_id: str, update_data: dict):
    """更新用户画像"""
    state.increment_request()

    try:
        from services.profile_service import get_profile_service
        profile_service = get_profile_service()
        profile = await profile_service.get_or_create_profile(user_id)

        # 更新基本信息
        if "basic_info" in update_data:
            if hasattr(profile, 'basic_info'):
                profile.basic_info.update(update_data["basic_info"])

        # 更新偏好
        if "preferences" in update_data:
            if hasattr(profile, 'preferences'):
                profile.preferences.update(update_data["preferences"])

        # 更新时间
        profile.updated_at = datetime.now().isoformat()

        # 保存
        await profile_service.save_profile(profile)

        return {
            "success": True,
            "message": "用户画像已更新",
            "user_id": user_id
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"更新用户画像失败: {str(e)}")


# ------------------------------------------------------------
# 7. 健康档案接口
# ------------------------------------------------------------

@app.get("/api/records", response_model=HealthRecordsResponse)
async def get_health_records(user_id: str):
    """
    获取健康档案

    包含:
    - 基础信息: 血型、身高、体重、BMI
    - 病史记录: 既往病史
    - 过敏记录: 药物过敏、食物过敏
    - 用药记录: 当前用药、过往用药
    - 手术史: 手术记录
    - 家族病史: 家族疾病史
    """
    state.increment_request()

    try:
        # 尝试从profile_service获取数据
        try:
            from services.profile_service import get_profile_service
            profile_service = get_profile_service()
            profile = await profile_service.get_or_create_profile(user_id)

            # 转换为响应格式
            medical_history_list = []
            if hasattr(profile, 'medical_history') and profile.medical_history:
                for condition in profile.medical_history:
                    medical_history_list.append({
                        "condition": condition,
                        "diagnosed_date": "",
                        "status": "active"
                    })

            medication_history_list = []
            if hasattr(profile, 'current_medications') and profile.current_medications:
                for med_name, med_info in profile.current_medications.items():
                    medication_history_list.append({
                        "name": med_name,
                        "dosage": med_info.get("dosage", ""),
                        "started": med_info.get("started", ""),
                        "status": "active"
                    })

            return HealthRecordsResponse(
                user_id=profile.user_id,
                basic_info=profile.basic_info if hasattr(profile, 'basic_info') else {},
                medical_history=medical_history_list,
                allergy_history=profile.allergies if hasattr(profile, 'allergies') else [],
                medication_history=medication_history_list,
                surgery_history=[],
                family_history=[]
            )
        except Exception as profile_error:
            # 如果profile_service不可用，返回空档案
            import traceback
            traceback.print_exc()

            return HealthRecordsResponse(
                user_id=user_id,
                basic_info={},
                medical_history=[],
                allergy_history=[],
                medication_history=[],
                surgery_history=[],
                family_history=[]
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取健康档案失败: {str(e)}")


@app.post("/api/records/update")
async def update_health_records(user_id: str, record_type: str, record_data: dict):
    """
    更新健康档案

    支持的记录类型:
    - medical_history: 病史
    - allergy: 过敏史
    - medication: 用药记录
    - surgery: 手术史
    - family_history: 家族病史
    """
    state.increment_request()

    try:
        from services.profile_service import get_profile_service
        profile_service = get_profile_service()
        profile = await profile_service.get_or_create_profile(user_id)

        # 根据记录类型更新
        if record_type == "medical_history":
            if hasattr(profile, 'medical_history'):
                condition = record_data.get("condition")
                if condition and condition not in profile.medical_history:
                    profile.medical_history.append(condition)

        elif record_type == "allergy":
            if hasattr(profile, 'allergies'):
                allergy = record_data.get("allergy")
                if allergy and allergy not in profile.allergies:
                    profile.allergies.append(allergy)

        elif record_type == "medication":
            if hasattr(profile, 'current_medications'):
                med_name = record_data.get("name")
                if med_name:
                    profile.current_medications[med_name] = {
                        "dosage": record_data.get("dosage", ""),
                        "started": datetime.now().isoformat()
                    }

        elif record_type == "surgery":
            if not hasattr(profile, 'surgery_history'):
                profile.surgery_history = []
            surgery = {
                "name": record_data.get("name", ""),
                "date": record_data.get("date", ""),
                "hospital": record_data.get("hospital", "")
            }
            profile.surgery_history.append(surgery)

        elif record_type == "family_history":
            if not hasattr(profile, 'family_history'):
                profile.family_history = []
            family = {
                "relation": record_data.get("relation", ""),
                "condition": record_data.get("condition", "")
            }
            profile.family_history.append(family)

        # 更新时间
        profile.updated_at = datetime.now().isoformat()

        # 保存
        await profile_service.save_profile(profile)

        return {
            "success": True,
            "message": f"{record_type} 已更新",
            "user_id": user_id
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"更新健康档案失败: {str(e)}")


# ============================================================
# WebSocket 端点（实时对话）
# ============================================================

class ConnectionManager:
    """WebSocket连接管理器"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """广播消息"""
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket聊天端点"""
    await manager.connect(websocket)
    session_id = f"ws_{id(websocket)}"
    user_id = "ws_user"

    try:
        while True:
            data = await websocket.receive_text()

            # 处理消息
            response = await state.agent.process(data, session_id, user_id)

            # 获取意图信息
            context = state.agent.get_or_create_context(session_id, user_id)
            intent_result = context.current_intent

            # 发送响应
            await websocket.send_json({
                "response": response,
                "intent": intent_result.intent.value if intent_result else None,
                "confidence": intent_result.confidence if intent_result else None,
                "timestamp": datetime.now().isoformat()
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============================================================
# 健康检查
# ============================================================

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": state.uptime
    }


# ============================================================
# 主函数
# ============================================================

def run_server(host: str = "127.0.0.1", port: int = 8000):
    """运行服务器"""
    uvicorn.run(
        "web_api_server:app",
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="医疗智能助手 Web API 服务器")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    args = parser.parse_args()

    print(f"\n启动服务器: http://{args.host}:{args.port}")
    print(f"API 文档: http://{args.host}:{args.port}/docs")

    run_server(args.host, args.port)
