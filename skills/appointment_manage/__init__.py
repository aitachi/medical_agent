# -*- coding: utf-8 -*-
"""
预约管理Skill
管理用户的预约挂号，支持查询、取消、修改预约
"""

import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class AppointmentStatus(Enum):
    """预约状态"""
    PENDING = "pending"       # 待支付
    CONFIRMED = "confirmed"   # 已确认
    COMPLETED = "completed"   # 已完成
    CANCELLED = "cancelled"   # 已取消
    EXPIRED = "expired"       # 已过期


@dataclass
class Appointment:
    """预约信息"""
    appointment_id: str
    user_id: str
    hospital: str
    department: str
    doctor: str
    appointment_time: str
    status: AppointmentStatus
    fee: int
    create_time: str


@dataclass
class AppointmentManageResult:
    """预约管理结果"""
    success: bool
    content: str
    appointments: Optional[List[Appointment]] = None
    appointment_id: Optional[str] = None
    error: Optional[str] = None
    follow_up_suggestions: List[str] = field(default_factory=list)


class AppointmentManageSkill:
    """
    预约管理Skill
    管理用户的预约挂号，支持查询、取消、修改预约
    """

    # 模拟预约数据
    MOCK_APPOINTMENTS = {
        "user_001": [
            Appointment(
                appointment_id="APT20260325001",
                user_id="user_001",
                hospital="北京协和医院",
                department="心内科",
                doctor="张主任",
                appointment_time="2026-03-28 09:00",
                status=AppointmentStatus.CONFIRMED,
                fee=50,
                create_time="2026-03-25 10:00:00"
            ),
            Appointment(
                appointment_id="APT20260320002",
                user_id="user_001",
                hospital="北京同仁医院",
                department="眼科",
                doctor="李医生",
                appointment_time="2026-03-15 14:00",
                status=AppointmentStatus.COMPLETED,
                fee=40,
                create_time="2026-03-10 09:30:00"
            ),
        ]
    }

    def __init__(self, mcp_client=None):
        """
        初始化预约管理Skill

        Args:
            mcp_client: MCP客户端，用于调用外部预约系统
        """
        self.mcp_client = mcp_client
        self._appointments = dict(self.MOCK_APPOINTMENTS)

    async def query_appointments(
        self,
        user_id: str,
        status_filter: Optional[str] = None
    ) -> AppointmentManageResult:
        """
        查询预约列表

        Args:
            user_id: 用户ID
            status_filter: 状态过滤（可选）

        Returns:
            AppointmentManageResult: 查询结果
        """
        try:
            user_appointments = self._appointments.get(user_id, [])

            # 状态过滤
            if status_filter:
                try:
                    filter_status = AppointmentStatus(status_filter)
                    user_appointments = [
                        apt for apt in user_appointments
                        if apt.status == filter_status
                    ]
                except ValueError:
                    pass

            if not user_appointments:
                return AppointmentManageResult(
                    success=True,
                    content=self._format_empty_appointments(),
                    appointments=[]
                )

            # 按时间排序
            user_appointments.sort(
                key=lambda x: x.appointment_time,
                reverse=True
            )

            content = self._format_appointment_list(user_appointments)

            return AppointmentManageResult(
                success=True,
                content=content,
                appointments=user_appointments,
                follow_up_suggestions=[
                    "如需取消预约，请提前4小时",
                    "请按时就诊，过时需重新预约"
                ]
            )

        except Exception as e:
            logger.error(f"查询预约失败: {e}")
            return AppointmentManageResult(
                success=False,
                error=str(e)
            )

    def _format_appointment_list(self, appointments: List[Appointment]) -> str:
        """格式化预约列表"""
        content = "## 📋 我的预约\n\n"

        # 按状态分组
        upcoming = [a for a in appointments if a.status in [AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]]
        completed = [a for a in appointments if a.status == AppointmentStatus.COMPLETED]
        cancelled = [a for a in appointments if a.status == AppointmentStatus.CANCELLED]

        if upcoming:
            content += "### 🔜 待就诊\n\n"
            for apt in upcoming:
                status_emoji = "⏰" if apt.status == AppointmentStatus.PENDING else "✅"
                content += self._format_appointment_item(apt, status_emoji)
            content += "\n"

        if completed:
            content += "### ✅ 已完成\n\n"
            for apt in completed[:3]:  # 只显示最近3个
                content += self._format_appointment_item(apt, "✅")
            if len(completed) > 3:
                content += f"...还有{len(completed) - 3}条已完成记录\n"
            content += "\n"

        if cancelled:
            content += "### ❌ 已取消\n\n"
            for apt in cancelled[:2]:
                content += self._format_appointment_item(apt, "❌")
            content += "\n"

        content += "---\n\n"
        content += "> 💡 **提示**: 取消预约请提前4小时，避免爽战记录。"

        return content

    def _format_appointment_item(self, apt: Appointment, emoji: str) -> str:
        """格式化预约条目"""
        appt_datetime = datetime.fromisoformat(apt.appointment_time)
        date_str = appt_datetime.strftime("%Y年%m月%d日")
        time_str = appt_datetime.strftime("%H:%M")

        return f"""{emoji} **{apt.hospital} - {apt.department}**
- 医生: {apt.doctor}
- 时间: {date_str} {time_str}
- 预约号: {apt.appointment_id}
- 挂号费: ¥{apt.fee}

"""

    def _format_empty_appointments(self) -> str:
        """格式化空预约列表"""
        return """## 📋 我的预约

您目前没有预约记录。

---

### 🏥 需要预约吗？

我可以帮您：
- 查看医院科室
- 预约医生门诊
- 选择合适的时间

请告诉我您想挂哪个科，我来帮您安排。

---

> 💡 **提示**: 您也可以直接说"我要挂号"开始预约。
"""

    async def cancel_appointment(
        self,
        user_id: str,
        appointment_id: Optional[str] = None,
        doctor_name: Optional[str] = None
    ) -> AppointmentManageResult:
        """
        取消预约

        Args:
            user_id: 用户ID
            appointment_id: 预约ID
            doctor_name: 医生姓名（用于定位预约）

        Returns:
            AppointmentManageResult: 取消结果
        """
        try:
            user_appointments = self._appointments.get(user_id, [])

            # 查找目标预约
            target_appointment = None

            if appointment_id:
                target_appointment = next(
                    (a for a in user_appointments if a.appointment_id == appointment_id),
                    None
                )
            elif doctor_name:
                target_appointment = next(
                    (a for a in user_appointments
                     if a.status in [AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]
                     and doctor_name in a.doctor),
                    None
                )

            if not target_appointment:
                return AppointmentManageResult(
                    success=False,
                    error="未找到要取消的预约"
                )

            # 检查状态
            if target_appointment.status != AppointmentStatus.CONFIRMED:
                if target_appointment.status == AppointmentStatus.CANCELLED:
                    return AppointmentManageResult(
                        success=False,
                        error="该预约已取消"
                    )
                elif target_appointment.status == AppointmentStatus.COMPLETED:
                    return AppointmentManageResult(
                        success=False,
                        error="该预约已完成，无法取消"
                    )
                elif target_appointment.status == AppointmentStatus.EXPIRED:
                    return AppointmentManageResult(
                        success=False,
                        error="该预约已过期"
                    )

            # 检查时间（提前4小时）
            appt_datetime = datetime.fromisoformat(target_appointment.appointment_time)
            if appt_datetime - datetime.now() < timedelta(hours=4):
                return AppointmentManageResult(
                    success=False,
                    error="预约时间前4小时内无法取消，请联系医院处理"
                )

            # 取消预约
            target_appointment.status = AppointmentStatus.CANCELLED

            content = self._format_cancel_success(target_appointment)

            return AppointmentManageResult(
                success=True,
                content=content,
                appointment_id=target_appointment.appointment_id,
                follow_up_suggestions=[
                    "如需重新预约，请告诉我",
                    "请提前安排好就诊时间"
                ]
            )

        except Exception as e:
            logger.error(f"取消预约失败: {e}")
            return AppointmentManageResult(
                success=False,
                error=str(e)
            )

    def _format_cancel_success(self, apt: Appointment) -> str:
        """格式化取消成功响应"""
        appt_datetime = datetime.fromisoformat(apt.appointment_time)
        date_str = appt_datetime.strftime("%Y年%m月%d日")
        time_str = appt_datetime.strftime("%H:%M")

        content = f"""## ✅ 预约已取消

**预约信息**:
- 医院: {apt.hospital}
- 科室: {apt.department}
- 医生: {apt.doctor}
- 原预约时间: {date_str} {time_str}
- 预约号: {apt.appointment_id}

### 💰 退款说明

挂号费将在3-5个工作日内退回到原支付账户。

---

### 📅 需要重新预约吗？

我可以帮您：
- 预约同一医生的其他时间
- 推荐其他医生
- 选择其他科室

---

> 💡 **提示**: 请合理安排就诊时间，避免频繁取消影响信用。
"""
        return content

    async def get_appointment_detail(
        self,
        user_id: str,
        appointment_id: str
    ) -> AppointmentManageResult:
        """
        获取预约详情

        Args:
            user_id: 用户ID
            appointment_id: 预约ID

        Returns:
            AppointmentManageResult: 预约详情
        """
        user_appointments = self._appointments.get(user_id, [])

        target = next(
            (a for a in user_appointments if a.appointment_id == appointment_id),
            None
        )

        if not target:
            return AppointmentManageResult(
                success=False,
                error="未找到该预约"
            )

        content = self._format_appointment_detail(target)

        return AppointmentManageResult(
            success=True,
            content=content,
            appointments=[target]
        )

    def _format_appointment_detail(self, apt: Appointment) -> str:
        """格式化预约详情"""
        appt_datetime = datetime.fromisoformat(apt.appointment_time)
        date_str = appt_datetime.strftime("%Y年%m月%d日")
        time_str = appt_datetime.strftime("%H:%M")
        weekday = appt_datetime.strftime("%A")

        status_map = {
            AppointmentStatus.PENDING: "待支付",
            AppointmentStatus.CONFIRMED: "已确认",
            AppointmentStatus.COMPLETED: "已完成",
            AppointmentStatus.CANCELLED: "已取消",
            AppointmentStatus.EXPIRED: "已过期"
        }

        content = f"""## 📋 预约详情

### 基本信息

**预约号**: {apt.appointment_id}
**状态**: {status_map.get(apt.status, '')}
**预约时间**: {date_str}（{weekday}） {time_str}

### 医院信息

**医院**: {apt.hospital}
**科室**: {apt.department}
**医生**: {apt.doctor}

### 费用信息

**挂号费**: ¥{apt.fee}
**创建时间**: {apt.create_time}

---

### 📝 就诊提示

- 请提前15分钟到达医院
- 携带身份证和医保卡
- 到达后在自助机取号
- 如需取消请提前4小时

---

### 📞 联系方式

- 医院电话: 010-12345678
- 如有疑问请联系医院客服
"""
        return content


# 便捷函数
async def query_my_appointments(
    user_id: str,
    status_filter: Optional[str] = None,
    mcp_client=None
) -> str:
    """
    查询我的预约（便捷函数）

    Args:
        user_id: 用户ID
        status_filter: 状态过滤
        mcp_client: MCP客户端

    Returns:
        str: 格式化的预约列表
    """
    skill = AppointmentManageSkill(mcp_client)
    result = await skill.query_appointments(user_id, status_filter)
    return result.content if result.success else f"查询失败: {result.error}"


if __name__ == "__main__":
    # 测试用例
    async def test():
        skill = AppointmentManageSkill()

        # 测试查询预约
        result = await skill.query_appointments("user_001")
        print(result.content)

        print("\n" + "="*60 + "\n")

        # 测试取消预约
        result2 = await skill.cancel_appointment(
            user_id="user_001",
            appointment_id="APT20260325001"
        )
        print(result2.content)

    import asyncio
    asyncio.run(test())
