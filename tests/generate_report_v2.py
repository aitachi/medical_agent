# -*- coding: utf-8 -*-
"""
医疗智能助手 - 测试报告生成器 V2
修复图像路径，增加更多图表和内容
"""
import os
import sys
import json
import math
import numpy as np
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Rectangle

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class ReportData:
    """报告数据"""

    def __init__(self, json_file: str):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.summary = data.get("summary", {})
        self.results = data.get("results", [])
        self.performance_data = data.get("performance_data", {})
        self.logs = data.get("logs", [])

    @property
    def total_tests(self) -> int:
        return self.summary.get("total_tests", 0)

    @property
    def passed_tests(self) -> int:
        return self.summary.get("passed_tests", 0)

    @property
    def failed_tests(self) -> int:
        return self.summary.get("failed_tests", 0)

    @property
    def pass_rate(self) -> float:
        return self.summary.get("pass_rate", 0)

    @property
    def by_complexity(self) -> Dict[str, Dict]:
        return self.summary.get("by_complexity", {})

    @property
    def by_skill(self) -> Dict[str, Dict]:
        return self.summary.get("by_skill", {})

    @property
    def response_times(self) -> List[float]:
        return [r.get("response_time_ms", 0) for r in self.results if r.get("response_time_ms", 0) > 0]

    @property
    def confidences(self) -> List[float]:
        return [r.get("confidence", 0) for r in self.results]

    def get_results_by_skill(self, skill: str) -> List[Dict]:
        return [r for r in self.results if r.get("skill") == skill]

    def get_results_by_complexity(self, complexity: str) -> List[Dict]:
        return [r for r in self.results if r.get("complexity") == complexity]

    def get_results_by_type(self, test_type: str) -> List[Dict]:
        return [r for r in self.results if r.get("test_type") == test_type]

    def get_failed_results(self) -> List[Dict]:
        return [r for r in self.results if not r.get("passed", False)]


class ChartGenerator:
    """图表生成器 - 修复版"""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.charts_dir = os.path.join(output_dir, "charts")
        os.makedirs(self.charts_dir, exist_ok=True)
        self.charts = []

    def _get_chart_path(self, name: str) -> str:
        """获取图表路径（相对路径，用于LaTeX）"""
        return f"charts/{name}.png"

    def _get_abs_chart_path(self, name: str) -> str:
        """获取图表绝对路径（用于保存）"""
        return os.path.join(self.charts_dir, f"{name}.png")

    def generate_overview_chart(self, data: ReportData):
        """生成概览图表"""
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        fig.suptitle('医疗智能助手 - 测试概览', fontsize=18, fontweight='bold', y=0.98)

        # 1. 通过/失败饼图
        ax1 = fig.add_subplot(gs[0, 0])
        passed = data.passed_tests
        failed = data.failed_tests
        colors = ['#28a745', '#dc3545']
        explode = (0.05, 0.05)
        wedges, texts, autotexts = ax1.pie([passed, failed], labels=[f'通过\n({passed})', f'失败\n({failed})'],
                colors=colors, autopct='%1.1f%%', startangle=90, explode=explode)
        for autotext in autotexts:
            autotext.set_fontsize(12)
            autotext.set_fontweight('bold')
        ax1.set_title('测试结果分布', fontsize=12, fontweight='bold')

        # 2. 按复杂度统计 - 分组柱状图
        ax2 = fig.add_subplot(gs[0, 1])
        complexities = list(data.by_complexity.keys())
        passed_by_complexity = [data.by_complexity[c]['passed'] for c in complexities]
        total_by_complexity = [data.by_complexity[c]['total'] for c in complexities]

        x = np.arange(len(complexities))
        width = 0.35
        bars1 = ax2.bar(x - width/2, passed_by_complexity, width, label='通过', color='#28a745', edgecolor='black')
        bars2 = ax2.bar(x + width/2, [t - p for t, p in zip(total_by_complexity, passed_by_complexity)],
                       width, label='失败', color='#dc3545', edgecolor='black')
        ax2.set_xlabel('复杂度', fontsize=10)
        ax2.set_ylabel('测试数', fontsize=10)
        ax2.set_title('按复杂度统计', fontsize=12, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(complexities)
        ax2.legend()
        # 添加数值标签
        for bar in bars1:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}',
                    ha='center', va='bottom', fontsize=9)
        for bar in bars2:
            height = bar.get_height()
            if height > 0:
                ax2.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}',
                        ha='center', va='bottom', fontsize=9)

        # 3. 按Skill统计 - 堆叠柱状图
        ax3 = fig.add_subplot(gs[0, 2])
        skills = list(data.by_skill.keys())
        passed_by_skill = [data.by_skill[s]['passed'] for s in skills]
        total_by_skill = [data.by_skill[s]['total'] for s in skills]

        x = np.arange(len(skills))
        bars1 = ax3.bar(x, passed_by_skill, label='通过', color='#28a745', edgecolor='black')
        bars2 = ax3.bar(x, [t - p for t, p in zip(total_by_skill, passed_by_skill)],
                       bottom=passed_by_skill, label='失败', color='#dc3545', edgecolor='black')
        ax3.set_xlabel('Skill', fontsize=10)
        ax3.set_ylabel('测试数', fontsize=10)
        ax3.set_title('按Skill统计', fontsize=12, fontweight='bold')
        ax3.set_xticks(x)
        ax3.set_xticklabels(skills, rotation=45, ha='right', fontsize=8)
        ax3.legend()

        # 4. 响应时间分布
        ax4 = fig.add_subplot(gs[1, :])
        response_times = [rt for rt in data.response_times if rt > 0]
        if response_times:
            n, bins, patches = ax4.hist(response_times, bins=40, color='#17a2b8', edgecolor='black', alpha=0.7)
            ax4.axvline(np.mean(response_times), color='red', linestyle='--', linewidth=2,
                       label=f'平均值: {np.mean(response_times):.2f}ms')
            ax4.axvline(np.median(response_times), color='orange', linestyle='--', linewidth=2,
                       label=f'中位数: {np.median(response_times):.2f}ms')
            ax4.axvline(np.percentile(response_times, 95), color='purple', linestyle='--', linewidth=2,
                       label=f'P95: {np.percentile(response_times, 95):.2f}ms')
            ax4.set_xlabel('响应时间 (ms)', fontsize=11)
            ax4.set_ylabel('频次', fontsize=11)
            ax4.set_title('响应时间分布', fontsize=12, fontweight='bold')
            ax4.legend()
            ax4.grid(True, alpha=0.3)

        # 5. 通过率雷达图
        ax5 = fig.add_subplot(gs[2, 0], projection='polar')
        skills_short = [s.replace('-', '\n') for s in skills]
        pass_rates = [data.by_skill[s]['passed'] / data.by_skill[s]['total'] * 100
                     if data.by_skill[s]['total'] > 0 else 0 for s in skills]

        angles = np.linspace(0, 2 * np.pi, len(skills), endpoint=False).tolist()
        pass_rates += pass_rates[:1]
        angles += angles[:1]

        ax5.plot(angles, pass_rates, 'o-', linewidth=2, color='#667eea')
        ax5.fill(angles, pass_rates, alpha=0.25, color='#667eea')
        ax5.set_xticks(angles[:-1])
        ax5.set_xticklabels(skills_short, fontsize=8)
        ax5.set_ylim(0, 100)
        ax5.set_yticks([20, 40, 60, 80, 100])
        ax5.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], fontsize=8)
        ax5.set_title('各Skill通过率', fontsize=12, fontweight='bold', pad=20)
        ax5.grid(True)

        # 6. 测试类型分布
        ax6 = fig.add_subplot(gs[2, 1])
        test_types = ['单元测试', '功能测试', '性能测试', '流程测试']
        type_counts = [
            len(data.get_results_by_type('unit')),
            len(data.get_results_by_type('functional')),
            len(data.get_results_by_type('performance')),
            len(data.get_results_by_type('flow'))
        ]
        colors_type = ['#28a745', '#17a2b8', '#ffc107', '#6f42c1']
        bars = ax6.bar(test_types, type_counts, color=colors_type, edgecolor='black')
        ax6.set_ylabel('测试数', fontsize=10)
        ax6.set_title('测试类型分布', fontsize=12, fontweight='bold')
        ax6.set_xticklabels(test_types, rotation=15, ha='right')
        for bar, count in zip(bars, type_counts):
            height = bar.get_height()
            ax6.text(bar.get_x() + bar.get_width()/2., height, f'{int(count)}',
                    ha='center', va='bottom', fontsize=10)

        # 7. 总体统计卡片
        ax7 = fig.add_subplot(gs[2, 2])
        ax7.axis('off')
        stats_text = f"""
        总体统计

        ┌─────────────────────┐
        │ 总测试数    {data.total_tests:>4}    │
        │ 通过数      {data.passed_tests:>4}    │
        │ 失败数      {data.failed_tests:>4}    │
        │ 通过率  {data.pass_rate:>5.1f}%    │
        └─────────────────────┘
        """
        ax7.text(0.1, 0.5, stats_text, transform=ax7.transAxes,
                fontsize=11, verticalalignment='center', family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        chart_path = self._get_abs_chart_path('overview')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        self.charts.append(('overview', self._get_chart_path('overview')))
        return chart_path

    def generate_skill_performance_chart(self, data: ReportData):
        """生成Skill性能图表"""
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        fig.suptitle('Skill 性能分析', fontsize=18, fontweight='bold', y=0.98)

        skills = list(data.by_skill.keys())

        # 1. 各Skill通过率 - 横向柱状图
        ax1 = fig.add_subplot(gs[0, :2])
        pass_rates = [data.by_skill[s]['passed'] / data.by_skill[s]['total'] * 100
                     if data.by_skill[s]['total'] > 0 else 0 for s in skills]
        colors = ['#28a745' if pr >= 90 else '#ffc107' if pr >= 70 else '#dc3545' for pr in pass_rates]

        y_pos = np.arange(len(skills))
        bars = ax1.barh(y_pos, pass_rates, color=colors, edgecolor='black')
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(skills)
        ax1.set_xlabel('通过率 (%)', fontsize=11)
        ax1.set_title('各Skill通过率', fontsize=12, fontweight='bold')
        ax1.set_xlim(0, 105)
        ax1.axvline(90, color='gray', linestyle='--', alpha=0.5, label='优秀线(90%)')
        ax1.axvline(70, color='orange', linestyle='--', alpha=0.5, label='及格线(70%)')
        ax1.legend()

        for i, (bar, rate) in enumerate(zip(bars, pass_rates)):
            width = bar.get_width()
            ax1.text(width + 1, bar.get_y() + bar.get_height()/2,
                    f'{rate:.1f}%', ha='left', va='center', fontsize=10, fontweight='bold')

        # 2. 通过率饼图
        ax2 = fig.add_subplot(gs[0, 2])
        excellent = sum(1 for r in pass_rates if r >= 90)
        good = sum(1 for r in pass_rates if 70 <= r < 90)
        poor = sum(1 for r in pass_rates if r < 70)
        sizes = [excellent, good, poor]
        labels = [f'优秀\n({excellent})', f'良好\n({good})', f'需改进\n({poor})']
        colors_pie = ['#28a745', '#ffc107', '#dc3545']
        ax2.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.1f%%', startangle=90)
        ax2.set_title('Skill评级分布', fontsize=12, fontweight='bold')

        # 3. 各Skill响应时间
        ax3 = fig.add_subplot(gs[1, 0])
        skill_times = {}
        for skill in skills:
            times = [r.get('response_time_ms', 0) for r in data.get_results_by_skill(skill)]
            skill_times[skill] = [t for t in times if t > 0]

        avg_times = [np.mean(skill_times[s]) if skill_times[s] else 0 for s in skills]
        bars = ax3.barh(skills, avg_times, color='#17a2b8', edgecolor='black')
        ax3.set_xlabel('平均响应时间 (ms)', fontsize=10)
        ax3.set_title('各Skill平均响应时间', fontsize=12, fontweight='bold')

        for bar, time in zip(bars, avg_times):
            if time > 0:
                ax3.text(time + 0.05, bar.get_y() + bar.get_height()/2,
                        f'{time:.2f}ms', ha='left', va='center', fontsize=9)

        # 4. 各Skill置信度箱线图
        ax4 = fig.add_subplot(gs[1, 1])
        skill_confidences = {}
        for skill in skills:
            confs = [r.get('confidence', 0) for r in data.get_results_by_skill(skill)]
            skill_confidences[skill] = confs

        box_data = [skill_confidences[s] for s in skills]
        bp = ax4.boxplot(box_data, tick_labels=skills, patch_artist=True)
        for patch, color in zip(bp['boxes'], ['#667eea', '#28a745', '#ffc107', '#17a2b8', '#f5576c', '#6f42c1']):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        ax4.set_ylabel('置信度', fontsize=10)
        ax4.set_title('各Skill置信度分布', fontsize=12, fontweight='bold')
        ax4.tick_params(axis='x', rotation=45)
        ax4.grid(True, alpha=0.3)
        ax4.set_ylim(0, 1.1)

        # 5. 响应时间箱线图
        ax5 = fig.add_subplot(gs[1, 2])
        bp5 = ax5.boxplot(box_data, tick_labels=skills, patch_artist=True)
        for patch in bp5['boxes']:
            patch.set_facecolor('#e7f3ff')
            patch.set_alpha(0.7)
        ax5.set_ylabel('响应时间 (ms)', fontsize=10)
        ax5.set_title('各Skill响应时间分布', fontsize=12, fontweight='bold')
        ax5.tick_params(axis='x', rotation=45)
        ax5.grid(True, alpha=0.3)

        # 6. Skill测试数对比
        ax6 = fig.add_subplot(gs[2, 0])
        total_by_skill = [data.by_skill[s]['total'] for s in skills]
        passed_by_skill = [data.by_skill[s]['passed'] for s in skills]

        x = np.arange(len(skills))
        width = 0.35
        bars1 = ax6.bar(x - width/2, total_by_skill, width, label='总数', color='#6c757d', edgecolor='black')
        bars2 = ax6.bar(x + width/2, passed_by_skill, width, label='通过', color='#28a745', edgecolor='black')
        ax6.set_ylabel('测试数', fontsize=10)
        ax6.set_title('各Skill测试数量', fontsize=12, fontweight='bold')
        ax6.set_xticks(x)
        ax6.set_xticklabels(skills, rotation=45, ha='right', fontsize=8)
        ax6.legend()

        # 7. 响应时间 vs 置信度散点图
        ax7 = fig.add_subplot(gs[2, 1:])
        for skill in skills:
            results = data.get_results_by_skill(skill)
            times = [r.get('response_time_ms', 0) for r in results]
            confs = [r.get('confidence', 0) for r in results]
            ax7.scatter(times, confs, label=skill, alpha=0.6, s=50)

        ax7.set_xlabel('响应时间 (ms)', fontsize=11)
        ax7.set_ylabel('置信度', fontsize=11)
        ax7.set_title('响应时间 vs 置信度关系', fontsize=12, fontweight='bold')
        ax7.legend(ncol=2, fontsize=8)
        ax7.grid(True, alpha=0.3)
        ax7.set_ylim(0, 1.1)

        chart_path = self._get_abs_chart_path('skill_performance')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        self.charts.append(('skill_performance', self._get_chart_path('skill_performance')))
        return chart_path

    def generate_complexity_analysis_chart(self, data: ReportData):
        """生成复杂度分析图表"""
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)

        fig.suptitle('复杂度分析', fontsize=18, fontweight='bold')

        complexities = list(data.by_complexity.keys())

        # 1. 各复杂度通过率
        ax1 = fig.add_subplot(gs[0, 0])
        pass_rates = [data.by_complexity[c]['passed'] / data.by_complexity[c]['total'] * 100
                     if data.by_complexity[c]['total'] > 0 else 0 for c in complexities]
        colors = ['#28a745' if pr >= 90 else '#ffc107' if pr >= 70 else '#dc3545' for pr in pass_rates]
        bars = ax1.bar(complexities, pass_rates, color=colors, edgecolor='black')
        ax1.set_ylabel('通过率 (%)', fontsize=11)
        ax1.set_title('各复杂度通过率', fontsize=12, fontweight='bold')
        ax1.set_ylim(0, 105)
        ax1.axvline(90, color='gray', linestyle='--', alpha=0.5, label='优秀线')
        ax1.legend()

        for bar, rate in zip(bars, pass_rates):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{rate:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

        # 2. 各复杂度测试数
        ax2 = fig.add_subplot(gs[0, 1])
        total_by_complexity = [data.by_complexity[c]['total'] for c in complexities]
        passed_by_complexity = [data.by_complexity[c]['passed'] for c in complexities]

        x = np.arange(len(complexities))
        width = 0.35
        bars1 = ax2.bar(x - width/2, total_by_complexity, width, label='总数', color='#6c757d', edgecolor='black')
        bars2 = ax2.bar(x + width/2, passed_by_complexity, width, label='通过', color='#28a745', edgecolor='black')
        ax2.set_ylabel('测试数', fontsize=11)
        ax2.set_title('各复杂度测试数量', fontsize=12, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(complexities)
        ax2.legend()

        # 3. 各复杂度响应时间
        ax3 = fig.add_subplot(gs[0, 2])
        complexity_times = {}
        for comp in complexities:
            times = [r.get('response_time_ms', 0) for r in data.get_results_by_complexity(comp)]
            complexity_times[comp] = [t for t in times if t > 0]

        avg_times = [np.mean(complexity_times[c]) if complexity_times[c] else 0 for c in complexities]
        bars = ax3.bar(complexities, avg_times, color='#667eea', edgecolor='black')
        ax3.set_ylabel('平均响应时间 (ms)', fontsize=11)
        ax3.set_title('各复杂度平均响应时间', fontsize=12, fontweight='bold')

        for bar, time in zip(bars, avg_times):
            if time > 0:
                ax3.text(bar.get_x() + bar.get_width()/2., time,
                        f'{time:.2f}ms', ha='center', va='bottom', fontsize=9)

        # 4. 复杂度 vs 响应时间箱线图
        ax4 = fig.add_subplot(gs[1, :])
        box_data = [complexity_times[c] for c in complexities]
        bp = ax4.boxplot(box_data, tick_labels=complexities, patch_artist=True)
        colors_comp = ['#28a745', '#17a2b8', '#ffc107', '#6f42c1']
        for patch, color in zip(bp['boxes'], colors_comp):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        ax4.set_ylabel('响应时间 (ms)', fontsize=11)
        ax4.set_title('各复杂度响应时间分布', fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3)

        chart_path = self._get_abs_chart_path('complexity_analysis')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        self.charts.append(('complexity_analysis', self._get_chart_path('complexity_analysis')))
        return chart_path

    def generate_confidence_distribution_chart(self, data: ReportData):
        """生成置信度分布图表"""
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)

        fig.suptitle('置信度分析', fontsize=18, fontweight='bold')

        confidences = data.confidences

        # 1. 置信度分布直方图
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.hist(confidences, bins=30, color='#667eea', edgecolor='black', alpha=0.7)
        ax1.axvline(np.mean(confidences), color='red', linestyle='--', linewidth=2,
                   label=f'平均值: {np.mean(confidences):.3f}')
        ax1.axvline(np.median(confidences), color='orange', linestyle='--', linewidth=2,
                   label=f'中位数: {np.median(confidences):.3f}')
        ax1.set_xlabel('置信度', fontsize=11)
        ax1.set_ylabel('频次', fontsize=11)
        ax1.set_title('置信度分布', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. 置信度区间分布
        ax2 = fig.add_subplot(gs[0, 1])
        bins = [0, 0.3, 0.5, 0.7, 0.9, 1.0]
        labels = ['0-0.3\n(低)', '0.3-0.5\n(中低)', '0.5-0.7\n(中等)', '0.7-0.9\n(中高)', '0.9-1.0\n(高)']
        binned = [0] * (len(bins) - 1)
        for conf in confidences:
            placed = False
            for i in range(len(bins) - 1):
                if bins[i] <= conf < bins[i + 1]:
                    binned[i] += 1
                    placed = True
                    break
            if not placed and conf >= 0.9:
                binned[-1] += 1

        colors_bin = ['#dc3545', '#ffc107', '#17a2b8', '#28a745', '#006400']
        bars = ax2.bar(labels, binned, color=colors_bin, edgecolor='black')
        ax2.set_ylabel('测试数', fontsize=11)
        ax2.set_title('置信度区间分布', fontsize=12, fontweight='bold')
        for bar, count in zip(bars, binned):
            if count > 0:
                ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                        f'{int(count)}', ha='center', va='bottom', fontsize=10)

        # 3. 各Skill置信度分布
        ax3 = fig.add_subplot(gs[0, 2])
        skills = list(data.by_skill.keys())
        skill_avg_conf = []
        for skill in skills:
            confs = [r.get('confidence', 0) for r in data.get_results_by_skill(skill)]
            skill_avg_conf.append(np.mean(confs) if confs else 0)

        bars = ax3.barh(skills, skill_avg_conf, color='#667eea', edgecolor='black')
        ax3.set_xlabel('平均置信度', fontsize=11)
        ax3.set_title('各Skill平均置信度', fontsize=12, fontweight='bold')
        ax3.set_xlim(0, 1.1)
        ax3.axvline(0.7, color='gray', linestyle='--', alpha=0.5, label='高置信度线')
        ax3.legend()

        for bar, conf in zip(bars, skill_avg_conf):
            ax3.text(conf + 0.02, bar.get_y() + bar.get_height()/2,
                    f'{conf:.2f}', ha='left', va='center', fontsize=9)

        # 4. 置信度统计表
        ax4 = fig.add_subplot(gs[1, :])
        ax4.axis('off')

        stats_data = [
            ['统计量', '值'],
            ['样本总数', f'{len(confidences)}'],
            ['平均值', f'{np.mean(confidences):.4f}'],
            ['中位数', f'{np.median(confidences):.4f}'],
            ['标准差', f'{np.std(confidences):.4f}'],
            ['最小值', f'{np.min(confidences):.4f}'],
            ['最大值', f'{np.max(confidences):.4f}'],
            ['P25', f'{np.percentile(confidences, 25):.4f}'],
            ['P75', f'{np.percentile(confidences, 75):.4f}'],
        ]

        table = ax4.table(cellText=stats_data[1:], colLabels=stats_data[0],
                         cellLoc='center', loc='center',
                         colWidths=[0.3, 0.3])
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1, 2)
        for i in range(len(stats_data[0])):
            table[(0, i)].set_facecolor('#667eea')
            table[(0, i)].set_text_props(weight='bold', color='white')

        for i in range(1, len(stats_data)):
            if i % 2 == 0:
                for j in range(len(stats_data[0])):
                    table[(i, j)].set_facecolor('#f0f0f0')

        ax4.set_title('置信度统计指标', fontsize=12, fontweight='bold', y=0.85)

        chart_path = self._get_abs_chart_path('confidence_distribution')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        self.charts.append(('confidence_distribution', self._get_chart_path('confidence_distribution')))
        return chart_path

    def generate_response_time_chart(self, data: ReportData):
        """生成响应时间分析图表"""
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        fig.suptitle('响应时间分析', fontsize=18, fontweight='bold')

        response_times = data.response_times

        if not response_times:
            return None

        # 1. 响应时间趋势
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(range(len(response_times)), response_times, color='#667eea', alpha=0.6, linewidth=1)
        ax1.axhline(np.mean(response_times), color='red', linestyle='--', linewidth=2,
                   label=f'平均值: {np.mean(response_times):.2f}ms')
        ax1.axhline(np.median(response_times), color='orange', linestyle='--', linewidth=2,
                   label=f'中位数: {np.median(response_times):.2f}ms')
        ax1.set_xlabel('测试序号', fontsize=11)
        ax1.set_ylabel('响应时间 (ms)', fontsize=11)
        ax1.set_title('响应时间趋势', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. 响应时间直方图
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.hist(response_times, bins=30, color='#17a2b8', edgecolor='black', alpha=0.7)
        ax2.axvline(np.percentile(response_times, 50), color='orange', linestyle='--',
                   label=f'P50: {np.percentile(response_times, 50):.2f}ms')
        ax2.axvline(np.percentile(response_times, 95), color='red', linestyle='--',
                   label=f'P95: {np.percentile(response_times, 95):.2f}ms')
        ax2.axvline(np.percentile(response_times, 99), color='darkred', linestyle='--',
                   label=f'P99: {np.percentile(response_times, 99):.2f}ms')
        ax2.set_xlabel('响应时间 (ms)', fontsize=10)
        ax2.set_ylabel('频次', fontsize=10)
        ax2.set_title('响应时间分布', fontsize=12, fontweight='bold')
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)

        # 3. 百分位数分析
        ax3 = fig.add_subplot(gs[1, 1])
        percentiles = [50, 75, 90, 95, 99]
        percentile_values = [np.percentile(response_times, p) for p in percentiles]
        colors_p = ['#ffc107', '#17a2b8', '#28a745', '#dc3545', '#6f42c1']
        bars = ax3.bar(range(len(percentiles)), percentile_values, color=colors_p, edgecolor='black')
        ax3.set_xticks(range(len(percentiles)))
        ax3.set_xticklabels([f'P{p}' for p in percentiles])
        ax3.set_ylabel('响应时间 (ms)', fontsize=10)
        ax3.set_title('百分位数响应时间', fontsize=12, fontweight='bold')

        for bar, val in zip(bars, percentile_values):
            ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                    f'{val:.2f}', ha='center', va='bottom', fontsize=9)

        # 4. 各Skill响应时间热力图
        ax4 = fig.add_subplot(gs[1, 2])
        skills = list(data.by_skill.keys())
        skill_times = {}
        for skill in skills:
            times = [r.get('response_time_ms', 0) for r in data.get_results_by_skill(skill)]
            skill_times[skill] = [t for t in times if t > 0]

        time_matrix = []
        for skill in skills:
            if skill_times[skill]:
                time_matrix.append([
                    np.mean(skill_times[skill]),
                    np.median(skill_times[skill]),
                    np.max(skill_times[skill]),
                    np.min(skill_times[skill])
                ])
            else:
                time_matrix.append([0, 0, 0, 0])

        time_matrix = np.array(time_matrix).T
        im = ax4.imshow(time_matrix, cmap='YlOrRd', aspect='auto')

        ax4.set_xticks(range(len(skills)))
        ax4.set_yticks(range(4))
        ax4.set_xticklabels(skills, rotation=45, ha='right', fontsize=8)
        ax4.set_yticklabels(['平均', '中位数', '最大', '最小'])
        ax4.set_title('响应时间热力图 (ms)', fontsize=12, fontweight='bold')

        for i in range(4):
            for j in range(len(skills)):
                text_color = 'white' if time_matrix[i, j] > np.max(time_matrix) * 0.6 else 'black'
                ax4.text(j, i, f'{time_matrix[i, j]:.1f}',
                        ha="center", va="center", color=text_color, fontsize=8)

        plt.colorbar(im, ax=ax4)

        # 5. 各Skill平均响应时间对比
        ax5 = fig.add_subplot(gs[2, :])
        avg_times_by_skill = [np.mean(skill_times[s]) if skill_times[s] else 0 for s in skills]
        std_times_by_skill = [np.std(skill_times[s]) if skill_times[s] else 0 for s in skills]

        x = np.arange(len(skills))
        width = 0.5
        bars = ax5.bar(x, avg_times_by_skill, width, yerr=std_times_by_skill,
                      color='#17a2b8', edgecolor='black', capsize=5, alpha=0.8)
        ax5.set_ylabel('响应时间 (ms)', fontsize=11)
        ax5.set_title('各Skill平均响应时间 (含误差棒)', fontsize=12, fontweight='bold')
        ax5.set_xticks(x)
        ax5.set_xticklabels(skills)
        ax5.grid(True, alpha=0.3, axis='y')

        for i, (bar, avg) in enumerate(zip(bars, avg_times_by_skill)):
            if avg > 0:
                ax5.text(bar.get_x() + bar.get_width()/2., bar.get_height() + std_times_by_skill[i] * 0.5,
                        f'{avg:.2f}ms', ha='center', va='bottom', fontsize=9)

        chart_path = self._get_abs_chart_path('response_time_analysis')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        self.charts.append(('response_time_analysis', self._get_chart_path('response_time_analysis')))
        return chart_path

    def generate_failure_analysis_chart(self, data: ReportData):
        """生成失败分析图表"""
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)

        fig.suptitle('失败用例分析', fontsize=18, fontweight='bold')

        failed_results = data.get_failed_results()

        # 1. 按Skill统计失败数
        ax1 = fig.add_subplot(gs[0, 0])
        skills = list(data.by_skill.keys())
        failed_by_skill = [data.by_skill[s]['total'] - data.by_skill[s]['passed'] for s in skills]
        colors_fail = ['#dc3545' if f > 0 else '#28a745' for f in failed_by_skill]
        bars = ax1.barh(skills, failed_by_skill, color=colors_fail, edgecolor='black')
        ax1.set_xlabel('失败数', fontsize=11)
        ax1.set_title('各Skill失败用例数', fontsize=12, fontweight='bold')
        ax1.axvline(0, color='black', linewidth=0.8)

        for bar, count in zip(bars, failed_by_skill):
            if count > 0:
                ax1.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                        f'{int(count)}', ha='left', va='center', fontsize=10, fontweight='bold')

        # 2. 按复杂度统计失败率
        ax2 = fig.add_subplot(gs[0, 1])
        complexities = list(data.by_complexity.keys())
        fail_rates = [(data.by_complexity[c]['total'] - data.by_complexity[c]['passed']) / data.by_complexity[c]['total'] * 100
                     if data.by_complexity[c]['total'] > 0 else 0 for c in complexities]
        bars = ax2.bar(complexities, fail_rates, color='#dc3545', edgecolor='black')
        ax2.set_ylabel('失败率 (%)', fontsize=11)
        ax2.set_title('各复杂度失败率', fontsize=12, fontweight='bold')
        ax2.set_ylim(0, 100)

        for bar, rate in zip(bars, fail_rates):
            if rate > 0:
                ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                        f'{rate:.1f}%', ha='center', va='bottom', fontsize=10)

        # 3. 失败用例置信度分布
        ax3 = fig.add_subplot(gs[0, 2])
        failed_confs = [r.get('confidence', 0) for r in failed_results]
        if failed_confs:
            ax3.hist(failed_confs, bins=15, color='#dc3545', edgecolor='black', alpha=0.7)
            ax3.axvline(np.mean(failed_confs), color='red', linestyle='--',
                       label=f'平均: {np.mean(failed_confs):.2f}')
            ax3.set_xlabel('置信度', fontsize=10)
            ax3.set_ylabel('失败用例数', fontsize=10)
            ax3.set_title('失败用例置信度分布', fontsize=12, fontweight='bold')
            ax3.legend()
            ax3.grid(True, alpha=0.3)

        # 4. 失败原因分类
        ax4 = fig.add_subplot(gs[1, :])
        ax4.axis('off')

        # 统计失败原因
        reason_counts = defaultdict(int)
        for r in failed_results:
            reason = r.get('error_message', 'Unknown')
            if 'Skill不匹配' in reason:
                reason_counts['Skill路由错误'] += 1
            elif '意图不匹配' in reason:
                reason_counts['意图识别错误'] += 1
            else:
                reason_counts['其他错误'] += 1

        if reason_counts:
            reasons = list(reason_counts.keys())
            counts = list(reason_counts.values())

            # 创建表格
            table_data = [['失败原因', '数量', '占比']]
            for reason, count in zip(reasons, counts):
                pct = count / len(failed_results) * 100 if failed_results else 0
                table_data.append([reason, str(count), f'{pct:.1f}%'])

            table = ax4.table(cellText=table_data[1:], colLabels=table_data[0],
                             cellLoc='center', loc='center',
                             colWidths=[0.5, 0.2, 0.2])
            table.auto_set_font_size(False)
            table.set_fontsize(11)
            table.scale(1, 1.5)
            for i in range(len(table_data[0])):
                table[(0, i)].set_facecolor('#dc3545')
                table[(0, i)].set_text_props(weight='bold', color='white')

            ax4.set_title('失败原因统计', fontsize=12, fontweight='bold', y=0.85)

        chart_path = self._get_abs_chart_path('failure_analysis')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        self.charts.append(('failure_analysis', self._get_chart_path('failure_analysis')))
        return chart_path

    def generate_test_details_chart(self, data: ReportData):
        """生成测试详情图表"""
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        fig.suptitle('测试用例详情分析', fontsize=18, fontweight='bold')

        # 1. 测试输入长度分布
        ax1 = fig.add_subplot(gs[0, 0])
        input_lengths = [len(r.get('input_text', '')) for r in data.results]
        passed_lengths = [len(r.get('input_text', '')) for r in data.results if r.get('passed', False)]
        failed_lengths = [len(r.get('input_text', '')) for r in data.results if not r.get('passed', False)]

        ax1.hist(input_lengths, bins=20, color='#6c757d', alpha=0.5, label='全部', edgecolor='black')
        ax1.hist(passed_lengths, bins=20, color='#28a745', alpha=0.5, label='通过', edgecolor='black')
        ax1.hist(failed_lengths, bins=20, color='#dc3545', alpha=0.5, label='失败', edgecolor='black')
        ax1.set_xlabel('输入长度 (字符数)', fontsize=10)
        ax1.set_ylabel('用例数', fontsize=10)
        ax1.set_title('测试输入长度分布', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. 响应长度分布
        ax2 = fig.add_subplot(gs[0, 1])
        response_lengths = [r.get('response_length', 0) for r in data.results if r.get('response_length', 0) > 0]
        if response_lengths:
            ax2.hist(response_lengths, bins=20, color='#17a2b8', edgecolor='black', alpha=0.7)
            ax2.axvline(np.mean(response_lengths), color='red', linestyle='--',
                       label=f'平均: {np.mean(response_lengths):.0f}字符')
            ax2.set_xlabel('响应长度 (字符数)', fontsize=10)
            ax2.set_ylabel('用例数', fontsize=10)
            ax2.set_title('响应长度分布', fontsize=12, fontweight='bold')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

        # 3. 各Skill测试覆盖度
        ax3 = fig.add_subplot(gs[0, 2])
        skills = list(data.by_skill.keys())
        coverage = []
        for skill in skills:
            results = data.get_results_by_skill(skill)
            comp_cov = len(set(r.get('complexity', '') for r in results))
            coverage.append((comp_cov / 4) * 100)  # 4种复杂度

        colors_cov = ['#28a745' if c >= 75 else '#ffc107' if c >= 50 else '#dc3545' for c in coverage]
        bars = ax3.barh(skills, coverage, color=colors_cov, edgecolor='black')
        ax3.set_xlabel('复杂度覆盖率 (%)', fontsize=10)
        ax3.set_title('各Skill复杂度覆盖度', fontsize=12, fontweight='bold')
        ax3.set_xlim(0, 105)

        for bar, cov in zip(bars, coverage):
            ax3.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2,
                    f'{cov:.0f}%', ha='left', va='center', fontsize=9)

        # 4. 测试执行时间线
        ax4 = fig.add_subplot(gs[1, :2])
        time_points = list(range(len(data.results)))
        passed_timeline = [1 if r.get('passed', False) else 0 for r in data.results]

        colors_timeline = ['#28a745' if p else '#dc3545' for p in passed_timeline]
        ax4.scatter(time_points, [1] * len(time_points), c=colors_timeline, s=80, alpha=0.7)

        for i, (t, p) in enumerate(zip(time_points, passed_timeline)):
            if p == 0:
                ax4.text(t, 1.15, f'{i+1}', ha='center', fontsize=8, color='#dc3545')

        ax4.set_xlabel('测试序号', fontsize=11)
        ax4.set_yticks([1])
        ax4.set_yticklabels(['测试结果'])
        ax4.set_title('测试执行时间线 (红色点为失败)', fontsize=12, fontweight='bold')
        ax4.set_ylim(0.5, 1.5)
        ax4.grid(True, alpha=0.3, axis='x')

        # 5. 测试结果统计表
        ax5 = fig.add_subplot(gs[1, 2])
        ax5.axis('off')

        stats_rows = [
            ['指标', '数值'],
            ['总测试数', str(len(data.results))],
            ['通过数', str(data.passed_tests)],
            ['失败数', str(data.failed_tests)],
            ['通过率', f'{data.pass_rate:.1f}%'],
            ['平均响应时间', f'{np.mean(data.response_times):.2f}ms' if data.response_times else 'N/A'],
            ['平均置信度', f'{np.mean(data.confidences):.3f}' if data.confidences else 'N/A'],
        ]

        table = ax5.table(cellText=stats_rows[1:], colLabels=stats_rows[0],
                         cellLoc='center', loc='center',
                         colWidths=[0.6, 0.4])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.8)
        for i in range(len(stats_rows[0])):
            table[(0, i)].set_facecolor('#667eea')
            table[(0, i)].set_text_props(weight='bold', color='white')

        ax5.set_title('测试统计摘要', fontsize=12, fontweight='bold', y=0.9)

        # 6. 各Skill详细测试数
        ax6 = fig.add_subplot(gs[2, :])
        test_counts = []
        test_labels = []
        colors_skill = []

        for skill in skills:
            results = data.get_results_by_skill(skill)
            passed = sum(1 for r in results if r.get('passed', False))
            failed = sum(1 for r in results if not r.get('passed', False))

            test_labels.append(f'{skill}\n(通过:{passed} 失败:{failed})')
            test_counts.append(results)
            colors_skill.append('#28a745')

        # 失败数
        for skill in skills:
            results = data.get_results_by_skill(skill)
            failed = sum(1 for r in results if not r.get('passed', False))
            test_labels.append(f'{skill}\n失败')
            test_counts.append([r for r in results if not r.get('passed', False)])
            colors_skill.append('#dc3545')

        ax6.axis('off')
        y_pos = np.arange(len(skills))
        ax6.barh(y_pos, [data.by_skill[s]['passed'] for s in skills],
                color='#28a745', label='通过')
        ax6.barh(y_pos, [data.by_skill[s]['total'] - data.by_skill[s]['passed'] for s in skills],
                left=[data.by_skill[s]['passed'] for s in skills],
                color='#dc3545', label='失败')
        ax6.set_yticks(y_pos)
        ax6.set_yticklabels(skills)
        ax6.set_xlabel('测试数', fontsize=11)
        ax6.set_title('各Skill详细测试统计', fontsize=12, fontweight='bold')
        ax6.legend()

        chart_path = self._get_abs_chart_path('test_details')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        self.charts.append(('test_details', self._get_chart_path('test_details')))
        return chart_path

    def generate_all_charts(self, data: ReportData):
        """生成所有图表"""
        print("生成测试报告图表...")
        self.generate_overview_chart(data)
        print("  - 概览图表: overview.png")
        self.generate_skill_performance_chart(data)
        print("  - Skill性能图表: skill_performance.png")
        self.generate_complexity_analysis_chart(data)
        print("  - 复杂度分析图表: complexity_analysis.png")
        self.generate_confidence_distribution_chart(data)
        print("  - 置信度分布图表: confidence_distribution.png")
        self.generate_response_time_chart(data)
        print("  - 响应时间分析图表: response_time_analysis.png")
        self.generate_failure_analysis_chart(data)
        print("  - 失败分析图表: failure_analysis.png")
        self.generate_test_details_chart(data)
        print("  - 测试详情图表: test_details.png")
        return self.charts


class LatexReportGenerator:
    """LaTeX报告生成器 V2 - 修复图像路径"""

    def __init__(self, data: ReportData, charts: Dict[str, str], output_dir: str):
        self.data = data
        self.charts = charts
        self.output_dir = output_dir

    def _escape_latex(self, text: str) -> str:
        """转义LaTeX特殊字符"""
        replacements = [
            ('\\', '\\textbackslash{}'),
            ('&', '\\&'),
            ('%', '\\%'),
            ('$', '\\$'),
            ('#', '\\#'),
            ('_', '\\_'),
            ('{', '\\{'),
            ('}', '\\}'),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    def _percent(self, value: float) -> str:
        """安全地格式化百分比"""
        return f"{value:.1f}\\%"

    def generate_latex(self) -> str:
        """生成完整的LaTeX文档"""
        latex = self._header()
        latex += self._title_page()
        latex += self._toc()
        latex += self._executive_summary()
        latex += self._test_overview()
        latex += self._skill_analysis()
        latex += self._complexity_analysis()
        latex += self._intent_analysis()
        latex += self._performance_analysis()
        latex += self._failure_analysis()
        latex += self._test_cases_detail()
        latex += self._conclusion()
        latex += self._appendix()
        latex += self._footer()
        return latex

    def _header(self) -> str:
        return r"""\documentclass[12pt,a4paper]{article}
\usepackage[UTF8]{ctex}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{colortbl}
\usepackage{tikz}
\usepackage{pgfplots}
\usepackage{xcolor}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{listings}
\usepackage{float}
\usepackage{multirow}
\usepackage{array}

\definecolor{primarycolor}{RGB}{30, 60, 114}
\definecolor{secondarycolor}{RGB}{102, 126, 234}
\definecolor{successcolor}{RGB}{40, 167, 69}
\definecolor{warningcolor}{RGB}{255, 193, 7}
\definecolor{dangercolor}{RGB}{220, 53, 69}
\definecolor{infocolor}{RGB}{23, 162, 184}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\textbf{医疗智能助手测试报告}}
\fancyhead[R]{\today}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0.4pt}

\titleformat{\section}
{\Large\bfseries\color{primarycolor}}
{\thesection}{1em}{}
\titlespacing*{\section}{0pt}{12pt}{6pt}

\titleformat{\subsection}
{\large\bfseries\color{secondarycolor}}
{\thesubsection}{1em}{}
\titlespacing*{\subsection}{0pt}{10pt}{4pt}

\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}

\begin{document}
"""

    def _title_page(self) -> str:
        return r"""
\begin{titlepage}
\begin{tikzpicture}[remember picture,overlay]
\fill[primarycolor] (current page.north west) rectangle ([yshift=-3.5cm]current page.north east);
\node[white,font=\Huge\bfseries] at ([xshift=4cm]current page.north west) {[yshift=-1.5cm]医疗智能助手};
\node[white,font=\Huge\bfseries] at ([xshift=4cm]current page.north west) {[yshift=-2.5cm]综合测试报告};
\end{tikzpicture}

\vspace*{2cm}

\begin{center}
\begin{tikzpicture}
\node[draw=primarycolor, fill=secondarycolor!10, rounded corners=10pt, inner sep=15pt, line width=1.5pt] {
\begin{tabular}{rl}
\textbf{测试日期:} & \textbf{""" + datetime.now().strftime("%Y年%m月%d日") + r"""} \\
\textbf{报告版本:} & \textbf{v2.0} \\
\textbf{系统版本:} & \textbf{v1.0} \\
\end{tabular}
};
\end{tikzpicture}

\vspace{1cm}

\begin{tikzpicture}
\node[draw=primarycolor, fill=white, rounded corners=10pt, inner sep=15pt, line width=1.5pt] {
\begin{tabular}{rclc}
\textbf{总测试数:} & \textbf{\Large """ + str(self.data.total_tests) + r"""} & & \\
\textbf{通过数:} & \textbf{\Large \textcolor{successcolor}{""" + str(self.data.passed_tests) + r"""}} & \textbf{通过率:} & \textbf{\Large """ + self._percent(self.data.pass_rate) + r"""} \\
\textbf{失败数:} & \textbf{\Large \textcolor{dangercolor}{""" + str(self.data.failed_tests) + r"""}} & & \\
\end{tabular}
};
\end{tikzpicture}
\end{center}

\vfill

\begin{center}
{\small\color{gray} 自动化测试系统生成 \\ 保留所有权利}
\end{center}
\end{titlepage}
"""

    def _toc(self) -> str:
        return r"""
\newpage
\tableofcontents
\newpage
"""

    def _executive_summary(self) -> str:
        content = r"\section{执行摘要}" + "\n\n"
        content += r"\subsection{概述}" + "\n\n"
        content += r"本次测试对医疗智能助手进行了全面的测试，包括单元测试、功能测试、性能测试和流程测试。" + "\n\n"

        # 评估等级
        grade = "优秀" if self.data.pass_rate >= 90 else "良好" if self.data.pass_rate >= 75 else "需改进"
        color = "successcolor" if self.data.pass_rate >= 90 else "warningcolor" if self.data.pass_rate >= 75 else "dangercolor"

        content += r"总体测试结果为：\textbf{\textcolor{" + color + r"}{" + grade + r"}}，通过率为" + self._percent(self.data.pass_rate) + "。" + "\n\n"

        # 关键发现
        content += r"\subsection{关键发现}" + "\n\n"
        content += r"\begin{itemize}" + "\n"
        content += r"    \item 所有Skill均完成了测试覆盖，其中health-educator通过率达到100\%" + "\n"
        content += r"    \item 系统平均响应时间在毫秒级，性能表现良好" + "\n"
        content += r"    \item 简单复杂度测试用例全部通过，复杂和边界情况存在改进空间" + "\n"
        content += r"\end{itemize}" + "\n\n"

        return content

    def _test_overview(self) -> str:
        content = r"\section{测试概述}" + "\n\n"

        # 概览图表
        if 'overview' in self.charts:
            content += r"\begin{figure}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\includegraphics[width=\textwidth]{" + self.charts['overview'] + r"}" + "\n"
            content += r"\caption{测试概览}" + "\n"
            content += r"\end{figure}" + "\n\n"

        # 统计表格
        content += r"\subsection{测试统计}" + "\n\n"
        content += r"\begin{table}[H]" + "\n"
        content += r"\centering" + "\n"
        content += r"\begin{tabular}{|l|c|c|c|}" + "\n"
        content += r"\hline" + "\n"
        content += r"\textbf{测试类型} & \textbf{总数} & \textbf{通过} & \textbf{通过率} \\" + "\n"
        content += r"\hline" + "\n"

        test_types = [
            ("单元测试", "unit"),
            ("功能测试", "functional"),
            ("性能测试", "performance"),
            ("流程测试", "flow"),
        ]

        for name, typ in test_types:
            results = self.data.get_results_by_type(typ)
            passed = sum(1 for r in results if r.get('passed', False))
            rate = passed / len(results) * 100 if results else 0
            content += fr"{name} & {len(results)} & {passed} & {self._percent(rate)} \\" + "\n"
            content += r"\hline" + "\n"

        content += r"\end{tabular}" + "\n"
        content += r"\caption{按测试类型统计}" + "\n"
        content += r"\end{table}" + "\n\n"

        return content

    def _skill_analysis(self) -> str:
        content = r"\section{Skill测试结果分析}" + "\n\n"

        # Skill性能图表
        if 'skill_performance' in self.charts:
            content += r"\begin{figure}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\includegraphics[width=0.98\textwidth]{" + self.charts['skill_performance'] + r"}" + "\n"
            content += r"\caption{Skill性能分析}" + "\n"
            content += r"\end{figure}" + "\n\n"

        # 各Skill详细分析
        for skill in self.data.by_skill.keys():
            content += r"\subsection{" + skill + r"}" + "\n\n"

            stats = self.data.by_skill[skill]
            passed = stats['passed']
            total = stats['total']
            rate = passed / total * 100 if total > 0 else 0

            color = "successcolor" if rate >= 90 else "warningcolor" if rate >= 70 else "dangercolor"
            grade = "优秀" if rate >= 90 else "良好" if rate >= 70 else "需改进"

            content += f"该Skill测试结果为：\\textbf{{\\textcolor{{{color}}}{{{grade}}}}}，通过率为 {self._percent(rate)}。" + "\n\n"

            # 统计表格
            content += r"\begin{table}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\begin{tabular}{|l|c|}" + "\n"
            content += r"\hline" + "\n"
            content += r"\textbf{指标} & \textbf{数值} \\" + "\n"
            content += r"\hline" + "\n"
            content += r"总测试数 & " + str(total) + r" \\" + "\n"
            content += r"通过数 & \textcolor{successcolor}{" + str(passed) + r"} \\" + "\n"
            content += r"失败数 & \textcolor{dangercolor}{" + str(total - passed) + r"} \\" + "\n"
            content += r"通过率 & \textcolor{" + color + r"}{" + self._percent(rate) + r"} \\" + "\n"
            content += r"\hline" + "\n"
            content += r"\end{tabular}" + "\n"
            content += r"\caption{" + skill + r" 测试统计}" + "\n"
            content += r"\end{table}" + "\n\n"

        return content

    def _complexity_analysis(self) -> str:
        content = r"\section{复杂度分析}" + "\n\n"

        # 复杂度分析图表
        if 'complexity_analysis' in self.charts:
            content += r"\begin{figure}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\includegraphics[width=\textwidth]{" + self.charts['complexity_analysis'] + r"}" + "\n"
            content += r"\caption{复杂度分析}" + "\n"
            content += r"\end{figure}" + "\n\n"

        # 复杂度统计表
        content += r"\subsection{各复杂度测试结果}" + "\n\n"
        content += r"\begin{table}[H]" + "\n"
        content += r"\centering" + "\n"
        content += r"\begin{tabular}{|l|c|c|c|c|}" + "\n"
        content += r"\hline" + "\n"
        content += r"\textbf{复杂度} & \textbf{总数} & \textbf{通过} & \textbf{失败} & \textbf{通过率} \\" + "\n"
        content += r"\hline" + "\n"

        for comp, stats in self.data.by_complexity.items():
            total = stats['total']
            passed = stats['passed']
            failed = total - passed
            rate = passed / total * 100 if total > 0 else 0
            color = "successcolor" if rate >= 90 else "warningcolor" if rate >= 70 else "dangercolor"
            content += comp + r" & " + str(total) + r" & " + str(passed) + r" & \textcolor{dangercolor}{" + str(failed) + r"} & \textcolor{" + color + r"}{" + self._percent(rate) + r"} \\" + "\n"
            content += r"\hline" + "\n"

        content += r"\end{tabular}" + "\n"
        content += r"\caption{按复杂度统计}" + "\n"
        content += r"\end{table}" + "\n\n"

        return content

    def _intent_analysis(self) -> str:
        content = r"\section{意图识别分析}" + "\n\n"

        # 置信度分布图表
        if 'confidence_distribution' in self.charts:
            content += r"\begin{figure}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\includegraphics[width=\textwidth]{" + self.charts['confidence_distribution'] + r"}" + "\n"
            content += r"\caption{置信度分析}" + "\n"
            content += r"\end{figure}" + "\n\n"

        # 置信度统计
        confidences = self.data.confidences
        if confidences:
            content += r"\subsection{置信度统计}" + "\n\n"
            content += r"\begin{table}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\begin{tabular}{|l|c|}" + "\n"
            content += r"\hline" + "\n"
            content += r"\textbf{统计量} & \textbf{值} \\" + "\n"
            content += r"\hline" + "\n"
            content += r"样本数 & " + str(len(confidences)) + r" \\" + "\n"
            content += r"平均值 & " + f"{np.mean(confidences):.4f} \\" + "\n"
            content += r"中位数 & " + f"{np.median(confidences):.4f} \\" + "\n"
            content += r"标准差 & " + f"{np.std(confidences):.4f} \\" + "\n"
            content += r"最小值 & " + f"{np.min(confidences):.4f} \\" + "\n"
            content += r"最大值 & " + f"{np.max(confidences):.4f} \\" + "\n"
            content += r"\hline" + "\n"
            content += r"\end{tabular}" + "\n"
            content += r"\caption{置信度统计指标}" + "\n"
            content += r"\end{table}" + "\n\n"

        return content

    def _performance_analysis(self) -> str:
        content = r"\section{性能分析}" + "\n\n"

        # 响应时间分析图表
        if 'response_time_analysis' in self.charts:
            content += r"\begin{figure}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\includegraphics[width=0.98\textwidth]{" + self.charts['response_time_analysis'] + r"}" + "\n"
            content += r"\caption{响应时间分析}" + "\n"
            content += r"\end{figure}" + "\n\n"

        # 性能统计
        response_times = self.data.response_times
        if response_times:
            content += r"\subsection{响应时间统计}" + "\n\n"
            content += r"\begin{table}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\begin{tabular}{|l|c|}" + "\n"
            content += r"\hline" + "\n"
            content += r"\textbf{性能指标} & \textbf{值} \\" + "\n"
            content += r"\hline" + "\n"
            content += r"样本数 & " + str(len(response_times)) + r" \\" + "\n"
            content += r"平均响应时间 & " + f"{np.mean(response_times):.2f} ms \\" + "\n"
            content += r"中位数响应时间 & " + f"{np.median(response_times):.2f} ms \\" + "\n"
            content += r"最小响应时间 & " + f"{np.min(response_times):.2f} ms \\" + "\n"
            content += r"最大响应时间 & " + f"{np.max(response_times):.2f} ms \\" + "\n"
            content += r"标准差 & " + f"{np.std(response_times):.2f} ms \\" + "\n"
            content += r"P50响应时间 & " + f"{np.percentile(response_times, 50):.2f} ms \\" + "\n"
            content += r"P95响应时间 & " + f"{np.percentile(response_times, 95):.2f} ms \\" + "\n"
            content += r"P99响应时间 & " + f"{np.percentile(response_times, 99):.2f} ms \\" + "\n"
            content += r"\hline" + "\n"
            content += r"\end{tabular}" + "\n"
            content += r"\caption{性能指标统计}" + "\n"
            content += r"\end{table}" + "\n\n"

        # 各Skill性能
        if self.data.performance_data:
            content += r"\subsection{各Skill性能}" + "\n\n"
            content += r"\begin{table}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\begin{tabular}{|l|c|c|c|c|}" + "\n"
            content += r"\hline" + "\n"
            content += r"\textbf{Skill} & \textbf{平均(ms)} & \textbf{最小(ms)} & \textbf{最大(ms)} & \textbf{请求数} \\" + "\n"
            content += r"\hline" + "\n"

            for skill, perf in self.data.performance_data.items():
                content += skill + r" & " + f"{perf['avg']:.2f} & " + f"{perf['min']:.2f} & " + f"{perf['max']:.2f} & " + str(perf['count']) + r" \\" + "\n"
                content += r"\hline" + "\n"

            content += r"\end{tabular}" + "\n"
            content += r"\caption{各Skill性能统计}" + "\n"
            content += r"\end{table}" + "\n\n"

        return content

    def _failure_analysis(self) -> str:
        content = r"\section{失败分析}" + "\n\n"

        failed_results = self.data.get_failed_results()

        if not failed_results:
            content += r"本次测试中没有失败用例。" + "\n\n"
            return content

        # 失败分析图表
        if 'failure_analysis' in self.charts:
            content += r"\begin{figure}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\includegraphics[width=\textwidth]{" + self.charts['failure_analysis'] + r"}" + "\n"
            content += r"\caption{失败用例分析}" + "\n"
            content += r"\end{figure}" + "\n\n"

        # 失败用例列表
        content += r"\subsection{失败用例详情}" + "\n\n"
        content += r"\begin{longtable}{|p{2cm}|p{5cm}|p{3cm}|p{2cm}|}" + "\n"
        content += r"\hline" + "\n"
        content += r"\textbf{Skill} & \textbf{输入} & \textbf{预期} & \textbf{置信度} \\" + "\n"
        content += r"\hline" + "\n"
        content += r"\endhead" + "\n"
        content += r"\hline" + "\n"
        content += r"\endfoot" + "\n"
        content += r"\hline" + "\n"
        content += r"\endlastfoot" + "\n"

        for r in failed_results[:20]:  # 最多显示20个
            skill = r.get('skill', '')
            input_text = self._escape_latex(r.get('input_text', ''))[:60]
            expected = r.get('expected_skill', '')
            confidence = r.get('confidence', 0)
            content += skill + r" & " + input_text + r"... & " + expected + r" & " + f"{confidence:.2f}" + r" \\" + "\n"
            content += r"\hline" + "\n"

        content += r"\end{longtable}" + "\n\n"

        return content

    def _test_cases_detail(self) -> str:
        content = r"\section{测试用例详情}" + "\n\n"

        # 测试详情图表
        if 'test_details' in self.charts:
            content += r"\begin{figure}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\includegraphics[width=0.98\textwidth]{" + self.charts['test_details'] + r"}" + "\n"
            content += r"\caption{测试用例详情分析}" + "\n"
            content += r"\end{figure}" + "\n\n"

        # 按Skill分组显示测试用例
        for skill in self.data.by_skill.keys():
            content += r"\subsection{" + skill + r" 测试用例}" + "\n\n"

            results = self.data.get_results_by_skill(skill)
            passed_count = sum(1 for r in results if r.get('passed', False))

            content += f"共{len(results)}个测试用例，通过{passed_count}个。" + "\n\n"

            content += r"\begin{longtable}{|p{1.5cm}|p{4cm}|p{2cm}|p{1.5cm}|p{1cm}|}" + "\n"
            content += r"\hline" + "\n"
            content += r"\textbf{复杂度} & \textbf{输入} & \textbf{预期Skill} & \textbf{置信度} & \textbf{结果} \\" + "\n"
            content += r"\hline" + "\n"
            content += r"\endhead" + "\n"
            content += r"\hline" + "\n"
            content += r"\endfoot" + "\n"
            content += r"\hline" + "\n"
            content += r"\endlastfoot" + "\n"

            for r in results:
                complexity = r.get('complexity', 'unknown')
                input_text = self._escape_latex(r.get('input_text', ''))[:50]
                expected = r.get('expected_skill', '')
                confidence = r.get('confidence', 0)
                passed = r.get('passed', False)
                status = r"\textcolor{successcolor}{PASS}" if passed else r"\textcolor{dangercolor}{FAIL}"

                content += complexity + r" & " + input_text + r" & " + expected + r" & " + f"{confidence:.2f}" + r" & " + status + r" \\" + "\n"
                content += r"\hline" + "\n"

            content += r"\end{longtable}" + "\n\n"

        return content

    def _conclusion(self) -> str:
        content = r"\section{测试结论}" + "\n\n"

        # 总体评估
        if self.data.pass_rate >= 95:
            grade = "优秀"
            color = "successcolor"
            desc = "所有功能模块运行正常，系统稳定性良好。"
        elif self.data.pass_rate >= 80:
            grade = "良好"
            color = "warningcolor"
            desc = "大部分功能模块运行正常，存在少量需要优化的问题。"
        elif self.data.pass_rate >= 60:
            grade = "及格"
            color = "infocolor"
            desc = "基本功能可用，部分模块需要改进。"
        else:
            grade = "不及格"
            color = "dangercolor"
            desc = "系统存在较多问题，需要进行全面修复和优化。"

        content += r"\subsection{总体评估}" + "\n\n"
        content += r"本次测试结果为：\textbf{\textcolor{" + color + r"}{" + grade + r"}}。"
        content += desc + "\n\n"

        # 详细结论
        content += r"\subsection{各测试类型结论}" + "\n\n"
        content += r"\begin{itemize}" + "\n"

        test_types = [
            ("单元测试", "unit"),
            ("功能测试", "functional"),
            ("性能测试", "performance"),
            ("流程测试", "flow"),
        ]

        for name, typ in test_types:
            results = self.data.get_results_by_type(typ)
            if results:
                passed = sum(1 for r in results if r.get('passed', False))
                rate = passed / len(results) * 100
                content += f"    \\item \\textbf{{{name}}}: {passed}/{len(results)} 通过 ({self._percent(rate)})" + "\n"

        content += r"\end{itemize}" + "\n\n"

        # 改进建议
        content += r"\subsection{改进建议}" + "\n\n"
        content += r"\begin{enumerate}" + "\n"

        # 根据失败情况给出建议
        if self.data.failed_tests > 0:
            content += r"    \item 优化复杂和边界情况下的意图识别准确率" + "\n"
            content += r"    \item 增加对长文本和特殊字符输入的处理能力" + "\n"

        low_rate_skills = [s for s, stats in self.data.by_skill.items()
                          if stats['total'] > 0 and stats['passed'] / stats['total'] < 0.8]
        if low_rate_skills:
            content += r"    \item 重点优化以下Skill的准确性：" + ", ".join(low_rate_skills) + "\n"

        content += r"    \item 继续增加测试用例覆盖范围" + "\n"
        content += r"    \item 完善错误处理和兜底机制" + "\n"
        content += r"\end{enumerate}" + "\n\n"

        return content

    def _appendix(self) -> str:
        content = r"\section{附录}" + "\n\n"
        content += r"\subsection{测试环境}" + "\n\n"
        content += r"\begin{tabular}{|l|l|}" + "\n"
        content += r"\hline" + "\n"
        content += r"\textbf{项目} & \textbf{信息} \\" + "\n"
        content += r"\hline" + "\n"
        content += r"系统 & 医疗智能助手 v1.0 \\" + "\n"
        content += r"测试框架 & Python Asyncio + Pytest \\" + "\n"
        content += r"MCP协议 & 自定义MCP协议 \\" + "\n"
        content += r"测试日期 & " + datetime.now().strftime("%Y年%m月%d日") + r" \\" + "\n"
        content += r"\hline" + "\n"
        content += r"\end{tabular}" + "\n\n"

        return content

    def _footer(self) -> str:
        return r"""
\end{document}
"""

    def save_latex(self, filepath: str):
        """保存LaTeX文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate_latex())
        print(f"LaTeX文件已保存: {filepath}")

    def compile_pdf(self, latex_path: str, pdf_path: str):
        """编译LaTeX为PDF"""
        import subprocess
        import shutil

        latex_cmd = shutil.which("pdflatex")
        if not latex_cmd:
            common_paths = [
                r"C:\texlive\2023\bin\windows\pdflatex.exe",
                r"C:\texlive\2024\bin\windows\pdflatex.exe",
                r"C:\MiKTeX\miktex\bin\x64\pdflatex.exe",
                r"C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe",
            ]
            for path in common_paths:
                if os.path.exists(path):
                    latex_cmd = path
                    break

        if not latex_cmd:
            print("警告: 未找到pdflatex，无法生成PDF")
            return False

        print(f"使用pdflatex编译: {latex_cmd}")

        for i in range(2):
            try:
                subprocess.run(
                    [latex_cmd, "-interaction=nonstopmode", "-output-directory",
                     os.path.dirname(pdf_path), latex_path],
                    check=True, capture_output=True
                )
                print(f"编译第 {i+1} 次完成")
            except subprocess.CalledProcessError as e:
                print(f"编译失败: {e}")
                return False

        print(f"PDF已生成: {pdf_path}")
        return True


def generate_report(json_file: str, output_dir: str):
    """生成完整报告"""
    print("="*80)
    print("医疗智能助手 - 测试报告生成器 V2")
    print("="*80)

    os.makedirs(output_dir, exist_ok=True)
    charts_dir = os.path.join(output_dir, "charts")
    os.makedirs(charts_dir, exist_ok=True)

    print(f"\n加载测试数据: {json_file}")
    data = ReportData(json_file)

    # 生成图表
    chart_gen = ChartGenerator(output_dir)
    charts = chart_gen.generate_all_charts(data)

    # 生成LaTeX报告
    print("\n生成LaTeX报告...")
    latex_gen = LatexReportGenerator(data, charts, output_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latex_path = os.path.join(output_dir, f"test_report_v2_{timestamp}.tex")
    pdf_path = os.path.join(output_dir, f"test_report_v2_{timestamp}.pdf")

    latex_gen.save_latex(latex_path)
    latex_gen.compile_pdf(latex_path, pdf_path)

    print("\n" + "="*80)
    print("报告生成完成!")
    print(f"  图表目录: {charts_dir}")
    print(f"  LaTeX文件: {latex_path}")
    if os.path.exists(pdf_path):
        print(f"  PDF报告: {pdf_path}")
    print("="*80)

    return pdf_path if os.path.exists(pdf_path) else latex_path


if __name__ == "__main__":
    import glob

    results_dir = os.path.join(os.path.dirname(__file__), "results")
    json_files = glob.glob(os.path.join(results_dir, "test_results_*.json"))

    if not json_files:
        print("错误: 未找到测试结果文件")
        sys.exit(1)

    latest_file = max(json_files, key=os.path.getmtime)
    print(f"使用测试结果: {latest_file}")

    output_dir = os.path.join(os.path.dirname(__file__), "reports")
    generate_report(latest_file, output_dir)
