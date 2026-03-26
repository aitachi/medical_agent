# -*- coding: utf-8 -*-
"""
医学知识库生成器 - 生成症状和疾病数据
"""

import asyncio
import aiohttp
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# 设置控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置
API_KEY = "sk-a9a4edb1b4214016baa11c9be3b9fec4"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen-max"
DATA_DIR = Path("d:/Users/liu.liu/Desktop/github/medical/data")


class MedicalKnowledgeGenerator:
    """医学知识库生成器"""

    def __init__(self):
        self.session = None
        self.generated_count = 0
        self.error_count = 0

    async def start(self):
        """启动会话"""
        timeout = aiohttp.ClientTimeout(total=300)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def stop(self):
        """停止会话"""
        if self.session:
            await self.session.close()

    async def call_llm(self, prompt: str) -> Dict:
        """调用LLM生成数据"""
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        system_prompt = """你是专业的医学数据生成专家。请严格按照要求生成医学数据。

规则：
1. 所有医学数据必须准确、专业
2. ICD-10编码必须真实有效
3. 参考范围必须符合临床标准
4. 输出必须是纯JSON格式，不要有任何其他文字
5. 必须包含所有必填字段

输出格式：纯JSON，不要markdown格式。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 8000,
            "result_format": "message"
        }

        try:
            async with self.session.post(
                f"{BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"  API错误: {response.status}")
                    return None

                result = await response.json()
                content = result["choices"][0]["message"]["content"]

                # 清理markdown格式
                content = content.strip()
                if content.startswith("```"):
                    content = re.sub(r'```(?:json)?\n?', '', content)
                    content = re.sub(r'\n```$', '', content)

                data = json.loads(content)
                self.generated_count += 1
                return data

        except Exception as e:
            print(f"  生成错误: {e}")
            self.error_count += 1
            return None

    def save_json(self, data: Any, filepath: str):
        """保存JSON数据"""
        full_path = DATA_DIR / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  已保存到: {full_path}")

    async def generate_symptoms(self, count: int = 200):
        """生成症状知识数据"""
        print(f"\n{'='*60}")
        print(f"生成症状知识数据 ({count}条)")
        print('='*60)

        # 症状分类和具体症状列表
        symptom_templates = [
            # 全身症状 (20)
            ("全身症状", ["发热", "乏力", "水肿", "消瘦", "肥胖", "盗汗", "畏寒", "潮热", "全身不适", "淋巴结肿大"]),
            # 呼吸系统 (25)
            ("呼吸系统", ["咳嗽", "咳痰", "呼吸困难", "胸痛", "咯血", "喘息", "胸闷", "气短", "紫绀", "鼻塞", "流涕", "打鼾", "喉咙痛", "声音嘶哑", "咽异物感"]),
            # 心血管系统 (20)
            ("心血管系统", ["心悸", "胸闷", "胸痛", "晕厥", "水肿", "发绀", "血压升高", "血压降低", "心前区不适", "脉搏异常"]),
            # 消化系统 (30)
            ("消化系统", ["腹痛", "恶心", "呕吐", "腹泻", "便秘", "黄疸", "呕血", "黑便", "反酸", "烧心", "吞咽困难", "食欲不振", "腹胀", "肝区痛", "口苦"]),
            # 神经系统 (25)
            ("神经系统", ["头痛", "头晕", "失眠", "嗜睡", "抽搐", "意识障碍", "记忆力减退", "肢体麻木", "行走不稳", "震颤", "肌肉萎缩", "肌肉无力"]),
            # 内分泌代谢 (15)
            ("内分泌代谢", ["多饮", "多尿", "多食", "怕热", "畏寒", "毛发脱落", "毛发增多", "色素沉着"]),
            # 泌尿生殖 (20)
            ("泌尿生殖", ["尿频", "尿急", "尿痛", "血尿", "排尿困难", "尿失禁", "少尿", "多尿", "夜尿增多", "阴囊肿大"]),
            # 血液系统 (15)
            ("血液系统", ["贫血", "出血", "瘀斑", "紫癜", "淋巴结肿大", "脾肿大"]),
            # 运动系统 (20)
            ("运动系统", ["关节痛", "肌肉痛", "活动受限", "晨僵", "关节肿胀", "关节畸形", "背痛", "颈痛", "腰痛", "四肢痛"]),
            # 五官症状 (20)
            ("五官症状", ["视力模糊", "视力下降", "眼痛", "流泪", "听力下降", "耳鸣", "耳痛", "鼻出血", "嗅觉减退", "味觉异常"])
        ]

        all_symptoms = []
        symptom_id = 1

        for category, symptoms in symptom_templates:
            print(f"\n生成 {category} 类症状 ({len(symptoms)}个)...")

            for symptom_name in symptoms:
                print(f"  生成: {symptom_name}...", end="", flush=True)

                prompt = f"""为症状"{symptom_name}"({category}类)生成详细知识数据：

格式：
{{
  "id": "SYM{symptom_id:03d}",
  "name": "{symptom_name}",
  "aliases": ["别名1", "别名2"],
  "category": "{category}",
  "description": "症状描述(30-50字，专业准确)",
  "common_causes": ["原因1", "原因2", "原因3", "原因4", "原因5"],
  "red_flags": ["危险信号1", "危险信号2"],
  "recommended_department": "首选科室",
  "alternative_departments": ["备选科室1", "备选科室2"],
  "self_care": ["护理建议1", "护理建议2"],
  "severity_levels": {{
    "mild": "轻度描述",
    "moderate": "中度描述",
    "severe": "重度描述"
  }}
}}

请生成纯JSON格式。"""

                symptom_data = await self.call_llm(prompt)
                if symptom_data:
                    all_symptoms.append(symptom_data)
                    symptom_id += 1
                    print(" OK")
                else:
                    print(" 失败，尝试重试...")
                    # 重试一次
                    symptom_data = await self.call_llm(prompt)
                    if symptom_data:
                        all_symptoms.append(symptom_data)
                        symptom_id += 1
                        print("  重试成功")

        # 如果数量不够，补充更多症状
        while len(all_symptoms) < count:
            print(f"\n补充生成症状... ({len(all_symptoms)}/{count})")
            remaining = count - len(all_symptoms)
            batch_size = min(10, remaining)

            prompt = f"""生成{batch_size}条新的症状知识数据，要求与之前不同：

涵盖以下分类：
- 妇科症状：痛经、月经不调、白带异常、外阴瘙痒
- 儿科症状：夜啼、出牙不适、喂养困难
- 眼科症状：眼干、眼痒、畏光、复视
- 耳鼻喉：眩晕、鼻痒、咽部异物
- 皮肤：皮疹、瘙痒、脱发、多汗
- 精神：焦虑、抑郁、烦躁、淡漠

每条症状格式：
{{
  "id": "SYM{{ID:03d}}",
  "name": "症状名",
  "aliases": ["别名"],
  "category": "分类",
  "description": "描述",
  "common_causes": ["原因1", "原因2", "原因3", "原因4", "原因5"],
  "red_flags": ["危险信号"],
  "recommended_department": "科室",
  "alternative_departments": ["备选科室"],
  "self_care": ["建议"],
  "severity_levels": {{"mild": "...", "moderate": "...", "severe": "..."}}
}}

生成纯JSON数组。ID从{len(all_symptoms)+1}开始。"""

            batch = await self.call_llm(prompt)
            if batch and isinstance(batch, list):
                all_symptoms.extend(batch)
                print(f"  补充了 {len(batch)} 条")

        # 保存
        result = {"total": len(all_symptoms), "symptoms": all_symptoms}
        self.save_json(result, "knowledge/symptoms.json")
        return all_symptoms

    async def generate_diseases(self, count: int = 100):
        """生成疾病知识数据"""
        print(f"\n{'='*60}")
        print(f"生成疾病知识数据 ({count}条)")
        print('='*60)

        # 详细的疾病列表
        disease_list = [
            # 心血管 (15)
            ("高血压", "心血管", "I10"),
            ("冠心病", "心血管", "I25"),
            ("急性心肌梗死", "心血管", "I21"),
            ("心力衰竭", "心血管", "I50"),
            ("心律失常", "心血管", "I49"),
            ("风湿性心脏病", "心血管", "I05"),
            ("肺源性心脏病", "心血管", "I27"),
            ("感染性心内膜炎", "心血管", "I33"),
            ("心肌炎", "心血管", "I40"),
            ("心包炎", "心血管", "I31"),
            ("主动脉瓣狭窄", "心血管", "I35"),
            ("二尖瓣关闭不全", "心血管", "I34"),
            ("主动脉夹层", "心血管", "I71"),
            ("阵发性室上性心动过速", "心血管", "I47"),
            ("病态窦房结综合征", "心血管", "I49"),

            # 呼吸 (12)
            ("慢性阻塞性肺疾病", "呼吸", "J44"),
            ("肺炎", "呼吸", "J18"),
            ("支气管哮喘", "呼吸", "J45"),
            ("急性支气管炎", "呼吸", "J20"),
            ("慢性支气管炎", "呼吸", "J42"),
            ("肺栓塞", "呼吸", "I26"),
            ("肺结核", "呼吸", "A15"),
            ("胸膜炎", "呼吸", "I26"),
            ("气胸", "呼吸", "J93"),
            ("睡眠呼吸暂停综合征", "呼吸", "G47"),
            ("急性呼吸窘迫综合征", "呼吸", "J80"),
            ("支气管扩张", "呼吸", "J47"),

            # 消化 (15)
            ("急性胃炎", "消化", "K29"),
            ("慢性胃炎", "消化", "K29"),
            ("消化性溃疡", "消化", "K25"),
            ("胃食管反流病", "消化", "K21"),
            ("肝硬化", "消化", "K74"),
            ("急性胰腺炎", "消化", "K85"),
            ("慢性胰腺炎", "消化", "K86"),
            ("胆囊炎", "消化", "K80"),
            ("胆石症", "消化", "K80"),
            ("脂肪肝", "消化", "K76"),
            ("溃疡性结肠炎", "消化", "K51"),
            ("克罗恩病", "消化", "K50"),
            ("肠梗阻", "消化", "K56"),
            ("急性阑尾炎", "消化", "K35"),
            ("痔疮", "消化", "K64"),

            # 内分泌 (10)
            ("2型糖尿病", "内分泌", "E11"),
            ("1型糖尿病", "内分泌", "E10"),
            ("甲状腺功能亢进症", "内分泌", "E05"),
            ("甲状腺功能减退症", "内分泌", "E03"),
            ("痛风", "内分泌", "M10"),
            ("骨质疏松症", "内分泌", "M80"),
            ("库欣综合征", "内分泌", "E24"),
            ("原发性醛固酮增多症", "内分泌", "E26"),
            ("嗜铬细胞瘤", "内分泌", "D35"),
            ("甲状旁腺功能亢进症", "内分泌", "E21"),

            # 神经 (12)
            ("脑梗死", "神经", "I63"),
            ("脑出血", "神经", "I61"),
            ("短暂性脑缺血发作", "神经", "G45"),
            ("偏头痛", "神经", "G43"),
            ("紧张性头痛", "神经", "G44"),
            ("帕金森病", "神经", "G20"),
            ("癫痫", "神经", "G40"),
            ("阿尔茨海默病", "神经", "G30"),
            ("面神经炎", "神经", "G51"),
            ("三叉神经痛", "神经", "G50"),
            ("重症肌无力", "神经", "G70"),
            ("吉兰-巴雷综合征", "神经", "G61"),

            # 泌尿 (8)
            ("肾结石", "泌尿", "N20"),
            ("输尿管结石", "泌尿", "N20"),
            ("膀胱炎", "泌尿", "N30"),
            ("肾盂肾炎", "泌尿", "N10"),
            ("前列腺增生", "泌尿", "N40"),
            ("前列腺炎", "泌尿", "N41"),
            ("慢性肾炎", "泌尿", "N03"),
            ("肾病综合征", "泌尿", "N04"),

            # 血液 (6)
            ("缺铁性贫血", "血液", "D50"),
            ("巨幼细胞性贫血", "血液", "D53"),
            ("再生障碍性贫血", "血液", "D61"),
            ("急性白血病", "血液", "C91"),
            ("慢性白血病", "血液", "C92"),
            ("淋巴瘤", "血液", "C81"),

            # 风湿 (8)
            ("类风湿关节炎", "风湿", "M05"),
            ("系统性红斑狼疮", "风湿", "M32"),
            ("强直性脊柱炎", "风湿", "M45"),
            ("干燥综合征", "风湿", "M35"),
            ("皮肌炎", "风湿", "M33"),
            ("系统性硬化症", "风湿", "M34"),
            ("骨关节炎", "风湿", "M15"),
            ("银屑病关节炎", "风湿", "M07"),

            # 感染 (4)
            ("流行性感冒", "感染", "J11"),
            ("病毒性肝炎", "感染", "B15"),
            ("细菌性肺炎", "感染", "J15"),
            ("尿路感染", "感染", "N39")
        ]

        all_diseases = []
        disease_id = 1

        for disease_name, category, icd_code in disease_list[:count]:
            print(f"生成: {disease_name} ({category})...", end="", flush=True)

            prompt = f"""为疾病"{disease_name}"({category}类，ICD-10编码: {icd_code})生成完整知识数据：

格式：
{{
  "id": "DIS{disease_id:03d}",
  "name": "{disease_name}",
  "aliases": ["别名"],
  "icd_code": "{icd_code}",
  "category": "{category}",
  "description": "疾病描述(50字内，专业准确)",
  "diagnostic_criteria": {{
    "definite": "确诊标准(具体、专业)",
    "suspected": "疑诊标准"
  }},
  "symptoms": {{
    "typical": ["典型症状1", "典型症状2", "典型症状3"],
    "atypical": ["不典型症状1", "不典型症状2"],
    "complications": ["并发症1", "并发症2", "并发症3"]
  }},
  "treatment": {{
    "medication": ["具体药物名称1+用法", "具体药物名称2+用法"],
    "lifestyle": ["生活方式干预1", "生活方式干预2", "生活方式干预3"]
  }},
  "prevention": {{
    "primary": ["一级预防措施1", "一级预防措施2"],
    "secondary": ["二级预防措施1", "二级预防措施2"]
  }}
}}

请生成纯JSON格式，确保医学准确性。"""

            disease_data = await self.call_llm(prompt)
            if disease_data:
                all_diseases.append(disease_data)
                disease_id += 1
                print(" OK")
            else:
                print(" 失败，重试...")
                disease_data = await self.call_llm(prompt)
                if disease_data:
                    all_diseases.append(disease_data)
                    disease_id += 1
                    print("  重试成功")

        # 保存
        result = {"total": len(all_diseases), "diseases": all_diseases}
        self.save_json(result, "knowledge/diseases.json")
        return all_diseases


async def main():
    """主函数"""
    generator = MedicalKnowledgeGenerator()
    await generator.start()

    try:
        print("\n" + "="*60)
        print("医学知识库生成器 - 使用Qwen-Max")
        print("="*60)

        # 1. 生成症状数据
        symptoms = await generator.generate_symptoms(200)
        print(f"\n症状数据生成完成: {len(symptoms)} 条")

        # 2. 生成疾病数据
        diseases = await generator.generate_diseases(100)
        print(f"\n疾病数据生成完成: {len(diseases)} 条")

        # 摘要
        print(f"\n{'='*60}")
        print("[生成摘要]")
        print('='*60)
        print(f"成功调用: {generator.generated_count} 次")
        print(f"失败次数: {generator.error_count} 次")
        if generator.generated_count + generator.error_count > 0:
            success_rate = generator.generated_count / (generator.generated_count + generator.error_count) * 100
            print(f"成功率: {success_rate:.1f}%")
        print('='*60)

    finally:
        await generator.stop()


if __name__ == "__main__":
    asyncio.run(main())
