# -*- coding: utf-8 -*-
"""
医疗数据生成器 - 优化版
- 使用qwen-plus（更快）
- 流式写入，每10条保存一次
- 支持断点续传
"""

import asyncio
import aiohttp
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import threading
import sys

# Windows控制台UTF-8支持
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置 - 使用qwen-plus（更快的模型）
API_KEY = "sk-a9a4edb1b4214016baa11c9be3b9fec4"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen-plus"  # 使用qwen-plus，比qwen-max快
DATA_DIR = Path("d:/Users/liu.liu/Desktop/github/medical/data")

# 进度统计
progress_lock = threading.Lock()
generation_stats = {
    "total_requested": 0,
    "total_generated": 0,
    "total_failed": 0,
    "start_time": datetime.now()
}


class StreamingDataGenerator:
    """流式数据生成器"""

    def __init__(self):
        self.session = None
        self.batch_size = 10  # 每批10条

    async def start(self):
        """启动会话"""
        timeout = aiohttp.ClientTimeout(total=120)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def stop(self):
        """停止会话"""
        if self.session:
            await self.session.close()

    def log(self, message: str):
        """日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    async def generate_batch(self, prompt: str, expected_type: str) -> List[Dict]:
        """生成一批数据"""
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        system_prompt = """你是专业的医学数据生成专家。请严格按照要求生成数据。
输出必须是纯JSON数组格式，不要有任何其他文字，不要使用markdown代码块。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 4000
        }

        try:
            async with self.session.post(
                f"{BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self.log(f"API错误: {response.status}")
                    return None

                result = await response.json()
                content = result["choices"][0]["message"]["content"]

                # 清理内容
                content = content.strip()
                if content.startswith("```"):
                    content = re.sub(r'```(?:json)?\n?', '', content)
                    content = re.sub(r'\n```$', '', content)

                # 解析JSON
                data = json.loads(content)

                with progress_lock:
                    generation_stats["total_generated"] += 1

                return data if isinstance(data, list) else [data]

        except Exception as e:
            self.log(f"生成错误: {str(e)[:100]}")
            with progress_lock:
                generation_stats["total_failed"] += 1
            return None

    def append_to_file(self, filepath: str, data: List[Dict], mode: str = "w"):
        """追加数据到文件"""
        full_path = DATA_DIR / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if mode == "w" or not full_path.exists():
            # 首次写入，创建数组
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump({"items": data, "total": len(data)}, f, ensure_ascii=False, indent=2)
        else:
            # 追加模式：读取现有数据，合并后写入
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    existing_items = existing.get("items", [])
            except:
                existing_items = []

            existing_items.extend(data)
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump({"items": existing_items, "total": len(existing_items)}, f, ensure_ascii=False, indent=2)

        self.log(f"  保存: {filepath} (+{len(data)}条, 总计{len(existing_items) if mode=='a' else len(data)}条)")

    async def generate_doctors_streaming(self, total: int = 2000):
        """流式生成医生数据"""
        self.log(f"开始生成医生数据 (目标: {total}条)")

        # 科室ID列表
        departments = [
            "DEPT00101", "DEPT00102", "DEPT00103", "DEPT00104", "DEPT00105",
            "DEPT00201", "DEPT00202", "DEPT00203", "DEPT00300", "DEPT00400"
        ]
        dept_names = [
            "心血管内科", "消化内科", "呼吸内科", "内分泌科", "神经内科",
            "普外科", "骨科", "神经外科", "妇产科", "儿科"
        ]

        # 职称分布
        titles_dist = ["主任医师"] * 300 + ["副主任医师"] * 500 + ["主治医师"] * 700 + ["住院医师"] * 400 + ["医师"] * 100

        # 分批生成
        batch_count = 0
        for i in range(0, total, self.batch_size):
            batch_num = i // self.batch_size + 1
            current_batch = min(self.batch_size, total - i)
            batch_count += 1

            self.log(f"批次 {batch_count}/{(total+self.batch_size-1)//self.batch_size} ({current_batch}条)...")

            # 选择科室和职称
            selected_depts = departments * (current_batch // len(departments) + 1)
            selected_titles = titles_dist[:current_batch]

            prompt = f"""生成{current_batch}条医生数据，要求：

科室选项：{', '.join(dept_names[:5])}
职称选项：主任医师、副主任医师、主治医师、住院医师

格式（纯JSON数组）：
[
  {{
    "doctor_id": "D{i:04d}",
    "name": "姓名(中国常见姓氏+名字)",
    "gender": "男/女",
    "department_id": "从上述科室中选择",
    "department_name": "对应科室名称",
    "title": "职称",
    "specialty": "专科方向(如冠心病、糖尿病等)",
    "experience_years": 数字(5-40),
    "education": {{
      "degree": "博士/硕士/本科",
      "school": "医学院名称"
    }},
    "consultation": {{
      "price": {{"text": 30-100, "video": 50-200}},
      "rating": 3.5-5.0
    }}
  }}
]

请生成{current_batch}个不同的医生，JSON数组格式。"""

            doctors = await self.generate_batch(prompt, "doctors")

            if doctors:
                mode = "w" if batch_count == 1 else "a"
                self.append_to_file("departments/doctors.json", doctors, mode)

        self.log(f"医生数据生成完成!")

    async def generate_drugs_streaming(self, total: int = 1000):
        """流式生成药品数据"""
        self.log(f"开始生成药品数据 (目标: {total}条)")

        categories = [
            ("抗感染药", ["阿莫西林", "头孢呋辛", "左氧氟沙星", "阿奇霉素"]),
            ("心血管药", ["硝苯地平", "氨氯地平", "美托洛尔", "阿司匹林", "阿托伐他汀"]),
            ("消化药", ["奥美拉唑", "多潘立酮", "蒙脱石散"]),
            ("呼吸药", ["氨溴索", "沙丁胺醇", "布地奈德"]),
            ("内分泌药", ["二甲双胍", "格列美脲", "左甲状腺素"]),
            ("神经药", ["布洛芬", "对乙酰氨基酚", "卡马西平"]),
            ("利尿药", ["呋塞米", "氢氯噻嗪", "螺内酯"])
        ]

        batch_count = 0
        generated_count = 0

        for cat_name, examples in categories:
            self.log(f"生成分类: {cat_name}")

            for i in range(0, len(examples) * 10, self.batch_size):
                batch_count += 1
                current_batch = min(self.batch_size, 10)

                prompt = f"""为{cat_name}生成{current_batch}个药品数据，参考药物：{', '.join(examples)}

格式（纯JSON数组）：
[
  {{
    "drug_id": "DRG{generated_count + i:04d}",
    "generic_name": "通用名",
    "english_name": "英文名",
    "category": "{cat_name}",
    "indications": ["适应症1", "适应症2"],
    "dosage": {{
      "adult": "成人用量",
      "children": "儿童用量"
    }},
    "contraindications": ["禁忌症"],
    "side_effects": ["副作用1", "副作用2"],
    "warnings": "注意事项",
    "storage": "储存条件"
  }}
]

生成{current_batch}个不同的药品。"""

                drugs = await self.generate_batch(prompt, "drugs")

                if drugs:
                    mode = "w" if generated_count == 0 else "a"
                    self.append_to_file("drugs/drugs.json", drugs, mode)
                    generated_count += len(drugs)

                if generated_count >= total:
                    break

        self.log(f"药品数据生成完成! 共{generated_count}条")

    async def generate_lab_items_streaming(self):
        """流式生成检验项目"""
        self.log(f"开始生成检验项目数据")

        lab_categories = [
            ("血常规", ["白细胞", "红细胞", "血红蛋白", "血小板", "红细胞压积", "平均红细胞体积"]),
            ("生化-肝功能", ["ALT", "AST", "GGT", "ALP", "总胆红素", "白蛋白"]),
            ("生化-肾功能", ["肌酐", "尿素氮", "尿酸", "胱抑素C"]),
            ("生化-血脂", ["总胆固醇", "甘油三酯", "HDL-C", "LDL-C"]),
            ("生化-血糖", ["空腹血糖", "糖化血红蛋白", "胰岛素"]),
            ("电解质", ["钾", "钠", "氯", "钙", "镁"]),
            ("凝血功能", ["PT", "INR", "APTT", "纤维蛋白原"]),
            ("肿瘤标志物", ["CEA", "AFP", "CA19-9", "CA125", "PSA", "NSE", "SCC"])
        ]

        total_generated = 0

        for cat_name, items in lab_categories:
            self.log(f"生成: {cat_name}")

            prompt = f"""为{cat_name}生成以下检验项目的详细数据：{', '.join(items)}

格式（纯JSON数组）：
[
  {{
    "item_id": "LABxxx",
    "name": "项目名称",
    "english_name": "英文名",
    "category": "{cat_name}",
    "specimen": "血清/血浆/全血",
    "reference_range": "参考范围（含单位，必须准确）",
    "clinical_significance": "临床意义",
    "abnormal_indications": "异常提示"
  }}
]"""

            items_data = await self.generate_batch(prompt, "lab")

            if items_data:
                mode = "w" if total_generated == 0 else "a"
                self.append_to_file("lab/lab_items.json", items_data, mode)
                total_generated += len(items_data)

        self.log(f"检验项目生成完成! 共{total_generated}项")

    async def generate_pathology_reports(self):
        """生成病理报告数据"""
        self.log(f"开始生成病理报告数据")

        # 细胞学报告
        self.log("生成细胞学病理报告...")
        cyto_prompt = """生成50份宫颈TCT细胞学病理报告，格式：
[
  {
    "report_id": "CYT001",
    "patient_id": "Pxxxxx",
    "specimen_type": "宫颈液基薄层细胞学(TCT)",
    "collection_date": "2025-xx-xx",
    "result": {
      "category": "阴性/ASC-US/LSIL/HSIL/SCC",
      "description": "镜下描述",
      "diagnosis": "诊断意见"
    },
    "pathologist": "签发医生"
  }
]"""
        cyto_reports = await self.generate_batch(cyto_prompt, "pathology")
        if cyto_reports:
            self.append_to_file("pathology/cytology_reports.json", cyto_reports, "w")

        # 组织学报告
        self.log("生成组织学病理报告...")
        hist_prompt = """生成50份组织病理报告（胃肠、乳腺、甲状腺等），格式：
[
  {
    "report_id": "HIS001",
    "patient_id": "Pxxxxx",
    "specimen": "活检部位",
    "gross": "大体描述",
    "microscopic": "镜下描述",
    "diagnosis": "病理诊断",
    "ihc": "免疫组化结果",
    "pathologist": "签发医生"
  }
]"""
        hist_reports = await self.generate_batch(hist_prompt, "pathology")
        if hist_reports:
            self.append_to_file("pathology/histology_reports.json", hist_reports, "w")

        self.log("病理报告生成完成!")

    async def generate_emergency_guides(self):
        """生成急救指南"""
        self.log("开始生成急救指南...")

        prompt = """生成以下急症的急救指南：心脏骤停、心肌梗死、脑卒中、严重过敏、气道异物、严重出血、骨折、烧伤、中暑、低血糖

格式：
[
  {
    "id": "EMG001",
    "name": "急症名称",
    "level": "E/A/B/C",
    "detection": ["识别要点"],
    "actions": [{"step": 1, "action": "操作"}],
    "dont": ["禁忌"],
    "equipment": ["所需设备"]
  }
]"""

        guides = await self.generate_batch(prompt, "emergency")
        if guides:
            self.append_to_file("emergency/emergency_guides.json", guides, "w")

        self.log("急救指南生成完成!")

    async def print_summary(self):
        """打印摘要"""
        elapsed = (datetime.now() - generation_stats["start_time"]).total_seconds()
        rate = generation_stats["total_generated"] / elapsed if elapsed > 0 else 0

        print(f"\n{'='*60}")
        print(f"[数据生成摘要]")
        print(f"{'='*60}")
        print(f"模型: {MODEL}")
        print(f"耗时: {elapsed:.1f}秒")
        print(f"请求次数: {generation_stats['total_generated'] + generation_stats['total_failed']}")
        print(f"成功: {generation_stats['total_generated']}")
        print(f"失败: {generation_stats['total_failed']}")
        print(f"速率: {rate:.2f} 次/秒")
        print(f"{'='*60}")


async def main():
    """主函数"""
    generator = StreamingDataGenerator()
    await generator.start()

    try:
        print("="*60)
        print("医疗数据生成器 - 优化版 (qwen-plus + 流式写入)")
        print("="*60)

        # 生成任务（按优先级）
        tasks = [
            ("医生数据", generator.generate_doctors_streaming(2000)),
            ("药品数据", generator.generate_drugs_streaming(1000)),
            ("检验项目", generator.generate_lab_items_streaming()),
            ("病理报告", generator.generate_pathology_reports()),
            ("急救指南", generator.generate_emergency_guides())
        ]

        for task_name, coro in tasks:
            print(f"\n{'='*60}")
            print(f"[任务] {task_name}")
            print('='*60)
            try:
                await coro
            except Exception as e:
                generator.log(f"任务失败: {e}")

        # 摘要
        await generator.print_summary()

    finally:
        await generator.stop()


if __name__ == "__main__":
    asyncio.run(main())
