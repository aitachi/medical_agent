# -*- coding: utf-8 -*-
"""
Concise Medical Knowledge Base Generator
Generates knowledge_base_concise.json with commonly used medications and conditions.
"""
import json
import sys
from pathlib import Path

# Add current directory to path to import generate_full_kb
sys.path.insert(0, str(Path('.').resolve()))

def convert_interaction_format(interactions):
    """Convert interaction format from drug_1/drug_2 to drugs list"""
    converted = {'critical': [], 'moderate': [], 'mild': []}

    for severity in ['critical', 'moderate', 'mild']:
        if severity not in interactions:
            continue
        for item in interactions[severity]:
            # Convert from {drug_1, drug_2, severity, effect, ...}
            # to {drugs: [drug1, drug2], description: ...}
            converted[severity].append({
                'drugs': [item['drug_1'], item['drug_2']],
                'description': f"{item.get('effect', '')}。机制：{item.get('mechanism', '')}。处理：{item.get('management', '')}"
            })

    return converted

def main():
    # Import from full KB generator
    import generate_full_kb as full_kb

    # Get all data from full generator
    all_drugs = full_kb.generate_drugs()
    all_interactions = full_kb.generate_interactions()
    additional_interactions = full_kb.generate_additional_interactions()
    all_diseases = full_kb.generate_diseases()
    all_more_diseases = full_kb.generate_more_diseases()
    all_symptoms = full_kb.generate_symptoms()
    all_emergency_patterns = full_kb.generate_emergency_patterns()

    # Merge diseases
    all_diseases.update(all_more_diseases)

    # Merge interactions
    for severity in additional_interactions:
        if severity in all_interactions:
            all_interactions[severity].extend(additional_interactions[severity])
        else:
            all_interactions[severity] = additional_interactions[severity]

    # Convert interaction format to match safety_checker expectations
    all_interactions = convert_interaction_format(all_interactions)

    # Add common_allergens to drug data for safety_checker
    common_allergens_map = {
        "青霉素类": ["青霉素", "抗生素"],
        "头孢菌素类": ["头孢类", "抗生素"],
        "磺胺类": ["磺胺"],
        "阿司匹林": ["水杨酸", "NSAID"],
        "布洛芬": ["NSAID"],
        "双氯芬酸钠": ["NSAID"],
    }

    for drug_name, drug_data in all_drugs.items():
        category = drug_data.get('category', '')
        for cat_key, allergens in common_allergens_map.items():
            if cat_key in category or cat_key == drug_name:
                drug_data['common_allergens'] = allergens
                break
        if 'common_allergens' not in drug_data:
            drug_data['common_allergens'] = []

    # Select subsets - most commonly used items
    # Drugs: 160 most commonly used
    priority_drugs = list(all_drugs.keys())[:160]

    # Interactions: 220 most critical
    critical_interactions = all_interactions.get('critical', [])[:100]
    moderate_interactions = all_interactions.get('moderate', [])[:100]
    mild_interactions = all_interactions.get('mild', [])[:20]

    # Diseases: 165 most common
    priority_diseases = dict(list(all_diseases.items())[:165])

    # Symptoms: 72 most common
    priority_symptoms = dict(list(all_symptoms.items())[:72])

    # Keep all emergency patterns (comprehensive coverage)
    emergency_patterns = all_emergency_patterns

    # Generate synonyms from symptom aliases
    synonyms = {}
    for symptom_name, symptom_data in priority_symptoms.items():
        aliases = symptom_data.get('aliases', [])
        if aliases:
            synonyms[symptom_name] = aliases

    # Add common synonyms manually to ensure coverage
    common_synonyms = {
        "头痛": ["头疼", "脑袋痛", "头部疼痛"],
        "发热": ["发烧", "体温升高", "发烧了"],
        "咳嗽": ["咳", "干咳", "咳痰"],
        "胸痛": ["胸口痛", "胸闷", "心口痛"],
        "腹痛": ["肚子痛", "胃痛", "腹疼"],
        "头晕": ["眩晕", "头昏", "头重脚轻"],
        "呕吐": ["吐", "反吐", "干呕"],
        "腹泻": ["拉肚子", "跑肚", "稀便"],
        "失眠": ["睡不着", "睡眠不足", "入睡困难"],
        "乏力": ["疲劳", "累", "没力气"],
        "心悸": ["心慌", "心跳快", "心跳加速"],
        "气短": ["呼吸困难", "喘不上气", "气促"],
        "水肿": ["浮肿", "肿胀", "发肿"],
        "皮疹": ["起疹子", "皮肤红点", "过敏疹"],
        "关节痛": ["关节炎", "关节疼", "关节不适"],
    }
    for main_term, syn_list in common_synonyms.items():
        if main_term not in synonyms:
            synonyms[main_term] = []
        # Add any synonyms from common list that aren't already there
        for syn in syn_list:
            if syn not in synonyms[main_term]:
                synonyms[main_term].append(syn)

    # Generate departments data
    departments = {
        "神经内科": {
            "description": "诊治脑血管疾病、头痛、癫痫等神经系统疾病",
            "common_symptoms": ["头痛", "头晕", "失眠", "意识障碍", "肢体麻木", "言语不清"],
            "sub_departments": ["神经电生理", "神经介入"]
        },
        "心血管内科": {
            "description": "诊治高血压、冠心病、心律失常等心血管疾病",
            "common_symptoms": ["胸痛", "心悸", "气短", "水肿", "晕厥"],
            "sub_departments": ["心电生理", "心脏介入"]
        },
        "呼吸内科": {
            "description": "诊治肺炎、哮喘、慢阻肺等呼吸系统疾病",
            "common_symptoms": ["咳嗽", "咳痰", "呼吸困难", "发热", "胸痛"],
            "sub_departments": ["呼吸内镜", "肺功能"]
        },
        "消化内科": {
            "description": "诊治胃炎、溃疡、肝病等消化系统疾病",
            "common_symptoms": ["腹痛", "恶心", "呕吐", "腹泻", "便秘", "黄疸"],
            "sub_departments": ["消化内镜", "肝胆"]
        },
        "内分泌科": {
            "description": "诊治糖尿病、甲状腺疾病等内分泌疾病",
            "common_symptoms": ["多饮", "多尿", "体重变化", "怕热", "乏力"],
            "sub_departments": ["糖尿病", "甲状腺"]
        },
        "肾内科": {
            "description": "诊治肾炎、肾衰竭等肾脏疾病",
            "common_symptoms": ["水肿", "蛋白尿", "血尿", "少尿", "泡沫尿"],
            "sub_departments": ["透析", "腹膜透析"]
        },
        "血液科": {
            "description": "诊治贫血、白血病等血液系统疾病",
            "common_symptoms": ["贫血", "出血", "发热", "淋巴结肿大", "骨痛"],
            "sub_departments": ["白血病", "淋巴瘤"]
        },
        "风湿免疫科": {
            "description": "诊治关节炎、红斑狼疮等风湿免疫疾病",
            "common_symptoms": ["关节痛", "皮疹", "发热", "口干", "眼干"],
            "sub_departments": ["关节炎", "结缔组织病"]
        },
        "骨科": {
            "description": "诊治骨折、关节炎等骨骼肌肉疾病",
            "common_symptoms": ["关节痛", "背痛", "颈痛", "腰痛", "骨折"],
            "sub_departments": ["创伤", "关节", "脊柱"]
        },
        "普外科": {
            "description": "诊治腹部、甲状腺等外科疾病",
            "common_symptoms": ["腹痛", "肿块", "黄疸", "腹部包块"],
            "sub_departments": ["胃肠", "肝胆", "甲状腺"]
        },
        "泌尿外科": {
            "description": "诊治泌尿系结石、前列腺等疾病",
            "common_symptoms": ["尿频", "尿急", "尿痛", "血尿", "排尿困难"],
            "sub_departments": ["结石", "前列腺", "男科"]
        },
        "妇科": {
            "description": "诊治女性生殖系统疾病",
            "common_symptoms": ["月经异常", "腹痛", "白带异常", "不孕"],
            "sub_departments": ["产科", "计划生育", "生殖内分泌"]
        },
        "产科": {
            "description": "孕产期保健",
            "common_symptoms": ["妊娠反应", "胎动异常", "腹痛", "出血"],
            "sub_departments": ["产前", "产房", "产后"]
        },
        "儿科": {
            "description": "儿童疾病诊治",
            "common_symptoms": ["发热", "咳嗽", "腹泻", "皮疹", "哭闹"],
            "sub_departments": ["新生儿", "小儿呼吸", "小儿消化"]
        },
        "眼科": {
            "description": "诊治眼部疾病",
            "common_symptoms": ["视力下降", "眼痛", "红眼", "流泪", "视物模糊"],
            "sub_departments": ["眼底", "青光眼", "白内障"]
        },
        "耳鼻喉科": {
            "description": "诊治耳鼻喉疾病",
            "common_symptoms": ["耳痛", "鼻塞", "咽痛", "声音嘶哑", "听力下降"],
            "sub_departments": ["耳科", "鼻科", "咽喉科"]
        },
        "口腔科": {
            "description": "诊治口腔疾病",
            "common_symptoms": ["牙痛", "口腔溃疡", "牙龈出血", "口臭"],
            "sub_departments": ["牙体牙髓", "牙周", "口腔黏膜"]
        },
        "皮肤科": {
            "description": "诊治皮肤疾病",
            "common_symptoms": ["皮疹", "瘙痒", "脱发", "色素沉着"],
            "sub_departments": ["性病", "美容"]
        },
        "感染科": {
            "description": "诊治感染性疾病",
            "common_symptoms": ["发热", "腹泻", "黄疸", "皮疹"],
            "sub_departments": ["肝病", "传染病"]
        },
        "精神科": {
            "description": "诊治精神心理疾病",
            "common_symptoms": ["失眠", "焦虑", "抑郁", "幻觉"],
            "sub_departments": ["情感障碍", "精神病性障碍"]
        },
        "急诊科": {
            "description": "急危重症救治",
            "common_symptoms": ["胸痛", "呼吸困难", "意识不清", "大出血", "剧烈疼痛"],
            "sub_departments": ["抢救", "留观"]
        },
        "麻醉科": {
            "description": "临床麻醉与疼痛治疗",
            "common_symptoms": ["疼痛"],
            "sub_departments": ["疼痛门诊", "麻醉"]
        },
        "肿瘤科": {
            "description": "诊治肿瘤疾病",
            "common_symptoms": ["肿块", "消瘦", "发热", "疼痛"],
            "sub_departments": ["化疗", "放疗", "靶向"]
        },
        "康复医学科": {
            "description": "功能康复训练",
            "common_symptoms": ["肢体活动障碍", "言语障碍", "吞咽困难"],
            "sub_departments": ["物理治疗", "作业治疗", "言语治疗"]
        },
        "老年医学科": {
            "description": "老年综合疾病诊治",
            "common_symptoms": ["衰弱", "跌倒", "认知下降", "多重用药"],
            "sub_departments": ["老年综合评估"]
        }
    }

    # Generate disease_prevention from diseases data
    disease_prevention = {}
    for disease_name, disease_data in priority_diseases.items():
        prevention_data = disease_data.get('prevention', [])
        risk_factors = disease_data.get('risk_factors', [])
        disease_prevention[disease_name] = {
            "prevention": prevention_data if prevention_data else ["健康生活方式", "定期体检"],
            "risk_factors": risk_factors if risk_factors else [],
            "description": disease_data.get('description', '')
        }
    
    # Calculate totals
    total_interactions = len(critical_interactions) + len(moderate_interactions) + len(mild_interactions)
    
    # Create knowledge base
    kb = {
        'version': 'concise_v1.0',
        'description': 'Simplified medical knowledge base with commonly used medications and conditions',
        'generated_date': __import__('datetime').datetime.now().isoformat(),
        'drugs': {k: all_drugs[k] for k in priority_drugs},
        'drug_interactions': {
            'critical': critical_interactions,
            'moderate': moderate_interactions,
            'mild': mild_interactions
        },
        'diseases': priority_diseases,
        'symptoms': priority_symptoms,
        'departments': departments,
        'synonyms': synonyms,
        'disease_prevention': disease_prevention,
        'emergency_patterns': emergency_patterns,
        'statistics': {
            'total_drugs': len(priority_drugs),
            'total_interactions': total_interactions,
            'total_diseases': len(priority_diseases),
            'total_symptoms': len(priority_symptoms),
            'total_departments': len(departments)
        }
    }
    
    # Output path
    output_path = Path('.') / 'knowledge_base_concise.json'
    
    # Write to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)
    
    # Calculate totals for display
    dr_count = len(priority_drugs)
    di_count = len(priority_diseases)
    sy_count = len(priority_symptoms)
    ei_count = len(critical_interactions)
    mi_count = len(moderate_interactions)
    ei2_count = len(mild_interactions)
    total_i_count = ei_count + mi_count + ei2_count
    
    total_patterns = sum(len(emergency_patterns[c]["patterns"]) for c in emergency_patterns)
    
    file_size_kb = output_path.stat().st_size / 1024
    
    # Print results
    print("=" * 60)
    print("Concise Medical Knowledge Base Generator")
    print("=" * 60)
    print(f"Knowledge base generated: {output_path}")
    print(f"File size: {file_size_kb:.2f} KB")
    print()
    print("Generated data statistics:")
    print(f"  Drugs:         {dr_count} (target: 150-180)")
    print(f"  Interactions:   {total_i_count} (target: 200-250)")
    print(f"    - Critical:  {ei_count}")
    print(f"    - Moderate:  {mi_count}")
    print(f"    - Mild:      {ei2_count}")
    print(f"  Diseases:      {di_count} (target: 150-180)")
    print(f"  Symptoms:      {sy_count} (target: 50-80)")
    print(f"  Emergency patterns: {total_patterns} (comprehensive)")
    print("=" * 60)
    print()
    print("Target achievement:")
    
    # Check targets and print status
    dr_ok = 150 <= dr_count <= 180
    di_ok = 200 <= total_i_count <= 250
    dis_ok = 150 <= di_count <= 180
    sy_ok = 50 <= sy_count <= 80
    
    print(f"  Drugs (150-180):        {'OK' if dr_ok else f'[{dr_count}]'}")
    print(f"  Interactions (200-250):  {'OK' if di_ok else f'[{total_i_count}]'}")
    print(f"  Diseases (150-180):      {'OK' if dis_ok else f'[{di_count}]'}")
    print(f"  Symptoms (50-80):        {'OK' if sy_ok else f'[{sy_count}]'}")
    print(f"  Emergency patterns:       Comprehensive coverage")
    
    return kb


if __name__ == "__main__":
    main()
