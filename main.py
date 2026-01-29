# -*- coding: utf-8 -*-
"""
医疗智能助手 - 主入口
从项目根目录运行: python main.py
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_protocol.mcp_protocol import MCPFactory
from mcp_tools.medical_tools import create_medical_mcp_server
from agent.medical_agent import MedicalAgent
from mcp_protocol.mcp_protocol import MCPClient


async def main():
    """主函数 - 演示医疗智能助手"""

    # 创建MCP基础设施
    host = MCPFactory.create_host("medical-mcp-host")
    await host.start()

    server = await create_medical_mcp_server(host)
    await server.start()

    mcp_client = MCPClient("agent-mcp-client", host)
    await mcp_client.start()

    # 创建Agent
    agent = MedicalAgent(mcp_client=mcp_client)
    await agent.start()

    print("\n" + "="*60)
    print("[Medical AI Assistant] Started")
    print("="*60 + "\n")

    # 测试对话
    test_inputs = [
        "你好",
        "我头痛好几天了",
        "头痛应该挂什么科",
        "阿莫西林怎么吃",
        "怎么预防高血压",
    ]

    for user_input in test_inputs:
        print(f"[User] {user_input}")
        response = await agent.process(user_input)
        print(f"[Agent] {response[:150]}...")
        print("-" * 60)
        await asyncio.sleep(0.3)

    # 清理
    await agent.stop()
    await mcp_client.stop()
    await server.stop()
    await host.stop()

    print("\n[Medical AI Assistant] Stopped")


if __name__ == "__main__":
    asyncio.run(main())
