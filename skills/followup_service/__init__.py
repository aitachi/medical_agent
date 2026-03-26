# -*- coding: utf-8 -*-
"""
随访服务Skill
管理患者随访计划，收集随访信息，评估康复进度
"""

import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class FollowupStatus(Enum):
    """随访状态"""
    PENDING = "pending"       # 待随访
    ACTIVE = "active"         # 随访中
    COMPLETED = "completed"   # 已完成
    MISSED = "missed"         # 已错过


class RecoveryStage(Enum):
    """康复阶段"""
    EXCELLENT = "excellent"   # 优秀
    GOOD = "good"             # 良好
    FAIR = "fair"             # 一般
    POOR = "poor"             # 较差


@dataclass
class FollowupPlan:
    """随访计划"""
    plan_id: str
    user_id: str
    condition: str           # 随访原因（疾病/手术）
    start_date: str
    end_date: str
    schedule: List[Dict]     # 随访时间表
    status: FollowupStatus


@dataclass
class FollowupFeedback:
    """随访反馈"""
    feedback_id: str
    plan_id: str
    user_id: str
    feedback_time: str
    symptoms: List[str]      # 症状情况
    medication: str          # 用药情况
    recovery_stage: RecoveryStage
    notes: str               # 备注信息
    next_action: str         # 下一步行动


@dataclass
class FollowupResult:
    """随访结果"""
    success: bool
    content: str
    plan_id: Optional[str] = None
    feedback_id: Optional[str] = None
    next_followup_date: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)
    error: Optional[str] = None


class FollowupServiceSkill:
    """
    随访服务Skill
    管理患者随访计划，收集随访信息，评估康复进度
    """

    # 随访模板
    FOLLOWUP_TEMPLATES = {
        "surgery": {
            "name": "术后随访",
            "intervals": [3, 7, 14, 30, 60, 90],  # 术后第3天、1周、2周、1月、2月、3月
            "questions": [
                "伤口情况如何？有无红肿渗液？",
                "疼痛程度如何？",
                "食欲和睡眠情况？",
                "有无发热？",
                "用药是否规律？"
            ]
        },
        "chronic_disease": {
            "name": "慢病随访",
            "intervals": [30, 60, 90, 180, 365],  # 每月、每2月、每季、每半年、每年
            "questions": [
                "近期症状控制如何？",
                "血压/血糖监测情况？",
                "用药依从性如何？",
                "生活方式改善情况？",
                "有无不良反应？"
            ]
        },
        "medication": {
            "name": "用药随访",
            "intervals": [7, 14, 30],  # 用药1周、2周、1月后
            "questions": [
                "是否按时服药？",
                "有无不良反应？",
                "症状改善情况？",
                "有无漏服？"
            ]
        }
    }

    def __init__(self, mcp_client=None):
        """
        初始化随访服务Skill

        Args:
            mcp_client: MCP客户端，用于调用外部随访系统
        """
        self.mcp_client = mcp_client
        self._plans: Dict[str, FollowupPlan] = {}
        self._feedbacks: Dict[str, List[FollowupFeedback]] = {}

    async def create_plan(
        self,
        user_id: str,
        condition: str,
        template_type: str,
        start_date: Optional[str] = None
    ) -> FollowupResult:
        """
        创建随访计划

        Args:
            user_id: 用户ID
            condition: 随访原因（疾病/手术）
            template_type: 模板类型
            start_date: 开始日期

        Returns:
            FollowupResult: 创建结果
        """
        try:
            template = self.FOLLOWUP_TEMPLATES.get(template_type)
            if not template:
                return FollowupResult(
                    success=False,
                    error=f"不支持的随访类型: {template_type}"
                )

            plan_id = f"FUP{datetime.now().strftime('%Y%m%d%H%M%S')}"
            if not start_date:
                start_date = (datetime.now() + timedelta(days=template['intervals'][0])).isoformat()

            # 生成随访时间表
            schedule = []
            base_date = datetime.now()
            for interval in template['intervals']:
                followup_date = base_date + timedelta(days=interval)
                schedule.append({
                    "day": interval,
                    "date": followup_date.isoformat(),
                    "completed": False
                })

            plan = FollowupPlan(
                plan_id=plan_id,
                user_id=user_id,
                condition=condition,
                start_date=start_date,
                end_date=schedule[-1]['date'] if schedule else start_date,
                schedule=schedule,
                status=FollowupStatus.PENDING
            )

            self._plans[plan_id] = plan

            content = self._format_plan_created(plan, template)

            return FollowupResult(
                success=True,
                content=content,
                plan_id=plan_id,
                next_followup_date=schedule[0]['date'] if schedule else None,
                recommendations=["请按时完成随访，有助于医生了解您的恢复情况"]
            )

        except Exception as e:
            logger.error(f"创建随访计划失败: {e}")
            return FollowupResult(
                success=False,
                error=str(e)
            )

    def _format_plan_created(self, plan: FollowupPlan, template: Dict) -> str:
        """格式化计划创建响应"""
        content = f"""## 📋 随访计划创建成功

**计划编号**: {plan.plan_id}
**随访类型**: {template['name']}
**随访原因**: {plan.condition}
**计划开始**: {plan.start_date[:10]}

### 📅 随访时间表

| 日期 | 天数 | 状态 |
|------|------|------|
"""
        for item in plan.schedule:
            date_str = item['date'][:10]
            status = "待随访" if not item['completed'] else "已完成"
            content += f"| {date_str} | 术后{item['day']}天 | {status} |\n"

        content += f"\n### 📝 随访内容\n\n"
        for i, question in enumerate(template['questions'], 1):
            content += f"{i}. {question}\n"

        content += "\n### 💡 温馨提示\n\n"
        content += "- 请按时完成随访反馈\n"
        content += "- 随访前一天会收到提醒\n"
        content += "- 可提前或推迟1-2天完成\n"
        content += "- 遇到问题可随时联系医生\n"

        return content

    async def submit_feedback(
        self,
        user_id: str,
        plan_id: str,
        symptoms: List[str],
        medication: str,
        recovery_stage: str,
        notes: str = ""
    ) -> FollowupResult:
        """
        提交随访反馈

        Args:
            user_id: 用户ID
            plan_id: 计划ID
            symptoms: 症状列表
            medication: 用药情况
            recovery_stage: 康复阶段
            notes: 备注

        Returns:
            FollowupResult: 提交结果
        """
        try:
            plan = self._plans.get(plan_id)
            if not plan:
                return FollowupResult(
                    success=False,
                    error=f"未找到随访计划: {plan_id}"
                )

            feedback_id = f"FDB{datetime.now().strftime('%Y%m%d%H%M%S')}"

            feedback = FollowupFeedback(
                feedback_id=feedback_id,
                plan_id=plan_id,
                user_id=user_id,
                feedback_time=datetime.now().isoformat(),
                symptoms=symptoms,
                medication=medication,
                recovery_stage=RecoveryStage(recovery_stage),
                notes=notes,
                next_action=self._determine_next_action(symptoms, recovery_stage)
            )

            # 保存反馈
            if plan_id not in self._feedbacks:
                self._feedbacks[plan_id] = []
            self._feedbacks[plan_id].append(feedback)

            # 更新计划状态
            plan.status = FollowupStatus.ACTIVE

            # 生成响应
            content, recommendations = self._generate_feedback_response(feedback, plan)

            # 找到下次随访日期
            next_followup = None
            for item in plan.schedule:
                if not item['completed'] and datetime.fromisoformat(item['date']) > datetime.now():
                    next_followup = item['date'][:10]
                    break

            return FollowupResult(
                success=True,
                content=content,
                feedback_id=feedback_id,
                plan_id=plan_id,
                next_followup_date=next_followup,
                recommendations=recommendations
            )

        except Exception as e:
            logger.error(f"提交随访反馈失败: {e}")
            return FollowupResult(
                success=False,
                error=str(e)
            )

    def _determine_next_action(self, symptoms: List[str], recovery_stage: str) -> str:
        """确定下一步行动"""
        # 检查是否有异常症状
        concerning_keywords = ["发热", "疼痛", "出血", "红肿", "渗液", "呕吐"]
        for symptom in symptoms:
            for keyword in concerning_keywords:
                if keyword in symptom:
                    return "建议及时就医或联系医生"

        # 根据康复阶段
        if recovery_stage == RecoveryStage.POOR.value:
            return "建议复诊评估"
        elif recovery_stage == RecoveryStage.FAIR.value:
            return "继续观察，按时随访"
        else:
            return "继续目前治疗方案"

    def _generate_feedback_response(
        self,
        feedback: FollowupFeedback,
        plan: FollowupPlan
    ) -> tuple:
        """生成反馈响应"""
        stage_emoji = {
            "excellent": "🌟",
            "good": "👍",
            "fair": "😐",
            "poor": "😟"
        }

        content = f"""## ✅ 随访反馈已提交

**反馈编号**: {feedback.feedback_id}
**随访计划**: {plan.plan_id}
**提交时间**: {feedback.feedback_time[:10]}

### 📊 您的反馈情况

**症状情况**: {', '.join(feedback.symptoms) if feedback.symptoms else '无特殊症状'}
**用药情况**: {feedback.medication}
**康复评估**: {stage_emoji.get(feedback.recovery_stage.value, '')} {feedback.recovery_stage.value}

### 📝 医生建议

{feedback.next_action}

---

> 💡 **提示**: 请继续保持随访，您的反馈对医生了解您的情况很重要。
"""

        recommendations = [
            "继续按时服药",
            "注意休息和营养",
            "保持良好心态",
            "出现异常及时就医"
        ]

        return content, recommendations

    async def get_plan_status(self, plan_id: str) -> FollowupResult:
        """
        获取随访计划状态

        Args:
            plan_id: 计划ID

        Returns:
            FollowupResult: 计划状态
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return FollowupResult(
                success=False,
                error=f"未找到随访计划: {plan_id}"
            )

        feedbacks = self._feedbacks.get(plan_id, [])

        content = f"""## 📋 随访计划状态

**计划编号**: {plan.plan_id}
**随访原因**: {plan.condition}
**当前状态**: {plan.status.value}

### 📅 随访进度

已完成 {len(feedbacks)} 次随访，共 {len(plan.schedule)} 次计划

### 📊 最近反馈

"""
        if feedbacks:
            latest = feedbacks[-1]
            content += f"**时间**: {latest.feedback_time[:10]}\n"
            content += f"**康复阶段**: {latest.recovery_stage.value}\n"
            content += f"**下一步**: {latest.next_action}\n"
        else:
            content += "暂无反馈记录\n"

        return FollowupResult(
            success=True,
            content=content,
            plan_id=plan_id
        )


# 便捷函数
async def create_followup_plan(
    user_id: str,
    condition: str,
    template_type: str,
    mcp_client=None
) -> str:
    """
    创建随访计划（便捷函数）

    Args:
        user_id: 用户ID
        condition: 随访原因
        template_type: 模板类型
        mcp_client: MCP客户端

    Returns:
        str: 格式化的创建结果
    """
    skill = FollowupServiceSkill(mcp_client)
    result = await skill.create_plan(user_id, condition, template_type)
    return result.content if result.success else f"创建失败: {result.error}"


if __name__ == "__main__":
    # 测试用例
    async def test():
        skill = FollowupServiceSkill()

        # 测试创建随访计划
        result = await skill.create_plan(
            user_id="test_user",
            condition="腹腔镜胆囊切除术",
            template_type="surgery"
        )
        print(result.content)

        print("\n" + "="*60 + "\n")

        # 测试提交反馈
        result2 = await skill.submit_feedback(
            user_id="test_user",
            plan_id=result.plan_id,
            symptoms=["伤口愈合良好", "无疼痛"],
            medication="按时服药",
            recovery_stage="good",
            notes="恢复顺利"
        )
        print(result2.content)

    import asyncio
    asyncio.run(test())
