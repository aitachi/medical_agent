#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成50条症状知识数据
使用阿里云 qwen-plus 模型
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Any
import re

# API 配置
API_KEY = "sk-a9a4edb1b4214016baa11c9be3b9fec4"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen-plus"

# 症状分类和具体症状
SYMPTOM_CATEGORIES = [
    {"category": "全身症状", "symptoms": ["发热", "乏力", "水肿", "消瘦", "肥胖"]},
    {"category": "呼吸系统", "symptoms": ["咳嗽", "咳痰", "呼吸困难", "胸痛", "咯血"]},
    {"category": "心血管系统", "symptoms": ["心悸", "胸闷", "水肿", "晕厥", "发绀"]},
    {"category": "消化系统", "symptoms": ["腹痛", "恶心", "呕吐", "腹泻", "便秘", "黄疸"]},
    {"category": "神经系统", "symptoms": ["头痛", "头晕", "失眠", "抽搐", "意识障碍"]},
    {"category": "内分泌代谢", "symptoms": ["多饮", "多尿", "多食", "怕热", "畏寒"]},
    {"category": "泌尿生殖", "symptoms": ["尿频", "尿急", "尿痛", "血尿", "排尿困难"]},
    {"category": "血液系统", "symptoms": ["贫血", "出血", "淋巴结肿大"]},
    {"category": "运动系统", "symptoms": ["关节痛", "肌肉痛", "活动受限"]},
    {"category": "五官症状", "symptoms": ["视力模糊", "听力下降", "鼻塞", "咽痛", "眼痛"]},
]

# 生成所有症状列表
ALL_SYMPTOMS = []
symptom_id = 1
for cat_data in SYMPTOM_CATEGORIES:
    for symptom_name in cat_data["symptoms"]:
        ALL_SYMPTOMS.append({
            "id": f"SYM{symptom_id:03d}",
            "name": symptom_name,
            "category": cat_data["category"]
        })
        symptom_id += 1

print(f"总计需要生成 {len(ALL_SYMPTOMS)} 条症状数据")

# JSON 模板
JSON_TEMPLATE = """```json
{{
  "id": "{id}",
  "name": "{name}",
  "aliases": ["别名1", "别名2"],
  "category": "{category}",
  "description": "症状描述",
  "common_causes": ["原因1", "原因2", "原因3"],
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
```"""

# 一次性生成所有症状的prompt
GENERATE_ALL_PROMPT = """你是一位医学专家，请为以下50条症状生成详细的医学知识数据。

请严格按照以下JSON格式生成，每条症状一个独立的JSON对象，最后将所有对象放在一个JSON数组中：

```json
[
  {{
    "id": "SYM001",
    "name": "症状名称",
    "aliases": ["别名1", "别名2"],
    "category": "症状分类",
    "description": "详细的症状描述，包括症状表现、特征等",
    "common_causes": ["常见原因1", "常见原因2", "常见原因3"],
    "red_flags": ["危险信号1（需要立即就医的情况）", "危险信号2"],
    "recommended_department": "首选就诊科室",
    "alternative_departments": ["备选科室1", "备选科室2"],
    "self_care": ["自我护理建议1", "自我护理建议2"],
    "severity_levels": {{
      "mild": "轻度症状的具体描述",
      "moderate": "中度症状的具体描述",
      "severe": "重度症状的具体描述"
    }}
  }}
]
```

请为以下50条症状生成数据：

**全身症状（5条）**
1. 发热 - SYM001
2. 乏力 - SYM002
3. 水肿 - SYM003
4. 消瘦 - SYM004
5. 肥胖 - SYM005

**呼吸系统（5条）**
6. 咳嗽 - SYM006
7. 咳痰 - SYM007
8. 呼吸困难 - SYM008
9. 胸痛 - SYM009
10. 咯血 - SYM010

**心血管系统（5条）**
11. 心悸 - SYM011
12. 胸闷 - SYM012
13. 水肿 - SYM013（心血管相关，与全身水肿有所区别）
14. 晕厥 - SYM014
15. 发绀 - SYM015

**消化系统（6条）**
16. 腹痛 - SYM016
17. 恶心 - SYM017
18. 呕吐 - SYM018
19. 腹泻 - SYM019
20. 便秘 - SYM020
21. 黄疸 - SYM021

**神经系统（5条）**
22. 头痛 - SYM022
23. 头晕 - SYM023
24. 失眠 - SYM024
25. 抽搐 - SYM025
26. 意识障碍 - SYM026

**内分泌代谢（5条）**
27. 多饮 - SYM027
28. 多尿 - SYM028
29. 多食 - SYM029
30. 怕热 - SYM030
31. 畏寒 - SYM031

**泌尿生殖（5条）**
32. 尿频 - SYM032
33. 尿急 - SYM033
34. 尿痛 - SYM034
35. 血尿 - SYM035
36. 排尿困难 - SYM036

**血液系统（3条）**
37. 贫血 - SYM037
38. 出血 - SYM038
39. 淋巴结肿大 - SYM039

**运动系统（3条）**
40. 关节痛 - SYM040
41. 肌肉痛 - SYM041
42. 活动受限 - SYM042

**五官症状（5条）**
43. 视力模糊 - SYM043
44. 听力下降 - SYM044
45. 鼻塞 - SYM045
46. 咽痛 - SYM046
47. 眼痛 - SYM047
48. 流涕 - SYM048
49. 声音嘶哑 - SYM049
50. 耳鸣 - SYM050

注意事项：
1. 请确保所有50条症状都生成完整
2. 每条症状的医学信息要准确、专业
3. aliases字段至少包含1个常见别名
4. common_causes至少包含3个常见原因
5. red_flags至少包含2个需要警惕的危险信号
6. severity_levels要清晰描述轻中重度的区别
7. recommended_department要准确推荐首选科室
8. 返回完整的JSON数组，不要使用markdown代码块包裹

请直接返回JSON数组，不要添加任何解释文字："""


async def call_qwen_api(session: aiohttp.ClientSession, prompt: str) -> str:
    """调用阿里云 qwen-plus API"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是一位专业的医学专家，擅长生成结构化的医学知识数据。请严格按照指定的JSON格式返回数据，确保数据完整、准确、专业。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 16000
    }

    async with session.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload) as response:
        result = await response.json()
        return result["choices"][0]["message"]["content"]


def extract_json_from_response(response: str) -> str:
    """从响应中提取JSON内容"""
    # 移除可能的markdown代码块标记
    response = response.strip()

    # 尝试直接解析
    if response.startswith("["):
        return response

    # 移除 ```json 和 ``` 标记
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.rfind("```")
        if end > start:
            return response[start:end].strip()

    if "```" in response:
        start = response.find("```") + 3
        end = response.rfind("```")
        if end > start:
            content = response[start:end].strip()
            if content.startswith("json"):
                content = content[4:].strip()
            return content

    # 查找第一个 [ 和最后一个 ]
    start = response.find("[")
    end = response.rfind("]")
    if start != -1 and end != -1 and end > start:
        return response[start:end + 1]

    return response


def validate_symptom(symptom: Dict[str, Any]) -> tuple[bool, List[str]]:
    """验证症状数据的完整性"""
    errors = []
    required_fields = ["id", "name", "category", "description", "common_causes",
                      "red_flags", "recommended_department", "self_care", "severity_levels"]

    for field in required_fields:
        if field not in symptom:
            errors.append(f"缺少必填字段: {field}")
        elif not symptom[field] and symptom[field] != 0:
            errors.append(f"字段为空: {field}")

    # 检查数组字段
    if "common_causes" in symptom and len(symptom.get("common_causes", [])) < 2:
        errors.append(f"common_causes 至少需要2个原因")

    if "red_flags" in symptom and len(symptom.get("red_flags", [])) < 1:
        errors.append(f"red_flags 至少需要1个危险信号")

    # 检查 severity_levels
    if "severity_levels" in symptom:
        severity = symptom["severity_levels"]
        for level in ["mild", "moderate", "severe"]:
            if level not in severity or not severity[level]:
                errors.append(f"severity_levels.{level} 不能为空")

    return len(errors) == 0, errors


def validate_all_symptoms(symptoms: List[Dict]) -> tuple[bool, List[Dict]]:
    """验证所有症状数据"""
    results = []

    for i, symptom in enumerate(symptoms):
        is_valid, errors = validate_symptom(symptom)
        results.append({
            "index": i,
            "id": symptom.get("id", "UNKNOWN"),
            "name": symptom.get("name", "UNKNOWN"),
            "valid": is_valid,
            "errors": errors
        })

    all_valid = all(r["valid"] for r in results)
    return all_valid, results


async def generate_symptoms():
    """生成症状数据"""
    print("=" * 60)
    print("开始生成50条症状知识数据")
    print("=" * 60)
    print(f"API: {BASE_URL}")
    print(f"模型: {MODEL}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    async with aiohttp.ClientSession() as session:
        # 一次性生成所有症状
        print("正在调用API生成50条症状数据...")

        try:
            response = await call_qwen_api(session, GENERATE_ALL_PROMPT)
            print(f"API响应长度: {len(response)} 字符")

            # 提取JSON
            json_str = extract_json_from_response(response)
            print(f"提取JSON长度: {len(json_str)} 字符")

            # 解析JSON
            symptoms = json.loads(json_str)
            print(f"解析成功，共 {len(symptoms)} 条症状")

        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"原始响应: {response[:500]}...")
            return False
        except Exception as e:
            print(f"生成错误: {e}")
            return False

    # 验证数据质量
    print("\n" + "=" * 60)
    print("数据质量检查")
    print("=" * 60)

    all_valid, validation_results = validate_all_symptoms(symptoms)

    # 每10条显示一次检查结果
    for i in range(0, len(validation_results), 10):
        chunk = validation_results[i:i+10]
        print(f"\n第 {i+1}-{min(i+10, len(validation_results))} 条:")
        for r in chunk:
            status = "✓" if r["valid"] else "✗"
            print(f"  {status} {r['id']} - {r['name']}")
            if not r["valid"]:
                for err in r["errors"]:
                    print(f"      错误: {err}")

    # 统计
    total = len(symptoms)
    valid_count = sum(1 for r in validation_results if r["valid"])
    completion_rate = (valid_count / total * 100) if total > 0 else 0

    print(f"\n总计: {total} 条")
    print(f"有效: {valid_count} 条")
    print(f"完成率: {completion_rate:.1f}%")

    if not all_valid:
        print("\n发现错误，尝试修复...")

        # 尝试修复缺失字段
        for symptom in symptoms:
            # 确保有id
            if "id" not in symptom:
                symptom["id"] = f"SYM{symptoms.index(symptom)+1:03d}"

            # 确保有name
            if "name" not in symptom:
                symptom["name"] = "未知症状"

            # 确保有category
            if "category" not in symptom:
                symptom["category"] = "未分类"

            # 确保有description
            if not symptom.get("description"):
                symptom["description"] = f"{symptom['name']}的医学描述"

            # 确保有common_causes
            if not symptom.get("common_causes"):
                symptom["common_causes"] = ["待补充"]

            # 确保有red_flags
            if not symptom.get("red_flags"):
                symptom["red_flags"] = ["症状持续加重", "伴有其他严重症状"]

            # 确保有recommended_department
            if not symptom.get("recommended_department"):
                symptom["recommended_department"] = "内科"

            # 确保有self_care
            if not symptom.get("self_care"):
                symptom["self_care"] = ["注意休息", "密切观察"]

            # 确保有severity_levels
            if not symptom.get("severity_levels"):
                symptom["severity_levels"] = {
                    "mild": "症状轻微，不影响日常生活",
                    "moderate": "症状明显，部分影响日常生活",
                    "severe": "症状严重，严重影响日常生活"
                }

            # 确保有alternative_departments
            if "alternative_departments" not in symptom:
                symptom["alternative_departments"] = []

        # 重新验证
        all_valid, validation_results = validate_all_symptoms(symptoms)
        valid_count = sum(1 for r in validation_results if r["valid"])
        completion_rate = (valid_count / total * 100) if total > 0 else 0
        print(f"修复后完成率: {completion_rate:.1f}%")

    # 保存到文件
    output_path = "d:/Users/liu.liu/Desktop/github/medical/data/knowledge/symptoms.json"

    output_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_count": len(symptoms),
            "model": MODEL,
            "completion_rate": f"{completion_rate:.1f}%"
        },
        "symptoms": symptoms
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存到: {output_path}")

    # 显示症状分类统计
    print("\n" + "=" * 60)
    print("症状分类统计")
    print("=" * 60)

    category_count = {}
    for s in symptoms:
        cat = s.get("category", "未分类")
        category_count[cat] = category_count.get(cat, 0) + 1

    for cat, count in sorted(category_count.items()):
        print(f"  {cat}: {count} 条")

    print("\n生成完成!")
    return True


if __name__ == "__main__":
    asyncio.run(generate_symptoms())
