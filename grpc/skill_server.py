"""
gRPC Skill 服务器实现
提供高性能的Skill服务部署
"""

import asyncio
import grpc
from concurrent import futures
import logging
import time
import json
from typing import Dict, List
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 模拟grpc模块（实际使用时需要安装grpcio和grpcio-tools）
# 这里提供接口定义，实际部署时需要生成Python代码

# ============================================================
# 服务状态管理
# ============================================================

class ServiceStatus:
    """服务状态"""
    def __init__(self):
        self.start_time = time.time()
        self.active_sessions: Dict[str, Dict] = {}
        self.request_count = 0
        self.error_count = 0

    @property
    def uptime(self) -> str:
        """获取运行时间"""
        uptime_seconds = time.time() - self.start_time
        uptime_delta = timedelta(seconds=int(uptime_seconds))
        return str(uptime_delta)

    @property
    def active_session_count(self) -> int:
        """获取活跃会话数"""
        return len(self.active_sessions)

    def add_session(self, session_id: str, user_id: str):
        """添加会话"""
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "start_time": datetime.now().isoformat(),
            "last_activity": time.time()
        }

    def remove_session(self, session_id: str):
        """移除会话"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

    def update_session_activity(self, session_id: str):
        """更新会话活动时间"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = time.time()

    def increment_request(self):
        """增加请求计数"""
        self.request_count += 1

    def increment_error(self):
        """增加错误计数"""
        self.error_count += 1

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "uptime": self.uptime,
            "active_sessions": self.active_session_count,
            "request_count": self.request_count,
            "error_count": self.error_count
        }


# ============================================================
# gRPC 服务实现
# ============================================================

class MedicalAgentServicer:
    """
    医疗Agent gRPC服务实现
    """

    def __init__(self, agent):
        self.agent = agent
        self.status = ServiceStatus()

    def ProcessInput(self, request, context):
        """处理用户输入"""
        start_time = time.time()
        self.status.increment_request()

        try:
            # 更新会话活动
            session_id = request.session_id or "default"
            user_id = request.user_id or "anonymous"
            self.status.update_session_activity(session_id)

            # 处理输入
            response_text = asyncio.run(
                self.agent.process(
                    user_input=request.user_input,
                    session_id=session_id,
                    user_id=user_id
                )
            )

            # 获取意图信息
            ctx = self.agent.get_context(session_id)
            intent_result = None
            if ctx and ctx.history:
                last_turn = ctx.history[-1]
                intent_result = {
                    "intent": last_turn.get("intent", "unknown"),
                    "confidence": last_turn.get("confidence", 0.0)
                }

            processing_time = time.time() - start_time

            return {
                "response": response_text,
                "intent": intent_result,
                "skill_used": intent_result.get("intent") if intent_result else "",
                "processing_time": processing_time
            }

        except Exception as e:
            self.status.increment_error()
            logger.error(f"ProcessInput error: {e}")
            return {
                "response": f"处理出错: {str(e)}",
                "intent": None,
                "skill_used": "",
                "processing_time": time.time() - start_time
            }

    def HealthCheck(self, request, context):
        """健康检查"""
        stats = self.status.get_stats()

        return {
            "healthy": True,
            "version": "1.0.0",
            "uptime": stats["uptime"],
            "active_sessions": stats["active_sessions"]
        }

    def Heartbeat(self, request, context):
        """心跳"""
        return {
            "service_id": "medical-agent-grpc",
            "timestamp": int(time.time()),
            "status": "running"
        }

    def GetSessionHistory(self, request, context):
        """获取会话历史"""
        ctx = self.agent.get_context(request.session_id)
        if ctx:
            for turn in ctx.history:
                yield {
                    "success": True,
                    "content": f"用户: {turn['user_input']}\n助手: {turn['agent_response']}"
                }

    def ClearSession(self, request, context):
        """清除会话"""
        self.agent.clear_context(request.session_id)
        self.status.remove_session(request.session_id)

        return {
            "success": True,
            "content": f"会话 {request.session_id} 已清除"
        }


class SymptomAnalyzerServicer:
    """症状分析服务"""

    def __init__(self, agent):
        self.agent = agent
        self.status = ServiceStatus()

    def AnalyzeSymptom(self, request, context):
        """分析症状"""
        start_time = time.time()
        self.status.increment_request()

        try:
            # 构建Skill请求
            from agent.medical_agent import SkillRequest, IntentType

            skill_request = SkillRequest(
                skill_name="symptom-analyzer",
                intent=IntentType.SYMPTOM_INQUIRY,
                entities=dict(request.entities),
                context=None,
                metadata={"user_input": request.metadata.get("user_input", "")}
            )

            # 调用Skill
            response = asyncio.run(
                self.agent.skill_invoker.invoke(skill_request)
            )

            return {
                "success": response.success,
                "content": response.content,
                "error": response.error,
                "need_clarification": response.need_clarification,
                "follow_up_suggestions": response.follow_up_suggestions
            }

        except Exception as e:
            self.status.increment_error()
            logger.error(f"AnalyzeSymptom error: {e}")
            return {
                "success": False,
                "content": "",
                "error": str(e)
            }


class DepartmentRecommenderServicer:
    """科室推荐服务"""

    def __init__(self, agent):
        self.agent = agent
        self.status = ServiceStatus()

    def RecommendDepartment(self, request, context):
        """推荐科室"""
        start_time = time.time()
        self.status.increment_request()

        try:
            from agent.medical_agent import SkillRequest, IntentType

            skill_request = SkillRequest(
                skill_name="department-recommender",
                intent=IntentType.DEPARTMENT_QUERY,
                entities=dict(request.entities),
                context=None,
                metadata={}
            )

            response = asyncio.run(
                self.agent.skill_invoker.invoke(skill_request)
            )

            return {
                "success": response.success,
                "content": response.content,
                "error": response.error
            }

        except Exception as e:
            self.status.increment_error()
            return {
                "success": False,
                "content": "",
                "error": str(e)
            }


class MedicationAdvisorServicer:
    """用药咨询服务"""

    def __init__(self, agent):
        self.agent = agent
        self.status = ServiceStatus()

    def AdviseMedication(self, request, context):
        """用药咨询"""
        start_time = time.time()
        self.status.increment_request()

        try:
            from agent.medical_agent import SkillRequest, IntentType

            skill_request = SkillRequest(
                skill_name="medication-advisor",
                intent=IntentType.MEDICATION_CONSULT,
                entities=dict(request.entities),
                context=None,
                metadata={}
            )

            response = asyncio.run(
                self.agent.skill_invoker.invoke(skill_request)
            )

            return {
                "success": response.success,
                "content": response.content,
                "error": response.error
            }

        except Exception as e:
            self.status.increment_error()
            return {
                "success": False,
                "content": "",
                "error": str(e)
            }


# ============================================================
# gRPC 服务器
# ============================================================

class SkillGRPCServer:
    """
    Skill gRPC服务器
    """

    def __init__(
        self,
        agent,
        host: str = "[::]",
        port: int = 50051,
        max_workers: int = 10
    ):
        self.agent = agent
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self.server = None

    def start(self):
        """启动gRPC服务器"""
        logger.info(f"Starting gRPC server on {self.host}:{self.port}")

        # 创建gRPC服务器
        # self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=self.max_workers))

        # 注册服务
        # medical_pb2_grpc.add_MedicalAgentServiceServicer_to_server(
        #     MedicalAgentServicer(self.agent), self.server
        # )
        # medical_pb2_grpc.add_SymptomAnalyzerServiceServicer_to_server(
        #     SymptomAnalyzerServicer(self.agent), self.server
        # )
        # medical_pb2_grpc.add_DepartmentRecommenderServiceServicer_to_server(
        #     DepartmentRecommenderServicer(self.agent), self.server
        # )
        # medical_pb2_grpc.add_MedicationAdvisorServiceServicer_to_server(
        #     MedicationAdvisorServicer(self.agent), self.server
        # )

        # 添加监听端口
        # self.server.add_insecure_port(f"{self.host}:{self.port}")
        # self.server.start()

        logger.info(f"gRPC server started on {self.host}:{self.port}")
        logger.info("Available services:")
        logger.info("  - MedicalAgentService")
        logger.info("  - SymptomAnalyzerService")
        logger.info("  - DepartmentRecommenderService")
        logger.info("  - MedicationAdvisorService")

    def stop(self, grace_period: int = 5):
        """停止gRPC服务器"""
        if self.server:
            logger.info("Stopping gRPC server...")
            # self.server.stop(grace_period)
            logger.info("gRPC server stopped")

    def wait_for_termination(self):
        """等待服务器终止"""
        if self.server:
            # self.server.wait_for_termination()
            pass


# ============================================================
# 启动脚本
# ============================================================

async def run_grpc_server():
    """运行gRPC服务器"""
    from agent.medical_agent import MedicalAgent
    from mcp_tools.medical_tools import create_medical_mcp_server, MCPFactory
    from mcp_protocol.mcp_protocol import MCPClient

    # 初始化MCP基础设施
    host = MCPFactory.create_host("medical-mcp-host")
    await host.start()

    mcp_server = await create_medical_mcp_server(host)
    await mcp_server.start()

    mcp_client = MCPClient("agent-mcp-client", host)
    await mcp_client.start()

    # 创建Agent
    agent = MedicalAgent(mcp_client=mcp_client)
    await agent.start()

    # 启动gRPC服务器
    grpc_server = SkillGRPCServer(agent, host="0.0.0.0", port=50051)
    grpc_server.start()

    logger.info("All services started. Press Ctrl+C to stop.")

    try:
        # grpc_server.wait_for_termination()
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        grpc_server.stop()
        await agent.stop()
        await mcp_client.stop()
        await mcp_server.stop()
        await host.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_grpc_server())
