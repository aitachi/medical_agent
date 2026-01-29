# -*- coding: utf-8 -*-
"""
医疗智能助手 - 交互式模式
持续运行，等待用户输入
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_protocol.mcp_protocol import MCPFactory
from mcp_tools.medical_tools import create_medical_mcp_server
from agent.medical_agent import MedicalAgent
from mcp_protocol.mcp_protocol import MCPClient


class InteractiveAssistant:
    """交互式医疗助手"""

    def __init__(self):
        self.agent = None
        self.host = None
        self.server = None
        self.client = None
        self.running = False

    async def start(self):
        """启动所有服务"""
        print("\n" + "="*60)
        print("[Medical AI Assistant] Initializing...")
        print("="*60)

        # 创建MCP基础设施
        self.host = MCPFactory.create_host("interactive-host")
        await self.host.start()

        self.server = await create_medical_mcp_server(self.host)
        await self.server.start()

        self.client = MCPClient("interactive-client", self.host)
        await self.client.start()

        # 创建Agent
        self.agent = MedicalAgent(mcp_client=self.client)
        await self.agent.start()

        self.running = True

        print("\n[Medical AI Assistant] Ready!")
        print("="*60)
        self._print_help()

    async def stop(self):
        """停止所有服务"""
        if not self.running:
            return

        print("\n[Medical AI Assistant] Shutting down...")

        await self.agent.stop()
        await self.client.stop()
        await self.server.stop()
        await self.host.stop()

        self.running = False
        print("[Medical AI Assistant] Stopped")

    def _print_help(self):
        """打印帮助信息"""
        print("\n可用命令:")
        print("  直接输入健康问题即可")
        print("  'quit' 或 'exit' - 退出")
        print("  'clear' - 清空对话历史")
        print("  'help' - 显示帮助")
        print("-" * 60)

    async def run(self):
        """运行交互循环"""
        session_id = "interactive-session"
        user_id = "user"

        print("\n请输入您的问题 (输入 'quit' 退出):\n")

        while self.running:
            try:
                # 获取用户输入
                user_input = await self._get_input()

                if not user_input:
                    continue

                # 检查退出命令
                if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                    break

                # 检查其他命令
                if user_input.lower() in ['clear', '清空']:
                    self.agent.clear_context(session_id)
                    print("\n[对话历史已清空]\n")
                    continue

                if user_input.lower() in ['help', '帮助']:
                    self._print_help()
                    continue

                # 处理用户输入
                print(f"\n[正在处理...]")
                response = await self.agent.process(user_input, session_id, user_id)

                # 显示响应
                print(f"\n{response}")
                print("-" * 60)

            except KeyboardInterrupt:
                print("\n\n检测到中断信号，正在退出...")
                break
            except Exception as e:
                print(f"\n[错误] {e}")
                continue

    async def _get_input(self) -> str:
        """获取用户输入"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, "> ")


async def main():
    """主函数"""
    assistant = InteractiveAssistant()

    try:
        await assistant.start()
        await assistant.run()
    finally:
        await assistant.stop()


if __name__ == "__main__":
    asyncio.run(main())
