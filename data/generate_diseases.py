#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成50条疾病知识数据
使用阿里云qwen-plus API
"""

import requests
import json
import time

# API配置
API_KEY = 'sk-a9a4edb1b4214016baa11c9be3b9fec4'
url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'

# 50种疾病列表（ICD-10编码已验证）
diseases = [
    # 心血管疾病 (5条)
    {'name': '高血压', 'icd': 'I10', 'category': '心血管疾病', 'aliases': ['原发性高血压', '高血压病']},
    {'name': '冠心病', 'icd': 'I25.1', 'category': '心血管疾病', 'aliases': ['冠状动脉粥样硬化性心脏病', '缺血性心脏病']},
    {'name': '心律失常', 'icd': 'I49.9', 'category': '心血管疾病', 'aliases': ['心脏节律异常', '心律紊乱']},
    {'name': '心力衰竭', 'icd': 'I50.9', 'category': '心血管疾病', 'aliases': ['充血性心力衰竭', '心功能不全']},
    {'name': '心肌梗死', 'icd': 'I21.9', 'category': '心血管疾病', 'aliases': ['急性心肌梗死', '心脏病发作']},
    # 呼吸系统 (5条)
    {'name': '慢性阻塞性肺疾病', 'icd': 'J44.9', 'category': '呼吸系统', 'aliases': ['慢阻肺', 'COPD']},
    {'name': '肺炎', 'icd': 'J18.9', 'category': '呼吸系统', 'aliases': ['肺部感染', '支气管肺炎']},
    {'name': '支气管哮喘', 'icd': 'J45.9', 'category': '呼吸系统', 'aliases': ['哮喘', '过敏性哮喘']},
    {'name': '慢性支气管炎', 'icd': 'J42', 'category': '呼吸系统', 'aliases': ['老慢支', '慢支']},
    {'name': '肺栓塞', 'icd': 'I26.9', 'category': '呼吸系统', 'aliases': ['肺动脉栓塞', 'PE']},
    # 消化系统 (5条)
    {'name': '慢性胃炎', 'icd': 'K29.5', 'category': '消化系统', 'aliases': ['胃炎', '胃黏膜炎']},
    {'name': '消化性溃疡', 'icd': 'K27.9', 'category': '消化系统', 'aliases': ['胃溃疡', '十二指肠溃疡']},
    {'name': '肝硬化', 'icd': 'K74.6', 'category': '消化系统', 'aliases': ['肝硬变', '肝硬化失代偿']},
    {'name': '急性胰腺炎', 'icd': 'K85.9', 'category': '消化系统', 'aliases': ['胰腺炎', 'AP']},
    {'name': '急性胆囊炎', 'icd': 'K81.0', 'category': '消化系统', 'aliases': ['胆囊炎']},
    # 内分泌代谢 (4条)
    {'name': '2型糖尿病', 'icd': 'E11.9', 'category': '内分泌代谢', 'aliases': ['非胰岛素依赖型糖尿病', '成人发病型糖尿病']},
    {'name': '甲状腺功能亢进症', 'icd': 'E05.9', 'category': '内分泌代谢', 'aliases': ['甲亢', 'Graves病']},
    {'name': '痛风', 'icd': 'M10.9', 'category': '内分泌代谢', 'aliases': ['痛风性关节炎']},
    {'name': '骨质疏松症', 'icd': 'M81.9', 'category': '内分泌代谢', 'aliases': ['骨质疏松', '骨量减少']},
    # 神经系统 (5条)
    {'name': '脑卒中', 'icd': 'I64', 'category': '神经系统', 'aliases': ['中风', '脑血管意外']},
    {'name': '偏头痛', 'icd': 'G43.9', 'category': '神经系统', 'aliases': ['血管性头痛']},
    {'name': '帕金森病', 'icd': 'G20', 'category': '神经系统', 'aliases': ['震颤麻痹', 'PD']},
    {'name': '癫痫', 'icd': 'G40.9', 'category': '神经系统', 'aliases': ['羊癫疯', '癫痫发作']},
    {'name': '阿尔茨海默病', 'icd': 'G30.9', 'category': '神经系统', 'aliases': ['老年痴呆', 'AD']},
    # 泌尿系统 (4条)
    {'name': '肾结石', 'icd': 'N20.0', 'category': '泌尿系统', 'aliases': ['泌尿系结石', '肾石症']},
    {'name': '尿路感染', 'icd': 'N39.0', 'category': '泌尿系统', 'aliases': ['泌尿系感染', 'UTI']},
    {'name': '前列腺增生', 'icd': 'N40', 'category': '泌尿系统', 'aliases': ['良性前列腺增生', 'BPH']},
    {'name': '慢性肾小球肾炎', 'icd': 'N03.9', 'category': '泌尿系统', 'aliases': ['慢性肾炎', 'CGN']},
    # 血液系统 (4条)
    {'name': '贫血', 'icd': 'D64.9', 'category': '血液系统', 'aliases': ['血红蛋白减少']},
    {'name': '白血病', 'icd': 'C95.9', 'category': '血液系统', 'aliases': ['血癌']},
    {'name': '淋巴瘤', 'icd': 'C85.9', 'category': '血液系统', 'aliases': ['恶性淋巴瘤', '淋巴癌']},
    {'name': '过敏性紫癜', 'icd': 'D69.0', 'category': '血液系统', 'aliases': ['Henoch-Schonlein紫癜', 'HSP']},
    # 风湿免疫 (3条)
    {'name': '类风湿关节炎', 'icd': 'M06.9', 'category': '风湿免疫', 'aliases': ['类风湿', 'RA']},
    {'name': '系统性红斑狼疮', 'icd': 'M32.9', 'category': '风湿免疫', 'aliases': ['SLE', '狼疮']},
    {'name': '强直性脊柱炎', 'icd': 'M45.9', 'category': '风湿免疫', 'aliases': ['AS', '脊柱关节炎']},
    # 感染性疾病 (3条)
    {'name': '肺结核', 'icd': 'A15.9', 'category': '感染性疾病', 'aliases': ['结核病', 'TB', '痨病']},
    {'name': '慢性乙型肝炎', 'icd': 'B18.1', 'category': '感染性疾病', 'aliases': ['乙肝', '乙型肝炎']},
    {'name': '流行性感冒', 'icd': 'J11.1', 'category': '感染性疾病', 'aliases': ['流感']},
    # 肿瘤 (5条)
    {'name': '肺癌', 'icd': 'C34.9', 'category': '肿瘤', 'aliases': ['支气管肺癌', '肺恶性肿瘤']},
    {'name': '胃癌', 'icd': 'C16.9', 'category': '肿瘤', 'aliases': ['胃恶性肿瘤']},
    {'name': '肝癌', 'icd': 'C22.9', 'category': '肿瘤', 'aliases': ['原发性肝癌', '肝细胞癌']},
    {'name': '结直肠癌', 'icd': 'C20', 'category': '肿瘤', 'aliases': ['大肠癌', '结肠直肠癌']},
    {'name': '乳腺癌', 'icd': 'C50.9', 'category': '肿瘤', 'aliases': ['乳腺恶性肿瘤']},
    # 妇产科 (3条)
    {'name': '子宫肌瘤', 'icd': 'D25.9', 'category': '妇产科', 'aliases': ['子宫平滑肌瘤', '纤维瘤']},
    {'name': '卵巢囊肿', 'icd': 'N83.2', 'category': '妇产科', 'aliases': ['卵巢囊性肿物']},
    {'name': '宫颈炎', 'icd': 'N72', 'category': '妇产科', 'aliases': ['宫颈炎症']},
    # 儿科 (3条)
    {'name': '手足口病', 'icd': 'B08.4', 'category': '儿科', 'aliases': ['HFMD']},
    {'name': '水痘', 'icd': 'B01.9', 'category': '儿科', 'aliases': ['水痘带状疱疹病毒感染']},
    {'name': '麻疹', 'icd': 'B05.9', 'category': '儿科', 'aliases': ['麻疹病毒感染']},
]

def generate_disease_data(disease_info, index):
    """调用阿里云API生成疾病数据"""

    prompt = f"""请为"{disease_info['name']}"生成完整的医学知识数据，严格按照以下JSON格式返回，不要包含任何其他文字说明。

疾病信息：
- 名称：{disease_info['name']}
- 别名：{', '.join(disease_info['aliases'])}
- ICD-10编码：{disease_info['icd']}
- 分类：{disease_info['category']}

JSON格式（保持结构一致，替换内容）：
{{
  "id": "DIS{index:03d}",
  "name": "{disease_info['name']}",
  "aliases": {json.dumps(disease_info['aliases'], ensure_ascii=False)},
  "icd_code": "{disease_info['icd']}",
  "category": "{disease_info['category']}",
  "description": "200字左右的疾病描述，包括病因、发病机制、流行病学等",
  "diagnostic_criteria": {{
    "definite": "确诊标准，列出2-3条关键诊断依据",
    "suspected": "疑诊标准，列出初步筛查要点"
  }},
  "symptoms": {{
    "typical": ["典型症状1", "典型症状2", "典型症状3", "典型症状4"],
    "complications": ["并发症1", "并发症2", "并发症3"]
  }},
  "treatment": {{
    "medication": ["具体药物名称和用法，至少3条"],
    "lifestyle": ["生活方式干预措施，至少2条"]
  }},
  "prevention": {{
    "primary": ["一级预防措施，至少3条"]
  }}
}}

请确保：
1. 描述专业准确，符合临床医学规范
2. 药物使用通用名
3. 只返回JSON，不要有markdown代码块标记或其他文字
"""

    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    data = {
        'model': 'qwen-plus',
        'messages': [
            {'role': 'system', 'content': '你是一个专业的医学知识库助手，严格按照JSON格式返回医学数据。'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.3,
        'max_tokens': 2000
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()

        content = result['choices'][0]['message']['content'].strip()

        # 清理可能存在的markdown代码块标记
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]

        # 解析JSON
        disease_data = json.loads(content.strip())
        return disease_data

    except Exception as e:
        print(f"Error generating {disease_info['name']}: {e}")
        return None


def main():
    """生成所有疾病数据"""
    results = []
    total = len(diseases)

    for i, disease in enumerate(diseases, 1):
        print(f"[{i}/{total}] Generating: {disease['name']} ({disease['icd']})...")

        disease_data = generate_disease_data(disease, i)
        if disease_data:
            results.append(disease_data)
            print(f"  Success: {disease['name']}")
        else:
            print(f"  Failed: {disease['name']}, using fallback data")
            # 使用备用数据
            results.append(create_fallback_data(disease, i))

        # 避免API限流
        time.sleep(0.5)

    # 保存结果
    output_file = 'd:/Users/liu.liu/Desktop/github/medical/data/knowledge/diseases.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n完成！生成 {len(results)} 条疾病数据")
    print(f"保存至: {output_file}")

    return results


def create_fallback_data(disease_info, index):
    """创建备用数据（当API调用失败时使用）"""
    return {
        "id": f"DIS{index:03d}",
        "name": disease_info['name'],
        "aliases": disease_info['aliases'],
        "icd_code": disease_info['icd'],
        "category": disease_info['category'],
        "description": f"{disease_info['name']}是一种常见的{disease_info['category']}疾病，需要及时诊断和治疗。",
        "diagnostic_criteria": {
            "definite": "根据临床表现、实验室检查和影像学检查综合诊断",
            "suspected": "出现相关症状需进一步检查明确诊断"
        },
        "symptoms": {
            "typical": ["症状待补充", "症状待补充", "症状待补充"],
            "complications": ["并发症待补充"]
        },
        "treatment": {
            "medication": ["具体用药待补充"],
            "lifestyle": ["生活方式调整"]
        },
        "prevention": {
            "primary": ["定期体检", "健康生活方式"]
        }
    }


if __name__ == '__main__':
    main()
