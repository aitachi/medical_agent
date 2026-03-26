# 医疗智能助手 - 数据需求规范文档 v2.0

**版本**: v2.0
**生成时间**: 2026-03-26
**用途**: 系统数据填充和初始化规范
**适用系统**: 医疗智能助手完整版

---

## 目录

1. [数据总体要求](#1-数据总体要求)
2. [医学知识库数据](#2-医学知识库数据)
3. [医院科室数据](#3-医院科室数据)
4. [医生信息数据](#4-医生信息数据)
5. [患者信息数据](#5-患者信息数据)
6. [药品数据库](#6-药品数据库)
7. [检查检验数据](#7-检查检验数据)
8. [病理学数据](#8-病理学数据)
9. [疾病诊疗档案](#9-疾病诊疗档案)
10. [慢病管理数据](#10-慢病管理数据)
11. [随访计划数据](#11-随访计划数据)
12. [在线问诊数据](#12-在线问诊数据)
13. [急救指南数据](#13-急救指南数据)
14. [体检套餐数据](#14-体检套餐数据)
15. [提醒服务数据](#15-提醒服务数据)
16. [系统配置数据](#16-系统配置数据)
17. [数据质量标准](#17-数据质量标准)

---

## 1. 数据总体要求

### 1.1 数据规模要求

| 数据类型 | 最小条数 | 推荐条数 | 目标条数 | 说明 |
|----------|----------|----------|----------|------|
| **知识库类** |
| 症状知识 | 50 | 100 | 200+ | 覆盖常见症状 |
| 疾病知识 | 100 | 300 | 500+ | ICD-10常见疾病 |
| 检查项目 | 80 | 150 | 300+ | 包含参考范围 |
| 药品信息 | 500 | 2000 | 10000+ | 常用药品为主 |
| **医院类** |
| 医院信息 | 10 | 50 | 100+ | 三级医院为主 |
| 科室信息 | 30 | 100 | 200+ | 含亚专科 |
| 医生信息 | 100 | 500 | 2000+ | 每科室至少5人 |
| **患者类** |
| 患者基本信息 | 1000 | 10000 | 50000+ | 测试/演示数据 |
| 健康档案 | 1000 | 10000 | 50000+ | 对应患者 |
| 门诊记录 | 5000 | 50000 | 200000+ | 每患者平均5条 |
| 住院记录 | 500 | 5000 | 20000+ | 重症患者为主 |
| **专科类** |
| 病理报告 | 200 | 1000 | 5000+ | 含诊断结果 |
| 影像检查 | 1000 | 5000 | 20000+ | 各类影像 |
| 检验报告 | 5000 | 20000 | 100000+ | 各类检验 |
| **管理类** |
| 随访计划 | 200 | 1000 | 5000+ | 慢病患者 |
| 随访记录 | 1000 | 10000 | 50000+ | 对应计划 |
| 预约记录 | 2000 | 10000 | 50000+ | 历史预约 |
| 提醒记录 | 5000 | 20000 | 100000+ | 各类提醒 |

### 1.2 数据更新频率要求

| 数据类型 | 更新频率 | 数据源 | 说明 |
|----------|----------|--------|------|
| 医学知识 | 每季度 | 权威指南 | 跟踪最新临床指南 |
| 药品信息 | 每月 | 药监局 | 新批/撤市药品 |
| 医生信息 | 每周 | 医院人事 | 排班/职称变动 |
| 急救指南 | 每年 | 急救协会 | 急救规范更新 |
| 体检套餐 | 每季度 | 体检中心 | 套餐调整 |
| 患者数据 | 实时 | 业务系统 | 就诊产生 |

---

## 2. 医学知识库数据

### 2.1 症状知识数据 (目标: 200条)

```json
{
  "symptoms": {
    "total_count": 200,
    "categories": {
      "全身症状": {
        "count": 20,
        "examples": ["发热", "乏力", "消瘦", "水肿", "肥胖"],
        "required_fields": ["症状名称", "描述", "常见原因", "红旗征", "推荐科室"]
      },
      "呼吸系统": {
        "count": 25,
        "examples": ["咳嗽", "咳痰", "呼吸困难", "胸痛", "咯血"],
        "required_fields": ["症状名称", "类型(干/湿)", "持续时间分级", "伴随症状"]
      },
      "心血管系统": {
        "count": 20,
        "examples": ["心悸", "胸闷", "水肿", "晕厥", "发绀"]
      },
      "消化系统": {
        "count": 30,
        "examples": ["腹痛", "恶心", "呕吐", "腹泻", "便秘", "黄疸", "吞咽困难"]
      },
      "神经系统": {
        "count": 35,
        "examples": ["头痛", "头晕", "失眠", "抽搐", "震颤", "意识障碍"]
      },
      "内分泌代谢": {
        "count": 20,
        "examples": ["多饮", "多尿", "多食", "怕热", "畏寒"]
      },
      "泌尿生殖": {
        "count": 25,
        "examples": ["尿频", "尿急", "尿痛", "血尿", "排尿困难"]
      },
      "血液系统": {
        "count": 15,
        "examples": ["贫血", "出血", "淋巴结肿大", "脾大"]
      },
      "运动系统": {
        "count": 10,
        "examples": ["关节痛", "肌肉痛", "活动受限", "畸形"]
      }
    },
    "data_structure": {
      "id": "string (SYM001-200)",
      "name": "string 必填",
      "aliases": "array 同义词",
      "category": "string 分类",
      "description": "string 描述",
      "common_causes": "array 常见原因(3-5个)",
      "red_flags": "array 危险信号(至少2个)",
      "recommended_department": "string 首选科室",
      "alternative_departments": "array 备选科室",
      "self_care": "array 自我护理建议",
      "related_symptoms": "array 相关症状",
      "severity_levels": "object 严重程度分级"
    }
  }
}
```

### 2.2 疾病知识数据 (目标: 500条)

```json
{
  "diseases": {
    "total_count": 500,
    "distribution": {
      "心血管疾病": 50,
      "呼吸系统疾病": 40,
      "消化系统疾病": 50,
      "内分泌代谢病": 40,
      "神经系统疾病": 40,
      "泌尿系统疾病": 30,
      "血液系统疾病": 25,
      "风湿免疫病": 25,
      "感染性疾病": 50,
      "肿瘤": 40,
      "妇产科疾病": 30,
      "儿科疾病": 30,
      "外科疾病": 40,
      "五官科疾病": 10
    },
    "required_fields": {
      "basic": ["疾病名称", "ICD编码", "疾病分类"],
      "clinical": ["诊断标准", "症状", "治疗方法"],
      "education": ["预防措施", "健康指导"]
    },
    "data_structure": {
      "id": "string (DIS001-500)",
      "name": "string 疾病名称",
      "aliases": "array 别名",
      "icd_code": "string ICD-10编码",
      "category": "string 疾病分类",
      "description": "string 疾病描述",
      "prevalence": {
        "incidence": "string 发病率",
        "population": "string 好发人群"
      },
      "diagnostic_criteria": {
        "definite": "string 确诊标准",
        "suspected": "string 疑诊标准"
      },
      "symptoms": {
        "typical": "array 典型症状",
        "atypical": "array 不典型症状",
        "complications": "array 并发症"
      },
      "examinations": {
        "lab": "array 实验室检查",
        "imaging": "array 影像学检查",
        "pathology": "array 病理检查"
      },
      "treatment": {
        "medication": "array 药物治疗",
        "surgery": "array 手术治疗",
        "lifestyle": "array 生活方式干预"
      },
      "prevention": {
        "primary": "array 一级预防",
        "secondary": "array 二级预防",
        "tertiary": "array 三级预防"
      },
      "prognosis": {
        "general": "string 总体预后",
        "factors": "array 预后因素"
      }
    }
  }
}
```

---

## 3. 医院科室数据

### 3.1 科室信息 (目标: 200个科室)

```json
{
  "departments": {
    "total_count": 200,
    "structure": {
      "临床科室": {
        "count": 150,
        "internal_medicine": {
          "count": 40,
          "sub_departments": [
            "心血管内科(含CCU)",
            "消化内科(含内镜中心)",
            "呼吸内科(含呼吸ICU)",
            "内分泌科",
            "肾内科(含血透中心)",
            "血液科",
            "风湿免疫科",
            "感染科",
            "神经内科(含卒中中心)",
            "肿瘤内科",
            "老年医学科",
            "康复医学科",
            "全科医疗科",
            "职业病科",
            "中西医结合科",
            "重症医学科(ICU)",
            "急诊科",
            "传染病科",
            "精神科",
            "心理科"
          ],
          "min_doctors_per_sub": 10
        },
        "surgery": {
          "count": 35,
          "sub_departments": [
            "普外科(含肝胆胰胃肠)",
            "骨科(含创伤关节脊柱)",
            "神经外科",
            "胸外科",
            "心血管外科",
            "泌尿外科",
            "整形外科",
            "烧伤科",
            "器官移植科"
          ],
          "min_doctors_per_sub": 8
        },
        "obstetrics_gynecology": {
          "count": 15,
          "sub_departments": [
            "产科(含产房)",
            "妇科",
            "生殖内分泌科",
            "计划生育科",
            "妇科肿瘤"
          ],
          "min_doctors_per_sub": 8
        },
        "pediatrics": {
          "count": 20,
          "sub_departments": [
            "新生儿科",
            "儿内科",
            "儿外科",
            "儿童保健科",
            "小儿急诊科"
          ],
          "min_doctors_per_sub": 6
        },
        "specialized": {
          "count": 40,
          "sub_departments": [
            "眼科",
            "耳鼻喉科",
            "口腔科",
            "皮肤性病科",
            "医学美容科",
            "性病科",
            "麻醉科",
            "疼痛科",
            "营养科",
            "核医学科"
          ]
        }
      },
      "医技科室": {
        "count": 30,
        "departments": [
          "放射科(含CT/MRI)",
          "超声科",
          "核医学科",
          "检验科",
          "病理科",
          "输血科",
          "药剂科",
          "理疗科",
          "高压氧科",
          "体检中心"
        ]
      },
      "护理科室": {
        "count": 20,
        "departments": [
          "门诊护理",
          "急诊护理",
          "住院护理",
          "手术室护理",
          "ICU护理",
          "消毒供应中心"
        ]
      }
    },
    "data_structure": {
      "id": "string (DEPT001-200)",
      "name": "string 科室名称",
      "parent_id": "string 上级科室ID",
      "level": "string 1=一级科室,2=二级科室,3=三级专科",
      "category": "string 临床/医技/护理/行政",
      "description": "string 科室介绍",
      "specialties": "array 专科特色(至少3项)",
      "common_symptoms": "array 常见症状(10+项)",
      "examinations": "array 开展检查",
      "treatments": "array 开展治疗",
      "equipment": "array 主要设备",
      "location": {
        "building": "string 院区/楼栋",
        "floor": "string 楼层",
        "area": "string 区域"
      },
      "contact": {
        "phone": "string 科室电话",
        "extension": "string 分机号"
      },
      "service_hours": {
        "outpatient": "string 门诊时间",
        "emergency": "string 急诊时间",
        "inpatient": "string 住院时间"
      }
    }
  }
}
```

### 3.2 科室治疗档案 (目标: 每科室至少50份)

```json
{
  "department_records": {
    "template": {
      "department_id": "string",
      "record_id": "string",
      "patient_case": {
        "chief_complaint": "string 主诉",
        "diagnosis": {
          "primary": "string 主要诊断",
          "secondary": "array 次要诊断",
          "icd_codes": "array ICD编码"
        },
        "treatment_plan": {
          "medication": "array 药物治疗",
          "surgery": "array 手术治疗",
          "other": "array 其他治疗"
        },
        "outcome": {
          "result": "string 治愈/好转/未愈/死亡",
          "length_of_stay": "integer 住院天数",
          "cost": "number 医疗费用"
        }
      },
      "clinical_pathway": {
        "pathway_id": "string",
        "stage": "string",
        "variations": "array 变异记录"
      }
    },
    "requirements": {
      "minimum_records_per_department": 50,
      "coverage": "常见疾病谱80%以上",
      "completeness": "关键字段100%填写"
    }
  }
}
```

---

## 4. 医生信息数据

### 4.1 医生基本信息 (目标: 2000条)

```json
{
  "doctors": {
    "total_count": 2000,
    "distribution": {
      "by_title": {
        "主任医师": 300,
        "副主任医师": 500,
        "主治医师": 700,
        "住院医师": 400,
        "医师": 100
      },
      "by_department": {
        "内科系统": 600,
        "外科系统": 500,
        "妇产科": 150,
        "儿科": 150,
        "急诊科": 100,
        "医技科室": 300,
        "其他": 200
      },
      "by_experience": {
        "10年以下": 500,
        "10-20年": 800,
        "20-30年": 500,
        "30年以上": 200
      }
    },
    "data_structure": {
      "doctor_id": "string (D0001-D2000)",
      "basic_info": {
        "name": "string 医生姓名",
        "gender": "string 男/女",
        "birth_date": "date 出生日期",
        "id_card": "string 身份证号",
        "phone": "string 手机号",
        "email": "string 邮箱",
        "avatar": "string 头像URL"
      },
      "professional": {
        "hospital_id": "string 医院ID",
        "department_id": "string 科室ID",
        "title": "string 职称",
        "position": "string 职务",
        "specialty": "string 专科方向",
        "sub_specialties": "array 亚专科方向",
        "experience_years": "integer 从业年限",
        "education": {
          "degree": "string 学位",
          "school": "string 毕业院校",
          "major": "string 专业",
          "graduation_year": "integer 毕业年份"
        },
        "certifications": {
          "license_number": "string 执业证号",
          "qualification": "string 资格证号",
          "title_certificate": "string 职称证号"
        }
      },
      "clinical": {
        "outpatient_hours": "array 门诊时段",
        "ward_responsibility": "array 负责病区",
        "surgery_types": "array 擅长手术",
        "expertise": "array 擅长疾病(至少5项)",
        "academic_positions": "array 学术任职",
        "research_fields": "array 研究方向",
        "publications": {
          "total": "integer 发表论文数",
          "sci": "integer SCI论文数",
          "core": "integer 核心期刊数"
        }
      },
      "service": {
        "consultation_types": "array 图文/视频/电话",
        "response_time": "integer 平均响应时间(分钟)",
        "consultation_count": "integer 累计咨询数",
        "rating": {
          "overall": "float 总评分(0-5)",
          "count": "integer 评价数",
          "details": {
            "professional": "float 专业度",
            "attitude": "float 服务态度",
            "effectiveness": "float 治疗效果"
          }
        },
        "price": {
          "text": "integer 图文咨询价格",
          "video": "integer 视频咨询价格",
          "phone": "integer 电话咨询价格"
        }
      },
      "schedule": {
        "weekly": "object 每周排班",
        "notice": "string 停诊通知"
      }
    },
    "quality_requirements": {
      "mandatory_fields": [
        "医生ID",
        "姓名",
        "医院",
        "科室",
        "职称",
        "执业证号"
      ],
      "update_frequency": "每周更新排班",
      "data_source": "医院人事系统"
    }
  }
}
```

### 4.2 医生排班数据 (每周更新)

```json
{
  "doctor_schedules": {
    "template": {
      "schedule_id": "string",
      "doctor_id": "string",
      "date": "date",
      "shifts": [
        {
          "shift_type": "string 上午/下午/晚上/夜班",
          "start_time": "time",
          "end_time": "time",
          "location": "string",
          "max_appointments": "integer",
          "booked": "integer",
          "status": "string 可约/满号"
        }
      ]
    },
    "requirements": {
      "coverage": "所有医生覆盖",
      "advance_days": 7,
      "update_time": "每日0点"
    }
  }
}
```

---

## 5. 患者信息数据

### 5.1 患者基本信息 (目标: 50000条)

```json
{
  "patients": {
    "total_count": 50000,
    "distribution": {
      "by_age": {
        "0-18岁": 5000,
        "19-35岁": 10000,
        "36-50岁": 15000,
        "51-65岁": 12000,
        "65岁以上": 8000
      },
      "by_gender": {
        "男": 25000,
        "女": 25000
      },
      "by_region": {
        "华北": 10000,
        "华东": 15000,
        "华南": 10000,
        "华中": 8000,
        "西南": 4000,
        "西北": 2000,
        "东北": 1000
      },
      "by_patient_type": {
        "门诊患者": 40000,
        "住院患者": 8000,
        "体检人群": 2000
      }
    },
    "data_structure": {
      "patient_id": "string (P00001-P50000)",
      "basic_info": {
        "name": "string 姓名",
        "gender": "string 性别",
        "birth_date": "date 出生日期",
        "age": "integer 年龄",
        "id_card": "string 身份证号",
        "phone": "string 手机号",
        "email": "string 邮箱",
        "address": {
          "province": "string 省份",
          "city": "string 城市",
          "district": "string 区县",
          "detail": "string 详细地址"
        },
        "emergency_contact": {
          "name": "string 联系人姓名",
          "relation": "string 关系",
          "phone": "string 电话"
        }
      },
      "medical_info": {
        "blood_type": "string A/B/O/AB",
        "rh_factor": "string (+/-)",
        "allergies": "array 过敏史",
        "chronic_diseases": "array 慢性病",
        "medications": "array 长期用药",
        "surgeries": "array 手术史"
      },
      "insurance": {
        "has_insurance": "boolean",
        "insurance_type": "string 医保/农合/自费",
        "insurance_number": "string 医保卡号"
      }
    },
    "privacy_requirements": {
      "sensitive_fields": [
        "身份证号",
        "手机号",
        "地址",
        "病史"
      ],
      "encryption": "AES-256",
      "access_control": "RBAC",
      "audit_log": "true"
    }
  }
}
```

---

## 6. 药品数据库

### 6.1 药品基本信息 (目标: 10000条)

```json
{
  "drugs": {
    "total_count": 10000,
    "categories": {
      "抗感染药": 800,
      "心血管系统用药": 1200,
      "消化系统用药": 1000,
      "呼吸系统用药": 600,
      "神经系统用药": 1000,
      "内分泌用药": 500,
      "血液系统用药": 400,
      "泌尿系统用药": 300,
      "抗肿瘤药": 800,
      "免疫调节药": 400,
      "维生素类": 200,
      "电解质平衡药": 300,
      "外科用药": 500,
      "五官科用药": 400,
      "皮肤科用药": 600,
      "中药": 2000
    },
    "data_structure": {
      "drug_id": "string (DR00001-DR10000)",
      "basic": {
        "generic_name": "string 通用名(必填)",
        "english_name": "string 英文名",
        "brand_names": "array 商品名",
        "category": "string 药品分类",
        "sub_category": "string 亚分类",
        "dosage_forms": "array 剂型",
        "strengths": "array 规格",
        "approval_number": "string 批准文号",
        "manufacturer": "string 生产企业"
      },
      "clinical": {
        "indications": "array 适应症(至少3项)",
        "contraindications": "array 禁忌症",
        "side_effects": {
          "common": "array 常见副作用",
          "severe": "array 严重副作用",
          "incidence": "object 发生率"
        },
        "interactions": {
          "drug_drug": "array 药物相互作用",
          "drug_food": "array 食物相互作用"
        },
        "warnings": "array 警告信息"
      },
      "dosage": {
        "adult": {
          "usual": "string 常用量",
          "min": "string 最小量",
          "max": "string 最大量",
          "renal_impairment": "string 肾功能不全",
          "hepatic_impairment": "string 肝功能不全"
        },
        "pediatric": {
          "calculation": "string 按体重/体表面积",
          "age_based": "object 分年龄剂量"
        },
        "elderly": "string 老年患者用量"
      },
      "pharmacology": {
        "mechanism": "string 作用机制",
        "onset": "string 起效时间",
        "peak": "string 达峰时间",
        "half_life": "string 半衰期",
        "metabolism": "string 代谢",
        "excretion": "string 排泄"
      },
      "pricing": {
        "retail_price": "number 零售价",
        "reimbursement": "string 医保类型",
        "reimbursement_ratio": "number 报销比例"
      }
    }
  }
}
```

---

## 7. 检查检验数据

### 7.1 检验项目 (目标: 500项)

```json
{
  "lab_items": {
    "total_count": 500,
    "categories": {
      "血常规": 20,
      "尿常规": 15,
      "生化检验": {
        "肝功能": 15,
        "肾功能": 10,
        "血糖": 8,
        "血脂": 10,
        "电解质": 8,
        "心肌酶": 8
      },
      "凝血功能": 10,
      "免疫检验": {
        "肿瘤标志物": 20,
        "甲状腺功能": 12,
        "性激素": 10,
        "过敏原": 30
      },
      "微生物检验": 50,
      "分子诊断": 30
    },
    "data_structure": {
      "item_id": "string (LAB001-LAB500)",
      "name": "string 项目名称",
      "english_name": "string 英文名",
      "category": "string 分类",
      "specimen": {
        "type": "string 标本类型",
        "container": "string 采血管",
        "volume": "string 采集量",
        "requirements": "array 采集要求"
      },
      "reference_ranges": [
        {
          "population": "string 人群",
          "min_value": "number",
          "max_value": "number",
          "unit": "string 单位",
          "conditions": "string 条件说明"
        }
      ],
      "method": "string 检测方法",
      "turnaround_time": "string 出报告时间",
      "clinical_significance": "string 临床意义"
    }
  }
}
```

### 7.2 检查项目 (目标: 200项)

```json
{
  "exam_items": {
    "total_count": 200,
    "modalities": {
      "X线": 30,
      "CT": 40,
      "MRI": 35,
      "超声": 40,
      "核医学": 15,
      "内镜": 20,
      "心电图": 10,
      "脑电图": 10
    },
    "data_structure": {
      "exam_id": "string (EXAM001-EXAM200)",
      "name": "string 检查名称",
      "modality": "string 检查方式",
      "body_part": "string 检查部位",
      "indications": "array 适应症",
      "contraindications": "array 禁忌症",
      "preparation": "array 检查前准备",
      "duration": "string 检查时长",
      "radiation": "string 辐射剂量"
    }
  }
}
```

---

## 8. 病理学数据

### 8.1 病理检查项目 (目标: 100项)

```json
{
  "pathology_items": {
    "total_count": 100,
    "categories": {
      "细胞病理学": {
        "count": 40,
        "items": [
          "宫颈液基薄层细胞学(TCT)",
          "细针穿刺细胞学(FNA)",
          "胸腹水细胞学",
          "痰液细胞学",
          "尿液细胞学"
        ]
      },
      "组织病理学": {
        "count": 50,
        "items": [
          "常规石蜡切片HE染色",
          "术中冰冻切片",
          "免疫组化(IHC)",
          "特殊染色",
          "原位杂交(ISH)"
        ]
      },
      "分子病理": {
        "count": 10,
        "items": [
          "EGFR基因突变检测",
          "ALK基因重排检测",
          "HER2基因扩增检测",
          "KRAS基因突变检测",
          "BRAF基因突变检测"
        ]
      }
    },
    "data_structure": {
      "item_id": "string (PATH001-PATH100)",
      "name": "string 项目名称",
      "category": "string 分类",
      "specimen_requirements": {
        "type": "string 标本类型",
        "fixative": "string 固定液",
        "time_limit": "string 固定时间",
        "transport": "string 运送要求"
      },
      "processing_time": {
        "routine": "string 常规时间",
        "urgent": "string 加急时间"
      },
      "report_components": {
        "macroscopic": "string 大体描述",
        "microscopic": "string 镜下描述",
        "diagnosis": "string 诊断意见",
        "comments": "string 备注"
      }
    }
  }
}
```

### 8.2 病理报告数据 (目标: 5000份)

```json
{
  "pathology_reports": {
    "total_count": 5000,
    "distribution": {
      "细胞学": 2000,
      "组织学": 2500,
      "分子病理": 500
    },
    "data_structure": {
      "report_id": "string (PR00001-PR05000)",
      "patient_id": "string",
      "specimen_info": {
        "specimen_id": "string",
        "type": "string 标本类型",
        "source": "string 取材部位",
        "collection_date": "date",
        "received_date": "date",
        "gross_description": "string 大体描述"
      },
      "microscopic": {
        "description": "string 镜下描述",
        "features": "array 病理特征"
      },
      "diagnosis": {
        "primary": "string 主要诊断",
        "secondary": "array 附加诊断",
        "grade": "string 分级",
        "stage": "string 分期(如适用)"
      },
      "supplementary": {
        "ihc_results": "array 免疫组化结果",
        "molecular_results": "array 分子检测结果",
        "margin_status": "string 切缘状态"
      },
      "pathologist": {
        "examining_doctor": "string 初检医生",
        "reviewing_doctor": "string 复检医生",
        "signing_doctor": "string 签发医生"
      },
      "report_date": "date"
    }
  }
}
```

---

## 9. 疾病诊疗档案

### 9.1 临床路径数据 (目标: 100个病种)

```json
{
  "clinical_pathways": {
    "total_count": 100,
    "data_structure": {
      "pathway_id": "string (CP001-CP100)",
      "disease_name": "string 疾病名称",
      "icd_code": "string ICD编码",
      "version": "string 版本号",
      "stages": [
        {
          "stage_order": "integer",
          "stage_name": "string",
          "duration": "string 预期时长",
          "activities": [
            {
              "activity_type": "string 评估/检查/治疗/护理/宣教",
              "description": "string",
              "indication": "string",
              "optional": "boolean"
            }
          ],
          "outcomes": {
            "expected": "array 预期结果",
            "discharge_criteria": "array 出院标准"
          }
        }
      ],
      "variations": {
        "allowed": "array 允许变异情况",
        "forbidden": "array 禁止变异情况"
      }
    }
  }
}
```

### 9.2 诊疗指南数据 (目标: 200条)

```json
{
  "clinical_guidelines": {
    "total_count": 200,
    "distribution": {
      "国家级指南": 50,
      "学会指南": 100,
      "专家共识": 30,
      "医院内部": 20
    },
    "data_structure": {
      "guideline_id": "string (GL001-GL200)",
      "title": "string 指南名称",
      "disease": "string 适用疾病",
      "publisher": "string 发布机构",
      "publish_date": "date",
      "version": "string 版本",
      "evidence_level": "string 证据等级",
      "recommendation_grade": "string 推荐级别",
      "key_recommendations": "array 核心推荐(至少5条)",
      "algorithms": "array 诊疗流程图",
      "references": "array 参考文献"
    }
  }
}
```

---

## 10. 慢病管理数据

### 10.1 慢病管理计划 (目标: 每10患者1计划)

```json
{
  "chronic_disease_plans": {
    "coverage_ratio": 0.1,
    "data_structure": {
      "plan_id": "string (CDP00001-)",
      "patient_id": "string",
      "condition": {
        "disease": "string 疾病",
        "icd_code": "string",
        "diagnosis_date": "date",
        "severity": "string 轻度/中度/重度",
        "complications": "array 并发症"
      },
      "control_targets": {
        "primary": "object 主要控制目标",
        "secondary": "array 次要目标",
        "acceptable_ranges": "object 可接受范围"
      },
      "monitoring_plan": {
        "home_monitoring": {
          "items": "array 监测项目",
          "frequency": "string 频率",
          "time_points": "array 时间点"
        },
        "hospital_checkups": {
          "items": "array 检查项目",
          "frequency": "string 频率"
        }
      },
      "treatment_regimen": {
        "medications": [
          {
            "name": "string",
            "dosage": "string",
            "frequency": "string",
            "duration": "string"
          }
        ],
        "non_pharmacological": "array 非药物治疗"
      },
      "lifestyle_interventions": {
        "diet": "string 饮食指导",
        "exercise": "string 运动处方",
        "habits": "array 戒烟限酒等",
        "education": "array 健康教育"
      },
      "alert_thresholds": [
        {
          "parameter": "string",
          "warning_value": "number",
          "critical_value": "number",
          "actions": "array 触发操作"
        }
      ]
    }
  }
}
```

---

## 11-16. 其他数据模块

[保持原有结构，增加具体数量要求...]

---

## 17. 数据质量标准

### 17.1 完整性要求

| 数据类型 | 必填字段完整度 | 可选字段完整度 | 总体要求 |
|----------|----------------|----------------|----------|
| 医生信息 | 100% | ≥80% | ≥90% |
| 患者信息 | 100% | ≥70% | ≥85% |
| 药品信息 | 100% | ≥90% | ≥95% |
| 检验项目 | 100% | ≥90% | ≥95% |
| 知识库 | 100% | ≥85% | ≥92% |

### 17.2 准确性要求

- 疾病ICD编码：准确率≥99%
- 药品信息：准确率100%（需权威来源验证）
- 参考范围：准确率≥99%
- 科室医生对应关系：准确率100%

### 17.3 时效性要求

| 数据类型 | 更新频率 | 容许延迟 |
|----------|----------|----------|
| 医生排班 | 每日 | ≤1小时 |
| 药品信息 | 每月 | ≤1周 |
| 指南更新 | 每季度 | ≤1月 |
| 患者数据 | 实时 | ≤5分钟 |
