# -*- coding: utf-8 -*-
"""
报告解读Skill
解读各类医学检查报告，包括血常规、生化、尿液、影像报告等
"""

import re
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class ReportType(Enum):
    """报告类型"""
    BLOOD_ROUTINE = "blood_routine"      # 血常规
    URINE_ROUTINE = "urine_routine"      # 尿常规
    BIOCHEMISTRY = "biochemistry"        # 生化
    BLOOD_LIPID = "blood_lipid"          # 血脂
    LIVER_FUNCTION = "liver_function"    # 肝功能
    KIDNEY_FUNCTION = "kidney_function"  # 肾功能
    BLOOD_SUGAR = "blood_sugar"          # 血糖
    THYROID = "thyroid"                  # 甲状腺
    TUMOR_MARKERS = "tumor_markers"      # 肿瘤标志物
    IMAGE_CT = "image_ct"                # CT
    IMAGE_MRI = "image_mri"              # MRI
    IMAGE_ULTRASOUND = "image_ultrasound"# B超
    IMAGE_XRAY = "image_xray"            # X光
    ECG = "ecg"                          # 心电图
    UNKNOWN = "unknown"


@dataclass
class IndicatorResult:
    """指标检查结果"""
    name: str                    # 指标名称
    value: str                   # 检测值
    unit: str                    # 单位
    reference_range: str         # 参考范围
    is_abnormal: bool            # 是否异常
    abnormal_type: str           # 异常类型: high/low/positive/negative
    clinical_significance: str   # 临床意义
    suggestions: List[str]       # 建议


@dataclass
class ReportInterpretationResult:
    """报告解读结果"""
    report_type: ReportType
    summary: str                         # 报告摘要
    abnormal_indicators: List[IndicatorResult]  # 异常指标
    normal_indicators: List[IndicatorResult]    # 正常指标
    overall_assessment: str              # 综合评估
    recommendations: List[str]           # 建议
    need_follow_up: bool                 # 是否需要随访
    follow_up_suggestions: str           # 随访建议


class ReportInterpreterSkill:
    """
    报告解读Skill
    解读各类医学检查报告，对比参考范围，标记异常指标，给出就医建议
    """

    # 血常规参考范围
    BLOOD_ROUTINE_RANGES = {
        "WBC": {"name": "白细胞", "unit": "10^9/L", "ref": "4.0-10.0", "low": "<4.0", "high": ">10.0"},
        "RBC": {"name": "红细胞", "unit": "10^12/L", "ref": "4.0-5.5", "low": "<4.0", "high": ">5.5"},
        "HGB": {"name": "血红蛋白", "unit": "g/L", "ref": "120-160", "low": "<120", "high": ">160"},
        "HCT": {"name": "红细胞压积", "unit": "%", "ref": "37-50", "low": "<37", "high": ">50"},
        "PLT": {"name": "血小板", "unit": "10^9/L", "ref": "100-300", "low": "<100", "high": ">300"},
        "NEUT%": {"name": "中性粒细胞%", "unit": "%", "ref": "50-70", "low": "<50", "high": ">70"},
        "LYMPH%": {"name": "淋巴细胞%", "unit": "%", "ref": "20-40", "low": "<20", "high": ">40"},
        "MONO%": {"name": "单核细胞%", "unit": "%", "ref": "3-8", "low": "<3", "high": ">8"},
    }

    # 生化参考范围
    BIOCHEMISTRY_RANGES = {
        "ALT": {"name": "谷丙转氨酶", "unit": "U/L", "ref": "0-40", "low": "", "high": ">40"},
        "AST": {"name": "谷草转氨酶", "unit": "U/L", "ref": "0-40", "low": "", "high": ">40"},
        "TP": {"name": "总蛋白", "unit": "g/L", "ref": "65-85", "low": "<65", "high": ">85"},
        "ALB": {"name": "白蛋白", "unit": "g/L", "ref": "40-55", "low": "<40", "high": ">55"},
        "GLB": {"name": "球蛋白", "unit": "g/L", "ref": "20-40", "low": "<20", "high": ">40"},
        "TBIL": {"name": "总胆红素", "unit": "umol/L", "ref": "5-21", "low": "", "high": ">21"},
        "DBIL": {"name": "直接胆红素", "unit": "umol/L", "ref": "0-7", "low": "", "high": ">7"},
    }

    # 血脂参考范围
    BLOOD_LIPID_RANGES = {
        "TC": {"name": "总胆固醇", "unit": "mmol/L", "ref": "<5.2", "low": "", "high": ">=5.2"},
        "TG": {"name": "甘油三酯", "unit": "mmol/L", "ref": "<1.7", "low": "", "high": ">=1.7"},
        "HDL-C": {"name": "高密度脂蛋白", "unit": "mmol/L", "ref": ">1.0", "low": "<=1.0", "high": ""},
        "LDL-C": {"name": "低密度脂蛋白", "unit": "mmol/L", "ref": "<3.4", "low": "", "high": ">=3.4"},
    }

    # 肾功能参考范围
    KIDNEY_FUNCTION_RANGES = {
        "CRE": {"name": "肌酐", "unit": "umol/L", "ref": "44-133", "low": "<44", "high": ">133"},
        "UREA": {"name": "尿素", "unit": "mmol/L", "ref": "2.9-8.2", "low": "<2.9", "high": ">8.2"},
        "UA": {"name": "尿酸", "unit": "umol/L", "ref": "150-420", "low": "<150", "high": ">420"},
        "eGFR": {"name": "肾小球滤过率", "unit": "ml/min", "ref": ">90", "low": "<=90", "high": ""},
    }

    # 血糖参考范围
    BLOOD_SUGAR_RANGES = {
        "GLU": {"name": "空腹血糖", "unit": "mmol/L", "ref": "3.9-6.1", "low": "<3.9", "high": ">6.1"},
        "HbA1c": {"name": "糖化血红蛋白", "unit": "%", "ref": "4-6", "low": "", "high": ">6"},
        "2hPG": {"name": "餐后2h血糖", "unit": "mmol/L", "ref": "<7.8", "low": "", "high": ">=7.8"},
    }

    # 尿常规参考范围
    URINE_ROUTINE_RANGES = {
        "U_PRO": {"name": "尿蛋白", "unit": "", "ref": "阴性", "positive": "阳性"},
        "U_GLU": {"name": "尿糖", "unit": "", "ref": "阴性", "positive": "阳性"},
        "U_BLD": {"name": "尿潜血", "unit": "", "ref": "阴性", "positive": "阳性"},
        "U_LEU": {"name": "尿白细胞", "unit": "", "ref": "阴性", "positive": "阳性"},
        "U_KET": {"name": "尿酮体", "unit": "", "ref": "阴性", "positive": "阳性"},
        "pH": {"name": "尿pH值", "unit": "", "ref": "5.5-7.5", "low": "<5.5", "high": ">7.5"},
    }

    # 甲状腺功能参考范围
    THYROID_RANGES = {
        "TSH": {"name": "促甲状腺激素", "unit": "mIU/L", "ref": "0.27-4.2", "low": "<0.27", "high": ">4.2"},
        "FT3": {"name": "游离T3", "unit": "pmol/L", "ref": "3.1-6.8", "low": "<3.1", "high": ">6.8"},
        "FT4": {"name": "游离T4", "unit": "pmol/L", "ref": "12-22", "low": "<12", "high": ">22"},
        "T3": {"name": "总T3", "unit": "nmol/L", "ref": "1.3-3.1", "low": "<1.3", "high": ">3.1"},
        "T4": {"name": "总T4", "unit": "nmol/L", "ref": "66-181", "low": "<66", "high": ">181"},
    }

    def __init__(self, mcp_client=None):
        """
        初始化报告解读Skill

        Args:
            mcp_client: MCP客户端，用于调用外部医学知识库
        """
        self.mcp_client = mcp_client
        self.all_ranges = {
            ReportType.BLOOD_ROUTINE: self.BLOOD_ROUTINE_RANGES,
            ReportType.BIOCHEMISTRY: self.BIOCHEMISTRY_RANGES,
            ReportType.BLOOD_LIPID: self.BLOOD_LIPID_RANGES,
            ReportType.KIDNEY_FUNCTION: self.KIDNEY_FUNCTION_RANGES,
            ReportType.BLOOD_SUGAR: self.BLOOD_SUGAR_RANGES,
            ReportType.URINE_ROUTINE: self.URINE_ROUTINE_RANGES,
            ReportType.LIVER_FUNCTION: self.BIOCHEMISTRY_RANGES,
            ReportType.THYROID: self.THYROID_RANGES,
        }

    async def interpret(
        self,
        report_text: str,
        report_type: Optional[str] = None
    ) -> ReportInterpretationResult:
        """
        解读检查报告

        Args:
            report_text: 报告文本内容
            report_type: 报告类型（可选）

        Returns:
            ReportInterpretationResult: 解读结果
        """
        # 1. 识别报告类型
        detected_type = self._detect_report_type(report_text, report_type)

        # 2. 解析指标数据
        indicators = self._parse_indicators(report_text, detected_type)

        # 3. 分析异常指标
        abnormal_indicators = []
        normal_indicators = []

        for indicator in indicators:
            if indicator.is_abnormal:
                abnormal_indicators.append(indicator)
            else:
                normal_indicators.append(indicator)

        # 4. 综合评估
        overall_assessment = self._generate_overall_assessment(
            detected_type, abnormal_indicators
        )

        # 5. 生成建议
        recommendations = self._generate_recommendations(
            detected_type, abnormal_indicators
        )

        # 6. 随访建议
        need_follow_up, follow_up_suggestions = self._generate_follow_up(
            detected_type, abnormal_indicators
        )

        return ReportInterpretationResult(
            report_type=detected_type,
            summary=self._generate_summary(detected_type, abnormal_indicators),
            abnormal_indicators=abnormal_indicators,
            normal_indicators=normal_indicators,
            overall_assessment=overall_assessment,
            recommendations=recommendations,
            need_follow_up=need_follow_up,
            follow_up_suggestions=follow_up_suggestions
        )

    def _detect_report_type(
        self,
        text: str,
        hint_type: Optional[str] = None
    ) -> ReportType:
        """检测报告类型"""
        if hint_type:
            type_map = {
                "blood": ReportType.BLOOD_ROUTINE,
                "blood_routine": ReportType.BLOOD_ROUTINE,
                "urine": ReportType.URINE_ROUTINE,
                "biochemistry": ReportType.BIOCHEMISTRY,
                "lipid": ReportType.BLOOD_LIPID,
                "liver": ReportType.LIVER_FUNCTION,
                "kidney": ReportType.KIDNEY_FUNCTION,
                "sugar": ReportType.BLOOD_SUGAR,
                "thyroid": ReportType.THYROID,
                "ct": ReportType.IMAGE_CT,
                "mri": ReportType.IMAGE_MRI,
                "ultrasound": ReportType.IMAGE_ULTRASOUND,
                "xray": ReportType.IMAGE_XRAY,
                "ecg": ReportType.ECG,
            }
            if hint_type.lower() in type_map:
                return type_map[hint_type.lower()]

        # 根据关键词检测
        text_lower = text.lower()

        if any(kw in text_lower for kw in ["血常规", "白细胞", "红细胞", "血红蛋白", "wbc", "rbc", "hgb"]):
            return ReportType.BLOOD_ROUTINE
        elif any(kw in text_lower for kw in ["尿常规", "尿液", "尿蛋白", "u_pro", "u_glu"]):
            return ReportType.URINE_ROUTINE
        elif any(kw in text_lower for kw in ["血脂", "胆固醇", "甘油三酯", "tc", "tg", "hdl", "ldl"]):
            return ReportType.BLOOD_LIPID
        elif any(kw in text_lower for kw in ["肝功能", "alt", "ast", "谷丙", "谷草"]):
            return ReportType.LIVER_FUNCTION
        elif any(kw in text_lower for kw in ["肾功能", "肌酐", "尿素", "cre", "urea", "egfr"]):
            return ReportType.KIDNEY_FUNCTION
        elif any(kw in text_lower for kw in ["血糖", "空腹血糖", "糖化", "glu", "hba1c"]):
            return ReportType.BLOOD_SUGAR
        elif any(kw in text_lower for kw in ["甲状腺", "tsh", "ft3", "ft4"]):
            return ReportType.THYROID
        elif any(kw in text_lower for kw in ["ct", "计算机断层"]):
            return ReportType.IMAGE_CT
        elif any(kw in text_lower for kw in ["mri", "核磁共振", "磁共振"]):
            return ReportType.IMAGE_MRI
        elif any(kw in text_lower for kw in ["b超", "彩超", "超声", "ultrasound"]):
            return ReportType.IMAGE_ULTRASOUND
        elif any(kw in text_lower for kw in ["x光", "x-ray", "xray"]):
            return ReportType.IMAGE_XRAY
        elif any(kw in text_lower for kw in ["心电图", "ecg", "ekg"]):
            return ReportType.ECG
        else:
            return ReportType.UNKNOWN

    def _parse_indicators(
        self,
        text: str,
        report_type: ReportType
    ) -> List[IndicatorResult]:
        """解析指标数据"""
        indicators = []

        # 获取对应的参考范围
        ranges = self.all_ranges.get(report_type, {})

        # 解析每个指标
        for code, info in ranges.items():
            # 尝试多种匹配模式
            patterns = [
                rf"{info['name']}\s*[：:]\s*([\d.]+)\s*{info['unit']}",
                rf"{code}\s*[：:]\s*([\d.]+)\s*{info['unit']}",
                rf"{code}\s+([\d.]+)",
                rf"{info['name']}\s+([\d.]+)",
            ]

            value = None
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    break

            if value is None:
                continue

            # 判断是否异常
            is_abnormal, abnormal_type = self._check_abnormal(
                code, value, info, text
            )

            # 获取临床意义和建议
            clinical_significance = self._get_clinical_significance(
                code, is_abnormal, abnormal_type
            )
            suggestions = self._get_indicator_suggestions(
                code, is_abnormal, abnormal_type
            )

            indicators.append(IndicatorResult(
                name=info['name'],
                value=value,
                unit=info['unit'],
                reference_range=info['ref'],
                is_abnormal=is_abnormal,
                abnormal_type=abnormal_type,
                clinical_significance=clinical_significance,
                suggestions=suggestions
            ))

        return indicators

    def _check_abnormal(
        self,
        code: str,
        value: str,
        info: Dict,
        text: str
    ) -> Tuple[bool, str]:
        """检查指标是否异常"""
        try:
            num_value = float(value)
        except ValueError:
            # 无法转换为数字，检查阴阳性
            if "positive" in info:
                is_positive = any(
                    kw in text for kw in ["阳性", "+", "Positive", "POS"]
                )
                return is_positive, "positive" if is_positive else "negative"
            return False, ""

        # 检查高低范围
        if info.get("high"):
            high_threshold = self._parse_threshold(info["high"], num_value)
            if num_value > high_threshold:
                return True, "high"

        if info.get("low"):
            low_threshold = self._parse_threshold(info["low"], num_value)
            if num_value < low_threshold:
                return True, "low"

        return False, ""

    def _parse_threshold(self, threshold: str, value: float) -> float:
        """解析阈值"""
        if threshold.startswith(">="):
            return float(threshold[2:])
        elif threshold.startswith(">"):
            return float(threshold[1:])
        elif threshold.startswith("<="):
            return float(threshold[2:])
        elif threshold.startswith("<"):
            return float(threshold[1:])
        else:
            return float(threshold)

    def _get_clinical_significance(
        self,
        code: str,
        is_abnormal: bool,
        abnormal_type: str
    ) -> str:
        """获取临床意义"""
        if not is_abnormal:
            return "指标在正常范围内"

        significance_map = {
            "WBC_high": "白细胞升高可能提示细菌感染、炎症或应激反应",
            "WBC_low": "白细胞降低可能提示病毒感染、免疫力低下或骨髓抑制",
            "HGB_low": "血红蛋白降低提示贫血，需进一步检查贫血类型",
            "PLT_low": "血小板降低可能影响凝血功能，需关注出血倾向",
            "ALT_high": "转氨酶升高提示肝细胞损伤，可能由肝炎、药物、脂肪肝等引起",
            "AST_high": "AST升高可见于肝病、心肌损伤等",
            "TC_high": "总胆固醇升高是心血管疾病危险因素",
            "TG_high": "甘油三酯升高与代谢综合征相关",
            "LDL-C_high": "低密度脂蛋白升高是动脉粥样硬化的主要危险因素",
            "GLU_high": "血糖升高需警惕糖尿病，建议复查空腹血糖和糖化血红蛋白",
            "CRE_high": "肌酐升高提示肾功能减退",
            "UA_high": "尿酸升高可能引起痛风，需控制饮食",
            "TSH_high": "TSH升高提示甲状腺功能减退",
            "TSH_low": "TSH降低提示甲状腺功能亢进",
        }

        key = f"{code}_{abnormal_type}"
        return significance_map.get(key, "指标异常，建议结合临床综合判断")

    def _get_indicator_suggestions(
        self,
        code: str,
        is_abnormal: bool,
        abnormal_type: str
    ) -> List[str]:
        """获取指标建议"""
        if not is_abnormal:
            return ["继续保持健康生活方式"]

        suggestions_map = {
            "WBC_high": ["多喝水，注意休息", "避免过度劳累", "如有发热及时就医"],
            "WBC_low": ["避免感染", "均衡营养，增强免疫", "定期复查"],
            "HGB_low": ["补充富含铁的食物", "查明贫血原因", "遵医嘱治疗"],
            "PLT_low": ["避免剧烈运动", "注意观察有无出血", "及时就医"],
            "ALT_high": ["戒酒", "控制体重", "避免肝毒性药物", "进一步检查肝脏B超"],
            "AST_high": ["检查肝脏和心脏功能", "避免熬夜饮酒"],
            "TC_high": ["低脂饮食", "增加运动", "必要时服用降脂药"],
            "TG_high": ["控制糖分摄入", "减少酒精", "增加有氧运动"],
            "LDL-C_high": ["严格低脂饮食", "规律运动", "遵医嘱用药"],
            "GLU_high": ["控制碳水化合物摄入", "监测血糖", "做糖耐量试验"],
            "CRE_high": ["低蛋白饮食", "避免肾毒性药物", "肾内科进一步检查"],
            "UA_high": ["低嘌呤饮食", "禁酒", "多喝水"],
            "TSH_high": ["补充甲状腺激素", "定期复查甲功"],
            "TSH_low": ["抗甲状腺治疗", "心内科随访"],
        }

        key = f"{code}_{abnormal_type}"
        return suggestions_map.get(key, ["建议咨询专科医生"])

    def _generate_summary(
        self,
        report_type: ReportType,
        abnormal_indicators: List[IndicatorResult]
    ) -> str:
        """生成报告摘要"""
        if not abnormal_indicators:
            return f"{report_type.value}报告未见明显异常，各项指标均在正常范围内。"

        abnormal_names = [ind.name for ind in abnormal_indicators]
        return f"{report_type.value}报告发现{len(abnormal_indicators)}项指标异常：{', '.join(abnormal_names)}"

    def _generate_overall_assessment(
        self,
        report_type: ReportType,
        abnormal_indicators: List[IndicatorResult]
    ) -> str:
        """生成综合评估"""
        if not abnormal_indicators:
            return "您的检查结果基本正常，建议继续保持健康的生活方式，定期体检。"

        severity_map = {
            "high": "升高",
            "low": "降低",
            "positive": "阳性",
            "negative": "阴性"
        }

        assessment_lines = ["您的检查结果存在以下情况："]
        for ind in abnormal_indicators:
            abnormal_desc = severity_map.get(ind.abnormal_type, "异常")
            assessment_lines.append(
                f"- {ind.name}{abnormal_desc}：{ind.clinical_significance}"
            )

        return "\n".join(assessment_lines)

    def _generate_recommendations(
        self,
        report_type: ReportType,
        abnormal_indicators: List[IndicatorResult]
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        # 收集所有异常指标的建议
        all_suggestions = set()
        for ind in abnormal_indicators:
            all_suggestions.update(ind.suggestions)

        recommendations.extend(list(all_suggestions))

        # 添加通用建议
        if abnormal_indicators:
            recommendations.extend([
                "建议1-2周后复查异常指标",
                "注意休息，避免过度劳累",
                "如有疑问，请咨询相关专科医生"
            ])

        return recommendations

    def _generate_follow_up(
        self,
        report_type: ReportType,
        abnormal_indicators: List[IndicatorResult]
    ) -> Tuple[bool, str]:
        """生成随访建议"""
        if not abnormal_indicators:
            return False, ""

        # 根据异常指标数量和程度决定是否需要随访
        critical_indicators = ["ALT", "AST", "GLU", "CRE", "TSH"]

        for ind in abnormal_indicators:
            if any(code in ind.name for code in critical_indicators):
                return True, "建议1-2周后复查相关指标，必要时专科就诊"

        return True, "建议3-6个月后复查，关注异常指标变化"

    def format_result(self, result: ReportInterpretationResult) -> str:
        """
        格式化解读结果为可读文本

        Args:
            result: 解读结果

        Returns:
            str: 格式化的报告
        """
        report = f"# 📋 检查报告解读\n\n"
        report += f"**报告类型**: {result.report_type.value}\n\n"
        report += f"**报告摘要**: {result.summary}\n\n"

        # 异常指标
        if result.abnormal_indicators:
            report += "## ⚠️ 异常指标\n\n"
            for ind in result.abnormal_indicators:
                abnormal_symbol = "↑" if ind.abnormal_type == "high" else ("↓" if ind.abnormal_type == "low" else "+")
                report += f"### {ind.name} {abnormal_symbol}\n\n"
                report += f"- **检测值**: {ind.value} {ind.unit}\n"
                report += f"- **参考范围**: {ind.reference_range}\n"
                report += f"- **临床意义**: {ind.clinical_significance}\n"

                if ind.suggestions:
                    report += f"- **建议**: {', '.join(ind.suggestions)}\n"
                report += "\n"
        else:
            report += "## ✅ 各项指标正常\n\n"
            report += "您的各项指标均在正常范围内，请继续保持健康的生活方式。\n\n"

        # 综合评估
        report += "## 📊 综合评估\n\n"
        report += result.overall_assessment + "\n\n"

        # 建议
        if result.recommendations:
            report += "## 💡 建议\n\n"
            for rec in result.recommendations:
                report += f"- {rec}\n"
            report += "\n"

        # 随访建议
        if result.need_follow_up:
            report += "## 📅 随访建议\n\n"
            report += result.follow_up_suggestions + "\n\n"

        # 免责声明
        report += "---\n\n"
        report += "> ⚠️ **免责声明**: 以上解读仅供参考，不能替代专业医生的诊断。如有疑问，请及时咨询相关专科医生。"

        return report


# 便捷函数
async def interpret_report(
    report_text: str,
    report_type: Optional[str] = None,
    mcp_client=None
) -> str:
    """
    解读检查报告（便捷函数）

    Args:
        report_text: 报告文本
        report_type: 报告类型
        mcp_client: MCP客户端

    Returns:
        str: 格式化的解读结果
    """
    skill = ReportInterpreterSkill(mcp_client)
    result = await skill.interpret(report_text, report_type)
    return skill.format_result(result)


if __name__ == "__main__":
    # 测试用例
    async def test():
        test_report = """
        血常规检查报告
        WBC: 12.5 10^9/L
        RBC: 4.5 10^12/L
        HGB: 135 g/L
        HCT: 40%
        PLT: 250 10^9/L
        NEUT%: 75%
        LYMPH%: 18%
        """

        skill = ReportInterpreterSkill()
        result = await skill.interpret(test_report, "blood")
        print(skill.format_result(result))

    import asyncio
    asyncio.run(test())
