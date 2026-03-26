#!/usr/bin/env python3
"""
Generate 50 drug records using Alibaba Cloud Qwen API
"""
import json
import requests
import time

API_KEY = "sk-a9a4edb1b4214016baa11c9be3b9fec4"
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

# Drug list organized by category
DRUG_BATCHES = [
    {
        "start_id": 1,
        "drugs": [
            ("Amoxicillin", "阿莫西林", "抗生素"),
            ("Cefuroxime", "头孢呋辛", "抗生素"),
            ("Ceftriaxone", "头孢曲松", "抗生素"),
            ("Levofloxacin", "左氧氟沙星", "抗生素"),
            ("Azithromycin", "阿奇霉素", "抗生素"),
            ("Moxifloxacin", "莫西沙星", "抗生素")
        ]
    },
    {
        "start_id": 7,
        "drugs": [
            ("Nifedipine", "硝苯地平", "心血管药"),
            ("Amlodipine", "氨氯地平", "心血管药"),
            ("Metoprolol", "美托洛尔", "心血管药"),
            ("Aspirin", "阿司匹林", "心血管药"),
            ("Atorvastatin", "阿托伐他汀", "心血管药"),
            ("Simvastatin", "辛伐他汀", "心血管药"),
            ("Clopidogrel", "氯吡格雷", "心血管药")
        ]
    },
    {
        "start_id": 14,
        "drugs": [
            ("Omeprazole", "奥美拉唑", "消化系统药"),
            ("Lansoprazole", "兰索拉唑", "消化系统药"),
            ("Domperidone", "多潘立酮", "消化系统药"),
            ("Montmorillonite", "蒙脱石散", "消化系统药"),
            ("Ursodeoxycholic", "熊去氧胆酸", "消化系统药")
        ]
    },
    {
        "start_id": 19,
        "drugs": [
            ("Ambroxol", "氨溴索", "呼吸系统药"),
            ("Salbutamol", "沙丁胺醇", "呼吸系统药"),
            ("Budesonide", "布地奈德", "呼吸系统药"),
            ("Montelukast", "孟鲁司特", "呼吸系统药")
        ]
    },
    {
        "start_id": 23,
        "drugs": [
            ("Metformin", "二甲双胍", "内分泌药"),
            ("Glimepiride", "格列美脲", "内分泌药"),
            ("Levothyroxine", "左甲状腺素", "内分泌药"),
            ("Methimazole", "甲巯咪唑", "内分泌药")
        ]
    },
    {
        "start_id": 27,
        "drugs": [
            ("Ibuprofen", "布洛芬", "神经系统药"),
            ("Paracetamol", "对乙酰氨基酚", "神经系统药"),
            ("Carbamazepine", "卡马西平", "神经系统药"),
            ("Gabapentin", "加巴喷丁", "神经系统药")
        ]
    },
    {
        "start_id": 31,
        "drugs": [
            ("Furosemide", "呋塞米", "利尿药"),
            ("Hydrochlorothiazide", "氢氯噻嗪", "利尿药"),
            ("Spironolactone", "螺内酯", "利尿药")
        ]
    },
    {
        "start_id": 34,
        "drugs": [
            ("Insulin", "胰岛素", "降糖药"),
            ("Repaglinide", "瑞格列奈", "降糖药"),
            ("Valsartan", "缬沙坦", "降压药"),
            ("Irbesartan", "厄贝沙坦", "降压药")
        ]
    },
    {
        "start_id": 38,
        "drugs": [
            ("Warfarin", "华法林", "抗凝药"),
            ("Dabigatran", "达比加群", "抗凝药")
        ]
    },
    {
        "start_id": 40,
        "drugs": [
            ("Losartan", "氯沙坦", "降压药"),
            ("Candesartan", "坎地沙坦", "降压药"),
            ("Olmesartan", "奥美沙坦", "降压药"),
            ("Telmisartan", "替米沙坦", "降压药"),
            ("Rosuvastatin", "瑞舒伐他汀", "心血管药"),
            ("Pitavastatin", "匹伐他汀", "心血管药")
        ]
    },
    {
        "start_id": 46,
        "drugs": [
            ("Cephalexin", "头孢氨苄", "抗生素"),
            ("Cefixime", "头孢克肟", "抗生素"),
            ("Clarithromycin", "克拉霉素", "抗生素"),
            ("Roxithromycin", "罗红霉素", "抗生素"),
            ("Famotidine", "法莫替丁", "消化系统药")
        ]
    }
]

def generate_drug_batch(batch):
    """Generate a batch of drug records"""
    drugs = batch["drugs"]
    start_id = batch["start_id"]

    prompt = f"Generate {len(drugs)} drug records as JSON array. Use drug_id DRG{start_id:03d} to DRG{start_id + len(drugs) - 1:03d}.\n"
    prompt += "Drugs and categories:\n"
    for i, (eng, cn, cat) in enumerate(drugs):
        prompt += f"{i+1}. {eng} ({cn}) - Category: {cat}\n"

    prompt += """
For each drug, include these fields in JSON object:
- drug_id: e.g., DRG001
- generic_name: Chinese generic name (通用名)
- english_name: English drug name
- brand_names: array of brand names (include common Chinese brands if applicable)
- category: drug category in Chinese
- indications: array of indications in Chinese
- dosage: object with "adult" and "children" dosage in Chinese
- contraindications: array of contraindications in Chinese
- side_effects: array of side effects in Chinese
- interactions: array of drug interactions in Chinese
- warnings: warnings in Chinese
- storage: storage conditions in Chinese
- approval_number: Chinese approval number format (e.g., 国药准字H12345678)

Return ONLY valid JSON array. No markdown, no code blocks, no explanation text."""

    payload = {
        "model": "qwen-plus",
        "messages": [
            {"role": "system", "content": "You are a medical drug database generator. Return only valid JSON array, no markdown code blocks, no explanation."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 8000
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]

            # Clean up markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)
        else:
            print(f"Error: No choices in response: {result}")
            return []

    except Exception as e:
        print(f"Error generating batch: {e}")
        return []

def main():
    """Generate all 50 drug records"""
    all_drugs = []

    print("开始生成50条药品数据...")

    for i, batch in enumerate(DRUG_BATCHES):
        print(f"正在生成第 {i+1}/{len(DRUG_BATCHES)} 批数据...")

        # Load existing result if any
        result_file = f"d:/Users/liu.liu/Desktop/github/medical/data/drugs/batch_{i+1}.json"

        try:
            with open(result_file, "r", encoding="utf-8") as f:
                batch_drugs = json.load(f)
                print(f"  从缓存加载 {len(batch_drugs)} 条记录")
        except FileNotFoundError:
            batch_drugs = generate_drug_batch(batch)
            if batch_drugs:
                # Save batch result
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump(batch_drugs, f, ensure_ascii=False, indent=2)
                print(f"  生成了 {len(batch_drugs)} 条记录")

        all_drugs.extend(batch_drugs)
        time.sleep(2)  # Rate limiting

    # Combine and save final result
    output_file = "d:/Users/liu.liu/Desktop/github/medical/data/drugs/drugs.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_drugs, f, ensure_ascii=False, indent=2)

    print(f"\n完成！共生成 {len(all_drugs)} 条药品数据")
    print(f"保存至: {output_file}")

    # Print summary
    categories = {}
    for drug in all_drugs:
        cat = drug.get("category", "未知")
        categories[cat] = categories.get(cat, 0) + 1

    print("\n分类统计:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}条")

if __name__ == "__main__":
    main()
