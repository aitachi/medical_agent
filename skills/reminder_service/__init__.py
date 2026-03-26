# -*- coding: utf-8 -*-
"""
提醒服务Skill
管理用药提醒、随访提醒、复诊提醒等各类健康提醒
"""

import re
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta, time


logger = logging.getLogger(__name__)


class ReminderType(Enum):
    """提醒类型"""
    MEDICATION = "medication"   # 用药提醒
    FOLLOWUP = "followup"       # 随访提醒
    APPOINTMENT = "appointment" # 预约提醒
    CHECKUP = "checkup"         # 体检提醒
    MEASUREMENT = "measurement" # 测量提醒（血压、血糖等）
    CUSTOM = "custom"           # 自定义提醒


class ReminderFrequency(Enum):
    """提醒频率"""
    ONCE = "once"           # 一次
    DAILY = "daily"         # 每天
    WEEKLY = "weekly"       # 每周
    MONTHLY = "monthly"     # 每月
    CUSTOM = "custom"       # 自定义


@dataclass
class Reminder:
    """提醒"""
    reminder_id: str
    user_id: str
    type: ReminderType
    title: str
    content: str
    frequency: ReminderFrequency
    time: str               # 提醒时间
    start_date: str
    end_date: Optional[str] = None
    is_active: bool = True
    metadata: Dict = field(default_factory=dict)


@dataclass
class ReminderResult:
    """提醒结果"""
    success: bool
    content: str
    reminder_id: Optional[str] = None
    reminders: Optional[List[Reminder]] = None
    error: Optional[str] = None


class ReminderServiceSkill:
    """
    提醒服务Skill
    管理用药提醒、随访提醒、复诊提醒等各类健康提醒
    """

    # 用药时间模板
    MEDICATION_TIME_TEMPLATES = {
        "daily_3": [
            {"time": "08:00", "label": "早餐后"},
            {"time": "13:00", "label": "午餐后"},
            {"time": "19:00", "label": "晚餐后"}
        ],
        "daily_2": [
            {"time": "08:00", "label": "早餐后"},
            {"time": "20:00", "label": "晚餐后"}
        ],
        "daily_1": [
            {"time": "08:00", "label": "早餐后"}
        ],
        "night": [
            {"time": "21:00", "label": "睡前"}
        ]
    }

    def __init__(self, mcp_client=None):
        """
        初始化提醒服务Skill

        Args:
            mcp_client: MCP客户端，用于调用外部提醒系统
        """
        self.mcp_client = mcp_client
        self._reminders: Dict[str, List[Reminder]] = {}

    async def create_medication_reminder(
        self,
        user_id: str,
        medication_name: str,
        dosage: str,
        frequency: str,
        time_template: str = "daily_3"
    ) -> ReminderResult:
        """
        创建用药提醒

        Args:
            user_id: 用户ID
            medication_name: 药品名称
            dosage: 用法用量
            frequency: 服用频率
            time_template: 时间模板

        Returns:
            ReminderResult: 创建结果
        """
        try:
            reminder_ids = []
            times = self.MEDICATION_TIME_TEMPLATES.get(time_template, self.MEDICATION_TIME_TEMPLATES["daily_3"])

            for time_info in times:
                reminder_id = f"REM{datetime.now().strftime('%Y%m%d%H%M%S')}{len(reminder_ids)}"

                reminder = Reminder(
                    reminder_id=reminder_id,
                    user_id=user_id,
                    type=ReminderType.MEDICATION,
                    title=f"服用{medication_name}提醒",
                    content=f"请服用{medication_name}，{dosage}，{time_info['label']}",
                    frequency=ReminderFrequency.DAILY,
                    time=time_info['time'],
                    start_date=datetime.now().strftime('%Y-%m-%d'),
                    metadata={
                        "medication_name": medication_name,
                        "dosage": dosage,
                        "frequency": frequency
                    }
                )

                if user_id not in self._reminders:
                    self._reminders[user_id] = []
                self._reminders[user_id].append(reminder)
                reminder_ids.append(reminder_id)

            content = self._format_medication_reminder_created(medication_name, dosage, times)

            return ReminderResult(
                success=True,
                content=content,
                reminder_id=reminder_ids[0] if reminder_ids else None
            )

        except Exception as e:
            logger.error(f"创建用药提醒失败: {e}")
            return ReminderResult(
                success=False,
                error=str(e)
            )

    def _format_medication_reminder_created(
        self,
        medication_name: str,
        dosage: str,
        times: List[Dict]
    ) -> str:
        """格式化用药提醒创建响应"""
        content = f"""## 💊 用药提醒设置成功

**药品名称**: {medication_name}
**用法用量**: {dosage}

### ⏰ 提醒时间

"""
        for time_info in times:
            content += f"- **{time_info['time']}** ({time_info['label']})\n"

        content += """
### 📝 温馨提示

- 请按时服药，不要擅自停药
- 如有不良反应请及时就医
- 设置后每日将收到提醒
- 可随时修改或取消提醒

---

> 💡 **小贴士**: 建议将药物放在显眼位置，避免漏服。
"""
        return content

    async def create_appointment_reminder(
        self,
        user_id: str,
        appointment_type: str,
        appointment_time: str,
        hospital: str,
        department: Optional[str] = None
    ) -> ReminderResult:
        """
        创建预约提醒

        Args:
            user_id: 用户ID
            appointment_type: 预约类型（挂号、复诊、体检等）
            appointment_time: 预约时间
            hospital: 医院名称
            department: 科室

        Returns:
            ReminderResult: 创建结果
        """
        try:
            reminder_id = f"REM{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # 计算提醒时间（提前1天）
            appt_datetime = datetime.fromisoformat(appointment_time)
            remind_datetime = appt_datetime - timedelta(days=1)
            remind_time = remind_datetime.strftime('%Y-%m-%d 09:00')

            reminder = Reminder(
                reminder_id=reminder_id,
                user_id=user_id,
                type=ReminderType.APPOINTMENT,
                title=f"{appointment_type}提醒",
                content=f"您于{appt_datetime.strftime('%Y-%m-%d %H:%M')}在{hospital}{' ' + department if department else ''}有{appointment_type}",
                frequency=ReminderFrequency.ONCE,
                time=remind_time,
                start_date=remind_datetime.strftime('%Y-%m-%d'),
                end_date=remind_datetime.strftime('%Y-%m-%d'),
                metadata={
                    "appointment_type": appointment_type,
                    "appointment_time": appointment_time,
                    "hospital": hospital,
                    "department": department
                }
            )

            if user_id not in self._reminders:
                self._reminders[user_id] = []
            self._reminders[user_id].append(reminder)

            content = self._format_appointment_reminder_created(
                appointment_type, appointment_time, hospital, department
            )

            return ReminderResult(
                success=True,
                content=content,
                reminder_id=reminder_id
            )

        except Exception as e:
            logger.error(f"创建预约提醒失败: {e}")
            return ReminderResult(
                success=False,
                error=str(e)
            )

    def _format_appointment_reminder_created(
        self,
        appointment_type: str,
        appointment_time: str,
        hospital: str,
        department: Optional[str]
    ) -> str:
        """格式化预约提醒创建响应"""
        appt_datetime = datetime.fromisoformat(appointment_time)

        content = f"""## 📅 预约提醒设置成功

**预约类型**: {appointment_type}
**预约时间**: {appt_datetime.strftime('%Y年%m月%d日 %H:%M')}
**地点**: {hospital}{f' - {department}' if department else ''}

### ⏰ 提醒安排

系统将在预约前1天发送提醒，届时会提醒您：
- 预约时间
- 就诊地点
- 需要携带的物品（身份证、医保卡等）

### 📝 温馨提示

- 请提前15分钟到达
- 携带身份证和医保卡
- 如需取消请提前4小时

---

> 💡 **小贴士**: 可以设置日历提醒，避免错过预约。
"""
        return content

    async def create_measurement_reminder(
        self,
        user_id: str,
        measurement_type: str,
        frequency: str = "daily",
        time: str = "08:00"
    ) -> ReminderResult:
        """
        创建测量提醒

        Args:
            user_id: 用户ID
            measurement_type: 测量类型（血压、血糖、体温等）
            frequency: 频率
            time: 提醒时间

        Returns:
            ReminderResult: 创建结果
        """
        try:
            reminder_id = f"REM{datetime.now().strftime('%Y%m%d%H%M%S')}"

            type_names = {
                "血压": "测量血压",
                "血糖": "测量血糖",
                "体温": "测量体温",
                "体重": "测量体重"
            }

            reminder = Reminder(
                reminder_id=reminder_id,
                user_id=user_id,
                type=ReminderType.MEASUREMENT,
                title=f"{type_names.get(measurement_type, measurement_type)}提醒",
                content=f"请{type_names.get(measurement_type, measurement_type)}并记录",
                frequency=ReminderFrequency(frequency),
                time=time,
                start_date=datetime.now().strftime('%Y-%m-%d'),
                metadata={"measurement_type": measurement_type}
            )

            if user_id not in self._reminders:
                self._reminders[user_id] = []
            self._reminders[user_id].append(reminder)

            content = f"""## 📊 测量提醒设置成功

**测量类型**: {type_names.get(measurement_type, measurement_type)}
**提醒时间**: 每天 {time}
**开始日期**: {datetime.now().strftime('%Y-%m-%d')}

### 📝 温馨提示

- 请在相同时间测量，便于对比
- 测量前休息5分钟
- 记录测量结果
- 可以直接告诉我结果进行记录

---

> 💡 **小贴士**: 定期监测有助于了解健康状况变化。
"""

            return ReminderResult(
                success=True,
                content=content,
                reminder_id=reminder_id
            )

        except Exception as e:
            logger.error(f"创建测量提醒失败: {e}")
            return ReminderResult(
                success=False,
                error=str(e)
            )

    async def get_active_reminders(self, user_id: str) -> ReminderResult:
        """
        获取活跃提醒列表

        Args:
            user_id: 用户ID

        Returns:
            ReminderResult: 提醒列表
        """
        user_reminders = self._reminders.get(user_id, [])
        active = [r for r in user_reminders if r.is_active]

        if not active:
            return ReminderResult(
                success=True,
                content="您目前没有活跃的提醒。",
                reminders=[]
            )

        content = "## 📋 您的提醒列表\n\n"

        # 按类型分组
        grouped = {}
        for reminder in active:
            rtype = reminder.type.value
            if rtype not in grouped:
                grouped[rtype] = []
            grouped[rtype].append(reminder)

        type_names = {
            "medication": "💊 用药提醒",
            "appointment": "📅 预约提醒",
            "measurement": "📊 测量提醒",
            "followup": "🔔 随访提醒",
            "checkup": "🏥 体检提醒",
        }

        for rtype, reminders in grouped.items():
            content += f"### {type_names.get(rtype, rtype.upper())}\n\n"
            for reminder in reminders:
                content += f"- **{reminder.title}**: {reminder.time}\n"
            content += "\n"

        return ReminderResult(
            success=True,
            content=content,
            reminders=active
        )

    async def cancel_reminder(
        self,
        user_id: str,
        reminder_id: str
    ) -> ReminderResult:
        """
        取消提醒

        Args:
            user_id: 用户ID
            reminder_id: 提醒ID

        Returns:
            ReminderResult: 取消结果
        """
        user_reminders = self._reminders.get(user_id, [])

        for reminder in user_reminders:
            if reminder.reminder_id == reminder_id:
                reminder.is_active = False
                return ReminderResult(
                    success=True,
                    content=f"提醒「{reminder.title}」已取消。",
                    reminder_id=reminder_id
                )

        return ReminderResult(
            success=False,
            error=f"未找到提醒: {reminder_id}"
        )


# 便捷函数
async def create_reminder(
    user_id: str,
    reminder_type: str,
    **kwargs
) -> str:
    """
    创建提醒（便捷函数）

    Args:
        user_id: 用户ID
        reminder_type: 提醒类型
        **kwargs: 其他参数

    Returns:
        str: 格式化的创建结果
    """
    skill = ReminderServiceSkill()

    if reminder_type == "medication":
        result = await skill.create_medication_reminder(
            user_id,
            kwargs.get("medication_name", "药品"),
            kwargs.get("dosage", "遵医嘱"),
            kwargs.get("frequency", "每日3次"),
            kwargs.get("time_template", "daily_3")
        )
    elif reminder_type == "appointment":
        result = await skill.create_appointment_reminder(
            user_id,
            kwargs.get("appointment_type", "预约"),
            kwargs.get("appointment_time", ""),
            kwargs.get("hospital", "医院"),
            kwargs.get("department")
        )
    elif reminder_type == "measurement":
        result = await skill.create_measurement_reminder(
            user_id,
            kwargs.get("measurement_type", "血压"),
            kwargs.get("frequency", "daily"),
            kwargs.get("time", "08:00")
        )
    else:
        result = ReminderResult(
            success=False,
            error=f"不支持的提醒类型: {reminder_type}"
        )

    return result.content if result.success else f"创建失败: {result.error}"


if __name__ == "__main__":
    # 测试用例
    async def test():
        skill = ReminderServiceSkill()

        # 测试用药提醒
        result = await skill.create_medication_reminder(
            user_id="test_user",
            medication_name="降压药",
            dosage="1片",
            frequency="每日1次",
            time_template="daily_1"
        )
        print(result.content)

        print("\n" + "="*60 + "\n")

        # 测试预约提醒
        result2 = await skill.create_appointment_reminder(
            user_id="test_user",
            appointment_type="复查",
            appointment_time="2026-04-01 10:00",
            hospital="北京协和医院",
            department="心内科"
        )
        print(result2.content)

    import asyncio
    asyncio.run(test())
