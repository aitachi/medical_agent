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
from agent.llm_service import init_llm_service, shutdown_llm_service, get_llm_service


# ============================================================
# LLM 配置
# ============================================================

DASHSCOPE_API_KEY = "sk-a9a4edb1b4214016baa11c9be3b9fec4"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_MODEL = "qwen-plus"


# ============================================================
# Pydantic 模型
# ============================================================

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: Optional[str] = "default"
    user_id: Optional[str] = "anonymous"
    use_llm: Optional[bool] = True  # 是否使用LLM增强响应


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    skill_invoked: Optional[str] = None
    timestamp: str


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
# FastAPI 应用
# ============================================================

app = FastAPI(
    title="医疗智能助手 API",
    description="基于MLP意图识别的医疗健康咨询助手",
    version="1.0.0"
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
            # 1. 发送意图识别过程
            context = state.agent.get_or_create_context(request.session_id, request.user_id)
            intent_result = await state.agent.classifier.classify(request.message, context)

            # 发送意图识别结果
            yield {
                "type": "intent_recognition",
                "intent": intent_result.intent.value,
                "confidence": intent_result.confidence,
                "confidence_percent": round(intent_result.confidence * 100, 2),
                "skill": intent_result.target_skill,
                "entities": intent_result.entities
            }

            # 2. 如果使用MCP工具，发送工具调用信息
            if intent_result.target_skill in ["symptom-analyzer", "department-recommender", "medication-advisor"]:
                yield {
                    "type": "tool_call",
                    "tool": intent_result.target_skill,
                    "message": f"正在调用医疗知识库..."
                }

            # 3. 生成响应
            if request.use_llm and state.llm_enabled and state.llm_service:
                # 使用LLM流式生成
                async for event in state.llm_service.generate_response_stream(
                    user_message=request.message,
                    intent=intent_result.intent.value,
                    session_id=request.session_id
                ):
                    yield event
            else:
                # 使用本地Agent
                response = await state.agent.process(
                    request.message,
                    request.session_id,
                    request.user_id
                )
                yield {
                    "type": "content",
                    "content": response
                }
                yield {"type": "done", "content": ""}

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
    state.increment_request()

    try:
        # 获取意图信息（先用本地分类器）
        context = state.agent.get_or_create_context(request.session_id, request.user_id)
        intent_result = await state.agent.classifier.classify(request.message, context)

        # 根据请求决定是否使用LLM
        if request.use_llm and state.llm_enabled and state.llm_service:
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

        return ChatResponse(
            response=response,
            intent=intent_result.intent.value if intent_result else None,
            confidence=intent_result.confidence if intent_result else None,
            skill_invoked=intent_result.target_skill if intent_result else None,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/clear")
async def clear_session(session_id: str = "default"):
    """清除会话"""
    if state.agent:
        state.agent.clear_context(session_id)
        if session_id in state.sessions:
            del state.sessions[session_id]
    return {"success": True, "message": "会话已清除"}


@app.get("/api/sessions")
async def get_sessions():
    """获取所有会话"""
    sessions = []
    for session_id, session_data in state.sessions.items():
        sessions.append({
            "session_id": session_id,
            "user_id": session_data.get("user_id", ""),
            "created_at": session_data.get("created_at", ""),
            "message_count": session_data.get("message_count", 0)
        })
    return {"sessions": sessions}


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
