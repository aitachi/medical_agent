"""
MCP (Medical Context Protocol) 协议实现
包含 Host、Server、Client 三层架构和注册机制
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Callable, Awaitable
from enum import Enum
import uuid
from datetime import datetime
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# MCP 协议定义
# ============================================================

class MCPMessageType(Enum):
    """MCP消息类型"""
    # 注册相关
    REGISTER = "register"
    REGISTER_RESPONSE = "register_response"
    DEREGISTER = "deregister"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_RESPONSE = "heartbeat_response"

    # 服务发现
    DISCOVER = "discover"
    DISCOVER_RESPONSE = "discover_response"
    LIST_TOOLS = "list_tools"
    LIST_TOOLS_RESPONSE = "list_tools_response"

    # 工具调用
    CALL_TOOL = "call_tool"
    CALL_TOOL_RESPONSE = "call_tool_response"
    TOOL_ERROR = "tool_error"

    # 订阅
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    EVENT = "event"


class MCPStatus(Enum):
    """MCP状态"""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class MCPMessage:
    """MCP消息"""
    message_type: MCPMessageType
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    receiver_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    status: MCPStatus = MCPStatus.RUNNING
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "MCPMessage":
        data["message_type"] = MCPMessageType(data["message_type"])
        if "status" in data:
            data["status"] = MCPStatus(data["status"])
        return cls(**data)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "MCPMessage":
        return cls.from_dict(json.loads(json_str))


@dataclass
class MCPTool:
    """MCP工具定义"""
    name: str
    description: str
    category: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    server_id: str = ""
    timeout: int = 30
    rate_limit: int = 100  # 每分钟调用次数限制
    version: str = "1.0.0"

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MCPServerInfo:
    """MCP服务器信息"""
    server_id: str
    name: str
    host: str
    port: int
    protocol: str = "grpc"
    status: MCPStatus = MCPStatus.STARTING
    tools: List[str] = field(default_factory=list)
    last_heartbeat: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class MCPCallResult:
    """MCP调用结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    tool_name: str = ""
    execution_time: float = 0.0
    server_id: str = ""


# ============================================================
# MCP Transport 层
# ============================================================

class MCPTransport(ABC):
    """MCP传输层抽象"""

    @abstractmethod
    async def send(self, message: MCPMessage, destination: str) -> bool:
        """发送消息"""
        pass

    @abstractmethod
    async def receive(self) -> Optional[MCPMessage]:
        """接收消息"""
        pass

    @abstractmethod
    async def start(self):
        """启动传输层"""
        pass

    @abstractmethod
    async def stop(self):
        """停止传输层"""
        pass


class InMemoryTransport(MCPTransport):
    """内存传输层（用于测试）"""

    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = {}
        self._running = False

    def get_queue(self, destination: str) -> asyncio.Queue:
        if destination not in self.queues:
            self.queues[destination] = asyncio.Queue()
        return self.queues[destination]

    async def send(self, message: MCPMessage, destination: str) -> bool:
        queue = self.get_queue(destination)
        await queue.put(message)
        return True

    async def receive(self) -> Optional[MCPMessage]:
        # 这个方法需要指定接收者，实际使用时会有特定实现
        return None

    async def start(self):
        self._running = True

    async def stop(self):
        self._running = False


# 全局传输层实例
_global_transport = InMemoryTransport()


# ============================================================
# MCP Host (注册中心)
# ============================================================

class MCPHost:
    """
    MCP Host - 注册中心
    负责管理所有MCP Server的注册、发现和健康检查
    """

    def __init__(self, host_id: str = "mcp-host", transport: Optional[MCPTransport] = None):
        self.host_id = host_id
        self.transport = transport or _global_transport
        self.servers: Dict[str, MCPServerInfo] = {}
        self.tools: Dict[str, MCPTool] = {}  # tool_name -> MCPTool
        self.server_tools: Dict[str, List[str]] = {}  # server_id -> [tool_names]
        self.subscriptions: Dict[str, List[str]] = {}  # client_id -> [tool_names]
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """启动Host"""
        logger.info(f"[MCP Host] {self.host_id} starting...")
        await self.transport.start()
        self._running = True

        # 启动心跳检查
        self._heartbeat_task = asyncio.ensure_future(self._heartbeat_loop())

        # 启动消息处理
        asyncio.ensure_future(self._message_loop())

        logger.info(f"[MCP Host] {self.host_id} started")

    async def stop(self):
        """停止Host"""
        logger.info(f"[MCP Host] {self.host_id} stopping...")
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        await self.transport.stop()
        logger.info(f"[MCP Host] {self.host_id} stopped")

    async def register_server(
        self,
        server_info: MCPServerInfo,
        tools: List[MCPTool]
    ) -> bool:
        """注册服务器"""
        logger.info(f"[MCP Host] Registering server: {server_info.server_id}")

        server_info.status = MCPStatus.RUNNING
        server_info.last_heartbeat = datetime.now().isoformat()
        self.servers[server_info.server_id] = server_info

        # 注册工具
        for tool in tools:
            tool.server_id = server_info.server_id
            self.tools[tool.name] = tool

        self.server_tools[server_info.server_id] = [t.name for t in tools]

        logger.info(f"[MCP Host] Server {server_info.server_id} registered with {len(tools)} tools")
        return True

    async def deregister_server(self, server_id: str) -> bool:
        """注销服务器"""
        logger.info(f"[MCP Host] Deregistering server: {server_id}")

        if server_id in self.servers:
            # 移除工具
            tool_names = self.server_tools.get(server_id, [])
            for tool_name in tool_names:
                if tool_name in self.tools:
                    del self.tools[tool_name]

            del self.servers[server_id]
            if server_id in self.server_tools:
                del self.server_tools[server_id]

            logger.info(f"[MCP Host] Server {server_id} deregistered")
            return True

        return False

    async def discover_tools(self, category: Optional[str] = None) -> List[MCPTool]:
        """发现工具"""
        tools = list(self.tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        return tools

    async def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """获取工具"""
        return self.tools.get(tool_name)

    async def get_server(self, server_id: str) -> Optional[MCPServerInfo]:
        """获取服务器信息"""
        return self.servers.get(server_id)

    async def list_servers(self) -> List[MCPServerInfo]:
        """列出所有服务器"""
        return list(self.servers.values())

    async def subscribe_tools(self, client_id: str, tool_names: List[str]) -> bool:
        """订阅工具"""
        for tool_name in tool_names:
            if tool_name not in self.tools:
                logger.warning(f"[MCP Host] Tool {tool_name} not found for subscription")
                continue

        if client_id not in self.subscriptions:
            self.subscriptions[client_id] = []

        self.subscriptions[client_id].extend(tool_names)
        # 去重
        self.subscriptions[client_id] = list(set(self.subscriptions[client_id]))

        logger.info(f"[MCP Host] Client {client_id} subscribed to {len(tool_names)} tools")
        return True

    async def unsubscribe_tools(self, client_id: str, tool_names: List[str]) -> bool:
        """取消订阅"""
        if client_id in self.subscriptions:
            for tool_name in tool_names:
                if tool_name in self.subscriptions[client_id]:
                    self.subscriptions[client_id].remove(tool_name)
            return True
        return False

    async def _message_loop(self):
        """消息处理循环"""
        while self._running:
            try:
                # 处理注册消息等
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MCP Host] Message loop error: {e}")

    async def _heartbeat_loop(self):
        """心跳检查循环"""
        while self._running:
            try:
                await asyncio.sleep(10)  # 每10秒检查一次

                now = datetime.now()
                dead_servers = []

                for server_id, server_info in self.servers.items():
                    # Python 3.6 兼容：使用 strptime 替代 fromisoformat
                    try:
                        last_hb = datetime.strptime(server_info.last_heartbeat, "%Y-%m-%dT%H:%M:%S.%f")
                    except ValueError:
                        # 如果没有微秒部分，尝试不带 %f 的格式
                        last_hb = datetime.strptime(server_info.last_heartbeat, "%Y-%m-%dT%H:%M:%S")
                    if (now - last_hb).total_seconds() > 30:  # 30秒无心跳
                        logger.warning(f"[MCP Host] Server {server_id} heartbeat timeout")
                        dead_servers.append(server_id)

                for server_id in dead_servers:
                    await self.deregister_server(server_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MCP Host] Heartbeat loop error: {e}")


# ============================================================
# MCP Server (服务提供方)
# ============================================================

class MCPToolHandler(ABC):
    """MCP工具处理器基类"""

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行工具"""
        pass


class MCPServer:
    """
    MCP Server - 服务提供方
    提供具体的工具实现
    """

    def __init__(
        self,
        server_id: str,
        name: str,
        host: str,
        port: int,
        mcp_host: MCPHost,
        protocol: str = "grpc"
    ):
        self.server_id = server_id
        self.name = name
        self.host = host
        self.port = port
        self.protocol = protocol
        self.mcp_host = mcp_host
        self.tools: Dict[str, MCPToolHandler] = {}
        self.tool_definitions: List[MCPTool] = []
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None

    def register_tool(self, tool_definition: MCPTool, handler: MCPToolHandler):
        """注册工具处理器"""
        self.tools[tool_definition.name] = handler
        tool_definition.server_id = self.server_id
        self.tool_definitions.append(tool_definition)
        logger.info(f"[MCP Server {self.server_id}] Registered tool: {tool_definition.name}")

    async def start(self):
        """启动服务器"""
        logger.info(f"[MCP Server {self.server_id}] Starting on {self.host}:{self.port}...")

        # 创建服务器信息
        server_info = MCPServerInfo(
            server_id=self.server_id,
            name=self.name,
            host=self.host,
            port=self.port,
            protocol=self.protocol,
            tools=[t.name for t in self.tool_definitions],
            status=MCPStatus.RUNNING
        )

        # 注册到Host
        await self.mcp_host.register_server(server_info, self.tool_definitions)

        self._running = True

        # 启动心跳
        self._heartbeat_task = asyncio.ensure_future(self._heartbeat_loop())

        logger.info(f"[MCP Server {self.server_id}] Started with {len(self.tool_definitions)} tools")

    async def stop(self):
        """停止服务器"""
        logger.info(f"[MCP Server {self.server_id}] Stopping...")

        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # 从Host注销
        await self.mcp_host.deregister_server(self.server_id)

        logger.info(f"[MCP Server {self.server_id}] Stopped")

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPCallResult:
        """执行工具"""
        import time
        start_time = time.time()

        if tool_name not in self.tools:
            return MCPCallResult(
                success=False,
                error=f"Tool {tool_name} not found",
                tool_name=tool_name,
                server_id=self.server_id
            )

        try:
            handler = self.tools[tool_name]
            result = await handler.execute(params)

            execution_time = time.time() - start_time

            return MCPCallResult(
                success=True,
                data=result,
                tool_name=tool_name,
                execution_time=execution_time,
                server_id=self.server_id
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[MCP Server {self.server_id}] Tool {tool_name} error: {e}")

            return MCPCallResult(
                success=False,
                error=str(e),
                tool_name=tool_name,
                execution_time=execution_time,
                server_id=self.server_id
            )

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self._running:
            try:
                await asyncio.sleep(5)  # 每5秒发送心跳

                # 更新心跳时间
                for server in await self.mcp_host.list_servers():
                    if server.server_id == self.server_id:
                        server.last_heartbeat = datetime.now().isoformat()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MCP Server {self.server_id}] Heartbeat error: {e}")


# ============================================================
# MCP Client (服务消费方)
# ============================================================

class MCPClient:
    """
    MCP Client - 服务消费方
    调用MCP Server提供的工具
    """

    def __init__(
        self,
        client_id: str,
        mcp_host: MCPHost,
        transport: Optional[MCPTransport] = None
    ):
        self.client_id = client_id
        self.mcp_host = mcp_host
        self.transport = transport or _global_transport
        self._server_connections: Dict[str, MCPServer] = {}
        self._running = False

    async def start(self):
        """启动客户端"""
        logger.info(f"[MCP Client {self.client_id}] Starting...")
        await self.transport.start()
        self._running = True
        logger.info(f"[MCP Client {self.client_id}] Started")

    async def stop(self):
        """停止客户端"""
        logger.info(f"[MCP Client {self.client_id}] Stopping...")
        self._running = False
        await self.transport.stop()
        logger.info(f"[MCP Client {self.client_id}] Stopped")

    async def discover_tools(self, category: Optional[str] = None) -> List[MCPTool]:
        """发现可用工具"""
        return await self.mcp_host.discover_tools(category)

    async def list_tools(self) -> List[MCPTool]:
        """列出所有工具"""
        return await self.discover_tools()

    async def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        timeout: float = 30.0
    ) -> MCPCallResult:
        """调用工具"""
        logger.info(f"[MCP Client {self.client_id}] Calling tool: {tool_name}")

        # 获取工具定义
        tool = await self.mcp_host.get_tool(tool_name)
        if not tool:
            return MCPCallResult(
                success=False,
                error=f"Tool {tool_name} not found",
                tool_name=tool_name
            )

        # 获取服务器连接
        server = await self._get_server_connection(tool.server_id)
        if not server:
            return MCPCallResult(
                success=False,
                error=f"Server {tool.server_id} not available",
                tool_name=tool_name
            )

        # 执行工具
        try:
            result = await asyncio.wait_for(
                server.execute_tool(tool_name, params),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            return MCPCallResult(
                success=False,
                error=f"Tool {tool_name} execution timeout",
                tool_name=tool_name
            )
        except Exception as e:
            return MCPCallResult(
                success=False,
                error=str(e),
                tool_name=tool_name
            )

    async def _get_server_connection(self, server_id: str) -> Optional[MCPServer]:
        """获取服务器连接"""
        # 简化实现：直接从Host获取服务器信息
        # 实际gRPC实现中会建立真实的连接
        server_info = await self.mcp_host.get_server(server_id)
        if not server_info:
            return None

        # 这里应该建立gRPC连接
        # 简化实现中我们直接返回一个代理对象
        if server_id not in self._server_connections:
            self._server_connections[server_id] = await self._create_server_proxy(server_info)

        return self._server_connections[server_id]

    async def _create_server_proxy(self, server_info: MCPServerInfo) -> "MCPServerProxy":
        """创建服务器代理"""
        return MCPServerProxy(server_info, self.mcp_host)

    async def subscribe_tools(self, tool_names: List[str]) -> bool:
        """订阅工具更新"""
        return await self.mcp_host.subscribe_tools(self.client_id, tool_names)


class MCPServerProxy:
    """MCP服务器代理（用于Client调用Server）"""

    def __init__(self, server_info: MCPServerInfo, mcp_host: MCPHost):
        self.server_info = server_info
        self.mcp_host = mcp_host

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPCallResult:
        """执行工具（通过Host转发）"""
        # 在实际gRPC实现中，这里会进行远程调用
        # 简化实现中我们直接从注册的工具处理器中获取结果

        # 这里需要访问实际的Server实例的处理器
        # 为了简化，我们返回一个模拟结果
        logger.info(f"[MCP Proxy] Executing {tool_name} on {self.server_info.server_id}")

        # 实际gRPC调用会在这里
        return MCPCallResult(
            success=True,
            data={"message": f"Executed {tool_name}", "params": params},
            tool_name=tool_name,
            server_id=self.server_info.server_id
        )


# ============================================================
# MCP 工厂
# ============================================================

class MCPFactory:
    """MCP组件工厂"""

    @staticmethod
    def create_host(host_id: str = "mcp-host") -> MCPHost:
        """创建Host"""
        return MCPHost(host_id=host_id)

    @staticmethod
    def create_server(
        server_id: str,
        name: str,
        host: str,
        port: int,
        mcp_host: MCPHost,
        protocol: str = "grpc"
    ) -> MCPServer:
        """创建Server"""
        return MCPServer(
            server_id=server_id,
            name=name,
            host=host,
            port=port,
            mcp_host=mcp_host,
            protocol=protocol
        )

    @staticmethod
    def create_client(
        client_id: str,
        mcp_host: MCPHost
    ) -> MCPClient:
        """创建Client"""
        return MCPClient(
            client_id=client_id,
            mcp_host=mcp_host
        )


# ============================================================
# 使用示例
# ============================================================

async def main():
    """演示MCP协议的使用"""

    # 创建Host
    host = MCPFactory.create_host("medical-mcp-host")
    await host.start()

    print("\n=== MCP Host Started ===")
    print(f"Host ID: {host.host_id}")
    print(f"Registered Servers: {len(host.servers)}")
    print(f"Registered Tools: {len(host.tools)}")

    # 等待一段时间
    await asyncio.sleep(2)

    # 停止Host
    await host.stop()
    print("\n=== MCP Host Stopped ===")


if __name__ == "__main__":
    asyncio.run(main())
