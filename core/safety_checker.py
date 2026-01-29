# -*- coding: utf-8 -*-
"""
医疗智能助手 - 用药安全检查器
检测药物相互作用、过敏风险、剂量问题等
"""

import json
import re
from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SafetySeverity(Enum):
    """安全风险严重程度"""
    SAFE = "safe"              # 安全
    INFO = "info"              # 信息性提示
    LOW = "low"                # 低风险
    MODERATE = "moderate"      # 中度风险
    HIGH = "high"              # 高风险
    CRITICAL = "critical"      # 严重风险，应避免


@dataclass
class SafetyWarning:
    """安全警告"""
    type: str                    # 警告类型：duplicate, interaction, allergy, dose, contraindication
    severity: SafetySeverity     # 严重程度
    message: str                 # 警告消息
    details: Dict[str, Any] = field(default_factory=dict)
    suggestion: str = ""         # 处理建议


@dataclass
class SafetyReport:
    """安全检查报告"""
    safe: bool                          # 是否安全
    warnings: List[SafetyWarning]       # 警告列表
    checked_drugs: List[str]            # 检查的药物列表
    timestamp: str = ""                 # 检查时间
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_critical_warnings(self) -> List[SafetyWarning]:
        """获取严重警告"""
        return [w for w in self.warnings if w.severity == SafetySeverity.CRITICAL]

    def get_high_severity_warnings(self) -> List[SafetyWarning]:
        """获取高风险及以上警告"""
        return [w for w in self.warnings if w.severity in [SafetySeverity.CRITICAL, SafetySeverity.HIGH]]

    def has_critical_issues(self) -> bool:
        """是否有严重问题"""
        return any(w.severity == SafetySeverity.CRITICAL for w in self.warnings)


class DrugSafetyChecker:
    """
    药物安全检查器
    检查重复用药、药物相互作用、过敏风险、剂量问题、禁忌症等
    """

    # 内置药物相互作用数据
    DEFAULT_INTERACTIONS = {
        "critical": [
            {"drugs": ["阿司匹林", "布洛芬"], "description": "增加出血风险，可能导致胃肠道出血"},
            {"drugs": ["华法林", "阿司匹林"], "description": "显著增加出血风险"},
            {"drugs": ["硝苯地平", "β受体阻滞剂"], "description": "可能导致严重低血压和心动过缓"},
            {"drugs": ["头孢类抗生素", "酒精"], "description": "双硫仑样反应：面部潮红、头痛、胸闷、呼吸困难"},
        ],
        "moderate": [
            {"drugs": ["奥美拉唑", "氯吡格雷"], "description": "降低氯吡格雷抗血小板效果"},
            {"drugs": ["二甲双胍", "碘造影剂"], "description": "增加乳酸酸中毒风险"},
            {"drugs": ["地高辛", "胺碘酮"], "description": "增加地高辛血药浓度，可能导致中毒"},
        ]
    }

    # 内置药物数据
    DEFAULT_DRUGS = {
        "阿莫西林": {
            "contraindications": ["青霉素过敏"],
            "max_dose_daily": 4000,  # mg
            "max_dose_single": 1000,  # mg
            "common_allergens": ["青霉素", "抗生素"],
        },
        "布洛芬": {
            "contraindications": ["活动性消化道溃疡", "阿司匹林过敏", "严重心衰"],
            "max_dose_daily": 1200,  # mg
            "max_dose_single": 400,  # mg
            "common_allergens": ["阿司匹林", "NSAID"],
        },
        "对乙酰氨基酚": {
            "contraindications": ["严重肝肾功能不全"],
            "max_dose_daily": 2000,  # mg
            "max_dose_single": 1000,  # mg
            "common_allergens": [],
        },
        "二甲双胍": {
            "contraindications": ["严重肾功能不全", "酮症酸中毒"],
            "max_dose_daily": 2550,  # mg
            "max_dose_single": 1000,  # mg
            "common_allergens": [],
        },
        "硝苯地平": {
            "contraindications": ["严重主动脉瓣狭窄", "心源性休克"],
            "max_dose_daily": 60,  # mg
            "max_dose_single": 20,  # mg
            "common_allergens": [],
        },
        "奥美拉唑": {
            "contraindications": ["对本品过敏"],
            "max_dose_daily": 40,  # mg
            "max_dose_single": 40,  # mg
            "common_allergens": ["苯并咪唑"],
        },
        "头孢氨苄": {
            "contraindications": ["对头孢类抗生素过敏"],
            "max_dose_daily": 4000,  # mg
            "max_dose_single": 1000,  # mg
            "common_allergens": ["头孢类", "抗生素"],
        },
    }

    def __init__(self, knowledge_base_path: Optional[str] = None):
        """
        初始化安全检查器

        Args:
            knowledge_base_path: 外部知识库路径
        """
        self.interactions = dict(self.DEFAULT_INTERACTIONS)
        self.drugs = dict(self.DEFAULT_DRUGS)
        self.knowledge_base_path = knowledge_base_path

        # 尝试从外部知识库加载
        if knowledge_base_path:
            self._load_from_knowledge_base()

    def _load_from_knowledge_base(self):
        """从外部知识库加载药物数据"""
        try:
            kb_path = Path(self.knowledge_base_path)
            if not kb_path.exists():
                return

            with open(kb_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载药物数据
            external_drugs = data.get('drugs', {})
            self.drugs.update(external_drugs)

            # 加载药物相互作用数据
            external_interactions = data.get('drug_interactions', {})
            for severity, interactions in external_interactions.items():
                if severity not in self.interactions:
                    self.interactions[severity] = []
                self.interactions[severity].extend(interactions)

        except Exception as e:
            import warnings
            warnings.warn(f"Failed to load drug data from knowledge base: {e}")

    async def check(
        self,
        drugs: List[str],
        user_profile: Optional[Dict[str, Any]] = None,
        check_interaction: bool = True,
        check_allergy: bool = True,
        check_dose: bool = True,
        check_contraindication: bool = True
    ) -> SafetyReport:
        """
        执行全面的安全检查

        Args:
            drugs: 药物列表
            user_profile: 用户画像，包含过敏史、疾病史等
            check_interaction: 是否检查相互作用
            check_allergy: 是否检查过敏
            check_dose: 是否检查剂量
            check_contraindication: 是否检查禁忌症

        Returns:
            SafetyReport: 安全检查报告
        """
        from datetime import datetime

        warnings_list = []
        checked_drugs = []

        # 标准化药物名称
        normalized_drugs = self._normalize_drug_names(drugs)

        # 1. 重复用药检查
        duplicate_warnings = self._check_duplicates(normalized_drugs)
        warnings_list.extend(duplicate_warnings)

        # 2. 相互作用检查
        if check_interaction:
            interaction_warnings = self._check_interactions(normalized_drugs)
            warnings_list.extend(interaction_warnings)

        # 3. 过敏检查
        if check_allergy and user_profile:
            allergy_warnings = self._check_allergies(normalized_drugs, user_profile)
            warnings_list.extend(allergy_warnings)

        # 4. 禁忌症检查
        if check_contraindication and user_profile:
            contraindication_warnings = self._check_contraindications(normalized_drugs, user_profile)
            warnings_list.extend(contraindication_warnings)

        # 5. 剂量检查
        if check_dose and user_profile:
            dose_warnings = self._check_doses(normalized_drugs, user_profile)
            warnings_list.extend(dose_warnings)

        # 确定是否安全
        critical_issues = [w for w in warnings_list if w.severity == SafetySeverity.CRITICAL]
        safe = len(critical_issues) == 0

        return SafetyReport(
            safe=safe,
            warnings=warnings_list,
            checked_drugs=list(set(normalized_drugs)),
            timestamp=datetime.now().isoformat(),
            metadata={
                "profile_checked": user_profile is not None,
                "checks_performed": {
                    "interaction": check_interaction,
                    "allergy": check_allergy,
                    "dose": check_dose,
                    "contraindication": check_contraindication,
                }
            }
        )

    def _normalize_drug_names(self, drugs: List[str]) -> List[str]:
        """标准化药物名称"""
        normalized = []
        for drug in drugs:
            drug = drug.strip()
            # 移除剂量信息
            drug = re.sub(r'\d+(\.\d+)?\s*(mg|g|ml|片|粒|粒)', '', drug, flags=re.IGNORECASE)
            # 查找匹配的标准名称
            matched = self._find_standard_name(drug)
            normalized.append(matched)
        return [d for d in normalized if d]

    def _find_standard_name(self, drug_name: str) -> Optional[str]:
        """查找标准药物名称"""
        # 精确匹配
        if drug_name in self.drugs:
            return drug_name

        # 模糊匹配
        for standard_name in self.drugs.keys():
            if drug_name in standard_name or standard_name in drug_name:
                return standard_name

        # 检查通用名
        for standard_name, info in self.drugs.items():
            if info.get('english_name', '').lower() == drug_name.lower():
                return standard_name

        return drug_name  # 返回原名

    def _check_duplicates(self, drugs: List[str]) -> List[SafetyWarning]:
        """检查重复用药"""
        warnings_list = []

        # 简单重复
        seen = set()
        duplicates = set()
        for drug in drugs:
            if drug in seen:
                duplicates.add(drug)
            seen.add(drug)

        if duplicates:
            warnings_list.append(SafetyWarning(
                type="duplicate",
                severity=SafetySeverity.HIGH,
                message=f"检测到重复用药: {', '.join(duplicates)}",
                details={"drugs": list(duplicates)},
                suggestion="请确认是否需要同时使用相同药物，避免过量"
            ))

        # 成分类似药物检测
        similar_pairs = self._find_similar_drugs(drugs)
        for pair in similar_pairs:
            warnings_list.append(SafetyWarning(
                type="similar",
                severity=SafetySeverity.MODERATE,
                message=f"{pair[0]}和{pair[1]}属于同类药物，可能产生重复效果",
                details={"drugs": pair},
                suggestion="请咨询医生或药师是否可以同时使用"
            ))

        return warnings_list

    def _find_similar_drugs(self, drugs: List[str]) -> List[Tuple[str, str]]:
        """查找同类药物"""
        similar_pairs = []

        # 解热镇痛药
        nsaid_drugs = [d for d in drugs if d in ["阿司匹林", "布洛芬", "对乙酰氨基酚", "双氯芬酸钠"]]
        if len(nsaid_drugs) > 1:
            for i in range(len(nsaid_drugs)):
                for j in range(i + 1, len(nsaid_drugs)):
                    similar_pairs.append((nsaid_drugs[i], nsaid_drugs[j]))

        # 抗生素
        antibiotic_drugs = [d for d in drugs if d in ["阿莫西林", "头孢氨苄", "阿奇霉素"]]
        if len(antibiotic_drugs) > 1:
            for i in range(len(antibiotic_drugs)):
                for j in range(i + 1, len(antibiotic_drugs)):
                    similar_pairs.append((antibiotic_drugs[i], antibiotic_drugs[j]))

        return similar_pairs

    def _check_interactions(self, drugs: List[str]) -> List[SafetyWarning]:
        """检查药物相互作用"""
        warnings_list = []

        for severity, interactions in self.interactions.items():
            for interaction in interactions:
                interaction_drugs = interaction['drugs']

                # 检查是否包含相互作用药物
                matched_drugs = [d for d in drugs if d in interaction_drugs or any(
                    id in d for id in interaction_drugs
                )]

                # 特殊处理：酒精
                if "酒精" in interaction_drugs:
                    continue  # 需要单独处理

                if len(matched_drugs) >= 2:
                    severity_level = {
                        "critical": SafetySeverity.CRITICAL,
                        "moderate": SafetySeverity.MODERATE
                    }.get(severity, SafetySeverity.LOW)

                    warnings_list.append(SafetyWarning(
                        type="interaction",
                        severity=severity_level,
                        message=f"药物相互作用警告: {', '.join(matched_drugs)}",
                        details={
                            "drugs": matched_drugs,
                            "interaction": interaction['description']
                        },
                        suggestion="请咨询医生或药师"
                    ))

        return warnings_list

    def _check_allergies(self, drugs: List[str], user_profile: Dict[str, Any]) -> List[SafetyWarning]:
        """检查过敏风险"""
        warnings_list = []

        # 处理UserProfile对象或字典
        if hasattr(user_profile, 'allergies'):
            allergies = user_profile.allergies
        else:
            allergies = user_profile.get('allergies', [])

        if not allergies:
            return warnings_list

        for drug in drugs:
            drug_info = self.drugs.get(drug, {})
            drug_allergens = drug_info.get('common_allergens', [])

            # 检查直接过敏
            if drug in allergies:
                warnings_list.append(SafetyWarning(
                    type="allergy",
                    severity=SafetySeverity.CRITICAL,
                    message=f"用户对{drug}过敏，禁用此药！",
                    details={"drug": drug, "allergen": drug},
                    suggestion="请勿使用此药物，立即告知医生"
                ))

            # 检查交叉过敏
            for allergen in drug_allergens:
                if allergen in allergies:
                    warnings_list.append(SafetyWarning(
                        type="allergy_cross",
                        severity=SafetySeverity.CRITICAL,
                        message=f"可能对{drug}存在交叉过敏（对{allergen}过敏）",
                        details={"drug": drug, "allergen": allergen},
                        suggestion="请咨询医生或药师"
                    ))

        return warnings_list

    def _check_contraindications(self, drugs: List[str], user_profile: Dict[str, Any]) -> List[SafetyWarning]:
        """检查禁忌症"""
        warnings_list = []

        # 获取用户的疾病史 - 支持UserProfile对象和字典
        if hasattr(user_profile, 'medical_history'):
            conditions = list(user_profile.medical_history)
            if hasattr(user_profile, 'chronic_conditions'):
                conditions.extend(user_profile.chronic_conditions)
        else:
            conditions = list(user_profile.get('medical_history', []))
            conditions.extend(user_profile.get('chronic_conditions', []))

        if not conditions:
            return warnings_list

        for drug in drugs:
            drug_info = self.drugs.get(drug, {})
            contraindications = drug_info.get('contraindications', [])

            for contraindication in contraindications:
                # 检查是否与用户疾病史冲突
                for condition in conditions:
                    if contraindication.lower() in condition.lower() or condition.lower() in contraindication.lower():
                        warnings_list.append(SafetyWarning(
                            type="contraindication",
                            severity=SafetySeverity.HIGH,
                            message=f"{drug}禁用于{contraindication}",
                            details={
                                "drug": drug,
                                "contraindication": contraindication,
                                "user_condition": condition
                            },
                            suggestion=f"有{condition}的患者应避免使用{drug}"
                        ))

        return warnings_list

    def _check_doses(self, drugs: List[str], user_profile: Dict[str, Any]) -> List[SafetyWarning]:
        """检查剂量"""
        warnings_list = []

        # 获取用户当前用药 - 支持UserProfile对象和字典
        if hasattr(user_profile, 'current_medications'):
            current_medications = user_profile.current_medications
        else:
            current_medications = user_profile.get('current_medications', {})

        for drug in drugs:
            drug_info = self.drugs.get(drug, {})

            # 检查最大单次剂量
            max_single = drug_info.get('max_dose_single')
            if max_single:
                # 这里需要从用户输入或配置中获取实际剂量
                # 简化处理：假设current_medications中包含剂量信息
                if drug in current_medications:
                    dose_info = current_medications[drug]
                    if isinstance(dose_info, dict):
                        actual_dose = dose_info.get('dose_single', 0)
                    else:
                        actual_dose = 0

                    if actual_dose > max_single:
                        warnings_list.append(SafetyWarning(
                            type="dose",
                            severity=SafetySeverity.HIGH,
                            message=f"{drug}单次剂量可能过高",
                            details={
                                "drug": drug,
                                "actual_dose": actual_dose,
                                "max_dose_single": max_single
                            },
                            suggestion=f"单次剂量不应超过{max_single}mg"
                        ))

            # 检查最大日剂量
            max_daily = drug_info.get('max_dose_daily')
            if max_daily:
                if drug in current_medications:
                    dose_info = current_medications[drug]
                    if isinstance(dose_info, dict):
                        daily_dose = dose_info.get('dose_daily', 0)
                    else:
                        daily_dose = 0

                    if daily_dose > max_daily:
                        warnings_list.append(SafetyWarning(
                            type="dose",
                            severity=SafetySeverity.CRITICAL,
                            message=f"{drug}日剂量超过安全上限！",
                            details={
                                "drug": drug,
                                "daily_dose": daily_dose,
                                "max_dose_daily": max_daily
                            },
                            suggestion=f"日剂量不应超过{max_daily}mg"
                        ))

        return warnings_list

    def check_alcohol_interaction(self, drugs: List[str]) -> List[SafetyWarning]:
        """检查酒精相互作用"""
        warnings_list = []

        alcohol_interactions = [
            ("头孢氨苄", "双硫仑样反应：面部潮红、头痛、胸闷、呼吸困难"),
            ("头孢类抗生素", "双硫仑样反应"),
            ("甲硝唑", "双硫仑样反应"),
            ("对乙酰氨基酚", "增加肝毒性风险"),
            ("布洛芬", "增加胃肠道出血风险"),
            ("阿司匹林", "增加胃肠道出血风险"),
        ]

        for drug in drugs:
            for interaction_drug, effect in alcohol_interactions:
                if interaction_drug in drug or drug in interaction_drug:
                    warnings_list.append(SafetyWarning(
                        type="alcohol_interaction",
                        severity=SafetySeverity.CRITICAL,
                        message=f"{drug}与酒精同用可能产生严重反应",
                        details={"drug": drug, "effect": effect},
                        suggestion="用药期间及停药后7天内禁止饮酒"
                    ))

        return warnings_list

    def format_report(self, report: SafetyReport) -> str:
        """格式化安全检查报告为用户可读格式"""
        lines = []

        if report.safe:
            lines.append("✅ 用药安全检查通过，未发现严重问题。\n")
        else:
            lines.append("⚠️ **用药安全检查发现以下问题**\n")

        # 按严重程度分组
        by_severity = {
            SafetySeverity.CRITICAL: [],
            SafetySeverity.HIGH: [],
            SafetySeverity.MODERATE: [],
            SafetySeverity.LOW: [],
            SafetySeverity.INFO: [],
        }

        for warning in report.warnings:
            by_severity[warning.severity].append(warning)

        # 严重警告
        if by_severity[SafetySeverity.CRITICAL]:
            lines.append("🚨 **严重警告**")
            for warning in by_severity[SafetySeverity.CRITICAL]:
                lines.append(f"- {warning.message}")
                if warning.suggestion:
                    lines.append(f"  建议: {warning.suggestion}")
            lines.append("")

        # 高风险
        if by_severity[SafetySeverity.HIGH]:
            lines.append("⚠️ **高风险**")
            for warning in by_severity[SafetySeverity.HIGH]:
                lines.append(f"- {warning.message}")
                if warning.suggestion:
                    lines.append(f"  建议: {warning.suggestion}")
            lines.append("")

        # 中度风险
        if by_severity[SafetySeverity.MODERATE]:
            lines.append("⚡ **中度风险**")
            for warning in by_severity[SafetySeverity.MODERATE]:
                lines.append(f"- {warning.message}")
                if warning.suggestion:
                    lines.append(f"  建议: {warning.suggestion}")
            lines.append("")

        # 检查的药物
        lines.append(f"\n已检查药物: {', '.join(report.checked_drugs)}")

        # 免责声明
        lines.append("\n---\n")
        lines.append("> ⚠️ **免责声明**: 以上安全检查仅供参考，不能替代专业医疗建议。")
        lines.append("> 用药前请咨询医生或药师，严格按医嘱使用。")

        return "\n".join(lines)

    def reload_data(self, knowledge_base_path: Optional[str] = None):
        """重新加载数据"""
        if knowledge_base_path:
            self.knowledge_base_path = knowledge_base_path

        self.interactions = dict(self.DEFAULT_INTERACTIONS)
        self.drugs = dict(self.DEFAULT_DRUGS)

        if self.knowledge_base_path:
            self._load_from_knowledge_base()


# ============================================================
# 便捷函数
# ============================================================

async def check_drug_safety(
    drugs: List[str],
    user_profile: Optional[Dict[str, Any]] = None,
    knowledge_base_path: Optional[str] = None
) -> SafetyReport:
    """
    便捷函数：检查用药安全

    Args:
        drugs: 药物列表
        user_profile: 用户画像
        knowledge_base_path: 知识库路径

    Returns:
        SafetyReport: 安全检查报告
    """
    checker = DrugSafetyChecker(knowledge_base_path)
    return await checker.check(drugs, user_profile)


# ============================================================
# 测试代码
# ============================================================

if __name__ == "__main__":
    import asyncio

    async def test():
        # 测试安全检查
        checker = DrugSafetyChecker()

        # 测试用例1: 重复用药
        print("=" * 60)
        print("测试1: 重复用药")
        report1 = await checker.check(["阿司匹林", "阿司匹林", "布洛芬"])
        print(checker.format_report(report1))

        # 测试用例2: 相互作用
        print("\n" + "=" * 60)
        print("测试2: 相互作用")
        report2 = await checker.check(["阿司匹林", "布洛芬"])
        print(checker.format_report(report2))

        # 测试用例3: 过敏检查
        print("\n" + "=" * 60)
        print("测试3: 过敏检查")
        profile = {"allergies": ["青霉素", "阿司匹林"]}
        report3 = await checker.check(["阿莫西林", "对乙酰氨基酚"], profile)
        print(checker.format_report(report3))

        # 测试用例4: 综合检查
        print("\n" + "=" * 60)
        print("测试4: 综合检查（有过敏史）")
        profile = {
            "allergies": ["青霉素"],
            "medical_history": ["胃溃疡"],
            "chronic_conditions": ["高血压"],
        }
        report4 = await checker.check(["阿莫西林", "布洛芬", "硝苯地平"], profile)
        print(checker.format_report(report4))

    asyncio.run(test())
