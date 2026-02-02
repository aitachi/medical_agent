# -*- coding: utf-8 -*-
"""
Query Rewrite 模块 - 使用LLM重写和优化用户输入
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class QueryRewriter:
    """
    查询重写器 - 使用LLM优化用户输入
    """

    def __init__(self, llm_client=None):
        """
        初始化查询重写器

        Args:
            llm_client: LLM客户端（可选）
        """
        self.llm_client = llm_client
        self.rewrite_history = {}  # session_id -> [(original, rewritten)]

    async def rewrite(
        self,
        user_input: str,
        session_id: str = "default",
        context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        重写用户输入

        Args:
            user_input: 原始用户输入
            session_id: 会话ID
            context: 对话上下文

        Returns:
            Dict containing:
                - original: 原始输入
                - rewritten: 重写后的输入
                - changed: 是否发生了改变
                - reason: 重写原因
        """
        # 1. 检查是否需要重写
        needs_rewrite, reason = self._check_needs_rewrite(user_input)

        if not needs_rewrite:
            return {
                "original": user_input,
                "rewritten": user_input,
                "changed": False,
                "reason": "输入清晰，无需重写"
            }

        # 2. 执行重写
        if self.llm_client:
            rewritten = await self._rewrite_with_llm(user_input, context)
        else:
            rewritten = await self._rewrite_with_rules(user_input, context)

        # 3. 判断是否改变
        changed = (rewritten != user_input)

        # 4. 记录历史
        if session_id not in self.rewrite_history:
            self.rewrite_history[session_id] = []
        self.rewrite_history[session_id].append({
            "original": user_input,
            "rewritten": rewritten,
            "reason": reason
        })

        logger.info(f"[QueryRewrite] '{user_input[:30]}...' -> '{rewritten[:30]}...'")

        return {
            "original": user_input,
            "rewritten": rewritten,
            "changed": changed,
            "reason": reason
        }

    def _check_needs_rewrite(self, user_input: str) -> tuple:
        """
        检查是否需要重写

        Returns:
            (是否需要重写, 原因)
        """
        # 1. 输入过短
        if len(user_input.strip()) < 3:
            return True, "输入过短"

        # 2. 包含错别字或拼写错误
        common_typos = {
            "使得": "是什么",
            "啥子": "什么",
            "咋": "怎么",
            "咋样": "怎么样",
            "啥": "什么",
            "呜": "无",
            "木有": "没有",
            "偶": "我",
            "银": "人"
        }

        for typo, correct in common_typos.items():
            if typo in user_input:
                return True, f"可能的错别字: {typo} -> {correct}"

        # 3. 输入不完整
        incomplete_patterns = [
            r"^.{1,3}$",  # 只有1-3个字
            r"[，。！？]$",  # 以标点结尾但前面内容太少
            r"^[头痛牙痛肚子痛]$|^感冒$"  # 常见症状但太简短
        ]

        import re
        for pattern in incomplete_patterns:
            if re.search(pattern, user_input):
                return True, "输入不完整"

        # 4. 混合意图（如"头痛挂什么科"同时包含症状和科室）
        if any(word in user_input for word in ["挂什么科", "挂哪个科", "看什么科"]):
            if any(word in user_input for word in ["头痛", "牙痛", "肚子痛", "发烧", "咳嗽"]):
                return True, "混合意图，需要明确化"

        # 5. 口语化或不正式表达
        colloquial = ["有点", "好像", "感觉", "好像", "是不是"]
        if any(word in user_input for word in colloquial):
            return True, "口语化表达，可以更正式"

        return False, "无需重写"

    async def _rewrite_with_llm(
        self,
        user_input: str,
        context: Optional[Any] = None
    ) -> str:
        """
        使用LLM重写输入

        Args:
            user_input: 原始输入
            context: 对话上下文

        Returns:
            重写后的输入
        """
        # 构建重写提示
        rewrite_prompt = f"""你是一个医疗咨询助手的输入优化专家。请将用户的输入重写为更清晰、更完整的医疗咨询问题。

原始输入：{user_input}

重写要求：
1. 保持原意，但使其更清晰
2. 补充缺失的信息（如果有明显暗示）
3. 使用标准的医疗咨询表达方式
4. 如果输入包含错别字，请纠正
5. 如果输入不完整，请补充完整
6. 重写后的问题应该更自然、更专业

请直接输出重写后的问题，不要解释。"""

        try:
            response = await self.llm_client.chat_with_system(
                user_message=rewrite_prompt,
                system_prompt="你是医疗咨询输入优化专家。"
            )

            # 清理响应
            rewritten = response.strip()
            rewritten = rewritten.strip('"\'').strip()

            # 移除可能的前缀
            prefixes = ["重写后：", "优化后：", "问题：", "建议："]
            for prefix in prefixes:
                if rewritten.startswith(prefix):
                    rewritten = rewritten[len(prefix):].strip()

            return rewritten

        except Exception as e:
            logger.error(f"[QueryRewrite] LLM重写失败: {e}")
            # 降级到规则重写
            return await self._rewrite_with_rules(user_input, context)

    async def _rewrite_with_rules(
        self,
        user_input: str,
        context: Optional[Any] = None
    ) -> str:
        """
        使用规则重写输入

        Args:
            user_input: 原始输入
            context: 对话上下文

        Returns:
            重写后的输入
        """
        import re

        # 1. 处理错别字
        typo_corrections = {
            "使得": "是什么",
            "啥子": "什么",
            "咋": "怎么",
            "咋样": "怎么样",
            "啥": "什么",
            "呜": "无",
            "木有": "没有",
            "偶": "我"
        }

        rewritten = user_input
        for typo, correct in typo_corrections.items():
            rewritten = rewritten.replace(typo, correct)

        # 2. 处理混合意图 "头痛挂什么科"
        if "挂什么科" in user_input or "挂哪个科" in user_input:
            # 提取症状
            symptoms = []
            symptom_keywords = {
                "头痛": "头痛", "头疼": "头痛", "牙痛": "牙痛", "肚子痛": "腹痛",
                "胃痛": "胃痛", "发烧": "发热", "咳嗽": "咳嗽", "感冒": "感冒"
            }

            for keyword, symptom in symptom_keywords.items():
                if keyword in user_input:
                    symptoms.append(symptom)

            if symptoms:
                rewritten = f"我{symptoms[0]}，请问应该挂什么科？"

        # 3. 处理过短输入
        elif len(user_input.strip()) < 5:
            # 如果是症状
            if user_input in ["头痛", "牙痛", "胃痛", "肚子痛", "发烧", "咳嗽"]:
                rewritten = f"我{user_input}，请问应该怎么办？"
            # 如果是科室名称
            elif user_input in ["内科", "外科", "儿科"]:
                rewritten = f"我想挂{user_input}，请问看什么病？"
            # 如果是药品名
            elif user_input in ["阿莫西林"]:
                rewritten = f"请问阿莫西林怎么吃？有什么注意事项？"
            else:
                rewritten = f"请问{user_input}是什么意思？"

        # 4. 补充缺失的标点
        if not any(punct in rewritten for punct in "。！？，、"):
            rewritten += "。"

        return rewritten

    def get_rewrite_history(self, session_id: str, limit: int = 10) -> list:
        """
        获取重写历史

        Args:
            session_id: 会话ID
            limit: 返回数量限制

        Returns:
            重写历史列表
        """
        if session_id not in self.rewrite_history:
            return []

        return self.rewrite_history[session_id][-limit:]

    def clear_history(self, session_id: str):
        """清除指定会话的重写历史"""
        if session_id in self.rewrite_history:
            del self.rewrite_history[session_id]


# ============================================================
# 使用示例
# ============================================================

async def main():
    """演示查询重写"""

    # 创建重写器
    rewriter = QueryRewriter()

    # 测试用例
    test_inputs = [
        "头痛挂什么科",
        "使得",
        "我感冒",
        "咋治疗",
        "牙痛咋办"
    ]

    print("=" * 60)
    print("查询重写测试")
    print("=" * 60)

    for user_input in test_inputs:
        result = await rewriter.rewrite(user_input)

        print(f"\n原始输入: {result['original']}")
        if result['changed']:
            print(f"重写输入: {result['rewritten']}")
            print(f"重写原因: {result['reason']}")
        else:
            print(f"(无需重写) - {result['reason']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
