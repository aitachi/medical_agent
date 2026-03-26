# -*- coding: utf-8 -*-
"""
数据整理脚本 - 裁剪超过50条的数据，生成不足50条的数据
"""
import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
import sys

# Windows控制台UTF-8支持
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

API_KEY = "sk-a9a4edb1b4214016baa11c9be3b9fec4"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen-plus"
DATA_DIR = Path("d:/Users/liu.liu/Desktop/github/medical/data")


def trim_file(filepath: str, key: str, target_count: int):
    """裁剪文件到指定数量"""
    full_path = DATA_DIR / filepath
    with open(full_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if key in data:
        items = data[key]
    else:
        items = data if isinstance(data, list) else []

    original_count = len(items)
    if original_count > target_count:
        trimmed = items[:target_count]
        if isinstance(data, dict):
            data[key] = trimmed
            if 'total' in data:
                data['total'] = target_count
        else:
            data = trimmed

        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ {filepath}: {original_count} → {target_count}")
    else:
        print(f"- {filepath}: {original_count} (无需裁剪)")


async def generate_data(prompt: str, count: int) -> list:
    """使用API生成数据"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = """你是专业的医学数据生成专家。请严格按照要求生成数据。
输出必须是纯JSON数组格式，不要有任何其他文字，不要使用markdown代码块。
每个条目必须包含所有必需字段。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 8000
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    print(f"  API错误: {response.status}")
                    return None

                result = await response.json()
                content = result["choices"][0]["message"]["content"]

                # 清理内容
                content = content.strip()
                if content.startswith("```"):
                    import re
                    content = re.sub(r'```(?:json)?\n?', '', content)
                    content = re.sub(r'\n```$', '', content)

                data = json.loads(content)
                return data if isinstance(data, list) else [data]
    except Exception as e:
        print(f"  生成错误: {str(e)[:100]}")
        return None


def append_to_file(filepath: str, new_items: list, key: str = "items"):
    """追加数据到文件"""
    full_path = DATA_DIR / filepath
    full_path.parent.mkdir(parents=True, exist_ok=True)

    if full_path.exists():
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            existing_items = data.get(key, []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    else:
        existing_items = []

    existing_items.extend(new_items)

    # 保存
    output_data = {key: existing_items, "total": len(existing_items)} if key else existing_items
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✓ {filepath}: {len(existing_items)}条")


async def main():
    print("="*60)
    print("数据整理 - 裁剪超量数据并补充不足数据")
    print("="*60)

    # 第一步：裁剪超过50条的文件
    print("\n[步骤1] 裁剪超过50条的文件:")
    print("-"*40)

    trim_file("knowledge/symptoms.json", "symptoms", 50)
    trim_file("departments/doctors.json", "items", 50)

    # 第二步：补充不足50条的文件
    print("\n[步骤2] 补充不足50条的文件:")
    print("-"*40)

    # 读取现有数据以确定需要生成多少
    needs = {}

    # 科室数据 (20 -> 50)
    with open(DATA_DIR / "departments/departments.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        needs['departments'] = 50 - len(data)

    # 检验项目 (30 -> 50)
    with open(DATA_DIR / "lab/lab_items.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        needs['lab'] = 50 - len(data)

    # 急救指南 (15 -> 50)
    with open(DATA_DIR / "emergency/guides.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        needs['emergency'] = 50 - len(data)

    # 病理报告 (20 -> 50)
    with open(DATA_DIR / "pathology/reports.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        needs['pathology'] = 50 - len(data)

    # 患者 (30 -> 50)
    with open(DATA_DIR / "patients/patients.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        needs['patients'] = 50 - len(data)

    # 体检套餐 (1 -> 50)
    with open(DATA_DIR / "checkup/packages.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        needs['checkup'] = 50 - len(data)

    # 随访计划 (20 -> 50)
    with open(DATA_DIR / "followup/plans.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        needs['followup_plans'] = 50 - len(data)

    # 提醒 (20 -> 50)
    with open(DATA_DIR / "reminder/reminders.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        needs['reminder'] = 50 - len(data)

    # 问诊医生 (20 -> 50)
    with open(DATA_DIR / "consult/doctors.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        needs['consult_doctors'] = 50 - len(data)

    # 问诊记录 (30 -> 50)
    with open(DATA_DIR / "consult/records.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        needs['consult_records'] = 50 - len(data)

    # 生成科室数据
    if needs['departments'] > 0:
        print(f"\n生成科室数据 (+{needs['departments']}条)...")
        prompt = f"""生成{needs['departments']}个医院科室，格式：
[
  {{
    "dept_id": "DEPTxxx",
    "name": "科室名称",
    "category": "内科/外科/妇儿/五官/其他",
    "description": "科室简介",
    "location": "楼层位置",
    "doctors_count": 数字
  }}
]
生成{needs['departments']}个不同的科室。"""

        items = await generate_data(prompt, needs['departments'])
        if items:
            # 追加到现有文件
            with open(DATA_DIR / "departments/departments.json", 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing.extend(items)
            with open(DATA_DIR / "departments/departments.json", 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            print(f"  科室: {len(existing)}条")

    # 生成检验项目
    if needs['lab'] > 0:
        print(f"\n生成检验项目 (+{needs['lab']}条)...")
        prompt = f"""生成{needs['lab']}个医学检验项目，包括血常规、生化、凝血、免疫等类别，格式：
[
  {{
    "item_id": "LABxxx",
    "name": "项目名称",
    "category": "类别",
    "specimen": "标本类型",
    "reference_range": "参考范围",
    "clinical_significance": "临床意义"
  }}
]
生成{needs['lab']}个不同的检验项目。"""

        items = await generate_data(prompt, needs['lab'])
        if items:
            with open(DATA_DIR / "lab/lab_items.json", 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing.extend(items)
            with open(DATA_DIR / "lab/lab_items.json", 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            print(f"  检验项目: {len(existing)}条")

    # 生成急救指南
    if needs['emergency'] > 0:
        print(f"\n生成急救指南 (+{needs['emergency']}条)...")
        prompt = f"""生成{needs['emergency']}个急救指南，涵盖各种急症和意外，格式：
[
  {{
    "id": "EMGxxx",
    "name": "急症名称",
    "level": "E/A/B/C",
    "detection": ["识别要点"],
    "actions": [{{"step": 1, "action": "操作"}}],
    "dont": ["禁忌"],
    "equipment": ["所需设备"]
  }}
]
生成{needs['emergency']}个不同的急救指南。"""

        items = await generate_data(prompt, needs['emergency'])
        if items:
            with open(DATA_DIR / "emergency/guides.json", 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing.extend(items)
            with open(DATA_DIR / "emergency/guides.json", 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            print(f"  急救指南: {len(existing)}条")

    # 生成病理报告
    if needs['pathology'] > 0:
        print(f"\n生成病理报告 (+{needs['pathology']}条)...")
        prompt = f"""生成{needs['pathology']}份病理报告，包括细胞学和组织学检查，格式：
[
  {{
    "report_id": "PATHxxx",
    "patient_id": "Pxxxxx",
    "specimen_type": "标本类型",
    "collection_date": "2025-xx-xx",
    "result": {{
      "category": "类别",
      "description": "描述",
      "diagnosis": "诊断意见"
    }},
    "pathologist": "签发医生"
  }}
]
生成{needs['pathology']}份不同的病理报告。"""

        items = await generate_data(prompt, needs['pathology'])
        if items:
            with open(DATA_DIR / "pathology/reports.json", 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing.extend(items)
            with open(DATA_DIR / "pathology/reports.json", 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            print(f"  病理报告: {len(existing)}条")

    # 生成患者数据
    if needs['patients'] > 0:
        print(f"\n生成患者数据 (+{needs['patients']}条)...")
        prompt = f"""生成{needs['patients']}个患者数据，格式：
[
  {{
    "patient_id": "Pxxxxx",
    "name": "姓名",
    "gender": "男/女",
    "age": 数字,
    "phone": "手机号",
    "id_card": "身份证号",
    "address": "地址",
    "emergency_contact": {{
      "name": "联系人",
      "phone": "电话",
      "relationship": "关系"
    }},
    "blood_type": "血型",
    "allergies": ["过敏史"],
    "register_date": "2025-xx-xx"
  }}
]
生成{needs['patients']}个不同的患者。"""

        items = await generate_data(prompt, needs['patients'])
        if items:
            with open(DATA_DIR / "patients/patients.json", 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing.extend(items)
            with open(DATA_DIR / "patients/patients.json", 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            print(f"  患者: {len(existing)}条")

    # 生成体检套餐
    if needs['checkup'] > 0:
        print(f"\n生成体检套餐 (+{needs['checkup']}条)...")
        prompt = f"""生成{needs['checkup']}个体检套餐，包括基础套餐、针对性套餐等，格式：
[
  {{
    "package_id": "PKGxxx",
    "name": "套餐名称",
    "category": "基础/ comprehensive/专项/高端",
    "price": 价格,
    "items": ["检查项目1", "检查项目2"],
    "suitable_for": "适用人群",
    "precautions": "注意事项"
  }}
]
生成{needs['checkup']}个不同的体检套餐。"""

        items = await generate_data(prompt, needs['checkup'])
        if items:
            with open(DATA_DIR / "checkup/packages.json", 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing.extend(items)
            with open(DATA_DIR / "checkup/packages.json", 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            print(f"  体检套餐: {len(existing)}条")

    # 生成随访计划
    if needs['followup_plans'] > 0:
        print(f"\n生成随访计划 (+{needs['followup_plans']}条)...")
        prompt = f"""生成{needs['followup_plans']}个随访计划，用于慢性病管理，格式：
[
  {{
    "plan_id": "FPxxx",
    "name": "计划名称",
    "target_condition": "目标疾病",
    "duration_days": 数字,
    "followup_frequency": "频率",
    "tasks": [
      {{
        "task_id": "FTxxx",
        "name": "任务名称",
        "type": "问卷/测量/检查/用药",
        "frequency": "频率"
      }}
    ],
    "reminders": ["提醒内容"]
  }}
]
生成{needs['followup_plans']}个不同的随访计划。"""

        items = await generate_data(prompt, needs['followup_plans'])
        if items:
            with open(DATA_DIR / "followup/plans.json", 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing.extend(items)
            with open(DATA_DIR / "followup/plans.json", 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            print(f"  随访计划: {len(existing)}条")

    # 生成提醒
    if needs['reminder'] > 0:
        print(f"\n生成提醒数据 (+{needs['reminder']}条)...")
        prompt = f"""生成{needs['reminder']}个医疗提醒，包括用药提醒、复诊提醒等，格式：
[
  {{
    "reminder_id": "REMxxx",
    "type": "用药/复诊/检查/生活方式",
    "title": "标题",
    "content": "内容",
    "frequency": "频率",
    "time": "时间",
    "priority": "high/medium/low"
  }}
]
生成{needs['reminder']}个不同的提醒。"""

        items = await generate_data(prompt, needs['reminder'])
        if items:
            with open(DATA_DIR / "reminder/reminders.json", 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing.extend(items)
            with open(DATA_DIR / "reminder/reminders.json", 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            print(f"  提醒: {len(existing)}条")

    # 生成问诊医生
    if needs['consult_doctors'] > 0:
        print(f"\n生成问诊医生 (+{needs['consult_doctors']}条)...")
        prompt = f"""生成{needs['consult_doctors']}个在线问诊医生，格式：
[
  {{
    "doctor_id": "CDxxx",
    "name": "姓名",
    "gender": "男/女",
    "department": "科室",
    "title": "职称",
    "specialty": "专科",
    "experience_years": 数字,
    "rating": 4.0-5.0,
    "consultation_fee": 价格,
    "available_times": ["时间段"],
    "intro": "简介"
  }}
]
生成{needs['consult_doctors']}个不同的医生。"""

        items = await generate_data(prompt, needs['consult_doctors'])
        if items:
            with open(DATA_DIR / "consult/doctors.json", 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing.extend(items)
            with open(DATA_DIR / "consult/doctors.json", 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            print(f"  问诊医生: {len(existing)}条")

    # 生成问诊记录
    if needs['consult_records'] > 0:
        print(f"\n生成问诊记录 (+{needs['consult_records']}条)...")
        prompt = f"""生成{needs['consult_records']}个在线问诊记录，格式：
[
  {{
    "record_id": "CRxxx",
    "patient_id": "Pxxxxx",
    "doctor_id": "CDxxx",
    "type": "图文/视频/电话",
    "status": "completed",
    "chief_complaint": "主诉",
    "symptoms": ["症状"],
    "diagnosis": "诊断",
    "prescription": ["建议"],
    "create_time": "2025-xx-xx xx:xx",
    "duration_minutes": 数字
  }}
]
生成{needs['consult_records']}个不同的问诊记录。"""

        items = await generate_data(prompt, needs['consult_records'])
        if items:
            with open(DATA_DIR / "consult/records.json", 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing.extend(items)
            with open(DATA_DIR / "consult/records.json", 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            print(f"  问诊记录: {len(existing)}条")

    print("\n" + "="*60)
    print("数据整理完成!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
