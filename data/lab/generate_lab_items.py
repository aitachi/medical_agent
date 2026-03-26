#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成检验项目数据"""

import requests
import json

API_KEY = "sk-a9a4edb1b4214016baa11c9be3b9fec4"
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

def generate_batch(prompt, timeout=60):
    """分批调用API生成数据"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "qwen-plus",
        "messages": [
            {"role": "system", "content": "你是医学检验专家，生成准确的检验项目数据，参考范围必须符合中国临床标准。只返回JSON数组。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }

    response = requests.post(API_URL, headers=headers, json=payload, timeout=timeout)
    result = response.json()

    if "choices" in result:
        content = result["choices"][0]["message"]["content"]
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return json.loads(content)
    else:
        print(f"API Error: {result}")
        return None

def generate_lab_items():
    """使用阿里云API分批生成检验项目数据"""
    all_items = []

    # 血常规6项
    print("生成血常规数据...")
    prompt = """生成6条血常规检验项目JSON数据：
1. 白细胞(WBC)
2. 红细胞(RBC)
3. 血红蛋白(HGB)
4. 血小板(PLT)
5. 红细胞压积(HCT)
6. 平均红细胞体积(MCV)

格式：[{"item_id":"LAB001","name":"中文名","english_name":"English Name","category":"血常规","specimen":"全血","reference_range":"参考范围","clinical_significance":"临床意义","abnormal_indications":"异常提示"}]
只返回JSON数组。"""
    items = generate_batch(prompt)
    if items:
        all_items.extend(items)

    # 肝功能6项
    print("生成肝功能数据...")
    prompt = """生成6条肝功能检验项目JSON数据：
1. ALT/谷丙转氨酶
2. AST/谷草转氨酶
3. GGT/谷氨酰转肽酶
4. ALP/碱性磷酸酶
5. 总胆红素(TBIL)
6. 白蛋白(ALB)

格式：[{"item_id":"LAB007","name":"中文名","english_name":"English Name","category":"肝功能","specimen":"血清","reference_range":"参考范围","clinical_significance":"临床意义","abnormal_indications":"异常提示"}]
只返回JSON数组。"""
    items = generate_batch(prompt)
    if items:
        all_items.extend(items)

    # 肾功能4项
    print("生成肾功能数据...")
    prompt = """生成4条肾功能检验项目JSON数据：
1. 肌酐
2. 尿素氮(BUN)
3. 尿酸(UA)
4. 胱抑素C

格式：[{"item_id":"LAB013","name":"中文名","english_name":"English Name","category":"肾功能","specimen":"血清","reference_range":"参考范围","clinical_significance":"临床意义","abnormal_indications":"异常提示"}]
只返回JSON数组。"""
    items = generate_batch(prompt)
    if items:
        all_items.extend(items)

    # 血脂4项
    print("生成血脂数据...")
    prompt = """生成4条血脂检验项目JSON数据：
1. 总胆固醇(TC)
2. 甘油三酯(TG)
3. HDL-C/高密度脂蛋白胆固醇
4. LDL-C/低密度脂蛋白胆固醇

格式：[{"item_id":"LAB017","name":"中文名","english_name":"English Name","category":"血脂","specimen":"血清","reference_range":"参考范围","clinical_significance":"临床意义","abnormal_indications":"异常提示"}]
只返回JSON数组。"""
    items = generate_batch(prompt)
    if items:
        all_items.extend(items)

    # 血糖3项
    print("生成血糖数据...")
    prompt = """生成3条血糖检验项目JSON数据：
1. 空腹血糖(FPG)
2. 糖化血红蛋白(HbA1c)
3. 胰岛素

格式：[{"item_id":"LAB021","name":"中文名","english_name":"English Name","category":"血糖","specimen":"血清或血浆","reference_range":"参考范围","clinical_significance":"临床意义","abnormal_indications":"异常提示"}]
只返回JSON数组。"""
    items = generate_batch(prompt)
    if items:
        all_items.extend(items)

    # 电解质5项
    print("生成电解质数据...")
    prompt = """生成5条电解质检验项目JSON数据：
1. 钾离子(K+)
2. 钠离子
3. 氯离子
4. 钙离子
5. 镁离子

格式：[{"item_id":"LAB024","name":"中文名","english_name":"English Name","category":"电解质","specimen":"血清","reference_range":"参考范围","clinical_significance":"临床意义","abnormal_indications":"异常提示"}]
只返回JSON数组。"""
    items = generate_batch(prompt)
    if items:
        all_items.extend(items)

    # 凝血4项
    print("生成凝血数据...")
    prompt = """生成4条凝血检验项目JSON数据：
1. PT/凝血酶原时间
2. INR
3. APTT/活化部分凝血活酶时间
4. 纤维蛋白原

格式：[{"item_id":"LAB029","name":"中文名","english_name":"English Name","category":"凝血","specimen":"血浆","reference_range":"参考范围","clinical_significance":"临床意义","abnormal_indications":"异常提示"}]
只返回JSON数组。"""
    items = generate_batch(prompt)
    if items:
        all_items.extend(items)

    return all_items

def save_lab_items(items, filepath):
    """保存检验项目数据"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(items)} 条检验项目数据到 {filepath}")

if __name__ == "__main__":
    items = generate_lab_items()
    if items:
        save_lab_items(items, "d:/Users/liu.liu/Desktop/github/medical/data/lab/lab_items.json")

        # 打印前3条预览
        print("\n=== 数据预览（前3条）===")
        for item in items[:3]:
            print(f"\n{item['name']} ({item['item_id']})")
            print(f"  参考范围: {item['reference_range']}")
