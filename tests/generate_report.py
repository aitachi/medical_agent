# -*- coding: utf-8 -*-
"""
医疗智能助手 - 测试报告生成器
生成图表、LaTeX文档和PDF报告
"""
import os
import sys
import json
import math
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

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
        return [r.get("response_time_ms", 0) for r in self.results]

    @property
    def confidences(self) -> List[float]:
        return [r.get("confidence", 0) for r in self.results]

    def get_results_by_skill(self, skill: str) -> List[Dict]:
        return [r for r in self.results if r.get("skill") == skill]

    def get_results_by_complexity(self, complexity: str) -> List[Dict]:
        return [r for r in self.results if r.get("complexity") == complexity]

    def get_results_by_type(self, test_type: str) -> List[Dict]:
        return [r for r in self.results if r.get("test_type") == test_type]


class ChartGenerator:
    """图表生成器"""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.charts = []

    def generate_overview_chart(self, data: ReportData):
        """生成概览图表"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('医疗智能助手 - 测试概览', fontsize=16, fontweight='bold')

        # 1. 通过/失败饼图
        ax1 = axes[0, 0]
        passed = data.passed_tests
        failed = data.failed_tests
        colors = ['#28a745', '#dc3545']
        ax1.pie([passed, failed], labels=[f'通过 ({passed})', f'失败 ({failed})'],
                colors=colors, autopct='%1.1f%%', startangle=90)
        ax1.set_title('测试结果分布')

        # 2. 按复杂度统计
        ax2 = axes[0, 1]
        complexities = list(data.by_complexity.keys())
        passed_by_complexity = [data.by_complexity[c]['passed'] for c in complexities]
        failed_by_complexity = [data.by_complexity[c]['total'] - data.by_complexity[c]['passed']
                                for c in complexities]

        x = np.arange(len(complexities))
        width = 0.35
        ax2.bar(x - width/2, passed_by_complexity, width, label='通过', color='#28a745')
        ax2.bar(x + width/2, failed_by_complexity, width, label='失败', color='#dc3545')
        ax2.set_xlabel('复杂度')
        ax2.set_ylabel('测试数')
        ax2.set_title('按复杂度统计')
        ax2.set_xticks(x)
        ax2.set_xticklabels(complexities)
        ax2.legend()

        # 3. 按Skill统计
        ax3 = axes[1, 0]
        skills = list(data.by_skill.keys())
        passed_by_skill = [data.by_skill[s]['passed'] for s in skills]
        total_by_skill = [data.by_skill[s]['total'] for s in skills]

        x = np.arange(len(skills))
        ax3.bar(x, passed_by_skill, label='通过', color='#28a745')
        ax3.bar(x, [t - p for t, p in zip(total_by_skill, passed_by_skill)],
                bottom=passed_by_skill, label='失败', color='#dc3545')
        ax3.set_xlabel('Skill')
        ax3.set_ylabel('测试数')
        ax3.set_title('按Skill统计')
        ax3.set_xticks(x)
        ax3.set_xticklabels(skills, rotation=45, ha='right')
        ax3.legend()

        # 4. 响应时间分布
        ax4 = axes[1, 1]
        response_times = [rt for rt in data.response_times if rt > 0]
        if response_times:
            ax4.hist(response_times, bins=30, color='#17a2b8', edgecolor='black', alpha=0.7)
            ax4.axvline(np.mean(response_times), color='red', linestyle='--',
                       label=f'平均值: {np.mean(response_times):.2f}ms')
            ax4.axvline(np.median(response_times), color='orange', linestyle='--',
                       label=f'中位数: {np.median(response_times):.2f}ms')
            ax4.set_xlabel('响应时间 (ms)')
            ax4.set_ylabel('频次')
            ax4.set_title('响应时间分布')
            ax4.legend()

        plt.tight_layout()
        chart_path = os.path.join(self.output_dir, 'overview.png')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        self.charts.append(('overview', chart_path))
        return chart_path

    def generate_skill_performance_chart(self, data: ReportData):
        """生成Skill性能图表"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Skill 性能分析', fontsize=16, fontweight='bold')

        skills = list(data.by_skill.keys())

        # 1. 各Skill通过率
        ax1 = axes[0, 0]
        pass_rates = [data.by_skill[s]['passed'] / data.by_skill[s]['total'] * 100
                     if data.by_skill[s]['total'] > 0 else 0 for s in skills]
        colors = ['#28a745' if pr >= 90 else '#ffc107' if pr >= 70 else '#dc3545' for pr in pass_rates]
        ax1.barh(skills, pass_rates, color=colors)
        ax1.set_xlabel('通过率 (%)')
        ax1.set_title('各Skill通过率')
        ax1.axvline(90, color='gray', linestyle='--', alpha=0.5)

        # 2. 各Skill响应时间
        ax2 = axes[0, 1]
        skill_times = {}
        for skill in skills:
            times = [r.get('response_time_ms', 0) for r in data.get_results_by_skill(skill)]
            skill_times[skill] = [t for t in times if t > 0]

        avg_times = [np.mean(skill_times[s]) if skill_times[s] else 0 for s in skills]
        ax2.barh(skills, avg_times, color='#17a2b8')
        ax2.set_xlabel('平均响应时间 (ms)')
        ax2.set_title('各Skill平均响应时间')

        # 3. 各Skill置信度分布
        ax3 = axes[1, 0]
        skill_confidences = {}
        for skill in skills:
            confs = [r.get('confidence', 0) for r in data.get_results_by_skill(skill)]
            skill_confidences[skill] = confs

        box_data = [skill_confidences[s] for s in skills]
        bp = ax3.boxplot(box_data, labels=skills, patch_artist=True)
        for patch, color in zip(bp['boxes'], ['#667eea', '#28a745', '#ffc107', '#17a2b8', '#f5576c', '#6f42c1']):
            patch.set_facecolor(color)
        ax3.set_ylabel('置信度')
        ax3.set_title('各Skill置信度分布')
        ax3.tick_params(axis='x', rotation=45)

        # 4. 响应时间箱线图
        ax4 = axes[1, 1]
        bp4 = ax4.boxplot(box_data, labels=skills, patch_artist=True)
        for patch in bp4['boxes']:
            patch.set_facecolor('#e7f3ff')
        ax4.set_ylabel('响应时间 (ms)')
        ax4.set_title('各Skill响应时间分布')
        ax4.tick_params(axis='x', rotation=45)

        plt.tight_layout()
        chart_path = os.path.join(self.output_dir, 'skill_performance.png')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        self.charts.append(('skill_performance', chart_path))
        return chart_path

    def generate_complexity_analysis_chart(self, data: ReportData):
        """生成复杂度分析图表"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        fig.suptitle('复杂度分析', fontsize=16, fontweight='bold')

        complexities = list(data.by_complexity.keys())

        # 1. 各复杂度通过率
        ax1 = axes[0]
        pass_rates = [data.by_complexity[c]['passed'] / data.by_complexity[c]['total'] * 100
                     if data.by_complexity[c]['total'] > 0 else 0 for c in complexities]
        colors = ['#28a745', '#17a2b8', '#ffc107', '#6f42c1']
        ax1.bar(complexities, pass_rates, color=colors)
        ax1.set_ylabel('通过率 (%)')
        ax1.set_title('各复杂度通过率')
        ax1.set_ylim(0, 105)

        # 2. 各复杂度响应时间
        ax2 = axes[1]
        complexity_times = {}
        for comp in complexities:
            times = [r.get('response_time_ms', 0) for r in data.get_results_by_complexity(comp)]
            complexity_times[comp] = [t for t in times if t > 0]

        avg_times = [np.mean(complexity_times[c]) if complexity_times[c] else 0 for c in complexities]
        ax2.bar(complexities, avg_times, color='#667eea')
        ax2.set_ylabel('平均响应时间 (ms)')
        ax2.set_title('各复杂度平均响应时间')

        plt.tight_layout()
        chart_path = os.path.join(self.output_dir, 'complexity_analysis.png')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        self.charts.append(('complexity_analysis', chart_path))
        return chart_path

    def generate_confidence_distribution_chart(self, data: ReportData):
        """生成置信度分布图表"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        fig.suptitle('置信度分析', fontsize=16, fontweight='bold')

        # 1. 置信度分布直方图
        ax1 = axes[0]
        confidences = data.confidences
        ax1.hist(confidences, bins=20, color='#667eea', edgecolor='black', alpha=0.7)
        ax1.axvline(np.mean(confidences), color='red', linestyle='--',
                   label=f'平均值: {np.mean(confidences):.3f}')
        ax1.set_xlabel('置信度')
        ax1.set_ylabel('频次')
        ax1.set_title('置信度分布')
        ax1.legend()

        # 2. 置信度区间分布
        ax2 = axes[1]
        bins = [0, 0.3, 0.5, 0.7, 0.9, 1.0]
        labels = ['0-0.3', '0.3-0.5', '0.5-0.7', '0.7-0.9', '0.9-1.0']
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

        colors = ['#dc3545', '#ffc107', '#17a2b8', '#28a745', '#006400']
        ax2.bar(labels, binned, color=colors)
        ax2.set_xlabel('置信度区间')
        ax2.set_ylabel('测试数')
        ax2.set_title('置信度区间分布')

        plt.tight_layout()
        chart_path = os.path.join(self.output_dir, 'confidence_distribution.png')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        self.charts.append(('confidence_distribution', chart_path))
        return chart_path

    def generate_response_time_chart(self, data: ReportData):
        """生成响应时间分析图表"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('响应时间分析', fontsize=16, fontweight='bold')

        response_times = [rt for rt in data.response_times if rt > 0]

        if not response_times:
            return None

        # 1. 响应时间趋势
        ax1 = axes[0, 0]
        ax1.plot(range(len(response_times)), response_times, color='#667eea', alpha=0.6)
        ax1.axhline(np.mean(response_times), color='red', linestyle='--',
                   label=f'平均值: {np.mean(response_times):.2f}ms')
        ax1.set_xlabel('测试序号')
        ax1.set_ylabel('响应时间 (ms)')
        ax1.set_title('响应时间趋势')
        ax1.legend()

        # 2. 响应时间直方图
        ax2 = axes[0, 1]
        ax2.hist(response_times, bins=30, color='#17a2b8', edgecolor='black', alpha=0.7)
        ax2.axvline(np.percentile(response_times, 50), color='orange', linestyle='--',
                   label=f'P50: {np.percentile(response_times, 50):.2f}ms')
        ax2.axvline(np.percentile(response_times, 95), color='red', linestyle='--',
                   label=f'P95: {np.percentile(response_times, 95):.2f}ms')
        ax2.axvline(np.percentile(response_times, 99), color='darkred', linestyle='--',
                   label=f'P99: {np.percentile(response_times, 99):.2f}ms')
        ax2.set_xlabel('响应时间 (ms)')
        ax2.set_ylabel('频次')
        ax2.set_title('响应时间分布')
        ax2.legend()

        # 3. 百分位数分析
        ax3 = axes[1, 0]
        percentiles = [50, 75, 90, 95, 99]
        percentile_values = [np.percentile(response_times, p) for p in percentiles]
        ax3.bar(range(len(percentiles)), percentile_values,
                color=['#ffc107', '#17a2b8', '#28a745', '#dc3545', '#6f42c1'])
        ax3.set_xticks(range(len(percentiles)))
        ax3.set_xticklabels([f'P{p}' for p in percentiles])
        ax3.set_ylabel('响应时间 (ms)')
        ax3.set_title('百分位数响应时间')

        # 4. 各Skill响应时间热力图
        ax4 = axes[1, 1]
        skills = list(data.by_skill.keys())
        skill_times = {}
        for skill in skills:
            times = [r.get('response_time_ms', 0) for r in data.get_results_by_skill(skill)]
            times = [t for t in times if t > 0]
            skill_times[skill] = times

        # 统计各Skill的时间统计
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
        ax4.set_xticklabels(skills, rotation=45, ha='right')
        ax4.set_yticklabels(['平均', '中位数', '最大', '最小'])
        ax4.set_title('响应时间热力图 (ms)')

        # 添加数值标注
        for i in range(4):
            for j in range(len(skills)):
                text = ax4.text(j, i, f'{time_matrix[i, j]:.1f}',
                               ha="center", va="center", color="black", fontsize=8)

        plt.colorbar(im, ax=ax4)

        plt.tight_layout()
        chart_path = os.path.join(self.output_dir, 'response_time_analysis.png')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        self.charts.append(('response_time_analysis', chart_path))
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
        return self.charts


class LatexReportGenerator:
    """LaTeX报告生成器"""

    def __init__(self, data: ReportData, charts: List[tuple], output_dir: str):
        self.data = data
        self.charts = dict(charts)
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
            ('~', '\\textasciitilde{}'),
            ('^', '\\^{}'),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    def _generate_header(self) -> str:
        """生成LaTeX文档头部"""
        return r"""\documentclass[12pt,a4paper]{article}
\usepackage[UTF8]{ctex}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{colortbl}
\usepackage{tikz}
\usepackage{pgfplots}
\pgfplotsset{compat=1.17}
\usepackage{xcolor}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{listings}
\usepackage{float}

\definecolor{primarycolor}{RGB}{30, 60, 114}
\definecolor{secondarycolor}{RGB}{102, 126, 234}
\definecolor{successcolor}{RGB}{40, 167, 69}
\definecolor{warningcolor}{RGB}{255, 193, 7}
\definecolor{dangercolor}{RGB}{220, 53, 69}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{医疗智能助手测试报告}
\fancyhead[R]{\today}
\fancyfoot[C]{\thepage}

\titleformat{\section}
{\Large\bfseries\color{primarycolor}}
{\thesection}{1em}{}

\titleformat{\subsection}
{\large\bfseries\color{secondarycolor}}
{\thesubsection}{1em}{}

\begin{document}
"""

    def _generate_title_page(self) -> str:
        """生成标题页"""
        return r"""
\begin{titlepage}
\begin{tikzpicture}[remember picture,overlay]
\fill[primarycolor] (current page.north west) rectangle ([yshift=-3cm]current page.north east);
\end{tikzpicture}

\vspace*{1cm}

\begin{center}
{\Huge\bfseries\color{white} 医疗智能助手}\\[0.5cm]
{\Huge\bfseries\color{white} 综合测试报告}\\[2cm]

{\Large\color{primarycolor} 测试日期：""" + datetime.now().strftime("%Y年%m月%d日") + r"""}\\[0.5cm]
{\Large\color{primarycolor} 版本：v1.0}\\[2cm]

\begin{tikzpicture}
\node[draw=primarycolor, fill=secondarycolor!10, rounded corners, inner sep=10pt] {
\begin{tabular}{cc}
\textbf{总测试数：} & \textbf{""" + str(self.data.total_tests) + r"""} \\
\textbf{通过数：} & \textcolor{successcolor}{""" + str(self.data.passed_tests) + r"""} \\
\textbf{失败数：} & \textcolor{dangercolor}{""" + str(self.data.failed_tests) + r"""} \\
\textbf{通过率：} & \textbf{""" + f"{self.data.pass_rate:.1f}\\%" + r"""} \\
\end{tabular}
};
\end{tikzpicture}
\end{center}

\vfill

\begin{center}
{\small\color{gray} 自动化测试系统生成}
\end{center}
\end{titlepage}

\tableofcontents
\newpage
"""

    def _generate_summary_section(self) -> str:
        """生成汇总章节"""
        content = r"\section{测试概述}" + "\n\n"

        # 总体统计
        content += r"\subsection{总体统计}" + "\n\n"
        content += r"\begin{table}[H]" + "\n"
        content += r"\centering" + "\n"
        content += r"\begin{tabular}{|l|c|}" + "\n"
        content += r"\hline" + "\n"
        content += r"\textbf{指标} & \textbf{数值} \\" + "\n"
        content += r"\hline" + "\n"
        content += r"总测试数 & " + str(self.data.total_tests) + r" \\" + "\n"
        content += r"通过数 & \textcolor{successcolor}{" + str(self.data.passed_tests) + r"} \\" + "\n"
        content += r"失败数 & \textcolor{dangercolor}{" + str(self.data.failed_tests) + r"} \\" + "\n"
        content += r"通过率 & \textbf{" + f"{self.data.pass_rate:.1f}\%" + r"} \\" + "\n"
        content += r"\hline" + "\n"
        content += r"\end{tabular}" + "\n"
        content += r"\caption{总体测试统计}" + "\n"
        content += r"\end{table}" + "\n\n"

        # 概览图表
        if 'overview' in self.charts:
            content += r"\begin{figure}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\includegraphics[width=0.9\textwidth]{" + self.charts['overview'] + r"}" + "\n"
            content += r"\caption{测试概览}" + "\n"
            content += r"\end{figure}" + "\n\n"

        return content

    def _generate_skill_section(self) -> str:
        """生成Skill测试章节"""
        content = r"\section{Skill测试结果}" + "\n\n"

        # Skill性能图表
        if 'skill_performance' in self.charts:
            content += r"\begin{figure}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\includegraphics[width=0.95\textwidth]{" + self.charts['skill_performance'] + r"}" + "\n"
            content += r"\caption{Skill性能分析}" + "\n"
            content += r"\end{figure}" + "\n\n"

        # 各Skill详细结果
        for skill, stats in self.data.by_skill.items():
            content += r"\subsection{" + skill + r"}" + "\n\n"
            content += r"\begin{table}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\begin{tabular}{|l|c|c|}" + "\n"
            content += r"\hline" + "\n"
            content += r"\textbf{指标} & \textbf{数值} & \textbf{通过率} \\" + "\n"
            content += r"\hline" + "\n"
            passed = stats['passed']
            total = stats['total']
            rate = passed / total * 100 if total > 0 else 0
            content += r"总测试数 & " + str(total) + r" & - \\" + "\n"
            content += r"通过数 & \textcolor{successcolor}{" + str(passed) + r"} & \textcolor{successcolor}{" + f"{rate:.1f}\%" + r"} \\" + "\n"
            content += r"失败数 & \textcolor{dangercolor}{" + str(total - passed) + r"} & - \\" + "\n"
            content += r"\hline" + "\n"
            content += r"\end{tabular}" + "\n"
            content += r"\caption{" + skill + r" 测试统计}" + "\n"
            content += r"\end{table}" + "\n\n"

        return content

    def _generate_complexity_section(self) -> str:
        """生成复杂度分析章节"""
        content = r"\section{复杂度分析}" + "\n\n"

        # 复杂度分析图表
        if 'complexity_analysis' in self.charts:
            content += r"\begin{figure}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\includegraphics[width=0.9\textwidth]{" + self.charts['complexity_analysis'] + r"}" + "\n"
            content += r"\caption{复杂度分析}" + "\n"
            content += r"\end{figure}" + "\n\n"

        # 复杂度统计表
        content += r"\begin{table}[H]" + "\n"
        content += r"\centering" + "\n"
        content += r"\begin{tabular}{|l|c|c|c|}" + "\n"
        content += r"\hline" + "\n"
        content += r"\textbf{复杂度} & \textbf{总测试} & \textbf{通过} & \textbf{通过率} \\" + "\n"
        content += r"\hline" + "\n"

        for comp, stats in self.data.by_complexity.items():
            total = stats['total']
            passed = stats['passed']
            rate = passed / total * 100 if total > 0 else 0
            color = "successcolor" if rate >= 90 else "warningcolor" if rate >= 70 else "dangercolor"
            content += comp + r" & " + str(total) + r" & " + str(passed) + r" & \textcolor{" + color + r"}{" + f"{rate:.1f}\%" + r"} \\" + "\n"
            content += r"\hline" + "\n"

        content += r"\end{tabular}" + "\n"
        content += r"\caption{按复杂度统计}" + "\n"
        content += r"\end{table}" + "\n\n"

        return content

    def _generate_confidence_section(self) -> str:
        """生成置信度分析章节"""
        content = r"\section{意图识别分析}" + "\n\n"

        # 置信度分布图表
        if 'confidence_distribution' in self.charts:
            content += r"\begin{figure}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\includegraphics[width=0.9\textwidth]{" + self.charts['confidence_distribution'] + r"}" + "\n"
            content += r"\caption{置信度分布}" + "\n"
            content += r"\end{figure}" + "\n\n"

        # 置信度统计
        confidences = self.data.confidences
        if confidences:
            content += r"\begin{table}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\begin{tabular}{|l|c|}" + "\n"
            content += r"\hline" + "\n"
            content += r"\textbf{统计量} & \textbf{值} \\" + "\n"
            content += r"\hline" + "\n"
            content += r"平均值 & " + f"{np.mean(confidences):.3f} \\" + "\n"
            content += r"中位数 & " + f"{np.median(confidences):.3f} \\" + "\n"
            content += r"标准差 & " + f"{np.std(confidences):.3f} \\" + "\n"
            content += r"最小值 & " + f"{np.min(confidences):.3f} \\" + "\n"
            content += r"最大值 & " + f"{np.max(confidences):.3f} \\" + "\n"
            content += r"\hline" + "\n"
            content += r"\end{tabular}" + "\n"
            content += r"\caption{置信度统计}" + "\n"
            content += r"\end{table}" + "\n\n"

        return content

    def _generate_performance_section(self) -> str:
        """生成性能分析章节"""
        content = r"\section{性能分析}" + "\n\n"

        # 响应时间分析图表
        if 'response_time_analysis' in self.charts:
            content += r"\begin{figure}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\includegraphics[width=0.95\textwidth]{" + self.charts['response_time_analysis'] + r"}" + "\n"
            content += r"\caption{响应时间分析}" + "\n"
            content += r"\end{figure}" + "\n\n"

        # 性能统计数据
        response_times = [rt for rt in self.data.response_times if rt > 0]
        if response_times:
            content += r"\begin{table}[H]" + "\n"
            content += r"\centering" + "\n"
            content += r"\begin{tabular}{|l|c|}" + "\n"
            content += r"\hline" + "\n"
            content += r"\textbf{性能指标} & \textbf{值} \\" + "\n"
            content += r"\hline" + "\n"
            content += r"平均响应时间 & " + f"{np.mean(response_times):.2f} ms \\" + "\n"
            content += r"中位数响应时间 & " + f"{np.median(response_times):.2f} ms \\" + "\n"
            content += r"最小响应时间 & " + f"{np.min(response_times):.2f} ms \\" + "\n"
            content += r"最大响应时间 & " + f"{np.max(response_times):.2f} ms \\" + "\n"
            content += r"标准差 & " + f"{np.std(response_times):.2f} ms \\" + "\n"
            content += r"P95响应时间 & " + f"{np.percentile(response_times, 95):.2f} ms \\" + "\n"
            content += r"P99响应时间 & " + f"{np.percentile(response_times, 99):.2f} ms \\" + "\n"
            content += r"\hline" + "\n"
            content += r"\end{tabular}" + "\n"
            content += r"\caption{性能指标统计}" + "\n"
            content += r"\end{table}" + "\n\n"

        # MCP工具性能
        if self.data.performance_data:
            content += r"\subsection{MCP工具性能}" + "\n\n"
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
            content += r"\caption{MCP工具性能统计}" + "\n"
            content += r"\end{table}" + "\n\n"

        return content

    def _generate_test_cases_section(self) -> str:
        """生成测试用例章节"""
        content = r"\section{测试用例详情}" + "\n\n"

        # 按Skill分组
        for skill in self.data.by_skill.keys():
            content += r"\subsection{" + skill + r" 测试用例}" + "\n\n"
            content += r"\begin{longtable}{|p{2cm}|p{4cm}|p{2cm}|p{2cm}|p{1.5cm}|}" + "\n"
            content += r"\hline" + "\n"
            content += r"\textbf{复杂度} & \textbf{输入} & \textbf{预期Skill} & \textbf{置信度} & \textbf{结果} \\" + "\n"
            content += r"\hline" + "\n"
            content += r"\endhead" + "\n"
            content += r"\hline" + "\n"
            content += r"\endfoot" + "\n"

            for result in self.data.get_results_by_skill(skill):
                complexity = result.get('complexity', 'unknown')
                input_text = self._escape_latex(result.get('input_text', ''))[:50]
                expected = result.get('expected_skill', '')
                confidence = result.get('confidence', 0)
                passed = result.get('passed', False)
                status = r"\textcolor{successcolor}{PASS}" if passed else r"\textcolor{dangercolor}{FAIL}"

                content += complexity + r" & " + input_text + r" & " + expected + r" & " + f"{confidence:.2f}" + r" & " + status + r" \\" + "\n"
                content += r"\hline" + "\n"

            content += r"\end{longtable}" + "\n\n"

        return content

    def _generate_conclusion_section(self) -> str:
        """生成结论章节"""
        content = r"\section{测试结论}" + "\n\n"

        # 总体评估
        content += r"\subsection{总体评估}" + "\n\n"
        if self.data.pass_rate >= 95:
            content += r"本次测试结果为：\textcolor{successcolor}{\textbf{优秀}}。所有功能模块运行正常，系统稳定性良好。" + "\n\n"
        elif self.data.pass_rate >= 80:
            content += r"本次测试结果为：\textcolor{warningcolor}{\textbf{良好}}。大部分功能模块运行正常，存在少量需要优化的问题。" + "\n\n"
        else:
            content += r"本次测试结果为：\textcolor{dangercolor}{\textbf{需要改进}}。部分功能模块存在问题，需要进行修复和优化。" + "\n\n"

        # 详细结论
        content += r"\subsection{详细结论}" + "\n\n"
        content += r"\begin{itemize}" + "\n"

        # 功能测试结论
        functional_results = self.data.get_results_by_type('functional')
        if functional_results:
            functional_pass = sum(1 for r in functional_results if r.get('passed', False))
            functional_rate = functional_pass / len(functional_results) * 100
            content += r"    \item \textbf{功能测试}: " + str(functional_pass) + r"/" + str(len(functional_results)) + r" 通过 (" + f"{functional_rate:.1f}\%" + r")" + "\n"

        # 单元测试结论
        unit_results = self.data.get_results_by_type('unit')
        if unit_results:
            unit_pass = sum(1 for r in unit_results if r.get('passed', False))
            unit_rate = unit_pass / len(unit_results) * 100
            content += r"    \item \textbf{单元测试}: " + str(unit_pass) + r"/" + str(len(unit_results)) + r" 通过 (" + f"{unit_rate:.1f}\%" + r")" + "\n"

        # 流程测试结论
        flow_results = self.data.get_results_by_type('flow')
        if flow_results:
            flow_pass = sum(1 for r in flow_results if r.get('passed', False))
            flow_rate = flow_pass / len(flow_results) * 100
            content += r"    \item \textbf{流程测试}: " + str(flow_pass) + r"/" + str(len(flow_results)) + r" 通过 (" + f"{flow_rate:.1f}\%" + r")" + "\n"

        content += r"\end{itemize}" + "\n\n"

        return content

    def _generate_footer(self) -> str:
        """生成文档尾部"""
        return r"""
\end{document}
"""

    def generate_latex(self) -> str:
        """生成完整的LaTeX文档"""
        latex = self._generate_header()
        latex += self._generate_title_page()
        latex += self._generate_summary_section()
        latex += self._generate_skill_section()
        latex += self._generate_complexity_section()
        latex += self._generate_confidence_section()
        latex += self._generate_performance_section()
        latex += self._generate_test_cases_section()
        latex += self._generate_conclusion_section()
        latex += self._generate_footer()
        return latex

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
            # 尝试常见路径
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
            print("请安装TeX Live或MiKTeX，或手动编译LaTeX文件")
            return False

        print(f"使用pdflatex编译: {latex_cmd}")

        # 编译两次以确保引用正确
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
    print("医疗智能助手 - 测试报告生成器")
    print("="*80)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    charts_dir = os.path.join(output_dir, "charts")
    os.makedirs(charts_dir, exist_ok=True)

    # 加载数据
    print(f"\n加载测试数据: {json_file}")
    data = ReportData(json_file)

    # 生成图表
    chart_gen = ChartGenerator(charts_dir)
    charts = chart_gen.generate_all_charts(data)

    # 生成LaTeX报告
    print("\n生成LaTeX报告...")
    latex_gen = LatexReportGenerator(data, charts, output_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latex_path = os.path.join(output_dir, f"test_report_{timestamp}.tex")
    pdf_path = os.path.join(output_dir, f"test_report_{timestamp}.pdf")

    latex_gen.save_latex(latex_path)

    # 尝试编译PDF
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

    # 查找最新的测试结果文件
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    json_files = glob.glob(os.path.join(results_dir, "test_results_*.json"))

    if not json_files:
        print("错误: 未找到测试结果文件")
        print("请先运行 test_comprehensive.py")
        sys.exit(1)

    # 使用最新的结果文件
    latest_file = max(json_files, key=os.path.getmtime)
    print(f"使用测试结果: {latest_file}")

    output_dir = os.path.join(os.path.dirname(__file__), "reports")
    generate_report(latest_file, output_dir)
