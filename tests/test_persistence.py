# -*- coding: utf-8 -*-
"""
医疗智能助手 - 持久化测试
测试会话存储和用户画像持久化
"""

import pytest
import asyncio
import sys
import tempfile
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入被测试模块
from core.session_store import (
    SessionStore,
    SessionRecord,
    TurnRecord
)
from services.profile_service import (
    ProfileService
)
from agent.user_profile import UserProfile, create_default_profile
from agent.medical_agent import DialogueContext, IntentResult


@pytest.fixture
def temp_db_path():
    """创建临时数据库路径"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # 清理
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
async def session_store(temp_db_path):
    """创建会话存储实例"""
    store = SessionStore(temp_db_path)
    await store.initialize()
    return store


@pytest.fixture
async def profile_service(temp_db_path):
    """创建用户画像服务实例"""
    # 使用不同的数据库文件
    profile_path = temp_db_path.replace(".db", "_profiles.db")
    service = ProfileService(profile_path)
    await service.initialize()
    return service


@pytest.fixture
def sample_context():
    """创建示例对话上下文"""
    context = DialogueContext(
        session_id="test_session_001",
        user_id="test_user_001",
        turn_count=0
    )

    # 添加一些对话历史
    context.add_turn(
        "你好",
        "您好，我是医疗助手，有什么可以帮助您的？",
        IntentResult(intent="greeting", confidence=0.95)
    )
    context.add_turn(
        "我头痛",
        "请问您的头痛持续多长时间了？",
        IntentResult(intent="symptom_inquiry", confidence=0.85)
    )

    return context


@pytest.fixture
def sample_profile():
    """创建示例用户画像"""
    profile = create_default_profile("test_user_profile")
    profile.basic_info['age'] = 35
    profile.basic_info['gender'] = 'male'
    profile.add_medical_history("高血压")
    profile.add_allergy("青霉素")
    profile.add_medication("硝苯地平", "10mg 每日2次")
    profile.add_chronic_condition("高血压")
    return profile


class TestSessionStore:
    """会话存储测试"""

    @pytest.mark.asyncio
    async def test_save_and_load_session(self, session_store, sample_context):
        """测试保存和加载会话"""
        # 保存会话
        await session_store.save_session(sample_context)

        # 加载会话
        loaded_context = await session_store.load_session(sample_context.session_id)

        assert loaded_context is not None
        assert loaded_context.session_id == sample_context.session_id
        assert loaded_context.user_id == sample_context.user_id
        assert loaded_context.turn_count == sample_context.turn_count
        assert len(loaded_context.history) == len(sample_context.history)

    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, session_store):
        """测试加载不存在的会话"""
        result = await session_store.load_session("nonexistent_session")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_session(self, session_store, sample_context):
        """测试删除会话"""
        # 保存会话
        await session_store.save_session(sample_context)

        # 删除会话
        success = await session_store.delete_session(sample_context.session_id)
        assert success is True

        # 确认已删除
        loaded = await session_store.load_session(sample_context.session_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_session_expiration(self, session_store, sample_context):
        """测试会话过期"""
        # 保存一个短TTL的会话
        await session_store.save_session(sample_context, ttl=0)  # 立即过期

        # 加载应该失败
        loaded = await session_store.load_session(sample_context.session_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_add_turn(self, session_store):
        """测试添加对话轮次"""
        session_id = "test_session_turns"

        await session_store.add_turn(
            session_id=session_id,
            turn=0,
            user_input="你好",
            agent_response="您好",
            intent="greeting",
            confidence=0.95,
            entities={}
        )

        history = await session_store.get_session_history(session_id)
        assert len(history) == 1
        assert history[0].user_input == "你好"
        assert history[0].agent_response == "您好"

    @pytest.mark.asyncio
    async def test_get_session_history(self, session_store):
        """测试获取会话历史"""
        session_id = "test_session_history"

        # 添加多个轮次
        for i in range(3):
            await session_store.add_turn(
                session_id=session_id,
                turn=i,
                user_input=f"输入{i}",
                agent_response=f"响应{i}",
                intent="test",
                confidence=0.8,
                entities={}
            )

        # 获取全部历史
        history = await session_store.get_session_history(session_id)
        assert len(history) == 3

        # 获取限制数量
        limited_history = await session_store.get_session_history(session_id, limit=2)
        assert len(limited_history) == 2

    @pytest.mark.asyncio
    async def test_get_user_sessions(self, session_store):
        """测试获取用户会话列表"""
        user_id = "test_user_list"

        # 创建多个会话
        for i in range(3):
            context = DialogueContext(
                session_id=f"session_{i}",
                user_id=user_id,
                turn_count=i
            )
            await session_store.save_session(context)

        # 获取用户会话
        sessions = await session_store.get_user_sessions(user_id)
        assert len(sessions) == 3

        # 验证顺序（按更新时间降序）
        assert sessions[0].session_id == "session_2"

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, session_store):
        """测试清理过期会话"""
        # 创建一些会话
        for i in range(3):
            context = DialogueContext(
                session_id=f"session_cleanup_{i}",
                user_id="test_user",
                turn_count=0
            )
            ttl = 0 if i < 2 else 86400  # 前两个立即过期
            await session_store.save_session(context, ttl=ttl)

        # 清理过期会话
        cleaned = await session_store.cleanup_expired(days=0)
        assert cleaned >= 2

    @pytest.mark.asyncio
    async def test_get_stats(self, session_store, sample_context):
        """测试获取统计信息"""
        # 保存一些数据
        await session_store.save_session(sample_context)
        await session_store.add_turn(
            sample_context.session_id,
            0,
            "测试",
            "响应",
            "test",
            0.9
        )

        stats = await session_store.get_stats()
        assert stats['total_sessions'] >= 1
        assert stats['active_sessions'] >= 1
        assert stats['total_turns'] >= 1


class TestProfileService:
    """用户画像服务测试"""

    @pytest.mark.asyncio
    async def test_save_and_load_profile(self, profile_service, sample_profile):
        """测试保存和加载用户画像"""
        # 保存画像
        await profile_service.save_profile(sample_profile)

        # 加载画像
        loaded_profile = await profile_service.load_profile(sample_profile.user_id)

        assert loaded_profile is not None
        assert loaded_profile.user_id == sample_profile.user_id
        assert loaded_profile.basic_info['age'] == sample_profile.basic_info['age']
        assert len(loaded_profile.allergies) == len(sample_profile.allergies)

    @pytest.mark.asyncio
    async def test_get_or_create_profile(self, profile_service):
        """测试获取或创建画像"""
        user_id = "new_user"

        # 第一次调用应该创建新画像
        profile1 = await profile_service.get_or_create_profile(user_id)
        assert profile1 is not None
        assert profile1.user_id == user_id

        # 第二次调用应该返回已存在的画像
        profile2 = await profile_service.get_or_create_profile(user_id)
        assert profile2.user_id == profile1.user_id
        # 更新时间应该不同
        profile2.basic_info['age'] = 30
        await profile_service.save_profile(profile2)

        profile3 = await profile_service.get_or_create_profile(user_id)
        assert profile3.basic_info['age'] == 30

    @pytest.mark.asyncio
    async def test_update_from_context(self, profile_service):
        """测试从上下文更新画像"""
        user_id = "context_update_user"

        entities = {
            'disease': '高血压',
            'drug': '硝苯地平',
            'dosage': '10mg',
            'symptom': '头痛'
        }

        updates = await profile_service.update_from_context(user_id, entities)

        assert len(updates) > 0

        # 验证画像已更新
        profile = await profile_service.load_profile(user_id)
        assert profile is not None
        assert '高血压' in profile.medical_history or '高血压' in profile.metadata.get('potential_chronic', [])

    @pytest.mark.asyncio
    async def test_get_update_history(self, profile_service):
        """测试获取更新历史"""
        user_id = "history_user"

        # 添加一些更新
        entities1 = {'disease': '糖尿病'}
        entities2 = {'allergy': '青霉素'}

        await profile_service.update_from_context(user_id, entities1, source="test1")
        await profile_service.update_from_context(user_id, entities2, source="test2")

        # 获取历史
        history = await profile_service.get_update_history(user_id)
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_delete_profile(self, profile_service, sample_profile):
        """测试删除画像"""
        await profile_service.save_profile(sample_profile)

        success = await profile_service.delete_profile(sample_profile.user_id)
        assert success is True

        loaded = await profile_service.load_profile(sample_profile.user_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_get_stats(self, profile_service, sample_profile):
        """测试获取统计信息"""
        await profile_service.save_profile(sample_profile)

        stats = await profile_service.get_stats()
        assert stats['total_users'] >= 1


class TestPersistenceIntegration:
    """持久化集成测试"""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, session_store, profile_service):
        """测试完整对话流程的持久化"""
        user_id = "integration_user"
        session_id = "integration_session"

        # 1. 创建上下文
        context = DialogueContext(
            session_id=session_id,
            user_id=user_id,
            turn_count=0
        )

        # 2. 模拟对话
        context.add_turn(
            "我有高血压",
            "请问您目前服用什么药物？",
            IntentResult(intent="symptom_inquiry", confidence=0.9)
        )

        entities = {'disease': '高血压', 'drug': '硝苯地平'}
        context.update_entities(entities)

        # 3. 保存会话
        await session_store.save_session(context)

        # 4. 更新用户画像
        await profile_service.update_from_context(user_id, entities)

        # 5. 添加对话轮次
        await session_store.add_turn(
            session_id=session_id,
            turn=0,
            user_input="我有高血压",
            agent_response="请问您目前服用什么药物？",
            intent="symptom_inquiry",
            confidence=0.9,
            entities=entities
        )

        # 6. 验证数据已保存
        loaded_context = await session_store.load_session(session_id)
        assert loaded_context is not None
        assert loaded_context.turn_count == 1

        profile = await profile_service.load_profile(user_id)
        assert profile is not None

        history = await session_store.get_session_history(session_id)
        assert len(history) == 1


class TestDataIntegrity:
    """数据完整性测试"""

    @pytest.mark.asyncio
    async def test_context_serialization(self, session_store, sample_context):
        """测试上下文序列化和反序列化"""
        await session_store.save_session(sample_context)
        loaded = await session_store.load_session(sample_context.session_id)

        # 验证关键字段
        assert loaded.session_id == sample_context.session_id
        assert loaded.user_id == sample_context.user_id
        assert len(loaded.history) == len(sample_context.history)

        # 验证历史记录
        for i, (orig, loaded_turn) in enumerate(zip(sample_context.history, loaded.history)):
            assert orig['user_input'] == loaded_turn['user_input']
            assert orig['agent_response'] == loaded_turn['agent_response']

    @pytest.mark.asyncio
    async def test_profile_serialization(self, profile_service, sample_profile):
        """测试画像序列化和反序列化"""
        await profile_service.save_profile(sample_profile)
        loaded = await profile_service.load_profile(sample_profile.user_id)

        # 验证所有字段
        assert loaded.basic_info == sample_profile.basic_info
        assert loaded.medical_history == sample_profile.medical_history
        assert loaded.allergies == sample_profile.allergies
        assert loaded.chronic_conditions == sample_profile.chronic_conditions


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
