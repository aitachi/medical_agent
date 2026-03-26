# -*- coding: utf-8 -*-
"""
体检服务Skill
提供体检套餐推荐、体检预约、体检报告解读预约等服务
"""

import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class CheckupType(Enum):
    """体检类型"""
    BASIC = "basic"               # 基础体检
    COMPREHENSIVE = "comprehensive" # 全面体检
    EXECUTIVE = "executive"       # 高管体检
    TARGETED = "targeted"         # 针对性体检
    CUSTOM = "custom"             # 自定义体检


class AgeGroup(Enum):
    """年龄分组"""
    YOUNG = "young"       # 18-35岁
    MIDDLE = "middle"     # 36-50岁
    SENIOR = "senior"     # 51-65岁
    ELDERLY = "elderly"   # 65岁以上


@dataclass
class CheckupPackage:
    """体检套餐"""
    package_id: str
    name: str
    type: CheckupType
    price: int
    items: List[str]           # 检查项目
    suitable_for: List[str]    # 适用人群
    duration: str              # 所需时间


@dataclass
class CheckupRecommendation:
    """体检推荐"""
    user_profile: Dict
    recommended_packages: List[CheckupPackage]
    advice: List[str]


@dataclass
class CheckupResult:
    """体检服务结果"""
    success: bool
    content: str
    packages: Optional[List[CheckupPackage]] = None
    recommended_package: Optional[str] = None
    booking_info: Optional[Dict] = None
    error: Optional[str] = None


class CheckupServiceSkill:
    """
    体检服务Skill
    提供体检套餐推荐、体检预约、体检报告解读预约等服务
    """

    # 体检套餐库
    CHECKUP_PACKAGES = {
        "basic_young": CheckupPackage(
            package_id="BASIC_YOUNG",
            name="青年基础体检",
            type=CheckupType.BASIC,
            price=299,
            items=[
                "一般检查（身高、体重、血压）",
                "内科检查",
                "外科检查",
                "血常规",
                "尿常规",
                "肝功能（ALT）",
                "肾功能（肌酐）",
                "空腹血糖",
                "血脂（总胆固醇、甘油三酯）",
                "胸部X线",
                "心电图",
                "健康评估报告"
            ],
            suitable_for=["18-35岁健康人群", "年度基础体检"],
            duration="半天"
        ),
        "basic_middle": CheckupPackage(
            package_id="BASIC_MIDDLE",
            name="中年基础体检",
            type=CheckupType.BASIC,
            price=499,
            items=[
                "一般检查",
                "内科、外科、眼科、耳鼻喉科",
                "血常规",
                "尿常规",
                "肝功能（ALT、AST）",
                "肾功能（肌酐、尿素）",
                "空腹血糖",
                "血脂四项",
                "肿瘤标志物（AFP、CEA）",
                "腹部B超（肝、胆、胰、脾、肾）",
                "胸部X线或CT",
                "心电图",
                "健康评估报告"
            ],
            suitable_for=["36-50岁人群", "亚健康人群"],
            duration="半天"
        ),
        "comprehensive": CheckupPackage(
            package_id="COMPREHENSIVE",
            name="全面体检套餐",
            type=CheckupType.COMPREHENSIVE,
            price=1299,
            items=[
                "一般检查（含体脂分析）",
                "全科室检查（内、外、妇、眼、耳鼻喉、口腔）",
                "血常规",
                "尿常规",
                "肝功能全项",
                "肾功能全项",
                "空腹血糖 + 糖化血红蛋白",
                "血脂全项",
                "甲状腺功能",
                "肿瘤标志物多项",
                "同型半胱氨酸",
                "腹部B超",
                "心脏彩超",
                "颈动脉彩超",
                "甲状腺彩超",
                "胸部低剂量CT",
                "头颅MRI/CT",
                "骨密度检测",
                "碳13呼气试验",
                "心电图",
                "健康评估报告 + 健康指导"
            ],
            suitable_for=["40岁以上人群", "有家族病史", "压力大人群"],
            duration="1天"
        ),
        "executive": CheckupPackage(
            package_id="EXECUTIVE",
            name="高端体检套餐",
            type=CheckupType.EXECUTIVE,
            price=2999,
            items=[
                "全面体检所有项目",
                "基因检测（肿瘤风险）",
                "心脏运动平板试验",
                "头颈部血管MRA",
                "冠脉CTA",
                "胃肠镜（无痛）",
                "PET-CT（可选）",
                "个性化健康规划",
                "VIP专属服务"
            ],
            suitable_for=["企业高管", "高净值人群", "注重健康管理"],
            duration="1-2天"
        ),
        "cardiovascular": CheckupPackage(
            package_id="CARDIO",
            name="心血管专项体检",
            type=CheckupType.TARGETED,
            price=899,
            items=[
                "一般检查",
                "内科、外科",
                "血常规",
                "尿常规",
                "肝肾功能",
                "空腹血糖 + 糖化血红蛋白",
                "血脂全项",
                "同型半胱氨酸",
                "心肌酶谱",
                "BNP（脑钠肽）",
                "心脏彩超",
                "颈动脉彩超",
                "心电图",
                "运动平板试验",
                "心血管评估报告"
            ],
            suitable_for=["心血管疾病高风险", "高血压、糖尿病", "家族史"],
            duration="半天"
        ),
        "female": CheckupPackage(
            package_id="FEMALE",
            name="女性专项体检",
            type=CheckupType.TARGETED,
            price=699,
            items=[
                "基础体检项目",
                "妇科检查",
                "白带常规",
                "TCT（液基薄层细胞检测）",
                "HPV检测",
                "乳腺彩超",
                "妇科彩超（子宫、附件）",
                "骨密度检测",
                "女性激素评估",
                "乳腺、宫颈健康指导"
            ],
            suitable_for=["25岁以上女性", "已婚女性"],
            duration="半天"
        ),
        "male": CheckupPackage(
            package_id="MALE",
            name="男性专项体检",
            type=CheckupType.TARGETED,
            price=599,
            items=[
                "基础体检项目",
                "前列腺彩超",
                "泌尿系彩超",
                "PSA（前列腺特异抗原）",
                "游离PSA",
                "男性激素评估",
                "前列腺健康指导"
            ],
            suitable_for=["40岁以上男性", "中年男性"],
            duration="半天"
        ),
    }

    def __init__(self, mcp_client=None):
        """
        初始化体检服务Skill

        Args:
            mcp_client: MCP客户端，用于调用外部体检系统
        """
        self.mcp_client = mcp_client

    async def recommend(
        self,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        health_concerns: Optional[List[str]] = None,
        budget: Optional[int] = None
    ) -> CheckupResult:
        """
        推荐体检套餐

        Args:
            age: 年龄
            gender: 性别
            health_concerns: 健康关注点
            budget: 预算

        Returns:
            CheckupResult: 推荐结果
        """
        try:
            # 获取年龄分组
            age_group = self._get_age_group(age) if age else None

            # 根据条件筛选套餐
            recommended = self._filter_packages(
                age_group, gender, health_concerns, budget
            )

            if not recommended:
                return CheckupResult(
                    success=False,
                    error="未找到合适的体检套餐，请联系客服定制"
                )

            # 生成推荐说明
            content = self._format_recommendation(
                age, gender, health_concerns, recommended
            )

            return CheckupResult(
                success=True,
                content=content,
                packages=recommended
            )

        except Exception as e:
            logger.error(f"推荐体检套餐失败: {e}")
            return CheckupResult(
                success=False,
                error=str(e)
            )

    def _get_age_group(self, age: int) -> AgeGroup:
        """获取年龄分组"""
        if age < 36:
            return AgeGroup.YOUNG
        elif age < 51:
            return AgeGroup.MIDDLE
        elif age < 66:
            return AgeGroup.SENIOR
        else:
            return AgeGroup.ELDERLY

    def _filter_packages(
        self,
        age_group: Optional[AgeGroup],
        gender: Optional[str],
        health_concerns: Optional[List[str]],
        budget: Optional[int]
    ) -> List[CheckupPackage]:
        """筛选体检套餐"""
        packages = list(self.CHECKUP_PACKAGES.values())

        # 性别筛选
        if gender:
            if gender.lower() in ["女", "female", "f"]:
                packages = [p for p in packages if "female" in p.package_id.lower() or p.type in [CheckupType.BASIC, CheckupType.COMPREHENSIVE]]
            elif gender.lower() in ["男", "male", "m"]:
                packages = [p for p in packages if "male" in p.package_id.lower() or p.type in [CheckupType.BASIC, CheckupType.COMPREHENSIVE]]

        # 预算筛选
        if budget:
            packages = [p for p in packages if p.price <= budget]

        # 健康关注点筛选
        if health_concerns:
            concern_mapping = {
                "心血管": ["cardiovascular", "comprehensive"],
                "心脏": ["cardiovascular", "comprehensive"],
                "血压": ["cardiovascular", "comprehensive"],
                "肿瘤": ["comprehensive", "executive"],
                "癌症": ["comprehensive", "executive"],
                "妇科": ["female"],
                "乳腺": ["female"],
                "宫颈": ["female"],
                "前列腺": ["male"],
                "全面": ["comprehensive", "executive"],
                "高端": ["executive"]
            }

            matched_packages = set()
            for concern in health_concerns:
                for keyword, pkg_ids in concern_mapping.items():
                    if keyword in concern:
                        matched_packages.update(pkg_ids)

            if matched_packages:
                packages = [p for p in packages if any(
                    pkg_id in p.package_id.lower()
                    for pkg_id in matched_packages
                )]

        return packages[:3]  # 返回最多3个推荐

    def _format_recommendation(
        self,
        age: Optional[int],
        gender: Optional[str],
        health_concerns: Optional[List[str]],
        packages: List[CheckupPackage]
    ) -> str:
        """格式化推荐响应"""
        content = "## 🏥 体检套餐推荐\n\n"

        # 个人概况
        if age or gender or health_concerns:
            content += "### 👤 根据您的情况\n\n"
            if age:
                content += f"- **年龄**: {age}岁\n"
            if gender:
                content += f"- **性别**: {gender}\n"
            if health_concerns:
                content += f"- **健康关注**: {', '.join(health_concerns)}\n"
            content += "\n"

        # 推荐套餐
        for i, pkg in enumerate(packages, 1):
            content += f"### 推荐{i}: {pkg.name}\n\n"
            content += f"- **套餐类型**: {pkg.type.value}\n"
            content += f"- **价格**: ¥{pkg.price}\n"
            content += f"- **所需时间**: {pkg.duration}\n"
            content += f"- **适用人群**: {', '.join(pkg.suitable_for)}\n\n"

            content += "**检查项目**:\n"
            for item in pkg.items[:10]:  # 显示前10项
                content += f"- {item}\n"
            if len(pkg.items) > 10:
                content += f"- ...等{len(pkg.items)}项检查\n"
            content += "\n"

        # 预约提示
        content += "### 📅 预约提示\n\n"
        content += "- 体检前3天清淡饮食，避免饮酒\n"
        content += "- 体检前1晚20点后禁食\n"
        content += "- 体检当日早晨空腹（可少量饮水）\n"
        content += "- 女性避开月经期\n"
        content += "- 佩戴者可正常服药（少量水）\n\n"

        return content

    def get_all_packages(self) -> CheckupResult:
        """获取所有体检套餐"""
        content = "## 🏥 体检套餐列表\n\n"

        grouped = {}
        for pkg in self.CHECKUP_PACKAGES.values():
            type_name = pkg.type.value
            if type_name not in grouped:
                grouped[type_name] = []
            grouped[type_name].append(pkg)

        for type_name, packages in grouped.items():
            content += f"### {type_name.upper()}\n\n"
            for pkg in packages:
                content += f"**{pkg.name}** - ¥{pkg.price}\n"
                content += f"- {', '.join(pkg.suitable_for)}\n"
                content += f"- 包含{len(pkg.items)}项检查\n\n"

        return CheckupResult(
            success=True,
            content=content,
            packages=list(self.CHECKUP_PACKAGES.values())
        )


# 便捷函数
async def recommend_checkup(
    age: Optional[int] = None,
    gender: Optional[str] = None,
    health_concerns: Optional[List[str]] = None,
    mcp_client=None
) -> str:
    """
    推荐体检套餐（便捷函数）

    Args:
        age: 年龄
        gender: 性别
        health_concerns: 健康关注点
        mcp_client: MCP客户端

    Returns:
        str: 格式化的推荐结果
    """
    skill = CheckupServiceSkill(mcp_client)
    result = await skill.recommend(age, gender, health_concerns)
    return result.content if result.success else f"推荐失败: {result.error}"


if __name__ == "__main__":
    # 测试用例
    async def test():
        skill = CheckupServiceSkill()

        # 测试推荐
        result = await skill.recommend(
            age=35,
            gender="女",
            health_concerns=["妇科", "乳腺"],
            budget=800
        )
        print(result.content)

        print("\n" + "="*60 + "\n")

        # 测试获取所有套餐
        result2 = skill.get_all_packages()
        print(result2.content)

    import asyncio
    asyncio.run(test())
