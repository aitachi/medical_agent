#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成科室和医生数据
- 200个科室（一级、二级、三级专科、医技科室）
- 2000名医生（主任医师300、副主任医师500、主治医师700、住院医师400、医师100）
"""

import json
import random
import os
from datetime import datetime

# 姓氏库（常见姓氏）
SURNAMES = [
    "王", "李", "张", "刘", "陈", "杨", "黄", "赵", "吴", "周",
    "徐", "孙", "马", "朱", "胡", "郭", "何", "林", "罗", "高",
    "郑", "梁", "谢", "宋", "唐", "许", "韩", "冯", "邓", "曹",
    "彭", "曾", "萧", "田", "董", "袁", "潘", "于", "蒋", "蔡",
    "余", "杜", "叶", "程", "苏", "魏", "吕", "丁", "任", "沈"
]

# 男性名字
MALE_NAMES = [
    "伟", "强", "磊", "洋", "勇", "军", "杰", "涛", "超", "明",
    "刚", "平", "辉", "鹏", "华", "飞", "鑫", "波", "斌", "宇",
    "建国", "建军", "志强", "文博", "天宇", "浩然", "子轩", "皓轩", "宇航", "皓然",
    "梓睿", "宇哲", "浩宇", "博文", "明轩", "天佑", "子涵", "亦辰", "俊驰", "俊杰"
]

# 女性名字
FEMALE_NAMES = [
    "芳", "娜", "敏", "静", "丽", "娟", "燕", "艳", "玲", "娟",
    "萍", "颖", "琳", "倩", "雪", "梅", "红", "霞", "婷", "慧",
    "欣怡", "子涵", "诗涵", "欣妍", "雨涵", "佳琪", "梦瑶", "梓涵", "思睿", "雅静",
    "雨萱", "可馨", "诗琪", "梓萱", "紫萱", "思妍", "梓琪", "雅琳", "梦洁", "静雯"
]

# 医学院校
MEDICAL_SCHOOLS = [
    "北京协和医学院", "北京大学医学部", "复旦大学上海医学院", "上海交通大学医学院",
    "中山大学医学院", "华中科技大学同济医学院", "四川大学华西医学中心", "中南大学湘雅医学院",
    "浙江大学医学院", "山东大学齐鲁医学院", "首都医科大学", "南京医科大学",
    "西安交通大学医学部", "吉林大学白求恩医学部", "哈尔滨医科大学", "中国医科大学",
    "天津医科大学", "南方医科大学", "重庆医科大学", "郑州大学医学院"
]

# 专科方向关键词
SPECIALTY_KEYWORDS = [
    "心血管疾病", "高血压", "冠心病", "心律失常", "心力衰竭",
    "消化系统疾病", "胃肠疾病", "肝病", "胰腺疾病", "炎症性肠病",
    "呼吸系统疾病", "慢性阻塞性肺病", "哮喘", "肺部感染", "睡眠呼吸障碍",
    "内分泌疾病", "糖尿病", "甲状腺疾病", "代谢综合征", "骨质疏松",
    "肾脏疾病", "血液净化", "肾小球疾病", "泌尿系统感染",
    "血液系统疾病", "贫血", "白血病", "淋巴瘤", "出血性疾病",
    "风湿免疫病", "类风湿关节炎", "系统性红斑狼疮", "强直性脊柱炎",
    "神经系统疾病", "脑血管病", "癫痫", "帕金森病", "头痛",
    "精神心理疾病", "抑郁症", "焦虑症", "睡眠障碍", "双相情感障碍",
    "感染性疾病", "病毒性肝炎", "结核病", "艾滋病", "发热待查",
    "肿瘤疾病", "肺癌", "消化道肿瘤", "乳腺癌", "淋巴瘤",
    "老年病", "慢性病管理", "老年综合征", "姑息治疗",
    "职业病", "中毒", "环境相关疾病",
    "创伤", "骨折", "关节疾病", "运动损伤", "脊柱疾病",
    "普外科疾病", "胃肠外科", "肝胆外科", "乳腺外科", "甲状腺外科",
    "神经外科疾病", "脑肿瘤", "脑血管病外科", "颅脑损伤", "功能神经外科",
    "胸外科疾病", "肺癌", "食管癌", "纵隔肿瘤", "胸壁疾病",
    "心血管外科", "冠心病外科", "心脏瓣膜病", "大血管疾病", "先心病",
    "泌尿外科疾病", "泌尿系统结石", "前列腺疾病", "泌尿系统肿瘤", "男性生殖健康",
    "小儿外科疾病", "先天性畸形", "小儿肿瘤", "小儿创伤",
    "整形美容", "瘢痕修复", "体表肿瘤", "美容整形",
    "烧伤", "创面修复", "瘢痕治疗",
    "神经内科疾病", "脑血管病", "神经免疫病", "神经变性病", "癫痫",
    "消化内科疾病", "胃肠病", "肝病", "胰腺病", "内镜治疗",
    "呼吸内科疾病", "肺部感染", "慢性气道疾病", "肺栓塞", "间质性肺病",
    "心内科疾病", "冠心病", "心律失常", "心力衰竭", "高血压",
    "肾内科疾病", "肾小球疾病", "肾小管疾病", "血液净化", "肾移植",
    "血液内科疾病", "白血病", "淋巴瘤", "骨髓瘤", "贫血",
    "内分泌代谢疾病", "糖尿病", "甲状腺疾病", "垂体肾上腺疾病", "代谢性骨病",
    "风湿免疫疾病", "关节炎", "结缔组织病", "血管炎", "自身免疫病",
    "感染性疾病", "细菌感染", "病毒感染", "真菌感染", "寄生虫病",
    "危重症", "多器官功能衰竭", "脓毒症", "休克", "生命支持",
    "妇科疾病", "妇科肿瘤", "内分泌疾病", "子宫内膜异位症", "盆底疾病",
    "产科", "妊娠并发症", "分娩管理", "产前诊断", "高危妊娠",
    "生殖医学", "不孕不育", "辅助生殖技术", "生殖内分泌",
    "新生儿疾病", "早产儿管理", "新生儿窒息", "新生儿黄疸", "新生儿感染",
    "小儿呼吸疾病", "小儿肺炎", "哮喘", "慢性咳嗽",
    "小儿消化疾病", "小儿腹泻", "消化不良", "胃肠道畸形",
    "小儿心血管疾病", "先心病", "心肌炎", "心律失常",
    "小儿血液疾病", "小儿贫血", "白血病", "出血性疾病",
    "小儿神经疾病", "癫痫", "脑瘫", "发育迟缓",
    "小儿肾病", "肾病综合征", "泌尿系感染", "肾小球疾病",
    "小儿内分泌疾病", "性早熟", "糖尿病", "甲状腺疾病",
    "小儿遗传代谢病", "遗传病筛查", "代谢病诊断",
    "小儿风湿免疫病", "幼年特发性关节炎", "过敏性疾病",
    "眼科疾病", "白内障", "青光眼", "眼底病", "屈光不正",
    "耳鼻喉疾病", "中耳炎", "鼻窦炎", "咽喉疾病", "听力障碍",
    "口腔疾病", "牙体牙髓病", "牙周病", "口腔黏膜病", "口腔颌面外科",
    "皮肤病", "湿疹", "皮炎", "银屑病", "痤疮",
    "性传播疾病", "艾滋病", "梅毒", "淋病", "尖锐湿疣",
    "医学影像诊断", "X线诊断", "CT诊断", "MRI诊断", "超声诊断",
    "超声医学", "腹部超声", "心脏超声", "血管超声", "介入超声",
    "核医学", "核素显像", "核素治疗", "PET/CT",
    "放射治疗", "肿瘤放疗", "立体定向放疗", "近距离放疗",
    "临床检验", "临床生化", "临床免疫", "临床微生物", "分子诊断",
    "病理诊断", "外科病理", "细胞病理", "分子病理", "尸检病理",
    "康复医学", "神经康复", "骨科康复", "心肺康复", "儿童康复",
    "运动医学", "运动损伤", "关节镜", "运动康复",
    "疼痛医学", "慢性疼痛", "癌性疼痛", "神经病理性疼痛",
    "营养支持", "临床营养", "肠内营养", "肠外营养", "代谢营养",
    "麻醉", "临床麻醉", "疼痛管理", "危重症生命支持",
    "健康管理", "健康体检", "慢病管理", "健康咨询",
    "全科医学", "常见病多发病", "慢性病管理", "健康维护",
    "老年医学", "老年综合评估", "老年综合征", "老年慢病管理",
    "姑息治疗", "临终关怀", "癌性疼痛控制", "症状管理",
    "职业病防治", "职业中毒", "尘肺病", "职业健康体检",
    "地方病", "碘缺乏病", "地方性氟中毒", "大骨节病",
    "急诊内科", "急诊创伤", "急诊危重症", "中毒急救",
    "院前急救", "灾害医学", "心肺复苏", "创伤急救"
]

# 科室数据结构定义
DEPARTMENT_DATA = {
    "内科": {
        "二级": [
            "心血管内科", "消化内科", "呼吸内科", "肾内科", "内分泌科",
            "血液内科", "风湿免疫科", "感染科", "神经内科", "老年医学科",
            "肿瘤内科", "职业病科", "变态反应科", "心理科", "重症医学科"
        ],
        "三级": {
            "心血管内科": ["CCU", "心脏介入中心", "高血压门诊", "心力衰竭门诊", "心律失常门诊"],
            "消化内科": ["内镜中心", "胃肠动力中心", "肝病门诊", "胰腺疾病门诊", "炎症性肠病门诊"],
            "呼吸内科": ["呼吸介入中心", "睡眠中心", "肺功能室", "哮喘门诊", "慢阻肺门诊"],
            "肾内科": ["血液净化中心", "腹透中心", "肾活检门诊", "血管通路门诊", "肾移植门诊"],
            "内分泌科": ["糖尿病门诊", "甲状腺门诊", "骨质疏松门诊", "肥胖门诊", "垂体肾上腺门诊"],
            "血液内科": ["白血病门诊", "淋巴瘤门诊", "骨髓瘤门诊", "贫血门诊", "出血性疾病门诊"],
            "风湿免疫科": ["关节炎门诊", "红斑狼疮门诊", "血管炎门诊", "肌炎门诊", "干燥综合征门诊"],
            "神经内科": ["卒中中心", "癫痫中心", "帕金森门诊", "头痛门诊", "睡眠障碍门诊"],
            "肿瘤内科": ["肺癌门诊", "消化道肿瘤门诊", "乳腺癌门诊", "淋巴瘤门诊", "靶向治疗门诊"]
        }
    },
    "外科": {
        "二级": [
            "普外科", "神经外科", "胸外科", "心血管外科", "泌尿外科",
            "骨科", "整形外科", "烧伤科", "小儿外科", "器官移植科"
        ],
        "三级": {
            "普外科": ["胃肠外科", "肝胆外科", "乳腺外科", "甲状腺外科", "肛肠外科", "疝外科"],
            "神经外科": ["脑肿瘤中心", "脑血管病中心", "颅脑创伤中心", "功能神经外科", "脊柱外科"],
            "胸外科": ["肺外科", "食管外科", "纵隔外科", "胸壁外科", "气管外科"],
            "心血管外科": ["冠脉外科", "瓣膜外科", "大血管外科", "先心病外科", "微创心脏外科"],
            "泌尿外科": ["泌尿系结石科", "泌尿系肿瘤科", "男科", "肾移植科", "女性泌尿外科"],
            "骨科": ["脊柱外科", "关节外科", "创伤骨科", "手足外科", "运动医学科", "小儿骨科"]
        }
    },
    "妇产科": {
        "二级": ["妇科", "产科", "生殖医学科", "计划生育科"],
        "三级": {
            "妇科": ["妇科肿瘤科", "妇科内分泌科", "子宫内膜异位症科", "盆底康复科", "宫颈疾病科"],
            "产科": ["产前诊断科", "高危产科", "胎儿医学科", "产后康复科"],
            "生殖医学科": ["不孕不育门诊", "辅助生殖中心", "生殖内分泌门诊", "遗传咨询门诊"]
        }
    },
    "儿科": {
        "二级": [
            "新生儿科", "小儿呼吸科", "小儿消化科", "小儿心血管科",
            "小儿血液科", "小儿神经科", "小儿肾脏科", "小儿内分泌科",
            "小儿风湿免疫科", "小儿感染科", "儿童保健科", "小儿重症医学科"
        ],
        "三级": {
            "新生儿科": ["新生儿重症监护", "早产儿门诊", "新生儿黄疸门诊", "新生儿感染门诊"],
            "小儿呼吸科": ["哮喘门诊", "慢性咳嗽门诊", "呼吸介入门诊"],
            "小儿神经科": ["癫痫门诊", "脑瘫康复门诊", "神经肌肉病门诊"],
            "儿童保健科": ["生长发育门诊", "营养门诊", "心理行为门诊", "智力发育门诊"]
        }
    },
    "五官科": {
        "二级": ["眼科", "耳鼻喉科", "口腔科"],
        "三级": {
            "眼科": ["白内障科", "青光眼科", "眼底病科", "眼视光科", "眼表疾病科", "眼整形科", "斜弱视科"],
            "耳鼻喉科": ["耳科", "鼻科", "咽喉科", "头颈外科", "听力障碍门诊", "眩晕门诊"],
            "口腔科": ["牙体牙髓科", "牙周科", "口腔黏膜科", "口腔颌面外科", "口腔修复科", "口腔正畸科", "口腔种植科"]
        }
    },
    "皮肤性病科": {
        "二级": ["皮肤科", "性病科", "医学美容科"],
        "三级": {
            "皮肤科": ["皮肤病门诊", "皮肤外科", "皮肤病理科", "真菌病门诊", "过敏门诊"],
            "医学美容科": ["激光美容门诊", "注射美容门诊", "皮肤护理门诊", "瘢痕治疗门诊"]
        }
    },
    "医技科室": {
        "二级": [
            "放射科", "超声科", "核医学科", "检验科", "病理科",
            "输血科", "药剂科", "营养科", "康复医学科", "高压氧科",
            "麻醉科", "疼痛科", "运动医学科", "体检中心", "输血科"
        ],
        "三级": {
            "放射科": ["X线诊断室", "CT室", "MRI室", "介入放射科", "乳腺影像室"],
            "超声科": ["腹部超声室", "心脏超声室", "血管超声室", "妇产科超声室", "介入超声室"],
            "检验科": ["临床生化室", "临床免疫室", "临床微生物室", "临床血液室", "分子诊断室"],
            "病理科": ["外科病理室", "细胞病理室", "分子病理室", "电镜室", "尸检室"],
            "康复医学科": ["神经康复室", "骨科康复室", "心肺康复室", "儿童康复室", "言语治疗室"],
            "麻醉科": ["临床麻醉室", "疼痛门诊", "麻醉复苏室", "体外循环室"],
            "体检中心": ["健康体检部", "职业病体检部", "入职体检部", "高端体检部"]
        }
    },
    "中医科": {
        "二级": ["中医内科", "中医外科", "中医妇科", "中医儿科", "中医骨伤科", "针灸科", "推拿科"],
        "三级": {
            "中医内科": ["中医脾胃病科", "中医心血管科", "中医呼吸科", "中医肾病科", "中医肿瘤科"],
            "针灸科": ["针灸门诊", "针刀门诊", "埋线门诊", "艾灸门诊"],
            "推拿科": ["成人推拿门诊", "小儿推拿门诊", "运动损伤推拿门诊"]
        }
    },
    "精神心理科": {
        "二级": ["精神科", "心理咨询科", "心身医学科"],
        "三级": {
            "精神科": ["情感障碍科", "焦虑障碍科", "精神分裂症科", "成瘾医学科", "老年精神科"],
            "心理咨询科": ["个体心理咨询", "团体心理咨询", "家庭治疗", "儿童心理门诊"]
        }
    },
    "急诊医学": {
        "二级": ["急诊内科", "急诊外科", "急诊儿科", "急诊妇产科", "院前急救科"],
        "三级": {
            "急诊内科": ["急诊重症监护室", "中毒救治中心", "发热门诊"],
            "院前急救科": ["救护车队", "空中救援中心", "急救培训中心"]
        }
    },
    "全科医学": {
        "二级": ["全科医学科", "社区医疗科", "家庭医学科", "健康管理科"],
        "三级": {
            "全科医学科": ["全科门诊", "慢病管理门诊", "健康咨询门诊"]
        }
    },
    "老年医学": {
        "二级": ["老年综合科", "老年心血管科", "老年神经科", "老年呼吸科", "老年内分泌科"],
        "三级": {
            "老年综合科": ["老年综合征门诊", "老年康复门诊", "老年营养门诊", "老年安宁疗护门诊"]
        }
    },
    "传染病科": {
        "二级": ["感染性疾病科", "肝病科", "结核病科", "艾滋病科"],
        "三级": {
            "感染性疾病科": ["发热门诊", "肠道门诊", "呼吸道门诊", "感染重症监护室"],
            "肝病科": ["肝炎门诊", "肝硬化门诊", "肝癌门诊", "肝移植门诊"]
        }
    },
    "临终关怀": {
        "二级": ["姑息治疗科", "临终关怀科", "安宁疗护科"],
        "三级": {
            "姑息治疗科": ["癌痛门诊", "症状管理门诊", "心理支持门诊", "居家安宁疗护"]
        }
    },
    "职业病": {
        "二级": ["职业病科", "中毒科", "尘肺科", "职业健康监护科"],
        "三级": {
            "职业病科": ["职业中毒门诊", "尘肺病门诊", "职业性噪声聋门诊", "职业性眼病门诊"]
        }
    }
}

# 职称配置
TITLE_CONFIG = {
    "主任医师": {"count": 300, "min_price": 100, "max_price": 300, "min_exp": 15, "max_exp": 40},
    "副主任医师": {"count": 500, "min_price": 60, "max_price": 150, "min_exp": 10, "max_exp": 20},
    "主治医师": {"count": 700, "min_price": 30, "max_price": 80, "min_exp": 5, "max_exp": 12},
    "住院医师": {"count": 400, "min_price": 15, "max_price": 50, "min_exp": 1, "max_exp": 5},
    "医师": {"count": 100, "min_price": 10, "max_price": 30, "min_exp": 0, "max_exp": 3}
}

# 一级科室列表（不含医技）
PRIMARY_DEPARTMENTS = [
    "内科", "外科", "妇产科", "儿科", "五官科", "皮肤性病科",
    "中医科", "精神心理科", "急诊医学", "全科医学",
    "老年医学", "传染病科", "临终关怀", "职业病"
]


def generate_name():
    """生成随机姓名"""
    surname = random.choice(SURNAMES)
    if random.random() < 0.6:
        # 单名
        first_name = random.choice(MALE_NAMES if random.random() < 0.5 else FEMALE_NAMES)
        return surname + first_name
    else:
        # 双名
        first = random.choice(MALE_NAMES[:20] if random.random() < 0.5 else FEMALE_NAMES[:20])
        second = random.choice(MALE_NAMES[:30] if random.random() < 0.5 else FEMALE_NAMES[:30])
        return surname + first + second


def generate_departments():
    """生成科室列表"""
    departments = []
    dept_id = 1

    # 添加一级科室
    for primary in PRIMARY_DEPARTMENTS:
        departments.append({
            "id": f"D{dept_id:04d}",
            "name": primary,
            "level": "一级",
            "parent_id": None,
            "description": f"{primary}相关疾病诊疗"
        })
        dept_id += 1

    # 添加医技一级科室
    departments.append({
        "id": f"D{dept_id:04d}",
        "name": "医技科室",
        "level": "一级",
        "parent_id": None,
        "description": "医学技术辅助科室"
    })
    med_tech_parent_id = f"D{dept_id:04d}"
    dept_id += 1

    # 生成二级和三级科室
    for category, data in DEPARTMENT_DATA.items():
        if category not in PRIMARY_DEPARTMENTS and category != "医技科室":
            continue

        parent_name = category if category in PRIMARY_DEPARTMENTS else "医技科室"
        parent_depts = [d for d in departments if d["name"] == parent_name]
        if not parent_depts:
            continue
        parent_id = parent_depts[0]["id"]

        for level2 in data["二级"]:
            # 二级科室
            level2_id = f"D{dept_id:04d}"
            departments.append({
                "id": level2_id,
                "name": level2,
                "level": "二级",
                "parent_id": parent_id,
                "description": f"{level2}相关疾病诊疗"
            })
            dept_id += 1

            # 三级科室
            if level2 in data.get("三级", {}):
                for level3 in data["三级"][level2]:
                    departments.append({
                        "id": f"D{dept_id:04d}",
                        "name": level3,
                        "level": "三级",
                        "parent_id": level2_id,
                        "description": f"{level3}专业诊疗"
                    })
                    dept_id += 1

    # 补充到200个科室
    while len(departments) < 200:
        dept_id = len(departments) + 1
        departments.append({
            "id": f"D{dept_id:04d}",
            "name": f"专科科室{dept_id}",
            "level": "二级",
            "parent_id": departments[0]["id"],  # 默认挂到内科下
            "description": f"专科科室{dept_id}相关诊疗"
        })

    return departments[:200]


def generate_education(exp_years):
    """根据从业年限生成教育背景"""
    if exp_years < 3:
        return f"{random.choice(MEDICAL_SCHOOLS)} 临床医学 本科"
    elif exp_years < 10:
        degree = random.choice(["硕士", "博士研究生"])
        return f"{random.choice(MEDICAL_SCHOOLS)} 内科学 {degree}"
    elif exp_years < 20:
        degree = random.choice(["硕士", "博士", "博士"])
        return f"{random.choice(MEDICAL_SCHOOLS)} 内科学 {degree}"
    else:
        return f"{random.choice(MEDICAL_SCHOOLS)} 内科学 博士"


def generate_doctors(departments):
    """生成医生列表"""
    doctors = []
    doctor_id = 1

    # 按职称生成医生
    for title, config in TITLE_CONFIG.items():
        count = config["count"]

        for i in range(count):
            # 选择科室
            # 优先选择二级和三级科室
            valid_depts = [d for d in departments if d["level"] in ["二级", "三级"]]
            if not valid_depts:
                valid_depts = departments

            # 根据职称权重分配科室（主任医师更多在三级科室）
            if title == "主任医师":
                weighted_depts = [d for d in valid_depts if d["level"] == "三级"]
                if not weighted_depts:
                    weighted_depts = valid_depts
            elif title in ["副主任医师", "主治医师"]:
                weighted_depts = valid_depts
            else:
                weighted_depts = [d for d in valid_depts if d["level"] == "二级"]
                if not weighted_depts:
                    weighted_depts = valid_depts

            dept = random.choice(weighted_depts)

            # 生成信息
            exp_years = random.randint(config["min_exp"], config["max_exp"])
            price = random.randint(config["min_price"], config["max_price"])

            # 确定性别（某些科室倾向）
            if dept["name"] in ["妇产科", "妇科", "产科", "生殖医学科"]:
                gender = random.choices(["男", "女"], weights=[0.3, 0.7])[0]
            elif dept["name"] in ["泌尿外科", "男科"]:
                gender = random.choices(["男", "女"], weights=[0.8, 0.2])[0]
            else:
                gender = random.choice(["男", "女"])

            # 生成姓名
            name = generate_name()
            while gender == "男" and any(c in name for c in FEMALE_NAMES[:20]):
                name = generate_name()
            while gender == "女" and any(c in name for c in MALE_NAMES[:20]):
                name = generate_name()

            # 专科方向
            specialty_keywords = [k for k in SPECIALTY_KEYWORDS if any(kw in dept["name"] for kw in [
                "心血管", "消化", "呼吸", "肾", "内分泌", "血液", "风湿", "神经",
                "肿瘤", "老年", "职业", "普外", "神外", "胸外", "心外", "泌尿",
                "骨", "整形", "烧伤", "小儿", "妇产", "产科", "生殖", "新生",
                "眼", "耳鼻喉", "口腔", "皮肤", "性病", "美容", "放射", "超声",
                "核医学", "检验", "病理", "康复", "疼痛", "麻醉", "体检",
                "中医", "针灸", "推拿", "精神", "心理", "急诊", "全科", "传染",
                "姑息", "临终"
            ])]

            if not specialty_keywords:
                # 根据科室名推断专科方向
                if "心" in dept["name"] or "心血管" in dept["name"]:
                    specialty_keywords = ["心血管疾病", "高血压", "冠心病", "心律失常", "心力衰竭"]
                elif "消化" in dept["name"] or "胃肠" in dept["name"] or "肝胆" in dept["name"]:
                    specialty_keywords = ["消化系统疾病", "胃肠疾病", "肝病", "胰腺疾病"]
                elif "呼吸" in dept["name"] or "肺" in dept["name"]:
                    specialty_keywords = ["呼吸系统疾病", "慢性阻塞性肺病", "哮喘", "肺部感染"]
                elif "内分泌" in dept["name"] or "代谢" in dept["name"]:
                    specialty_keywords = ["内分泌疾病", "糖尿病", "甲状腺疾病", "代谢综合征"]
                elif "神经" in dept["name"]:
                    specialty_keywords = ["神经系统疾病", "脑血管病", "癫痫", "帕金森病"]
                elif "肿瘤" in dept["name"]:
                    specialty_keywords = ["肿瘤疾病", "肺癌", "消化道肿瘤", "淋巴瘤"]
                elif "骨" in dept["name"] or "关节" in dept["name"]:
                    specialty_keywords = ["骨折", "关节疾病", "运动损伤", "脊柱疾病"]
                elif "妇产" in dept["name"] or "产科" in dept["name"] or "妇科" in dept["name"]:
                    specialty_keywords = ["妇科疾病", "妊娠并发症", "分娩管理", "产前诊断"]
                elif "儿" in dept["name"]:
                    specialty_keywords = ["新生儿疾病", "小儿呼吸疾病", "小儿消化疾病", "小儿心血管疾病"]
                elif "眼" in dept["name"]:
                    specialty_keywords = ["白内障", "青光眼", "眼底病", "屈光不正"]
                elif "耳鼻喉" in dept["name"]:
                    specialty_keywords = ["中耳炎", "鼻窦炎", "咽喉疾病", "听力障碍"]
                elif "口腔" in dept["name"]:
                    specialty_keywords = ["牙体牙髓病", "牙周病", "口腔黏膜病", "口腔颌面外科"]
                elif "皮肤" in dept["name"]:
                    specialty_keywords = ["皮肤病", "湿疹", "皮炎", "银屑病"]
                elif "精神" in dept["name"] or "心理" in dept["name"]:
                    specialty_keywords = ["精神心理疾病", "抑郁症", "焦虑症", "睡眠障碍"]
                elif "急诊" in dept["name"]:
                    specialty_keywords = ["急诊救治", "危重症", "创伤急救", "中毒急救"]
                elif "中医" in dept["name"]:
                    specialty_keywords = ["中医内科", "中医调理", "针灸推拿", "中医养生"]
                elif "康复" in dept["name"]:
                    specialty_keywords = ["神经康复", "骨科康复", "心肺康复", "康复训练"]
                else:
                    specialty_keywords = ["常见病多发病", "慢性病管理", "健康咨询", "疾病预防"]

            specialty = random.choice(specialty_keywords) if specialty_keywords else "常见病诊疗"

            doctors.append({
                "id": f"D{doctor_id:06d}",
                "name": name,
                "gender": gender,
                "title": title,
                "department_id": dept["id"],
                "department_name": dept["name"],
                "specialty": specialty,
                "experience_years": exp_years,
                "education": generate_education(exp_years),
                "consultation_price": price,
                "rating": round(random.uniform(3.5, 5.0), 1),
                "consultation_count": random.randint(0, 10000),
                "introduction": f"从事{dept['name']}临床工作{exp_years}年，擅长{specialty}的诊治。",
                "is_available": random.choice([True, True, True, False])
            })
            doctor_id += 1

    # 打乱医生顺序
    random.shuffle(doctors)

    # 重新分配ID
    for i, doc in enumerate(doctors, 1):
        doc["id"] = f"D{i:06d}"

    return doctors


def ensure_department_has_doctors(departments, doctors):
    """确保每个科室至少有5名医生"""
    dept_doctor_count = {}

    for doc in doctors:
        dept_id = doc["department_id"]
        dept_doctor_count[dept_id] = dept_doctor_count.get(dept_id, 0) + 1

    # 找出医生不足的科室
    shortage_depts = [d for d in departments if dept_doctor_count.get(d["id"], 0) < 5]

    if shortage_depts:
        # 从医生多的科室调配医生
        doctor_id = len(doctors) + 1

        for dept in shortage_depts:
            needed = 5 - dept_doctor_count.get(dept["id"], 0)

            for i in range(needed):
                exp_years = random.randint(1, 20)
                title_candidates = []

                if exp_years >= 15:
                    title_candidates = ["主任医师", "副主任医师", "主治医师"]
                elif exp_years >= 10:
                    title_candidates = ["副主任医师", "主治医师", "住院医师"]
                elif exp_years >= 5:
                    title_candidates = ["主治医师", "住院医师", "医师"]
                else:
                    title_candidates = ["住院医师", "医师"]

                title = random.choice(title_candidates)

                gender = random.choice(["男", "女"])
                name = generate_name()

                # 专科方向
                specialty = "常见病诊疗"
                if "心" in dept["name"] or "心血管" in dept["name"]:
                    specialty = random.choice(["心血管疾病", "高血压", "冠心病", "心律失常", "心力衰竭"])
                elif "消化" in dept["name"]:
                    specialty = random.choice(["消化系统疾病", "胃肠疾病", "肝病"])
                elif "呼吸" in dept["name"]:
                    specialty = random.choice(["呼吸系统疾病", "慢性阻塞性肺病", "哮喘"])

                doctors.append({
                    "id": f"D{doctor_id:06d}",
                    "name": name,
                    "gender": gender,
                    "title": title,
                    "department_id": dept["id"],
                    "department_name": dept["name"],
                    "specialty": specialty,
                    "experience_years": exp_years,
                    "education": generate_education(exp_years),
                    "consultation_price": random.randint(20, 100),
                    "rating": round(random.uniform(3.5, 5.0), 1),
                    "consultation_count": random.randint(0, 5000),
                    "introduction": f"从事{dept['name']}临床工作{exp_years}年，擅长{specialty}的诊治。",
                    "is_available": random.choice([True, True, True, False])
                })
                doctor_id += 1

    return doctors


def main():
    """主函数"""
    print("开始生成科室和医生数据...")

    # 创建输出目录
    output_dir = "D:/Users/liu.liu/Desktop/github/medical/data/departments"
    os.makedirs(output_dir, exist_ok=True)

    # 生成科室
    print("生成科室数据...")
    departments = generate_departments()
    print(f"  生成 {len(departments)} 个科室")

    # 生成医生
    print("生成医生数据...")
    doctors = generate_doctors(departments)
    print(f"  生成 {len(doctors)} 名医生")

    # 确保每个科室至少5名医生
    print("调整科室医生分布...")
    doctors = ensure_department_has_doctors(departments, doctors)
    print(f"  调整后共 {len(doctors)} 名医生")

    # 统计
    title_count = {}
    for doc in doctors:
        title_count[doc["title"]] = title_count.get(doc["title"], 0) + 1

    print("\n医生职称分布:")
    for title, count in title_count.items():
        print(f"  {title}: {count}人")

    # 统计科室医生数
    dept_doctor_count = {}
    for doc in doctors:
        dept_id = doc["department_id"]
        dept_doctor_count[dept_id] = dept_doctor_count.get(dept_id, 0) + 1

    min_doctors = min(dept_doctor_count.values())
    max_doctors = max(dept_doctor_count.values())
    avg_doctors = sum(dept_doctor_count.values()) / len(dept_doctor_count)

    print(f"\n科室医生统计:")
    print(f"  最少: {min_doctors}人")
    print(f"  最多: {max_doctors}人")
    print(f"  平均: {avg_doctors:.1f}人")

    # 保存文件
    departments_file = os.path.join(output_dir, "departments.json")
    doctors_file = os.path.join(output_dir, "doctors.json")

    with open(departments_file, "w", encoding="utf-8") as f:
        json.dump(departments, f, ensure_ascii=False, indent=2)

    with open(doctors_file, "w", encoding="utf-8") as f:
        json.dump(doctors, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存:")
    print(f"  {departments_file}")
    print(f"  {doctors_file}")


if __name__ == "__main__":
    main()
