"""
MCP Server 实现示例
医疗知识库 MCP Server
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum
import asyncio
import json


# ============================================================
# MCP 协议定义
# ============================================================

class MCPError(Enum):
    """MCP错误类型"""
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


@dataclass
class MCPTool:
    """MCP工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


@dataclass
class MCPRequest:
    """MCP请求"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str = ""
    params: Optional[Dict[str, Any]] = None


@dataclass
class MCPResponse:
    """MCP响应"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


# ============================================================
# MCP 工具实现
# ============================================================

class MCPToolBase(ABC):
    """MCP工具基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """输入参数Schema"""
        pass

    @property
    @abstractmethod
    def output_schema(self) -> Dict[str, Any]:
        """输出结果Schema"""
        pass

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行工具"""
        pass


class QuerySymptomTool(MCPToolBase):
    """症状查询工具"""

    @property
    def name(self) -> str:
        return "query_symptom"

    @property
    def description(self) -> str:
        return "查询症状相关信息，包括描述、可能原因和注意事项"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symptom": {
                    "type": "string",
                    "description": "症状名称"
                },
                "body_part": {
                    "type": "string",
                    "description": "身体部位"
                }
            },
            "required": ["symptom"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "possible_causes": {"type": "array", "items": {"type": "string"}},
                "red_flags": {"type": "array", "items": {"type": "string"}},
                "self_care": {"type": "array", "items": {"type": "string"}}
            }
        }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行症状查询"""
        symptom = params.get("symptom", "")
        body_part = params.get("body_part", "")

        # 模拟医学知识库查询
        # 实际应用中这里会查询真实的医学知识库

        symptom_db = {
            "疼痛": {
                "description": f"{body_part}疼痛是一种常见的症状",
                "possible_causes": ["肌肉紧张", "神经性疼痛", "炎症反应", "其他原因"],
                "red_flags": ["剧烈突发疼痛", "伴有发热", "意识改变"],
                "self_care": ["休息", "适当热敷或冷敷", "避免剧烈活动"]
            },
            "发热": {
                "description": "体温升高超过正常范围",
                "possible_causes": ["感染", "炎症", "免疫反应"],
                "red_flags": ["体温超过39°C", "持续高烧不退", "伴有意识模糊"],
                "self_care": ["多饮水", "物理降温", "注意休息"]
            },
            "咳嗽": {
                "description": "呼吸道常见的防御性反射",
                "possible_causes": ["感冒", "咽炎", "支气管炎", "过敏"],
                "red_flags": ["咳血", "呼吸困难", "持续超过2周"],
                "self_care": ["多饮温水", "避免刺激物", "保持空气湿润"]
            }
        }

        result = symptom_db.get(symptom, {
            "description": f"关于{symptom}的相关信息",
            "possible_causes": ["需要进一步诊断"],
            "red_flags": [],
            "self_care": ["建议咨询医生"]
        })

        return result


class CheckRedFlagsTool(MCPToolBase):
    """红旗征检查工具"""

    @property
    def name(self) -> str:
        return "check_red_flags"

    @property
    def description(self) -> str:
        return "检查症状是否存在危险信号（红旗征），需要紧急医疗关注的情况"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symptoms": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "body_part": {"type": "string"},
                            "symptom": {"type": "string"},
                            "severity": {"type": "string"},
                            "duration": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["symptoms"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "has_red_flag": {"type": "boolean"},
                "flags": {"type": "array", "items": {"type": "object"}},
                "urgency": {"type": "string", "enum": ["emergency", "urgent", "routine", "self_care"]},
                "action": {"type": "string"}
            }
        }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """检查红旗征"""
        symptoms = params.get("symptoms", [])

        # 定义红旗征规则
        red_flag_rules = {
            "severe": {
                "description": "症状严重程度为严重",
                "urgency": "urgent"
            },
            "sudden": {
                "description": "症状突发",
                "urgency": "urgent"
            },
            "long_duration": {
                "description": "症状持续时间过长",
                "urgency": "routine"
            }
        }

        detected_flags = []
        has_red_flag = False
        urgency = "routine"

        for symptom in symptoms:
            severity = symptom.get("severity", "")
            duration = symptom.get("duration", "")

            # 检查严重程度
            if severity == "severe":
                detected_flags.append({
                    "type": "high_severity",
                    "message": "症状严重程度较高，建议尽快就医"
                })
                has_red_flag = True
                urgency = "urgent"

            # 检查持续时间
            if duration:
                if "周" in duration or "月" in duration:
                    detected_flags.append({
                        "type": "long_duration",
                        "message": f"症状持续{duration}，建议就医检查"
                    })
                    has_red_flag = True

        action = {
            "emergency": "请立即拨打120或前往急诊",
            "urgent": "建议您尽快就医",
            "routine": "建议您预约门诊就诊",
            "self_care": "可先自行观察，注意休息"
        }.get(urgency, "建议您咨询医生")

        return {
            "has_red_flag": has_red_flag,
            "flags": detected_flags,
            "urgency": urgency,
            "action": action
        }


class GetTriageSuggestionTool(MCPToolBase):
    """分诊建议工具"""

    @property
    def name(self) -> str:
        return "get_triage_suggestion"

    @property
    def description(self) -> str:
        return "根据症状提供分诊建议，包括紧急程度和推荐科室"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symptoms": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "patient_info": {
                    "type": "object",
                    "properties": {
                        "age": {"type": "integer"},
                        "gender": {"type": "string"}
                    }
                }
            },
            "required": ["symptoms"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "urgency": {"type": "string"},
                "department": {"type": "string"},
                "possible_diagnosis": {"type": "array", "items": {"type": "string"}},
                "advice": {"type": "string"}
            }
        }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取分诊建议"""
        symptoms = params.get("symptoms", [])

        # 简单的分诊规则
        # 头部症状 → 神经内科
        # 胸部症状 → 心内科/呼吸内科
        # 腹部症状 → 消化内科
        # 皮肤症状 → 皮肤科

        department_map = {
            "头部": "神经内科",
            "头": "神经内科",
            "颈部": "骨科",
            "脖子": "骨科",
            "胸部": "心内科",
            "胸口": "呼吸内科",
            "腹部": "消化内科",
            "肚子": "消化内科",
            "皮肤": "皮肤科",
        }

        default_department = "内科"

        for symptom in symptoms:
            body_part = symptom.get("body_part", "")
            for key, dept in department_map.items():
                if key in body_part:
                    default_department = dept
                    break

        return {
            "urgency": "routine",
            "department": default_department,
            "possible_diagnosis": ["需要医生进一步诊断"],
            "advice": f"建议挂{default_department}进行详细检查"
        }


class GetReferenceRangeTool(MCPToolBase):
    """检验指标参考范围工具"""

    @property
    def name(self) -> str:
        return "get_reference_range"

    @property
    def description(self) -> str:
        return "获取医学检验指标的正常参考范围"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "indicator": {
                    "type": "string",
                    "description": "指标名称（如：白细胞计数、血红蛋白等）"
                },
                "age": {
                    "type": "integer",
                    "description": "患者年龄"
                },
                "gender": {
                    "type": "string",
                    "enum": ["male", "female", "other"],
                    "description": "患者性别"
                }
            },
            "required": ["indicator"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "indicator": {"type": "string"},
                "display_name": {"type": "string"},
                "min": {"type": "number"},
                "max": {"type": "number"},
                "unit": {"type": "string"},
                "notes": {"type": "string"}
            }
        }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取参考范围"""
        indicator = params.get("indicator", "")

        # 常见检验指标参考范围
        reference_ranges = {
            "白细胞": {
                "display_name": "白细胞计数 (WBC)",
                "min": 4.0,
                "max": 10.0,
                "unit": "×10^9/L",
                "notes": "升高可能提示感染或炎症"
            },
            "血红蛋白": {
                "display_name": "血红蛋白 (Hb)",
                "min": 120,
                "max": 160,
                "unit": "g/L",
                "notes": "低于正常值可能提示贫血"
            },
            "血小板": {
                "display_name": "血小板计数 (PLT)",
                "min": 100,
                "max": 300,
                "unit": "×10^9/L",
                "notes": "异常可能影响凝血功能"
            },
            "血糖": {
                "display_name": "空腹血糖 (FPG)",
                "min": 3.9,
                "max": 6.1,
                "unit": "mmol/L",
                "notes": "高于正常值需进一步检查糖尿病"
            }
        }

        result = reference_ranges.get(indicator, {
            "display_name": indicator,
            "min": 0,
            "max": 0,
            "unit": "N/A",
            "notes": "请联系实验室获取参考范围"
        })

        result["indicator"] = indicator
        return result


# ============================================================
# MCP Server 实现
# ============================================================

class MCPServer:
    """MCP服务器"""

    def __init__(self, server_name: str, version: str = "1.0.0"):
        self.server_name = server_name
        self.version = version
        self.tools: Dict[str, MCPToolBase] = {}
        self._initialized = False

    def register_tool(self, tool: MCPToolBase):
        """注册工具"""
        self.tools[tool.name] = tool

    async def initialize(self):
        """初始化服务器"""
        if self._initialized:
            return

        # 注册默认工具
        self.register_tool(QuerySymptomTool())
        self.register_tool(CheckRedFlagsTool())
        self.register_tool(GetTriageSuggestionTool())
        self.register_tool(GetReferenceRangeTool())

        self._initialized = True
        print(f"[MCP Server] {self.server_name} v{self.version} initialized")
        print(f"[MCP Server] Registered tools: {list(self.tools.keys())}")

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """处理MCP请求"""

        try:
            if request.method == "tools.list":
                return await self._list_tools(request)

            elif request.method == "tools.call":
                return await self._call_tool(request)

            elif request.method == "server.info":
                return await self._server_info(request)

            else:
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": MCPError.METHOD_NOT_FOUND.value,
                        "message": f"Method not found: {request.method}"
                    }
                )

        except Exception as e:
            return MCPResponse(
                id=request.id,
                error={
                    "code": MCPError.INTERNAL_ERROR.value,
                    "message": str(e)
                }
            )

    async def _list_tools(self, request: MCPRequest) -> MCPResponse:
        """列出所有工具"""
        tools_info = []
        for tool in self.tools.values():
            tools_info.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
                "outputSchema": tool.output_schema
            })

        return MCPResponse(
            id=request.id,
            result={
                "server": self.server_name,
                "tools": tools_info
            }
        )

    async def _call_tool(self, request: MCPRequest) -> MCPResponse:
        """调用工具"""
        params = request.params or {}
        tool_name = params.get("name", "")
        tool_params = params.get("parameters", {})

        if tool_name not in self.tools:
            return MCPResponse(
                id=request.id,
                error={
                    "code": MCPError.METHOD_NOT_FOUND.value,
                    "message": f"Tool not found: {tool_name}"
                }
            )

        tool = self.tools[tool_name]

        # 参数验证
        # (实际应用中应该进行完整的Schema验证)

        # 执行工具
        result = await tool.execute(tool_params)

        return MCPResponse(
            id=request.id,
            result={
                "tool": tool_name,
                "success": True,
                "data": result
            }
        )

    async def _server_info(self, request: MCPRequest) -> MCPResponse:
        """获取服务器信息"""
        return MCPResponse(
            id=request.id,
            result={
                "name": self.server_name,
                "version": self.version,
                "description": "医疗知识库 MCP Server",
                "capabilities": {
                    "tools": list(self.tools.keys())
                }
            }
        )


# ============================================================
# 使用示例
# ============================================================

async def main():
    """主函数"""

    # 创建并初始化MCP Server
    server = MCPServer("medical_knowledge", "1.0.0")
    await server.initialize()

    print("\n" + "="*60)
    print("MCP Server 测试")
    print("="*60 + "\n")

    # 测试1: 获取服务器信息
    print("[测试1] 获取服务器信息")
    response = await server.handle_request(MCPRequest(
        id="1",
        method="server.info"
    ))
    print(f"结果: {json.dumps(response.result, indent=2, ensure_ascii=False)}\n")

    # 测试2: 列出所有工具
    print("[测试2] 列出所有工具")
    response = await server.handle_request(MCPRequest(
        id="2",
        method="tools.list"
    ))
    print(f"工具数量: {len(response.result['tools'])}")
    for tool in response.result['tools']:
        print(f"  - {tool['name']}: {tool['description']}")
    print()

    # 测试3: 调用症状查询工具
    print("[测试3] 调用 query_symptom 工具")
    response = await server.handle_request(MCPRequest(
        id="3",
        method="tools.call",
        params={
            "name": "query_symptom",
            "parameters": {
                "symptom": "疼痛",
                "body_part": "头部"
            }
        }
    ))
    print(f"结果: {json.dumps(response.result['data'], indent=2, ensure_ascii=False)}\n")

    # 测试4: 调用红旗征检查工具
    print("[测试4] 调用 check_red_flags 工具")
    response = await server.handle_request(MCPRequest(
        id="4",
        method="tools.call",
        params={
            "name": "check_red_flags",
            "parameters": {
                "symptoms": [
                    {
                        "body_part": "头部",
                        "symptom": "疼痛",
                        "severity": "severe",
                        "duration": "3天"
                    }
                ]
            }
        }
    ))
    print(f"结果: {json.dumps(response.result['data'], indent=2, ensure_ascii=False)}\n")

    # 测试5: 调用分诊建议工具
    print("[测试5] 调用 get_triage_suggestion 工具")
    response = await server.handle_request(MCPRequest(
        id="5",
        method="tools.call",
        params={
            "name": "get_triage_suggestion",
            "parameters": {
                "symptoms": [
                    {
                        "body_part": "头部",
                        "symptom": "疼痛"
                    }
                ]
            }
        }
    ))
    print(f"结果: {json.dumps(response.result['data'], indent=2, ensure_ascii=False)}\n")

    # 测试6: 调用参考范围工具
    print("[测试6] 调用 get_reference_range 工具")
    response = await server.handle_request(MCPRequest(
        id="6",
        method="tools.call",
        params={
            "name": "get_reference_range",
            "parameters": {
                "indicator": "白细胞",
                "age": 30
            }
        }
    ))
    print(f"结果: {json.dumps(response.result['data'], indent=2, ensure_ascii=False)}\n")


if __name__ == "__main__":
    asyncio.run(main())
