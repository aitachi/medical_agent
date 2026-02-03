# -*- coding: utf-8 -*-
"""
LLM服务 - 接入阿里云DashScope qwen-plus模型
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DashScopeLLM:
    """
    阿里云DashScope LLM客户端
    支持qwen-plus等模型
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen-plus",
        timeout: int = 30
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        """启动客户端"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info(f"[LLM] DashScope client started with model: {self.model}")

    async def stop(self):
        """停止客户端"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("[LLM] DashScope client stopped")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        **kwargs
    ):
        """
        发起聊天请求

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式输出

        Returns:
            str 或 AsyncIterator: 模型响应
        """
        if not stream:
            # 非流式：返回coroutine
            return self._chat_non_stream(messages, temperature, max_tokens, **kwargs)
        else:
            # 流式：返回async generator
            return self._chat_stream_gen(messages, temperature, max_tokens, **kwargs)

    async def _chat_non_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """非流式请求"""
        if not self.session:
            await self.start()

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            **kwargs
        }

        try:
            async with self.session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"[LLM] API error: {response.status} - {error_text}")
                    raise Exception(f"API error {response.status}: {error_text}")

                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                return content

        except asyncio.TimeoutError:
            logger.error(f"[LLM] Request timeout")
            raise Exception("LLM request timeout")
        except Exception as e:
            logger.error(f"[LLM] Request failed: {e}")
            raise

    async def _chat_stream_gen(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ):
        """流式请求"""
        if not self.session:
            await self.start()

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs
        }

        try:
            async with self.session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"[LLM] API error: {response.status} - {error_text}")
                    raise Exception(f"API error {response.status}: {error_text}")

                # aiohttp streaming: read line by line
                buffer = ""
                async for chunk in response.content.iter_chunked(1024):
                    if chunk:
                        buffer += chunk.decode('utf-8', errors='ignore')
                        lines = buffer.split('\n')
                        buffer = lines.pop()  # Keep incomplete line in buffer

                        for line in lines:
                            line = line.strip()
                            if line.startswith('data: '):
                                data_str = line[6:]
                                if data_str == '[DONE]':
                                    return
                                try:
                                    data = json.loads(data_str)
                                    if 'choices' in data and len(data['choices']) > 0:
                                        delta = data['choices'][0].get('delta', {})
                                        content = delta.get('content', '')
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue

        except asyncio.TimeoutError:
            logger.error(f"[LLM] Request timeout")
            raise Exception("LLM request timeout")
        except Exception as e:
            logger.error(f"[LLM] Stream failed: {e}")
            raise

    async def chat_with_system(
        self,
        user_message: str,
        system_prompt: str,
        conversation_history: List[Dict] = None,
        temperature: float = 0.7
    ) -> str:
        """
        使用系统提示词进行对话

        Args:
            user_message: 用户消息
            system_prompt: 系统提示词
            conversation_history: 对话历史
            temperature: 温度参数

        Returns:
            str: 模型响应
        """
        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_message})

        return await self.chat(messages, temperature=temperature)


# ============================================================
# 医疗专用LLM服务
# ============================================================

class MedicalLLMService:
    """
    医疗LLM服务
    结合意图分类和LLM生成响应
    """

    # 医疗助手系统提示
    SYSTEM_PROMPT = """你是一个专业的医疗健康助手，名为"医小助"。你的职责是：

## 核心原则
1. **安全第一**: 始终优先考虑用户健康安全
2. **专业准确**: 提供基于医学知识的准确信息
3. **温馨友好**: 用温暖、关怀的语气与用户交流
4. **不诊断**: 明确说明不能替代专业医疗诊断

## 回答规范
- 对症状分析，提供可能的原因和建议
- 对科室查询，给出明确的科室推荐
- 对用药咨询，说明用法、注意事项、副作用
- 对健康问题，提供预防建议和生活指导
- 对预约请求，引导用户提供必要信息

## 免责声明
每次涉及医疗建议时，都要加上："以上信息仅供参考，不能替代专业医疗诊断和治疗。如有不适请及时就医。"

## 格式要求
- 使用Markdown格式
- 用emoji增加可读性 (🩺症状、🏥科室、💊药品、📅预约、📚健康)
- 重要信息用加粗或引用块突出
- 条理清晰，分点说明"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen-plus"
    ):
        self.llm = DashScopeLLM(api_key=api_key, base_url=base_url, model=model)
        self.conversation_history: Dict[str, List[Dict]] = {}

    async def start(self):
        """启动服务"""
        await self.llm.start()

    async def stop(self):
        """停止服务"""
        await self.llm.stop()

    def get_history(self, session_id: str) -> List[Dict]:
        """获取对话历史"""
        return self.conversation_history.get(session_id, [])

    def add_to_history(self, session_id: str, role: str, content: str):
        """添加到对话历史"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []

        self.conversation_history[session_id].append({
            "role": role,
            "content": content
        })

        # 保持历史记录在合理范围内（最近10轮）
        if len(self.conversation_history[session_id]) > 20:
            self.conversation_history[session_id] = self.conversation_history[session_id][-20:]

    def clear_history(self, session_id: str):
        """清除对话历史"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]

    async def generate_response(
        self,
        user_message: str,
        intent: str,
        session_id: str = "default",
        custom_prompt: str = None
    ) -> str:
        """
        生成医疗响应

        Args:
            user_message: 用户消息
            intent: 意图类型
            session_id: 会话ID
            custom_prompt: 自定义系统提示词

        Returns:
            str: 生成的响应
        """
        # 根据意图类型定制系统提示
        intent_prompts = {
            "symptom_inquiry": """你是一位资深医疗专家，具有丰富的临床诊断经验。你的任务是全面分析用户提供的症状信息，给出专业、准确、实用的健康指导。

## 分析要求
请根据用户提供的以下信息进行综合分析：
- **症状标签**：用户选择的症状类型（如头痛、发热、咳嗽等）
- **症状描述**：用户详细描述的症状表现
- **持续时间**：症状已经持续了多久
- **严重程度**：症状对日常生活的影响程度

## 输出结构
请按照以下结构输出分析结果（使用Markdown格式）：

### 1. 症状综合分析
- 根据用户提供的所有信息（症状、持续时间、严重程度）进行综合分析
- 评估病情的紧急程度和严重性
- 分析症状组合可能代表的健康问题

### 2. 可能原因分析
- 列出最可能的3-5个原因，按可能性排序
- 针对用户提供的具体症状组合进行原因推断
- 考虑持续时间和严重程度对原因判断的影响
- 简要说明每个原因的特征

### 3. 危险信号识别（红旗征）
- 列出需要立即关注的危险症状
- 标明哪些情况下需要紧急就医
- 根据症状的严重程度评估风险等级

### 4. 推荐就诊科室
- 首选科室：针对当前症状最合适的科室
- 备选科室：如需多科室协作的建议
- 说明推荐理由

### 5. 自我护理建议
- 针对当前症状的家庭护理方法
- 饮食、作息方面的建议
- 可以缓解症状的非药物措施
- 需要避免的行为

### 6. 就医时机建议
- 明确说明什么情况下需要立即就医
- 什么情况下可以观察等待
- 建议的就医时间范围（根据持续时间判断）

## 专业要求
- 分析要基于循证医学知识
- 考虑症状之间的关联性
- 充分利用用户提供的所有信息
- 语气专业但平易近人
- 避免使用过于晦涩的医学术语，必要时加以解释
- 始终强调：本分析仅供参考，不能替代面对面医疗诊断""",
            "department_query": """你是科室推荐专家。根据用户症状，推荐最合适的就诊科室：
1. 首选科室及理由
2. 备选科室（如有）
3. 该科室的诊疗范围""",
            "medication_consult": """你是用药咨询专家。提供药品相关信息：
1. 药品用途和适应症
2. 正确用法用量
3. 常见副作用
4. 重要注意事项和禁忌
5. 用药提醒""",
            "appointment": """你是预约挂号助手。引导用户完成预约：
1. 确认用户需求
2. 询问缺失信息（科室、时间、医生类型）
3. 说明预约流程
4. 提供温馨提示""",
            "health_education": """你是健康教育专家。提供专业的健康指导：
1. 疾病预防知识
2. 健康生活方式建议
3. 饮食运动指导
4. 长期管理建议"""
        }

        system_prompt = custom_prompt or intent_prompts.get(intent, self.SYSTEM_PROMPT)

        # 获取对话历史
        history = self.get_history(session_id)

        # 添加用户消息到历史
        self.add_to_history(session_id, "user", user_message)

        try:
            # 调用LLM生成响应
            response = await self.llm.chat_with_system(
                user_message=user_message,
                system_prompt=system_prompt,
                conversation_history=history if len(history) <= 10 else history[-10:],
                temperature=0.7
            )

            # 添加助手响应到历史
            self.add_to_history(session_id, "assistant", response)

            return response

        except Exception as e:
            logger.error(f"[LLM] Generate response failed: {e}")
            # 返回兜底响应
            return self._get_fallback_response(intent, user_message)

    async def generate_response_stream(
        self,
        user_message: str,
        intent: str,
        session_id: str = "default",
        custom_prompt: str = None
    ):
        """
        流式生成医疗响应

        Args:
            user_message: 用户消息
            intent: 意图类型
            session_id: 会话ID
            custom_prompt: 自定义系统提示词

        Yields:
            dict: 包含type和data的流式事件
                - {"type": "thinking", "content": "..."}
                - {"type": "content", "content": "..."}
                - {"type": "done", "content": ""}
        """
        # 根据意图类型定制系统提示
        intent_prompts = {
            "symptom_inquiry": """你是一位资深医疗专家，具有丰富的临床诊断经验。你的任务是全面分析用户提供的症状信息，给出专业、准确、实用的健康指导。

## 分析要求
请根据用户提供的以下信息进行综合分析：
- **症状标签**：用户选择的症状类型（如头痛、发热、咳嗽等）
- **症状描述**：用户详细描述的症状表现
- **持续时间**：症状已经持续了多久
- **严重程度**：症状对日常生活的影响程度

## 输出结构
请按照以下结构输出分析结果（使用Markdown格式）：

### 1. 症状综合分析
- 根据用户提供的所有信息（症状、持续时间、严重程度）进行综合分析
- 评估病情的紧急程度和严重性
- 分析症状组合可能代表的健康问题

### 2. 可能原因分析
- 列出最可能的3-5个原因，按可能性排序
- 针对用户提供的具体症状组合进行原因推断
- 考虑持续时间和严重程度对原因判断的影响
- 简要说明每个原因的特征

### 3. 危险信号识别（红旗征）
- 列出需要立即关注的危险症状
- 标明哪些情况下需要紧急就医
- 根据症状的严重程度评估风险等级

### 4. 推荐就诊科室
- 首选科室：针对当前症状最合适的科室
- 备选科室：如需多科室协作的建议
- 说明推荐理由

### 5. 自我护理建议
- 针对当前症状的家庭护理方法
- 饮食、作息方面的建议
- 可以缓解症状的非药物措施
- 需要避免的行为

### 6. 就医时机建议
- 明确说明什么情况下需要立即就医
- 什么情况下可以观察等待
- 建议的就医时间范围（根据持续时间判断）

## 专业要求
- 分析要基于循证医学知识
- 考虑症状之间的关联性
- 充分利用用户提供的所有信息
- 语气专业但平易近人
- 避免使用过于晦涩的医学术语，必要时加以解释
- 始终强调：本分析仅供参考，不能替代面对面医疗诊断""",
            "department_query": """你是科室推荐专家。根据用户症状，推荐最合适的就诊科室：
1. 首选科室及理由
2. 备选科室（如有）
3. 该科室的诊疗范围""",
            "medication_consult": """你是用药咨询专家。提供药品相关信息：
1. 药品用途和适应症
2. 正确用法用量
3. 常见副作用
4. 重要注意事项和禁忌
5. 用药提醒""",
            "appointment": """你是预约挂号助手。引导用户完成预约：
1. 确认用户需求
2. 询问缺失信息（科室、时间、医生类型）
3. 说明预约流程
4. 提供温馨提示""",
            "health_education": """你是健康教育专家。提供专业的健康指导：
1. 疾病预防知识
2. 健康生活方式建议
3. 饮食运动指导
4. 长期管理建议"""
        }

        system_prompt = custom_prompt or intent_prompts.get(intent, self.SYSTEM_PROMPT)

        # 获取对话历史
        history = self.get_history(session_id)

        # 添加用户消息到历史
        self.add_to_history(session_id, "user", user_message)

        # 发送思考过程事件
        yield {
            "type": "thinking",
            "content": f"正在分析您的请求..."
        }

        yield {
            "type": "thinking",
            "content": f"识别到意图: {intent}"
        }

        yield {
            "type": "thinking",
            "content": f"调用qwen-plus大模型生成回复..."
        }

        try:
            # 构建消息列表
            messages = [{"role": "system", "content": system_prompt}]
            if history and len(history) <= 10:
                messages.extend(history)
            messages.append({"role": "user", "content": user_message})

            # 流式调用LLM
            full_response = ""
            async for chunk in self.llm.chat(messages, stream=True):
                full_response += chunk
                yield {
                    "type": "content",
                    "content": chunk
                }

            # 添加助手响应到历史
            self.add_to_history(session_id, "assistant", full_response)

            # 发送完成事件
            yield {"type": "done", "content": ""}

        except Exception as e:
            logger.error(f"[LLM] Stream generation failed: {e}")
            yield {
                "type": "error",
                "content": str(e)
            }

    def _get_fallback_response(self, intent: str, user_message: str) -> str:
        """获取兜底响应"""
        fallbacks = {
            "symptom_inquiry": f"""## 关于您的症状

感谢您描述的症状「{user_message}」。

为了给您更准确的建议，请告诉我：
- 症状持续多长时间了？
- 有没有其他伴随症状？
- 症状的严重程度如何？

> ⚠️ **免责声明**: 以上信息仅供参考，不能替代专业医疗诊断和治疗。如有不适请及时就医。""",
            "department_query": f"""## 科室推荐

根据您提到的「{user_message}」，建议您挂号前先明确具体症状。

常见科室参考：
- 头痛头晕 → 神经内科
- 咳嗽发热 → 呼吸内科/发热门诊
- 腹痛恶心 → 消化内科
- 心悸胸痛 → 心血管内科

> ⚠️ **免责声明**: 以上信息仅供参考，不能替代专业医疗诊断和治疗。如有不适请及时就医。""",
            "medication_consult": """## 用药咨询

关于药品使用，请咨询：
1. 查阅药品说明书
2. 咨询医院药师
3. 咨询开药医生

> ⚠️ **重要提醒**: 请严格按医嘱或说明书使用药品，不要自行调整剂量。""",
            "appointment": """## 预约挂号

请提供以下信息：
1. 挂号科室
2. 就诊时间
3. 医生类型（专家/普通）

> 💡 **提示**: 如果不确定挂什么科，可以先告诉我您的症状。""",
            "health_education": """## 健康知识

保持健康的生活方式：
- 均衡饮食，少盐少油
- 适量运动，每周150分钟
- 充足睡眠，规律作息
- 戒烟限酒，保持好心情

> ⚠️ **免责声明**: 以上信息仅供参考，不能替代专业医疗诊断和治疗。"""
        }

        return fallbacks.get(intent, "抱歉，我暂时无法处理您的请求，请稍后重试。")


# ============================================================
# 单例管理
# ============================================================

_llm_service: Optional[MedicalLLMService] = None


def get_llm_service() -> Optional[MedicalLLMService]:
    """获取LLM服务单例"""
    return _llm_service


async def init_llm_service(api_key: str, base_url: str = None, model: str = "qwen-plus"):
    """初始化LLM服务"""
    global _llm_service

    if _llm_service is None:
        _llm_service = MedicalLLMService(
            api_key=api_key,
            base_url=base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
            model=model
        )
        await _llm_service.start()
        logger.info("[LLM] Service initialized")

    return _llm_service


async def shutdown_llm_service():
    """关闭LLM服务"""
    global _llm_service

    if _llm_service:
        await _llm_service.stop()
        _llm_service = None
        logger.info("[LLM] Service shutdown")
