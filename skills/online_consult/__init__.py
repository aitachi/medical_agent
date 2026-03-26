# -*- coding: utf-8 -*-
"""
在线问诊Skill
提供图文、视频、电话等多种方式的在线问诊服务
"""

import re
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class ConsultType(Enum):
    """问诊类型"""
    TEXT = "text"           # 图文问诊
    VIDEO = "video"         # 视频问诊
    PHONE = "phone"         # 电话问诊


class ConsultStatus(Enum):
    """问诊状态"""
    PENDING = "pending"     # 待支付
    QUEUED = "queued"       # 已排队
    ACTIVE = "active"       # 进行中
    COMPLETED = "completed" # 已完成
    CANCELLED = "cancelled" # 已取消


class DoctorLevel(Enum):
    """医生级别"""
    CHIEF = "chief"         # 主任医师
    VICE_CHIEF = "vice_chief" # 副主任医师
    ATTENDING = "attending"   # 主治医师
    RESIDENT = "resident"     # 住院医师


@dataclass
class DoctorInfo:
    """医生信息"""
    doctor_id: str
    name: str
    department: str
    level: DoctorLevel
    specialty: List[str]
    experience: int          # 从业年限
    rating: float            # 评分
    consultation_count: int  # 咨询次数
    available: bool          # 是否可接诊
    consult_price: Dict[str, int]  # 各类型问诊价格


@dataclass
class ConsultRequest:
    """问诊请求"""
    consult_type: ConsultType
    department: Optional[str] = None
    doctor_id: Optional[str] = None
    symptom_desc: str = ""
    images: List[str] = field(default_factory=list)
    patient_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsultOrder:
    """问诊订单"""
    consult_id: str
    user_id: str
    consult_type: ConsultType
    doctor: DoctorInfo
    symptom_desc: str
    status: ConsultStatus
    create_time: str
    payment_info: Dict[str, Any]
    queue_position: Optional[int] = None
    estimated_wait: Optional[int] = None


@dataclass
class ConsultResponse:
    """问诊响应"""
    success: bool
    content: str
    consult_id: Optional[str] = None
    status: Optional[ConsultStatus] = None
    queue_position: Optional[int] = None
    estimated_wait: Optional[int] = None
    payment_info: Optional[Dict] = None
    error: Optional[str] = None
    follow_up_suggestions: List[str] = field(default_factory=list)


class OnlineConsultSkill:
    """
    在线问诊Skill
    提供图文、视频、电话等多种方式的在线问诊服务
    """

    # 科室医生列表（模拟数据）
    DEPARTMENT_DOCTORS = {
        "内科": [
            {
                "doctor_id": "D001",
                "name": "张医生",
                "level": DoctorLevel.CHIEF,
                "specialty": ["高血压", "糖尿病", "心血管疾病"],
                "experience": 20,
                "rating": 4.9,
                "consultation_count": 5000,
                "consult_price": {"text": 30, "video": 60, "phone": 50}
            },
            {
                "doctor_id": "D002",
                "name": "李医生",
                "level": DoctorLevel.VICE_CHIEF,
                "specialty": ["呼吸系统", "消化系统"],
                "experience": 15,
                "rating": 4.8,
                "consultation_count": 3500,
                "consult_price": {"text": 25, "video": 50, "phone": 40}
            },
        ],
        "外科": [
            {
                "doctor_id": "D003",
                "name": "王医生",
                "level": DoctorLevel.ATTENDING,
                "specialty": ["普外", "创伤"],
                "experience": 10,
                "rating": 4.7,
                "consultation_count": 2000,
                "consult_price": {"text": 20, "video": 45, "phone": 35}
            },
        ],
        "儿科": [
            {
                "doctor_id": "D004",
                "name": "赵医生",
                "level": DoctorLevel.CHIEF,
                "specialty": ["儿童呼吸", "儿童消化", "新生儿"],
                "experience": 25,
                "rating": 4.9,
                "consultation_count": 6000,
                "consult_price": {"text": 40, "video": 80, "phone": 60}
            },
        ],
        "妇科": [
            {
                "doctor_id": "D005",
                "name": "刘医生",
                "level": DoctorLevel.VICE_CHIEF,
                "specialty": ["妇科炎症", "内分泌", "计划生育"],
                "experience": 12,
                "rating": 4.8,
                "consultation_count": 3000,
                "consult_price": {"text": 30, "video": 55, "phone": 45}
            },
        ],
    }

    # 问诊类型说明
    CONSULT_TYPE_INFO = {
        ConsultType.TEXT: {
            "name": "图文问诊",
            "description": "通过文字和图片与医生沟通，医生24小时内回复",
            "response_time": "24小时内",
            "suitable_for": "症状较轻、需要专业建议、复诊咨询"
        },
        ConsultType.VIDEO: {
            "name": "视频问诊",
            "description": "与医生面对面视频沟通，即时回复",
            "response_time": "即时",
            "suitable_for": "需要面对面交流、病情复杂、看诊检查"
        },
        ConsultType.PHONE: {
            "name": "电话问诊",
            "description": "医生电话回拨，语音沟通",
            "response_time": "预约后1小时内",
            "suitable_for": "不方便视频、需要详细沟通"
        },
    }

    def __init__(self, mcp_client=None):
        """
        初始化在线问诊Skill

        Args:
            mcp_client: MCP客户端，用于调用外部问诊系统
        """
        self.mcp_client = mcp_client
        self._active_consults: Dict[str, ConsultOrder] = {}

    async def get_available_doctors(
        self,
        department: Optional[str] = None,
        consult_type: ConsultType = ConsultType.TEXT
    ) -> List[DoctorInfo]:
        """
        获取可用医生列表

        Args:
            department: 科室（可选）
            consult_type: 问诊类型

        Returns:
            List[DoctorInfo]: 可用医生列表
        """
        # 如果有MCP客户端，调用外部系统
        if self.mcp_client:
            try:
                mcp_result = await self.mcp_client.call_tool(
                    "online_consult",
                    {
                        "action": "get_available_doctors",
                        "department": department,
                        "consult_type": consult_type.value
                    }
                )
                if mcp_result.success:
                    return [
                        DoctorInfo(**doc)
                        for doc in mcp_result.data.get("doctors", [])
                    ]
            except Exception as e:
                logger.warning(f"MCP调用失败，使用本地数据: {e}")

        # 使用本地数据
        doctors = []
        departments = [department] if department else self.DEPARTMENT_DOCTORS.keys()

        for dept in departments:
            if dept in self.DEPARTMENT_DOCTORS:
                for doc_data in self.DEPARTMENT_DOCTORS[dept]:
                    doctor = DoctorInfo(
                        doctor_id=doc_data["doctor_id"],
                        name=doc_data["name"],
                        department=dept,
                        level=doc_data["level"],
                        specialty=doc_data["specialty"],
                        experience=doc_data["experience"],
                        rating=doc_data["rating"],
                        consultation_count=doc_data["consultation_count"],
                        available=True,
                        consult_price=doc_data["consult_price"]
                    )
                    doctors.append(doctor)

        return doctors

    async def recommend_doctors(
        self,
        symptom: str,
        consult_type: ConsultType = ConsultType.TEXT
    ) -> Tuple[List[DoctorInfo], str]:
        """
        根据症状推荐医生

        Args:
            symptom: 症状描述
            consult_type: 问诊类型

        Returns:
            Tuple[List[DoctorInfo], str]: 推荐医生列表和推荐科室
        """
        # 1. 识别症状相关科室
        department = self._identify_department(symptom)

        # 2. 获取该科室医生
        doctors = await self.get_available_doctors(department, consult_type)

        # 3. 根据专科方向排序
        doctors = self._rank_doctors_by_symptom(doctors, symptom)

        return doctors, department

    def _identify_department(self, symptom: str) -> str:
        """根据症状识别科室"""
        symptom_dept_map = {
            # 内科相关
            "头痛": "内科", "头晕": "内科", "发热": "内科", "咳嗽": "内科",
            "胸闷": "内科", "心悸": "内科", "气短": "内科", "乏力": "内科",
            "高血压": "内科", "糖尿病": "内科", "失眠": "内科",

            # 外科相关
            "外伤": "外科", "骨折": "外科", "扭伤": "外科", "伤口": "外科",
            "腹痛": "外科", "阑尾": "外科",

            # 儿科相关
            "儿童": "儿科", "宝宝": "儿科", "小孩": "儿科", "儿科": "儿科",

            # 妇科相关
            "月经": "妇科", "痛经": "妇科", "白带": "妇科", "妇科": "妇科",

            # 皮肤科
            "皮疹": "皮肤科", "过敏": "皮肤科", "瘙痒": "皮肤科",

            # 眼科
            "眼睛": "眼科", "视力": "眼科", "眼痛": "眼科",

            # 耳鼻喉科
            "耳鸣": "耳鼻喉科", "鼻塞": "耳鼻喉科", "咽痛": "耳鼻喉科",
        }

        for symptom_key, dept in symptom_dept_map.items():
            if symptom_key in symptom:
                return dept

        return "内科"  # 默认内科

    def _rank_doctors_by_symptom(
        self,
        doctors: List[DoctorInfo],
        symptom: str
    ) -> List[DoctorInfo]:
        """根据症状对医生排序"""
        scored_doctors = []

        for doctor in doctors:
            score = 0.0

            # 专科匹配加分
            for specialty in doctor.specialty:
                if specialty in symptom:
                    score += 10.0

            # 评分加分
            score += doctor.rating * 2

            # 经验加分
            score += min(doctor.experience / 5, 5)

            # 咨询量加分
            score += min(doctor.consultation_count / 1000, 3)

            scored_doctors.append((score, doctor))

        # 按得分排序
        scored_doctors.sort(key=lambda x: x[0], reverse=True)

        return [doc for _, doc in scored_doctors]

    async def create_consult(
        self,
        request: ConsultRequest,
        user_id: str = "anonymous"
    ) -> ConsultResponse:
        """
        创建问诊单

        Args:
            request: 问诊请求
            user_id: 用户ID

        Returns:
            ConsultResponse: 问诊响应
        """
        # 1. 获取推荐医生
        if request.doctor_id:
            # 指定医生
            doctors = await self.get_available_doctors(request.department)
            doctor = next((d for d in doctors if d.doctor_id == request.doctor_id), None)
            if not doctor:
                return ConsultResponse(
                    success=False,
                    content="抱歉，指定的医生当前不可用",
                    error="Doctor not available"
                )
        else:
            # 推荐医生
            doctors, department = await self.recommend_doctors(
                request.symptom_desc,
                request.consult_type
            )
            if not doctors:
                return ConsultResponse(
                    success=False,
                    content="抱歉，暂无可用医生",
                    error="No available doctors"
                )
            doctor = doctors[0]
            request.department = department

        # 2. 创建订单
        consult_id = f"C{datetime.now().strftime('%Y%m%d%H%M%S')}"
        price = doctor.consult_price.get(request.consult_type.value, 30)

        order = ConsultOrder(
            consult_id=consult_id,
            user_id=user_id,
            consult_type=request.consult_type,
            doctor=doctor,
            symptom_desc=request.symptom_desc,
            status=ConsultStatus.PENDING,
            create_time=datetime.now().isoformat(),
            payment_info={
                "amount": price,
                "currency": "CNY",
                "discount": 0,
                "final_amount": price
            }
        )

        self._active_consults[consult_id] = order

        # 3. 生成响应
        content = self._format_consult_creation(order)

        # 4. 估算等待时间
        estimated_wait = self._estimate_wait_time(doctor, request.consult_type)

        return ConsultResponse(
            success=True,
            content=content,
            consult_id=consult_id,
            status=order.status,
            queue_position=1,
            estimated_wait=estimated_wait,
            payment_info=order.payment_info,
            follow_up_suggestions=[
                "请尽快完成支付以确保问诊",
                "支付完成后医生将尽快接诊",
                "您可以在'我的问诊'中查看状态"
            ]
        )

    def _estimate_wait_time(
        self,
        doctor: DoctorInfo,
        consult_type: ConsultType
    ) -> int:
        """估算等待时间（分钟）"""
        base_wait = {
            ConsultType.TEXT: 60,    # 图文24小时内回复
            ConsultType.VIDEO: 5,    # 视频较快
            ConsultType.PHONE: 30,   # 电话需预约回拨
        }
        return base_wait.get(consult_type, 30)

    def _format_consult_creation(self, order: ConsultOrder) -> str:
        """格式化问诊创建响应"""
        consult_type_info = self.CONSULT_TYPE_INFO[order.consult_type]

        response = f"""## 📅 在线问诊创建成功

**问诊编号**: {order.consult_id}
**问诊类型**: {consult_type_info['name']}
**接诊医生**: {order.doctor.department} - {order.doctor.name} {self._format_level(order.doctor.level)}

### 📋 问诊详情

**医生信息**:
- 职称: {self._format_level(order.doctor.level)}
- 从业经验: {order.doctor.experience}年
- 擅长: {', '.join(order.doctor.specialty)}
- 评分: ⭐{order.doctor.rating}

**问诊说明**: {consult_type_info['description']}

**症状描述**: {order.symptom_desc[:100]}{'...' if len(order.symptom_desc) > 100 else ''}

### 💰 支付信息

**问诊费用**: ¥{order.payment_info['amount']}
**优惠券**: -¥{order.payment_info['discount']}
**实付金额**: ¥{order.payment_info['final_amount']}

### ⏱️ 预计等待时间

{consult_type_info['response_time']}内回复

### 📝 温馨提示

1. 请尽快完成支付以确保问诊
2. 支付完成后，医生将在预计时间内接诊
3. 问诊有效期为24小时
4. 如有紧急情况，请及时就医

---

> ⚠️ **重要提醒**: 在线问诊不能替代线下就诊。如遇紧急情况，请立即拨打120或前往最近医院急诊。"""
        return response

    def _format_level(self, level: DoctorLevel) -> str:
        """格式化医生级别"""
        level_map = {
            DoctorLevel.CHIEF: "主任医师",
            DoctorLevel.VICE_CHIEF: "副主任医师",
            DoctorLevel.ATTENDING: "主治医师",
            DoctorLevel.RESIDENT: "住院医师",
        }
        return level_map.get(level, "")

    async def get_consult_status(self, consult_id: str) -> ConsultResponse:
        """
        获取问诊状态

        Args:
            consult_id: 问诊ID

        Returns:
            ConsultResponse: 问诊状态响应
        """
        order = self._active_consults.get(consult_id)

        if not order:
            return ConsultResponse(
                success=False,
                content="未找到该问诊记录",
                error="Consult not found"
            )

        status_text = self._format_status(order)

        return ConsultResponse(
            success=True,
            content=status_text,
            consult_id=consult_id,
            status=order.status,
            payment_info=order.payment_info
        )

    def _format_status(self, order: ConsultOrder) -> str:
        """格式化问诊状态"""
        status_map = {
            ConsultStatus.PENDING: "待支付",
            ConsultStatus.QUEUED: "排队中",
            ConsultStatus.ACTIVE: "问诊中",
            ConsultStatus.COMPLETED: "已完成",
            ConsultStatus.CANCELLED: "已取消",
        }

        return f"""## 📋 问诊状态

**问诊编号**: {order.consult_id}
**当前状态**: {status_map.get(order.status, '')}
**问诊类型**: {order.consult_type.value}
**接诊医生**: {order.doctor.name}
**创建时间**: {order.create_time}

---

> 💡 如有疑问，请联系客服
"""

    async def cancel_consult(self, consult_id: str) -> ConsultResponse:
        """
        取消问诊

        Args:
            consult_id: 问诊ID

        Returns:
            ConsultResponse: 取消响应
        """
        order = self._active_consults.get(consult_id)

        if not order:
            return ConsultResponse(
                success=False,
                content="未找到该问诊记录",
                error="Consult not found"
            )

        if order.status in [ConsultStatus.COMPLETED, ConsultStatus.CANCELLED]:
            return ConsultResponse(
                success=False,
                content=f"问诊已{order.status.value}，无法取消",
                error="Cannot cancel completed/cancelled consult"
            )

        order.status = ConsultStatus.CANCELLED

        return ConsultResponse(
            success=True,
            content=f"问诊 {consult_id} 已成功取消。退款将在3-5个工作日内返回到原支付账户。",
            consult_id=consult_id,
            status=ConsultStatus.CANCELLED
        )

    def format_consult_types(self) -> str:
        """格式化问诊类型说明"""
        response = "## 📞 问诊类型\n\n"

        for consult_type, info in self.CONSULT_TYPE_INFO.items():
            response += f"### {info['name']}\n\n"
            response += f"- **说明**: {info['description']}\n"
            response += f"- **响应时间**: {info['response_time']}\n"
            response += f"- **适用情况**: {info['suitable_for']}\n\n"

        response += "---\n\n"
        response += "> 💡 **提示**: 图文问诊最经济，视频问诊最直接，请根据需要选择"

        return response

    def format_doctor_list(self, doctors: List[DoctorInfo]) -> str:
        """格式化医生列表"""
        if not doctors:
            return "暂无可用医生"

        response = "## 👨‍⚕️ 可用医生\n\n"

        for i, doctor in enumerate(doctors, 1):
            response += f"### {i}. {doctor.name} {self._format_level(doctor.level)}\n\n"
            response += f"- **科室**: {doctor.department}\n"
            response += f"- **从业经验**: {doctor.experience}年\n"
            response += f"- **擅长**: {', '.join(doctor.specialty)}\n"
            response += f"- **评分**: ⭐{doctor.rating} ({doctor.consultation_count}次咨询)\n"
            response += f"- **价格**: "
            prices = [f"{ct.value}¥{price}" for ct, price in doctor.consult_price.items()]
            response += " | ".join(prices)
            response += "\n\n"

        return response


# 便捷函数
async def start_online_consult(
    symptom: str,
    consult_type: str = "text",
    department: Optional[str] = None,
    doctor_id: Optional[str] = None,
    mcp_client=None
) -> str:
    """
    发起在线问诊（便捷函数）

    Args:
        symptom: 症状描述
        consult_type: 问诊类型
        department: 科室
        doctor_id: 医生ID
        mcp_client: MCP客户端

    Returns:
        str: 格式化的响应
    """
    skill = OnlineConsultSkill(mcp_client)

    if not symptom:
        return skill.format_consult_types()

    # 转换问诊类型
    consult_type_enum = ConsultType(consult_type)

    # 获取推荐医生
    if not doctor_id:
        doctors, recommended_dept = await skill.recommend_doctors(
            symptom, consult_type_enum
        )
        if doctors:
            doctor_info = skill.format_doctor_list(doctors[:3])
            return f"""{skill.format_consult_types()}

## 🎯 根据您的症状，推荐科室: {recommended_dept}

{doctor_info}

💡 请告诉我您想选择哪位医生，或直接说"选择第X位医生"
"""

    # 创建问诊
    request = ConsultRequest(
        consult_type=consult_type_enum,
        department=department,
        doctor_id=doctor_id,
        symptom_desc=symptom
    )

    result = await skill.create_consult(request)
    return result.content


if __name__ == "__main__":
    # 测试用例
    async def test():
        skill = OnlineConsultSkill()

        # 测试获取医生
        doctors, dept = await skill.recommend_doctors("头痛发热")
        print(f"推荐科室: {dept}")
        print(skill.format_doctor_list(doctors[:2]))

        # 测试创建问诊
        request = ConsultRequest(
            consult_type=ConsultType.TEXT,
            symptom_desc="头痛发热两天，伴有咳嗽"
        )
        result = await skill.create_consult(request, user_id="test_user")
        print("\n" + result.content)

    import asyncio
    asyncio.run(test())
