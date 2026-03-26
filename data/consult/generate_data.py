#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成在线问诊数据"""

import requests
import json
from datetime import datetime, timedelta
import random

# API配置
API_KEY = 'sk-a9a4edb1b4214016baa11c9be3b9fec4'
API_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'

def call_api(prompt):
    """调用阿里云API"""
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'model': 'qwen-plus',
        'messages': [{'role': 'user', 'content': prompt}]
    }
    response = requests.post(API_URL, headers=headers, json=data, timeout=60)
    return response.json()

def extract_json(content):
    """从响应中提取JSON"""
    if '```json' in content:
        content = content.split('```json')[1].split('```')[0].strip()
    elif '```' in content:
        content = content.split('```')[1].split('```')[0].strip()
    return content

def generate_doctors():
    """生成医生列表"""
    print('正在生成医生列表...')

    doctor_prompt = '''生成20个可咨询医生的JSON列表，每个医生包含以下字段：
- doctor_id: D001-D020
- name: 中文姓名
- title: 主任医师/副主任医师/主治医师
- department: 内科/外科/儿科/妇产科/骨科/心血管科/神经科/皮肤科/眼科/耳鼻喉科/呼吸科/消化科/内分泌科/泌尿外科
- specialty: 专科方向
- experience_years: 5-35年
- rating: 4.0-5.0
- available: true或false
- consultation_types: 数组，包含text/video/phone中的至少一种
- price: 对象，{text: 价格30-100, video: 价格80-300}
- schedule: 数组，如["周一上午", "周三下午"]
- introduction: 50-100字医生简介

请确保数据真实合理，直接返回JSON数组，不要其他说明文字。'''

    try:
        doctor_response = call_api(doctor_prompt)
        print('API响应:', json.dumps(doctor_response, ensure_ascii=False)[:300])

        if 'choices' in doctor_response and len(doctor_response['choices']) > 0:
            content = doctor_response['choices'][0]['message']['content']
            content = extract_json(content)
            doctors = json.loads(content)

            # 修正doctor_id格式
            for i, doc in enumerate(doctors):
                if 'doctor_id' not in doc:
                    doc['doctor_id'] = f'D{(i+1):03d}'

            print(f'成功生成 {len(doctors)} 个医生')

            # 保存医生数据
            with open('d:/Users/liu.liu/Desktop/github/medical/data/consult/doctors.json', 'w', encoding='utf-8') as f:
                json.dump(doctors, f, ensure_ascii=False, indent=2)
            print('医生数据已保存到 doctors.json')
            return doctors
        else:
            print('API调用失败，使用默认数据')
            return get_default_doctors()
    except Exception as e:
        print(f'生成医生数据出错: {e}')
        return get_default_doctors()

def get_default_doctors():
    """获取默认医生数据"""
    departments = ['内科', '外科', '儿科', '妇产科', '骨科', '心血管科', '神经科', '皮肤科', '眼科', '耳鼻喉科', '呼吸科', '消化科', '内分泌科', '泌尿外科']
    titles = ['主任医师', '副主任医师', '主治医师']
    specialties_map = {
        '内科': ['高血压', '糖尿病', '冠心病', '呼吸道感染'],
        '外科': ['普外手术', '微创手术', '创伤外科'],
        '儿科': ['儿童呼吸', '儿童消化', '新生儿疾病'],
        '妇产科': ['妇科炎症', '产科保健', '不孕不育'],
        '骨科': ['脊柱外科', '关节外科', '骨折治疗'],
        '心血管科': ['冠心病', '心律失常', '心力衰竭'],
        '神经科': ['脑血管病', '癫痫', '帕金森'],
        '皮肤科': ['湿疹', '皮炎', '痤疮'],
        '眼科': ['白内障', '青光眼', '近视矫正'],
        '耳鼻喉科': ['中耳炎', '鼻炎', '咽炎'],
        '呼吸科': ['肺炎', '哮喘', '慢阻肺'],
        '消化科': ['胃炎', '溃疡', '肝病'],
        '内分泌科': ['甲状腺疾病', '糖尿病', '骨质疏松'],
        '泌尿外科': ['前列腺疾病', '泌尿系结石', '男科']
    }

    first_names = ['王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴', '徐', '孙', '马', '胡', '朱', '高', '林', '何', '郭', '梁']
    last_names = ['伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '军', '洋', '勇', '艳', '杰', '涛', '明', '超', '秀英', '娟', '英', '华']

    doctors = []
    for i in range(20):
        dept = departments[i % len(departments)]
        name = first_names[i % len(first_names)] + last_names[i % len(last_names)]

        doctors.append({
            'doctor_id': f'D{(i+1):03d}',
            'name': name,
            'title': titles[i % 3],
            'department': dept,
            'specialty': specialties_map.get(dept, ['全科诊疗'])[i % len(specialties_map.get(dept, ['全科诊疗']))],
            'experience_years': random.randint(5, 35),
            'rating': round(random.uniform(4.0, 5.0), 1),
            'available': random.choice([True, False]),
            'consultation_types': random.sample(['text', 'video', 'phone'], k=random.randint(1, 3)),
            'price': {
                'text': random.randint(30, 100),
                'video': random.randint(80, 300)
            },
            'schedule': random.sample(['周一上午', '周一下午', '周二上午', '周二下午', '周三上午', '周三下午', '周四上午', '周四下午', '周五上午', '周五下午', '周六上午', '周日上午'], k=2),
            'introduction': f'{name}医生从事{dept}临床工作{random.randint(5,35)}年，擅长{specialties_map.get(dept, ["常见疾病"])[0]}等疾病的诊治，具有丰富的临床经验。'
        })

    with open('d:/Users/liu.liu/Desktop/github/medical/data/consult/doctors.json', 'w', encoding='utf-8') as f:
        json.dump(doctors, f, ensure_ascii=False, indent=2)

    return doctors

def generate_consultation_records(doctors):
    """生成问诊记录"""
    print('正在生成问诊记录...')

    # 先获取患者列表
    try:
        with open('d:/Users/liu.liu/Desktop/github/medical/data/user/patients.json', 'r', encoding='utf-8') as f:
            patients = json.load(f)
            patient_ids = [p.get('patient_id', p.get('id', f'P{i+1:03d}')) for i, p in enumerate(patients[:30])]
    except:
        patient_ids = [f'P{i+1:03d}' for i in range(30)]

    if len(patient_ids) < 30:
        patient_ids += [f'P{i+1:03d}' for i in range(len(patient_ids), 30)]

    consult_types = ['text', 'video', 'phone']
    statuses = ['waiting', 'completed', 'cancelled']
    chief_complaints = [
        '头痛头晕', '咳嗽咳痰', '腹痛腹泻', '发热', '胸闷气短',
        '关节疼痛', '皮肤瘙痒', '视力模糊', '失眠多梦', '食欲不振',
        '尿频尿急', '鼻塞流涕', '咽喉痛', '恶心呕吐', '便秘',
        '腰痛', '乏力', '心悸', '皮疹', '口腔溃疡'
    ]

    records = []
    for i in range(30):
        doctor = random.choice(doctors)
        patient_id = random.choice(patient_ids)
        consult_type = random.choice(consult_types)
        status = random.choice(statuses)
        complaint = random.choice(chief_complaints)

        # 生成时间（过去30天内）
        days_ago = random.randint(0, 30)
        created_at = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))

        # 生成对话消息
        messages = []
        if status in ['waiting', 'completed']:
            messages.append({
                'sender': 'patient',
                'content': f'医生你好，我{complaint}已经{random.randint(1,7)}天了，请问应该怎么办？',
                'timestamp': created_at.strftime('%Y-%m-%d %H:%M')
            })

            if status == 'completed':
                responses = [
                    f'您好，根据您的描述，{complaint}可能是由多种原因引起的。请问您还有其他症状吗？比如发热、恶心等？',
                    f'了解，建议您注意休息，多喝温水。如果症状持续加重，建议来院进行详细检查。',
                    f'根据您的症状，建议您服用一些对症药物，同时注意饮食清淡。如有不适请及时就医。'
                ]
                messages.append({
                    'sender': 'doctor',
                    'content': random.choice(responses),
                    'timestamp': (created_at + timedelta(minutes=random.randint(5, 30))).strftime('%Y-%m-%d %H:%M')
                })

        records.append({
            'consult_id': f'C{(i+1):03d}',
            'patient_id': patient_id,
            'doctor_id': doctor['doctor_id'],
            'consult_type': consult_type,
            'chief_complaint': complaint,
            'description': f'患者出现{complaint}症状{random.randint(1,7)}天，伴有{"乏力" if random.choice([True, False]) else "食欲不振"}。',
            'status': status,
            'created_at': created_at.strftime('%Y-%m-%d %H:%M'),
            'messages': messages
        })

    # 保存问诊记录
    with open('d:/Users/liu.liu/Desktop/github/medical/data/consult/records.json', 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f'问诊记录已保存，共 {len(records)} 条')

    return records

if __name__ == '__main__':
    # 生成医生数据
    doctors = generate_doctors()

    # 生成问诊记录
    records = generate_consultation_records(doctors)

    print('\\n数据生成完成！')
    print(f'- 医生数据: {len(doctors)} 条 -> d:/Users/liu.liu/Desktop/github/medical/data/consult/doctors.json')
    print(f'- 问诊记录: {len(records)} 条 -> d:/Users/liu.liu/Desktop/github/medical/data/consult/records.json')
