# -*- coding: utf-8 -*-
"""
医疗数据生成器 - 使用Qwen-Max生成高质量医学数据
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

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置
API_KEY = "sk-a9a4edb1b4214016baa11c9be3b9fec4"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen-max"
DATA_DIR = Path("d:/Users/liu.liu/Desktop/github/medical/data")


class MedicalDataGenerator:
    """医学数据生成器"""

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

    async def generate_with_llm(self, prompt: str, schema: Dict) -> Dict:
        """使用LLM生成数据"""
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        system_prompt = f"""你是专业的医学数据生成专家。请严格按照要求生成医学数据。

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
            "temperature": 0.3,  # 降低温度确保准确性
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
                    print(f"API错误: {response.status} - {error_text}")
                    return None

                result = await response.json()
                content = result["choices"][0]["message"]["content"]

                # 清理markdown格式
                content = content.strip()
                if content.startswith("```"):
                    content = re.sub(r'```(?:json)?\n?', '', content)
                    content = re.sub(r'\n```$', '', content)

                # 解析JSON
                try:
                    data = json.loads(content)
                    self.generated_count += 1
                    return data
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误: {e}")
                    print(f"原始内容: {content[:500]}")
                    self.error_count += 1
                    return None

        except Exception as e:
            print(f"生成错误: {e}")
            self.error_count += 1
            return None

    def save_json(self, data: Any, filepath: str):
        """保存JSON数据"""
        full_path = DATA_DIR / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"已保存: {full_path}")

    async def generate_symptoms(self, count: int = 200):
        """生成症状知识数据"""
        print(f"\n{'='*60}")
        print(f"生成症状知识数据 ({count}条)")
        print('='*60)

        # 分批生成，每次50条
        batch_size = 50
        all_symptoms = []

        categories = [
            "全身症状:发热,乏力,水肿,消瘦,肥胖",
            "呼吸系统:咳嗽,咳痰,呼吸困难,胸痛,咯血",
            "心血管系统:心悸,胸闷,水肿,晕厥,发绀",
            "消化系统:腹痛,恶心,呕吐,腹泻,便秘,黄疸",
            "神经系统:头痛,头晕,失眠,抽搐,意识障碍",
            "内分泌代谢:多饮,多尿,多食,怕热,畏寒",
            "泌尿生殖:尿频,尿急,尿痛,血尿,排尿困难",
            "血液系统:贫血,出血,淋巴结肿大",
            "运动系统:关节痛,肌肉痛,活动受限",
            "五官症状:视力模糊,听力下降,鼻塞,咽痛"
        ]

        for i in range(0, count, batch_size):
            batch_num = i // batch_size + 1
            total_batches = (count + batch_size - 1) // batch_size
            current_count = min(batch_size, count - i)

            print(f"生成第 {batch_num}/{total_batches} 批 ({current_count}条)...")

            prompt = f"""请生成{current_count}条症状知识数据，要求：

症状分类列表：{categories[i//20] if i//20 < len(categories) else '其他'}

每条症状必须包含：
{{
  "id": "SYM{i+1:03d}",
  "name": "症状名称",
  "aliases": ["别名1", "别名2"],
  "category": "症状分类",
  "description": "症状描述(30-50字)",
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

请生成纯JSON数组格式，不要有其他文字。"""

            symptoms = await self.generate_with_llm(prompt, {})
            if symptoms and isinstance(symptoms, list):
                all_symptoms.extend(symptoms)
                print(f"  ✓ 已生成 {len(symptoms)} 条")
            else:
                print(f"  ✗ 生成失败")

        # 保存
        self.save_json({"total": len(all_symptoms), "symptoms": all_symptoms},
                      "knowledge/symptoms.json")
        return all_symptoms

    async def generate_diseases(self, count: int = 100):
        """生成疾病知识数据"""
        print(f"\n{'='*60}")
        print(f"生成疾病知识数据 ({count}条)")
        print('='*60)

        # 常见疾病列表
        disease_categories = {
            "心血管": ["高血压", "冠心病", "心律失常", "心力衰竭", "心肌梗死"],
            "呼吸": ["慢性阻塞性肺病", "肺炎", "哮喘", "支气管炎", "肺栓塞"],
            "消化": ["胃炎", "消化性溃疡", "肝硬化", "急性胰腺炎", "胆囊炎"],
            "内分泌": ["2型糖尿病", "甲状腺功能亢进", "痛风", "骨质疏松症"],
            "神经": ["脑卒中", "偏头痛", "帕金森病", "癫痫", "阿尔茨海默病"],
            "泌尿": ["肾结石", "尿路感染", "前列腺增生", "慢性肾炎"],
            "血液": ["贫血", "白血病", "淋巴瘤", "过敏性紫癜"],
            "风湿": ["类风湿关节炎", "系统性红斑狼疮", "强直性脊柱炎"]
        }

        all_diseases = []

        for category, diseases in disease_categories.items():
            for disease in diseases:
                print(f"生成: {disease}...")

                prompt = f"""请为"{disease}"({category}类)生成完整的疾病知识数据：

必须包含：
{{
  "id": "DISxxx",
  "name": "{disease}",
  "aliases": ["别名"],
  "icd_code": "ICD-10编码",
  "category": "{category}",
  "description": "疾病描述(50字内)",
  "diagnostic_criteria": {{
    "definite": "确诊标准",
    "suspected": "疑诊标准"
  }},
  "symptoms": {{
    "typical": ["典型症状"],
    "atypical": ["不典型症状"],
    "complications": ["并发症"]
  }},
  "treatment": {{
    "medication": ["用药方案"],
    "lifestyle": ["生活方式干预"]
  }},
  "prevention": {{
    "primary": ["一级预防"],
    "secondary": ["二级预防"]
  }}
}}

请生成纯JSON格式。"""

                disease_data = await self.generate_with_llm(prompt, {})
                if disease_data:
                    all_diseases.append(disease_data)
                    print(f"  ✓ 完成")

        # 保存
        self.save_json({"total": len(all_diseases), "diseases": all_diseases},
                      "knowledge/diseases.json")
        return all_diseases

    async def generate_departments_and_doctors(self):
        """生成科室和医生数据"""
        print(f"\n{'='*60}")
        print(f"生成科室和医生数据")
        print('='*60)

        # 科室数据
        departments_prompt = """生成完整的医院科室结构数据，包含：

{{
  "departments": [
    {{
      "id": "DEPT001",
      "name": "科室名称",
      "level": "1=一级,2=二级,3=三级",
      "category": "临床/医技",
      "parent_id": "上级科室ID",
      "description": "科室介绍",
      "common_symptoms": ["症状1", "症状2", "..."],
      "sub_departments": ["亚专科1", "亚专科2"]
    }}
  ]
}}

要求：
1. 至少150个科室
2. 包含内科系统所有专科(心内、消化、呼吸、内分泌、神经、肾内、血液、风湿免疫)
3. 包含外科系统(普外、骨科、神外、胸外、心外、泌尿外)
4. 包含妇产、儿科、急诊、重症、麻醉等
5. 包含医技科室(检验、放射、超声、病理、药剂)

生成纯JSON数组。"""

        departments = await self.generate_with_llm(departments_prompt, {})
        self.save_json(departments, "departments/departments.json")

        # 医生数据（生成500条示例）
        print(f"\n生成医生数据...")
        doctors_prompt = f"""生成500条医生数据示例，科室使用上述科室中的ID：

每条必须包含：
{{
  "doctor_id": "Dxxx",
  "name": "医生姓名",
  "gender": "男/女",
  "department_id": "科室ID",
  "title": "主任医师/副主任医师/主治医师/住院医师",
  "specialty": "专科方向",
  "experience_years": 数字,
  "education": {{
    "degree": "学位",
    "school": "毕业院校"
  }},
  "consultation": {{
    "types": ["text", "video"],
    "price": {{"text": 价格, "video": 价格}},
    "rating": 评分
  }}
}}

按以下比例生成：主任医师15%、副主任医师25%、主治医师35%、住院医师25%

生成纯JSON数组。"""

        doctors = await self.generate_with_llm(doctors_prompt, {})
        self.save_json(doctors, "departments/doctors.json")

        return departments, doctors

    async def generate_drugs(self, count: int = 1000):
        """生成药品数据（分批生成）"""
        print(f"\n{'='*60}")
        print(f"生成药品数据 ({count}条)")
        print('='*60)

        all_drugs = []
        drug_categories = [
            ("抗感染药", ["抗生素", "抗病毒药", "抗真菌药"]),
            ("心血管药", ["降压药", "抗心绞痛", "抗心律失常", "降脂药"]),
            ("消化系统药", ["抑酸药", "胃肠动力药", "肝胆药"]),
            ("呼吸系统药", ["祛痰药", "平喘药", "止咳药"]),
            ("内分泌药", ["降糖药", "甲状腺药", "激素类"]),
            ("神经系统药", ["镇痛药", "抗癫痫", "镇静催眠"]),
            ("血液系统药", ["止血药", "抗凝药", "促造血药"])
        ]

        for category, subcats in drug_categories:
            for subcat in subcats[:2]:  # 每个子类别取2个
                print(f"  生成 {category}-{subcat}...")

                prompt = f"""生成50个{subcat}的药品数据，格式：

[{{
  "drug_id": "DRGxxx",
  "generic_name": "通用名",
  "english_name": "英文名",
  "category": "{category}",
  "sub_category": "{subcat}",
  "indications": ["适应症1", "适应症2"],
  "dosage": {{
    "adult": "成人用量",
    "children": "儿童用量"
  }},
  "contraindications": ["禁忌症"],
  "side_effects": ["副作用1", "副作用2"],
  "warnings": "注意事项",
  "storage": "储存条件"
}}]

生成纯JSON数组。"""

                drugs = await self.generate_with_llm(prompt, {})
                if drugs and isinstance(drugs, list):
                    all_drugs.extend(drugs)

        self.save_json({"total": len(all_drugs), "drugs": all_drugs},
                      "drugs/drugs.json")
        return all_drugs

    async def generate_lab_items(self):
        """生成检验项目数据"""
        print(f"\n{'='*60}")
        print(f"生成检验项目数据")
        print('='*60)

        lab_categories = [
            ("血常规", ["白细胞", "红细胞", "血红蛋白", "血小板", "红细胞压积",
                       "平均红细胞体积", "平均血红蛋白量", "红细胞分布宽度"]),
            ("生化-肝功能", ["ALT", "AST", "GGT", "ALP", "总胆红素", "直接胆红素",
                        "白蛋白", "球蛋白", "白球比"]),
            ("生化-肾功能", ["肌酐", "尿素氮", "尿酸", "胱抑素C", "β2微球蛋白"]),
            ("生化-血脂", ["总胆固醇", "甘油三酯", "HDL-C", "LDL-C", "载脂蛋白A1",
                        "载脂蛋白B"]),
            ("生化-血糖", ["空腹血糖", "餐后血糖", "糖化血红蛋白", "胰岛素", "C肽"]),
            ("电解质", ["钾", "钠", "氯", "钙", "磷", "镁", "二氧化碳结合力"]),
            ("凝血功能", ["PT", "INR", "APTT", "TT", "纤维蛋白原"]),
            ("肿瘤标志物", ["CEA", "AFP", "CA19-9", "CA125", "CA15-3", "PSA", "NSE",
                        "SCC", "CYFRA21-1", "HE4"]),
            ("甲状腺功能", ["TSH", "FT3", "FT4", "T3", "T4", "TPOAb", "TGAb", "TRAb"])
        ]

        all_items = []

        for category, items in lab_categories:
            print(f"  生成 {category} ({len(items)}项)...")

            item_list = []
            for item in items:
                item_list.append(f'"{item}"')

            prompt = f"""为以下检验项目生成详细数据，每个项目包含：
检验项目列表：{', '.join(item_list)}

格式：
[{{
  "item_id": "LABxxx",
  "name": "项目名称",
  "english_name": "英文名",
  "category": "{category}",
  "specimen": "标本类型(血清/血浆/全血)",
  "reference_range": "参考范围(含单位)",
  "clinical_significance": "临床意义",
  "abnormal_indications": "异常提示"
}}]

生成纯JSON数组，参考范围必须准确！"""

            items_data = await self.generate_with_llm(prompt, {})
            if items_data and isinstance(items_data, list):
                all_items.extend(items_data)

        self.save_json({"total": len(all_items), "lab_items": all_items},
                      "lab/lab_items.json")
        return all_items

    async def generate_emergency_guides(self):
        """生成急救指南"""
        print(f"\n{'='*60}")
        print(f"生成急救指南数据")
        print('='*60)

        emergency_types = [
            "心脏骤停", "心肌梗死", "脑卒中", "严重过敏反应",
            "气道异物梗阻", "严重出血", "骨折", "烧伤",
            "中暑", "低血糖", "中毒", "触电", "溺水",
            "蛇咬伤", "癫痫发作", "休克"
        ]

        prompt = f"""为以下急症生成急救指南数据，每个包含：

急症列表：{', '.join(emergency_types)}

格式：
[{{
  "id": "EMGxxx",
  "name": "急症名称",
  "level": "E=紧急/A=严重/B=一般/C=轻微",
  "detection": ["识别要点1", "识别要点2"],
  "immediate_actions": [
    {{"step": 1, "action": "操作", "details": "详情"}},
    {{"step": 2, "action": "操作", "details": "详情"}}
  ],
  "dont": ["禁忌1", "禁忌2"],
  "equipment": ["所需设备"],
  "call_emergency": "是否需要120"
}}]

生成纯JSON数组。"""

        guides = await self.generate_with_llm(prompt, {})
        self.save_json(guides, "emergency/emergency_guides.json")
        return guides

    async def generate_checkup_packages(self):
        """生成体检套餐"""
        print(f"\n{'='*60}")
        print(f"生成体检套餐数据")
        print('='*60)

        prompt = """生成体检套餐数据，包含4个档次：

1. 基础套餐(299元) - 青年人基础体检
2. 标准套餐(699元) - 中年人全面体检
3. 高端套餐(1599元) - 50岁以上或高危人群
4. VIP套餐(3999元) - 最高端全面体检

每个套餐必须包含：
- 套餐ID、名称、价格、适用人群
- 详细检查项目列表（含科室、项目、参考范围、意义）
- 注意事项

格式：
{{
  "packages": [
    {{
      "id": "PKGxxx",
      "name": "套餐名称",
      "price": 价格,
      "suitable_for": "适用人群",
      "duration": "检查时长",
      "items": [
        {{"category": "科室", "tests": ["项目1", "项目2"]}},
        ...
      ],
      "notice": ["注意事项"]
    }}
  ]
}}

生成纯JSON。"""

        packages = await self.generate_with_llm(prompt, {})
        self.save_json(packages, "checkup/checkup_packages.json")
        return packages

    async def generate_summary(self):
        """生成摘要报告"""
        print(f"\n{'='*60}")
        print(f"[数据生成摘要]")
        print('='*60)
        print(f"生成成功: {self.generated_count} 次")
        print(f"生成失败: {self.error_count} 次")
        print(f"成功率: {self.generated_count/(self.generated_count+self.error_count)*100:.1f}%")
        print('='*60)


async def main():
    """主函数"""
    generator = MedicalDataGenerator()
    await generator.start()

    try:
        # 按优先级生成数据
        print("\n" + "="*60)
        print("医疗数据生成器 - 使用Qwen-Max")
        print("="*60)

        # 1. 医学知识库
        await generator.generate_symptoms(200)
        await generator.generate_diseases(100)

        # 2. 科室医生
        await generator.generate_departments_and_doctors()

        # 3. 药品数据
        await generator.generate_drugs(500)

        # 4. 检验项目
        await generator.generate_lab_items()

        # 5. 急救指南
        await generator.generate_emergency_guides()

        # 6. 体检套餐
        await generator.generate_checkup_packages()

        # 摘要
        await generator.generate_summary()

    finally:
        await generator.stop()


if __name__ == "__main__":
    asyncio.run(main())
