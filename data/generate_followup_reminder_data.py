#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成随访和提醒数据
使用阿里云 qwen-plus 模型
"""

import json
import random
import os
from datetime import datetime, timedelta
import requests

API_KEY = "sk-a9a9a4edb1b4214016baa11c9be3b9fec4"
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "qwen-plus"

# 医生名单
DOCTORS = [
    "王伟", "李芳", "张强", "刘敏", "陈静",
    "杨洋", "赵军", "孙丽", "周杰", "吴婷",
    "郑涛", "冯雪", "于飞", "袁娜", "邓超"
]

# 疾病列表
DISEASES = ["高血压", "糖尿病", "冠心病"]

# 随访频率
FREQUENCIES = ["monthly", "weekly", "biweekly"]

# 随访项目类型
FOLLOWUP_ITEMS = [
    {"type": "blood_pressure", "name": "血压监测"},
    {"type": "blood_sugar", "name": "血糖监测"},
    {"type": "heart_rate", "name": "心率监测"},
    {"type": "medication", "name": "用药情况"},
    {"type": "diet", "name": "饮食记录"},
    {"type": "exercise", "name": "运动情况"},
    {"type": "symptom", "name": "症状记录"},
    {"type": "weight", "name": "体重监测"}
]

# 提醒类型
REMINDER_TYPES = ["medication", "measurement", "appointment"]

# 重复模式
REPEAT_PATTERNS = ["daily", "weekly", "monthly", "onetime"]

# 状态
STATUSES = ["active", "paused", "completed"]

# 症状列表
SYMPTOMS = [
    "头晕", "头痛", "乏力", "心悸", "胸闷",
    "多饮", "多尿", "多食", "视力模糊", "手脚麻木",
    "气短", "水肿", "失眠", "恶心", "背痛"
]

# 医生反馈模板
DOCTOR_FEEDBACKS = [
    "继续当前方案，保持良好生活习惯。",
    "血压控制良好，建议减少盐的摄入。",
    "血糖有所波动，请严格控制饮食。",
    "心率正常，建议适当增加有氧运动。",
    "用药依从性良好，继续坚持。",
    "症状改善明显，维持当前治疗。",
    "需要调整用药剂量，请按时复诊。",
    "各项指标稳定，继续保持。",
    "体重控制良好，建议继续监测。",
    "注意休息，避免过度劳累。",
    "血压偏高，建议增加服药频率。",
    "血糖控制不理想，需调整饮食结构。",
    "症状有所缓解，继续观察。",
    "按时服药，定期复查。",
    "建议每周增加监测频率。"
]

def call_qwen_api(system_prompt, user_prompt, temperature=0.7):
    """调用阿里云 qwen-plus API"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": 4000
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"API调用失败: {e}")
        return None

def generate_followup_plans():
    """生成随访计划数据"""
    print("正在生成随访计划数据...")

    prompt = f"""请生成20条随访计划数据，用于医疗随访管理系统。

要求：
1. plan_id格式: FP001-FP020
2. patient_id格式: P001-P020
3. disease从以下选择: {", ".join(DISEASES)}
4. start_date在2025年1月到3月之间
5. frequency从以下选择: {", ".join(FREQUENCIES)}
6. status从以下选择: {", ".join(STATUSES)}
7. items是数组，每个item包含type(从{", ".join([i["type"] for i in FOLLOWUP_ITEMS])}选择), name(对应的中文名称), frequency
8. assigned_doctor从以下选择: {", ".join(DOCTORS[:10])}

请严格按照以下JSON格式返回，不要包含任何其他说明文字：
{{
  "plans": [
    {{
      "plan_id": "FP001",
      "patient_id": "P001",
      "disease": "高血压",
      "start_date": "2025-01-15",
      "frequency": "weekly",
      "status": "active",
      "items": [
        {{"type": "blood_pressure", "name": "血压监测", "frequency": "weekly"}},
        {{"type": "medication", "name": "用药情况", "frequency": "monthly"}}
      ],
      "assigned_doctor": "王伟"
    }}
  ]
}}"""

    system_prompt = "你是一个医疗数据生成专家，专门生成符合规范的随访计划JSON数据。只返回JSON格式的数据，不要包含任何解释说明。"

    response = call_qwen_api(system_prompt, prompt, temperature=0.5)

    if response:
        try:
            # 清理可能的markdown代码块标记
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            data = json.loads(response)
            return data.get("plans", data)
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"响应内容: {response[:500]}")

    # API失败时使用本地生成
    return generate_followup_plans_local()

def generate_followup_plans_local():
    """本地生成随访计划"""
    plans = []
    for i in range(1, 21):
        plan_id = f"FP{i:03d}"
        patient_id = f"P{i:03d}"
        disease = random.choice(DISEASES)
        start_date = f"2025-{random.randint(1,3):02d}-{random.randint(1,28):02d}"
        frequency = random.choice(FREQUENCIES)
        status = random.choice(STATUSES)

        # 根据疾病选择合适的随访项目
        items = []
        if disease == "高血压":
            items.extend([
                {"type": "blood_pressure", "name": "血压监测", "frequency": "weekly"},
                {"type": "heart_rate", "name": "心率监测", "frequency": "weekly"},
                {"type": "medication", "name": "用药情况", "frequency": "monthly"}
            ])
        elif disease == "糖尿病":
            items.extend([
                {"type": "blood_sugar", "name": "血糖监测", "frequency": "daily"},
                {"type": "diet", "name": "饮食记录", "frequency": "weekly"},
                {"type": "medication", "name": "用药情况", "frequency": "monthly"}
            ])
        else:  # 冠心病
            items.extend([
                {"type": "blood_pressure", "name": "血压监测", "frequency": "weekly"},
                {"type": "heart_rate", "name": "心率监测", "frequency": "weekly"},
                {"type": "symptom", "name": "症状记录", "frequency": "weekly"}
            ])

        # 随机添加额外项目
        extra_items = [item for item in FOLLOWUP_ITEMS if item["type"] not in [i["type"] for i in items]]
        if extra_items and random.random() > 0.5:
            extra = random.choice(extra_items)
            items.append({"type": extra["type"], "name": extra["name"], "frequency": random.choice(FREQUENCIES)})

        plans.append({
            "plan_id": plan_id,
            "patient_id": patient_id,
            "disease": disease,
            "start_date": start_date,
            "frequency": frequency,
            "status": status,
            "items": items,
            "assigned_doctor": random.choice(DOCTORS)
        })

    return plans

def generate_followup_records(plans):
    """生成随访记录数据"""
    print("正在生成随访记录数据...")

    records = []
    record_id = 1

    # 每个计划生成2-3条记录
    for plan in plans:
        num_records = random.randint(2, 3)

        for i in range(num_records):
            patient_id = plan["patient_id"]
            disease = plan["disease"]

            # 生成随访日期
            base_date = datetime.strptime(plan["start_date"], "%Y-%m-%d")
            followup_date = base_date + timedelta(days=random.randint(7, 60))

            # 生成监测数据
            data = {}

            if disease == "高血压":
                data["blood_pressure"] = {
                    "systolic": random.randint(110, 160),
                    "diastolic": random.randint(65, 100)
                }
                data["heart_rate"] = random.randint(60, 95)
                data["medication_adherence"] = random.choice(["good", "fair", "poor"])

            elif disease == "糖尿病":
                data["blood_sugar"] = {
                    "fasting": random.uniform(4.5, 9.0),
                    "postprandial": random.uniform(6.5, 13.0)
                }
                data["medication_adherence"] = random.choice(["good", "fair", "poor"])
                data["diet_compliance"] = random.choice(["good", "fair", "poor"])

            else:  # 冠心病
                data["blood_pressure"] = {
                    "systolic": random.randint(110, 150),
                    "diastolic": random.randint(65, 95)
                }
                data["heart_rate"] = random.randint(55, 90)
                data["symptoms"] = random.sample(SYMPTOMS, k=random.randint(0, 3))

            # 添加通用症状
            if "symptoms" not in data:
                data["symptoms"] = random.sample(SYMPTOMS, k=random.randint(0, 2))

            records.append({
                "record_id": f"FR{record_id:03d}",
                "plan_id": plan["plan_id"],
                "patient_id": patient_id,
                "followup_date": followup_date.strftime("%Y-%m-%d"),
                "data": data,
                "doctor_feedback": random.choice(DOCTOR_FEEDBACKS)
            })
            record_id += 1

    # 补充到50条
    while len(records) < 50:
        patient_id = f"P{random.randint(1, 20):03d}"
        disease = random.choice(DISEASES)

        data = {}
        if disease == "高血压":
            data["blood_pressure"] = {
                "systolic": random.randint(110, 160),
                "diastolic": random.randint(65, 100)
            }
            data["heart_rate"] = random.randint(60, 95)
        elif disease == "糖尿病":
            data["blood_sugar"] = {
                "fasting": round(random.uniform(4.5, 9.0), 1),
                "postprandial": round(random.uniform(6.5, 13.0), 1)
            }
        else:
            data["blood_pressure"] = {
                "systolic": random.randint(110, 150),
                "diastolic": random.randint(65, 95)
            }
            data["heart_rate"] = random.randint(55, 90)

        data["symptoms"] = random.sample(SYMPTOMS, k=random.randint(0, 3))
        data["medication_adherence"] = random.choice(["good", "fair", "poor"])

        followup_date = datetime(2025, random.randint(1, 3), random.randint(1, 28))

        records.append({
            "record_id": f"FR{record_id:03d}",
            "plan_id": f"FP{random.randint(1, 20):03d}",
            "patient_id": patient_id,
            "followup_date": followup_date.strftime("%Y-%m-%d"),
            "data": data,
            "doctor_feedback": random.choice(DOCTOR_FEEDBACKS)
        })
        record_id += 1

    return records[:50]

def generate_reminders():
    """生成提醒服务数据"""
    print("正在生成提醒服务数据...")

    prompt = f"""请生成20条提醒服务数据，用于医疗提醒管理系统。

要求：
1. reminder_id格式: REM001-REM020
2. user_id格式: U001-U020
3. reminder_type从以下选择: {", ".join(REMINDER_TYPES)}
4. title是简短的提醒标题(10字以内)
5. content是详细的提醒内容(20-50字)
6. remind_time格式: HH:MM
7. repeat从以下选择: {", ".join(REPEAT_PATTERNS)}
8. status从以下选择: {", ".join(STATUSES)}

提醒类型对应的标题和内容建议：
- medication: 药物提醒，如"按时服用降压药"
- measurement: 测量提醒，如"测量血压并记录"
- appointment: 复诊提醒，如"医院复诊预约"

请严格按照以下JSON格式返回，不要包含任何其他说明文字：
{{
  "reminders": [
    {{
      "reminder_id": "REM001",
      "user_id": "U001",
      "reminder_type": "medication",
      "title": "服用降压药",
      "content": "请于早餐后服用1片降压药，不要漏服。",
      "remind_time": "08:00",
      "repeat": "daily",
      "status": "active"
    }}
  ]
}}"""

    system_prompt = "你是一个医疗数据生成专家，专门生成符合规范的提醒服务JSON数据。只返回JSON格式的数据，不要包含任何解释说明。"

    response = call_qwen_api(system_prompt, prompt, temperature=0.6)

    if response:
        try:
            # 清理可能的markdown代码块标记
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            data = json.loads(response)
            return data.get("reminders", data)
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"响应内容: {response[:500]}")

    # API失败时使用本地生成
    return generate_reminders_local()

def generate_reminders_local():
    """本地生成提醒服务"""
    reminders = []

    # 药物提醒
    medication_titles = [
        ("服用降压药", "请于早餐后服用1片降压药，不要漏服。"),
        ("服用降糖药", "请于餐前30分钟服用降糖药。"),
        ("服用阿司匹林", "请服用阿司匹林，预防血栓形成。"),
        ("服用他汀类药物", "睡前服用他汀类药物，调节血脂。"),
        ("服用硝酸甘油", "如出现胸闷症状，请含服硝酸甘油。"),
        ("胰岛素注射", "请按时注射胰岛素，注意剂量。"),
        ("服用利尿剂", "请于早晨服用利尿剂。"),
        ("服用钙通道阻滞剂", "请按时服用钙通道阻滞剂。")
    ]

    # 测量提醒
    measurement_titles = [
        ("测量血压", "请测量血压并记录收缩压和舒张压。"),
        ("测量血糖", "请测量空腹血糖并记录数值。"),
        ("测量餐后血糖", "请测量餐后2小时血糖。"),
        ("测量心率", "请静息5分钟后测量心率。"),
        ("测量体重", "请在清晨空腹时测量体重。"),
        ("记录症状", "请记录今日是否有不适症状。"),
        ("记录运动", "请记录今日运动情况。"),
        ("记录饮食", "请记录今日饮食情况。")
    ]

    # 复诊提醒
    appointment_titles = [
        ("心内科复诊", "请按时到心内科复诊，携带检查报告。"),
        ("内分泌科复诊", "请到内分泌科复查血糖和糖化血红蛋白。"),
        ("血压监测门诊", "请到高血压门诊复查。"),
        ("心电图检查", "请到医院做心电图检查。"),
        ("血液检查", "请空腹到医院做血液检查。"),
        ("眼底检查", "请到眼科做眼底检查。")
    ]

    all_reminders = []

    for i in range(8):
        reminder_type = "medication"
        title, content = medication_titles[i % len(medication_titles)]
        all_reminders.append((reminder_type, title, content))

    for i in range(8):
        reminder_type = "measurement"
        title, content = measurement_titles[i % len(measurement_titles)]
        all_reminders.append((reminder_type, title, content))

    for i in range(4):
        reminder_type = "appointment"
        title, content = appointment_titles[i % len(appointment_titles)]
        all_reminders.append((reminder_type, title, content))

    # 生成提醒数据
    for i, (r_type, title, content) in enumerate(all_reminders[:20]):
        hour = random.randint(6, 21)
        minute = random.choice([0, 15, 30, 45])

        reminders.append({
            "reminder_id": f"REM{i+1:03d}",
            "user_id": f"U{i+1:03d}",
            "reminder_type": r_type,
            "title": title,
            "content": content,
            "remind_time": f"{hour:02d}:{minute:02d}",
            "repeat": random.choice(REPEAT_PATTERNS),
            "status": random.choice(["active", "active", "active", "paused"])
        })

    return reminders

def main():
    """主函数"""
    # 确保目录存在
    os.makedirs("d:/Users/liu.liu/Desktop/github/medical/data/followup", exist_ok=True)
    os.makedirs("d:/Users/liu.liu/Desktop/github/medical/data/reminder", exist_ok=True)

    # 生成随访计划
    print("=" * 50)
    print("开始生成随访和提醒数据...")
    print("=" * 50)

    plans = generate_followup_plans()
    print(f"生成随访计划: {len(plans)} 条")

    # 生成随访记录
    records = generate_followup_records(plans)
    print(f"生成随访记录: {len(records)} 条")

    # 生成提醒服务
    reminders = generate_reminders()
    print(f"生成提醒服务: {len(reminders)} 条")

    # 保存数据
    plans_path = "d:/Users/liu.liu/Desktop/github/medical/data/followup/plans.json"
    records_path = "d:/Users/liu.liu/Desktop/github/medical/data/followup/records.json"
    reminders_path = "d:/Users/liu.liu/Desktop/github/medical/data/reminder/reminders.json"

    with open(plans_path, "w", encoding="utf-8") as f:
        json.dump(plans, f, ensure_ascii=False, indent=2)

    with open(records_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    with open(reminders_path, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print("数据生成完成！")
    print(f"- 随访计划: {plans_path}")
    print(f"- 随访记录: {records_path}")
    print(f"- 提醒服务: {reminders_path}")
    print("=" * 50)

if __name__ == "__main__":
    main()
