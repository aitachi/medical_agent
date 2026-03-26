# -*- coding: utf-8 -*-
"""
慢病记录Skill
记录和管理慢病监测数据（血压、血糖等），提供趋势分析和异常告警
"""

import re
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from statistics import mean, median


logger = logging.getLogger(__name__)


class DiseaseType(Enum):
    """疾病类型"""
    HYPERTENSION = "hypertension"    # 高血压
    DIABETES = "diabetes"            # 糖尿病
    HYPERLIPIDEMIA = "hyperlipidemia"# 高血脂
    CORONARY = "coronary"            # 冠心病
    COPD = "copd"                    # 慢阻肺
    GOUT = "gout"                    # 痛风


class IndicatorStatus(Enum):
    """指标状态"""
    NORMAL = "normal"        # 正常
    ELEVATED = "elevated"    # 偏高/偏低
    HIGH = "high"            # 高/严重偏高
    CRITICAL = "critical"    # 危急


@dataclass
class ChronicRecord:
    """慢病记录"""
    record_id: str
    user_id: str
    disease_type: DiseaseType
    measure_data: Dict[str, float]
    measure_time: str
    note: Optional[str] = None
    status: IndicatorStatus = IndicatorStatus.NORMAL
    trend: str = "stable"  # rising, falling, stable


@dataclass
class TrendAnalysis:
    """趋势分析"""
    trend: str              # rising, falling, stable
    change_rate: float      # 变化率
    avg_value: float        # 平均值
    min_value: float        # 最小值
    max_value: float        # 最大值
    data_points: int        # 数据点数


@dataclass
class ChronicRecordResult:
    """慢病记录结果"""
    success: bool
    record_id: Optional[str] = None
    analysis: Optional[Dict] = None
    trend: Optional[str] = None
    alert: Optional[str] = None
    advice: List[str] = field(default_factory=list)
    chart_data: Optional[Dict] = None
    error: Optional[str] = None


class ChronicRecorderSkill:
    """
    慢病记录Skill
    记录慢病监测数据，分析趋势，异常告警，提供健康建议
    """

    # 参考范围配置
    REFERENCE_RANGES = {
        DiseaseType.HYPERTENSION: {
            "systolic": {"normal": (90, 140), "elevated": (140, 160), "high": (160, 180), "critical": (180, 300), "unit": "mmHg"},
            "diastolic": {"normal": (60, 90), "elevated": (90, 100), "high": (100, 110), "critical": (110, 150), "unit": "mmHg"},
            "heart_rate": {"normal": (60, 100), "elevated": (100, 120), "high": (120, 150), "critical": (150, 200), "unit": "bpm"},
        },
        DiseaseType.DIABETES: {
            "fasting_glucose": {"normal": (3.9, 6.1), "elevated": (6.1, 7.0), "high": (7.0, 11.1), "critical": (11.1, 30), "unit": "mmol/L"},
            "postprandial_glucose": {"normal": (4.4, 7.8), "elevated": (7.8, 11.1), "high": (11.1, 16.7), "critical": (16.7, 30), "unit": "mmol/L"},
            "hba1c": {"normal": (4.0, 6.0), "elevated": (6.0, 7.0), "high": (7.0, 9.0), "critical": (9.0, 15), "unit": "%"},
        },
        DiseaseType.HYPERLIPIDEMIA: {
            "total_cholesterol": {"normal": (0, 5.2), "elevated": (5.2, 6.2), "high": (6.2, 7.8), "critical": (7.8, 15), "unit": "mmol/L"},
            "triglycerides": {"normal": (0, 1.7), "elevated": (1.7, 2.3), "high": (2.3, 5.6), "critical": (5.6, 15), "unit": "mmol/L"},
            "ldl": {"normal": (0, 3.4), "elevated": (3.4, 4.1), "high": (4.1, 4.9), "critical": (4.9, 10), "unit": "mmol/L"},
        },
        DiseaseType.GOUT: {
            "uric_acid": {"normal": (150, 420), "elevated": (420, 500), "high": (500, 600), "critical": (600, 1000), "unit": "μmol/L"},
        },
    }

    # 健康建议库
    ADVICE_LIBRARY = {
        DiseaseType.HYPERTENSION: {
            "normal": ["血压控制良好，继续保持", "规律服药，定期监测", "保持健康生活方式"],
            "elevated": ["血压偏高，注意休息", "低盐饮食", "按时服药", "减少压力"],
            "high": ["血压偏高，建议就医", "及时测量血压", "联系医生调整用药", "避免剧烈活动"],
            "critical": ["血压过高，请立即就医", "立即服用降压药", "保持卧床休息", "必要时拨打120"]
        },
        DiseaseType.DIABETES: {
            "normal": ["血糖控制良好", "继续控制饮食", "规律运动", "定期监测"],
            "elevated": ["血糖偏高，注意饮食", "减少碳水化合物", "适当运动", "监测血糖变化"],
            "high": ["血糖偏高，建议就医", "检查用药情况", "控制饮食", "增加运动"],
            "critical": ["血糖过高，请立即就医", "不要进食", "多喝水", "立即联系医生"]
        },
        DiseaseType.HYPERLIPIDEMIA: {
            "normal": ["血脂正常，继续保持", "健康饮食", "适量运动"],
            "elevated": ["血脂偏高，注意饮食", "低脂饮食", "增加运动", "减少油腻食物"],
            "high": ["血脂偏高，建议就医", "严格低脂饮食", "规律运动", "考虑降脂治疗"],
            "critical": ["血脂过高，请立即就医", "遵医嘱治疗", "控制饮食", "定期复查"]
        },
        DiseaseType.GOUT: {
            "normal": ["尿酸正常，继续保持", "多喝水", "低嘌呤饮食"],
            "elevated": ["尿酸偏高，注意饮食", "低嘌呤饮食", "禁酒", "多喝水"],
            "high": ["尿酸偏高，建议就医", "严格低嘌呤饮食", "禁酒", "多喝水", "药物治疗"],
            "critical": ["尿酸过高，请立即就医", "立即就医", "大量饮水", "卧床休息"]
        }
    }

    def __init__(self, mcp_client=None):
        """
        初始化慢病记录Skill

        Args:
            mcp_client: MCP客户端，用于调用外部慢病管理系统
        """
        self.mcp_client = mcp_client
        self._records: Dict[str, List[ChronicRecord]] = {}

    async def record(
        self,
        user_id: str,
        disease_type: str,
        measure_data: Dict[str, float],
        measure_time: Optional[str] = None,
        note: Optional[str] = None
    ) -> ChronicRecordResult:
        """
        记录慢病数据

        Args:
            user_id: 用户ID
            disease_type: 疾病类型
            measure_data: 测量数据
            measure_time: 测量时间
            note: 备注

        Returns:
            ChronicRecordResult: 记录结果
        """
        try:
            # 1. 转换疾病类型
            disease_enum = DiseaseType(disease_type)

            # 2. 分析数据
            analysis = self._analyze_measure_data(disease_enum, measure_data)

            # 3. 判断趋势
            trend = self._get_trend(user_id, disease_enum, measure_data)

            # 4. 生成告警
            alert = self._generate_alert(disease_enum, analysis)

            # 5. 生成建议
            advice = self._generate_advice(disease_enum, analysis)

            # 6. 保存记录
            record_id = f"{disease_type.upper()}{datetime.now().strftime('%Y%m%d%H%M%S')}"
            if measure_time is None:
                measure_time = datetime.now().isoformat()

            record = ChronicRecord(
                record_id=record_id,
                user_id=user_id,
                disease_type=disease_enum,
                measure_data=measure_data,
                measure_time=measure_time,
                note=note,
                status=analysis.get("overall_status", IndicatorStatus.NORMAL),
                trend=trend
            )

            # 保存到本地存储
            if user_id not in self._records:
                self._records[user_id] = []
            self._records[user_id].append(record)

            return ChronicRecordResult(
                success=True,
                record_id=record_id,
                analysis=analysis,
                trend=trend,
                alert=alert,
                advice=advice,
                chart_data=self._generate_chart_data(user_id, disease_enum)
            )

        except ValueError as e:
            return ChronicRecordResult(
                success=False,
                error=f"无效的疾病类型: {disease_type}"
            )
        except Exception as e:
            logger.error(f"记录慢病数据失败: {e}")
            return ChronicRecordResult(
                success=False,
                error=str(e)
            )

    def _analyze_measure_data(
        self,
        disease_type: DiseaseType,
        measure_data: Dict[str, float]
    ) -> Dict:
        """分析测量数据"""
        ranges = self.REFERENCE_RANGES.get(disease_type, {})
        analysis = {}
        overall_status = IndicatorStatus.NORMAL

        for indicator, value in measure_data.items():
            if indicator not in ranges:
                continue

            indicator_range = ranges[indicator]
            status = self._get_indicator_status(value, indicator_range)

            analysis[indicator] = {
                "value": value,
                "unit": indicator_range["unit"],
                "status": status,
                "range": indicator_range["normal"]
            }

            # 更新整体状态（取最严重的）
            status_priority = {
                IndicatorStatus.CRITICAL: 4,
                IndicatorStatus.HIGH: 3,
                IndicatorStatus.ELEVATED: 2,
                IndicatorStatus.NORMAL: 1
            }
            if status_priority.get(status, 0) > status_priority.get(overall_status, 0):
                overall_status = status

        analysis["overall_status"] = overall_status
        return analysis

    def _get_indicator_status(
        self,
        value: float,
        range_info: Dict
    ) -> IndicatorStatus:
        """获取指标状态"""
        if range_info["normal"][0] <= value <= range_info["normal"][1]:
            return IndicatorStatus.NORMAL
        elif range_info.get("elevated") and range_info["elevated"][0] <= value <= range_info["elevated"][1]:
            return IndicatorStatus.ELEVATED
        elif range_info.get("high") and range_info["high"][0] <= value <= range_info["high"][1]:
            return IndicatorStatus.HIGH
        else:
            return IndicatorStatus.CRITICAL

    def _get_trend(
        self,
        user_id: str,
        disease_type: DiseaseType,
        current_data: Dict[str, float]
    ) -> str:
        """获取趋势"""
        user_records = self._records.get(user_id, [])
        disease_records = [
            r for r in user_records
            if r.disease_type == disease_type
            and r.measure_time > (datetime.now() - timedelta(days=7)).isoformat()
        ]

        if not disease_records:
            return "stable"

        # 取主要指标分析趋势
        primary_indicator = self._get_primary_indicator(disease_type)
        if primary_indicator not in current_data:
            return "stable"

        current_value = current_data[primary_indicator]
        recent_values = [
            r.measure_data.get(primary_indicator)
            for r in disease_records[-7:]
            if primary_indicator in r.measure_data
        ]

        if not recent_values:
            return "stable"

        avg_value = mean(recent_values)
        change_rate = (current_value - avg_value) / avg_value if avg_value > 0 else 0

        if change_rate > 0.05:
            return "rising"
        elif change_rate < -0.05:
            return "falling"
        else:
            return "stable"

    def _get_primary_indicator(self, disease_type: DiseaseType) -> str:
        """获取主要指标"""
        primary_map = {
            DiseaseType.HYPERTENSION: "systolic",
            DiseaseType.DIABETES: "fasting_glucose",
            DiseaseType.HYPERLIPIDEMIA: "total_cholesterol",
            DiseaseType.GOUT: "uric_acid",
        }
        return primary_map.get(disease_type, "")

    def _generate_alert(
        self,
        disease_type: DiseaseType,
        analysis: Dict
    ) -> Optional[str]:
        """生成告警"""
        status = analysis.get("overall_status", IndicatorStatus.NORMAL)

        if status == IndicatorStatus.NORMAL:
            return None

        alert_messages = {
            IndicatorStatus.ELEVATED: "⚠️ 指标偏高，请注意监测",
            IndicatorStatus.HIGH: "⚠️ 指标偏高，建议及时就医",
            IndicatorStatus.CRITICAL: "🚨 指标异常，请立即就医"
        }

        return alert_messages.get(status)

    def _generate_advice(
        self,
        disease_type: DiseaseType,
        analysis: Dict
    ) -> List[str]:
        """生成建议"""
        status = analysis.get("overall_status", IndicatorStatus.NORMAL)
        advice_set = self.ADVICE_LIBRARY.get(disease_type, {}).get(status.value, [])

        return advice_set.copy() if advice_set else []

    def _generate_chart_data(
        self,
        user_id: str,
        disease_type: DiseaseType
    ) -> Optional[Dict]:
        """生成图表数据"""
        user_records = self._records.get(user_id, [])
        disease_records = [
            r for r in user_records
            if r.disease_type == disease_type
        ][:30]  # 最近30条

        if not disease_records:
            return None

        primary_indicator = self._get_primary_indicator(disease_type)
        data = []
        for record in reversed(disease_records):
            if primary_indicator in record.measure_data:
                data.append({
                    "time": record.measure_time,
                    "value": record.measure_data[primary_indicator]
                })

        return {"data": data, "indicator": primary_indicator}

    async def get_history(
        self,
        user_id: str,
        disease_type: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """
        获取历史记录

        Args:
            user_id: 用户ID
            disease_type: 疾病类型（可选）
            days: 查询天数

        Returns:
            Dict: 历史记录
        """
        user_records = self._records.get(user_id, [])

        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()

        filtered_records = [
            r for r in user_records
            if r.measure_time >= cutoff_time
            and (disease_type is None or r.disease_type.value == disease_type)
        ]

        # 按疾病类型分组
        grouped = {}
        for record in filtered_records:
            dt = record.disease_type.value
            if dt not in grouped:
                grouped[dt] = []
            grouped[dt].append({
                "record_id": record.record_id,
                "measure_time": record.measure_time,
                "data": record.measure_data,
                "status": record.status.value,
                "note": record.note
            })

        # 计算统计信息
        stats = {}
        for dt, records in grouped.items():
            if records:
                stats[dt] = self._calculate_stats(records, DiseaseType(dt))

        return {
            "records": grouped,
            "statistics": stats,
            "total_count": len(filtered_records)
        }

    def _calculate_stats(
        self,
        records: List[Dict],
        disease_type: DiseaseType
    ) -> Dict:
        """计算统计信息"""
        ranges = self.REFERENCE_RANGES.get(disease_type, {})
        stats = {}

        for indicator in ranges.keys():
            values = [
                r["data"].get(indicator)
                for r in records
                if indicator in r["data"]
            ]
            values = [v for v in values if v is not None]

            if values:
                stats[indicator] = {
                    "avg": round(mean(values), 2),
                    "min": round(min(values), 2),
                    "max": round(max(values), 2),
                    "count": len(values),
                    "latest": values[-1] if values else None
                }

        return stats

    def format_record_result(self, result: ChronicRecordResult, disease_type: str) -> str:
        """格式化记录结果"""
        if not result.success:
            return f"❌ 记录失败: {result.error}"

        response = f"## ✅ 记录成功\n\n"
        response += f"**记录编号**: {result.record_id}\n"

        # 分析结果
        if result.analysis:
            response += "\n### 📊 测量分析\n\n"

            for indicator, info in result.analysis.items():
                if indicator == "overall_status":
                    continue

                status_emoji = {
                    "normal": "✅",
                    "elevated": "⚠️",
                    "high": "⚠️",
                    "critical": "🔴"
                }

                status = info.get("status", "normal")
                emoji = status_emoji.get(status, "")

                response += f"**{indicator}**: {info['value']} {info['unit']} {emoji}\n"
                response += f"- 参考范围: {info['range'][0]}-{info['range'][1]}\n"
                response += f"- 状态: {status}\n\n"

        # 趋势
        if result.trend:
            trend_emoji = {
                "rising": "📈",
                "falling": "📉",
                "stable": "➡️"
            }
            response += f"### 📈 趋势\n\n"
            response += f"近期趋势: {trend_emoji.get(result.trend, '')} {result.trend}\n\n"

        # 告警
        if result.alert:
            response += f"### {result.alert}\n\n"

        # 建议
        if result.advice:
            response += "### 💡 建议\n\n"
            for advice in result.advice:
                response += f"- {advice}\n"
            response += "\n"

        response += "---\n\n"
        response += "> 💡 继续保持监测，定期记录有助于控制病情。"

        return response

    def parse_natural_input(self, text: str) -> Optional[Dict]:
        """
        解析自然语言输入

        支持格式：
        - "血压 120/80"
        - "血糖 6.5"
        - "空腹血糖 7.0"
        - "收缩压140 舒张压90 心率75"
        """
        result = {}

        # 血压模式
        blood_pressure_patterns = [
            r'血压\s*(\d+)\s*/\s*(\d+)',
            r'(\d+)\s*/\s*(\d+)\s*mm?Hg?',
            r'收缩压\s*(\d+).*?舒张压\s*(\d+)',
        ]
        for pattern in blood_pressure_patterns:
            match = re.search(pattern, text)
            if match:
                result["disease_type"] = "hypertension"
                result["measure_data"] = {
                    "systolic": float(match.group(1)),
                    "diastolic": float(match.group(2))
                }

                # 检查是否包含心率
                hr_match = re.search(r'心率\s*(\d+)', text)
                if hr_match:
                    result["measure_data"]["heart_rate"] = float(hr_match.group(1))

                return result

        # 血糖模式
        glucose_patterns = [
            r'(空腹|餐后)?\s*血糖\s*(\d+\.?\d*)',
            r'glucose\s*(\d+\.?\d*)',
        ]
        for pattern in glucose_patterns:
            match = re.search(pattern, text)
            if match:
                is_fasting = match.group(1) == "空腹"
                result["disease_type"] = "diabetes"
                if is_fasting:
                    result["measure_data"] = {"fasting_glucose": float(match.group(2))}
                else:
                    result["measure_data"] = {"postprandial_glucose": float(match.group(2))}
                return result

        # 尿酸模式
        uric_match = re.search(r'尿酸\s*(\d+)', text)
        if uric_match:
            result["disease_type"] = "gout"
            result["measure_data"] = {"uric_acid": float(uric_match.group(1))}
            return result

        return None


# 便捷函数
async def record_chronic_data(
    user_id: str,
    disease_type: str,
    measure_data: Dict[str, float],
    mcp_client=None
) -> str:
    """
    记录慢病数据（便捷函数）

    Args:
        user_id: 用户ID
        disease_type: 疾病类型
        measure_data: 测量数据
        mcp_client: MCP客户端

    Returns:
        str: 格式化的记录结果
    """
    skill = ChronicRecorderSkill(mcp_client)
    result = await skill.record(user_id, disease_type, measure_data)
    return skill.format_record_result(result, disease_type)


if __name__ == "__main__":
    # 测试用例
    async def test():
        skill = ChronicRecorderSkill()

        # 测试血压记录
        result = await skill.record(
            user_id="test_user",
            disease_type="hypertension",
            measure_data={"systolic": 145, "diastolic": 95, "heart_rate": 82},
            note="早上测量"
        )
        print(skill.format_record_result(result, "hypertension"))

        # 测试自然语言解析
        print("\n--- 测试自然语言解析 ---")
        test_inputs = [
            "血压 120/80",
            "血压140/90心率85",
            "空腹血糖 6.5",
            "餐后血糖8.0",
            "尿酸450"
        ]
        for text in test_inputs:
            parsed = skill.parse_natural_input(text)
            print(f"{text} -> {parsed}")

    import asyncio
    asyncio.run(test())
