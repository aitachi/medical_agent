# 医疗智能助手 - 数据填充示例模板

**配套文档**: DATA_REQUIREMENTS.md
**用途**: 数据填充的SQL/JSON示例

---

## 1. 医生信息批量填充模板 (2000条)

### 1.1 医生基础信息分布

```sql
-- 医生职称分布建议
INSERT INTO doctors (doctor_id, name, title, department_id, experience_years, status) VALUES
-- 主任医师 (300人) - 分布在各重点科室
('D0001', '张伟', '主任医师', 'DEPT00101', 25, 'active'),
('D0002', '李娜', '主任医师', 'DEPT00101', 28, 'active'),
('D0003', '王强', '主任医师', 'DEPT00102', 30, 'active'),
-- ... 每个科室至少2名主任医师

-- 副主任医师 (500人)
('D0301', '刘洋', '副主任医师', 'DEPT00101', 15, 'active'),
-- ... 每个科室至少5名副主任医师

-- 主治医师 (700人)
('D0801', '陈静', '主治医师', 'DEPT00101', 8, 'active'),
-- ... 每个科室至少8名主治医师

-- 住院医师 (400人)
('D1501', '杨帆', '住院医师', 'DEPT00101', 3, 'active'),
-- ... 每个科室至少5名住院医师

-- 医师 (100人)
('D1901', '赵敏', '医师', 'DEPT00101', 1, 'active');
```

### 1.2 各科室医生人数分配

| 科室代码 | 科室名称 | 主任医师 | 副主任医师 | 主治医师 | 住院医师 | 总计 |
|----------|----------|----------|-------------|----------|----------|------|
| DEPT00101 | 心血管内科 | 5 | 10 | 15 | 10 | 40 |
| DEPT00102 | 消化内科 | 4 | 8 | 12 | 8 | 32 |
| DEPT00103 | 呼吸内科 | 4 | 8 | 12 | 8 | 32 |
| DEPT00104 | 内分泌科 | 3 | 6 | 10 | 6 | 25 |
| DEPT00105 | 神经内科 | 5 | 10 | 15 | 10 | 40 |
| DEPT00201 | 普外科 | 6 | 12 | 18 | 12 | 48 |
| DEPT00202 | 骨科 | 5 | 10 | 15 | 10 | 40 |
| DEPT00203 | 神经外科 | 4 | 8 | 12 | 8 | 32 |
| DEPT00300 | 妇产科 | 8 | 15 | 20 | 12 | 55 |
| DEPT00400 | 儿科 | 6 | 12 | 18 | 10 | 46 |
| DEPT00500 | 急诊科 | 3 | 8 | 20 | 15 | 46 |
| DEPT00600 | 麻醉科 | 4 | 10 | 15 | 10 | 39 |
| 其他医技 | - | - | - | - | - | 455 |
| **总计** | | **300** | **500** | **700** | **400** | **2000** |

---

## 2. 患者信息批量填充模板 (50000条)

### 2.1 患者年龄分布

```sql
-- 年龄段分布示例
年龄段       人数占比    人数范围
0-18岁       10%        5000人
19-35岁      20%        10000人
36-50岁      30%        15000人
51-65岁      24%        12000人
65岁以上     16%        8000人
```

### 2.2 慢病患者标记

```sql
-- 慢病患者应在患者表中标记
ALTER TABLE patients ADD COLUMN chronic_diseases JSON;

-- 示例数据 (约10%患者有慢病)
UPDATE patients SET chronic_diseases = '[
  {"disease": "高血压", "diagnosis_date": "2020-01-15", "status": "active"},
  {"disease": "2型糖尿病", "diagnosis_date": "2021-06-20", "status": "active"}
]' WHERE patient_id IN (
  SELECT patient_id FROM chronic_disease_plans
);

-- 慢病分布建议
高血压      3000人
糖尿病      2000人
冠心病      1500人
慢阻肺      1000人
慢性肾病     800人
其他慢病     1700人
小计       10000人 (占总患者20%)
```

---

## 3. 药品数据填充模板 (10000条)

### 3.1 药品分类填充示例

```json
{
  "填充顺序": [
    {
      "分类": "抗感染药",
      "数量": 800,
      "必填药品": [
        "阿莫西林", "头孢呋辛", "头孢曲松", "左氧氟沙星",
        "阿奇霉素", "莫西沙星", "万古霉素", "美罗培南"
      ],
      "模板": "参考国家基本药物目录"
    },
    {
      "分类": "心血管系统用药",
      "数量": 1200,
      "必填药品": [
        "硝苯地平", "氨氯地平", "美托洛尔", "阿司匹林",
        "阿托伐他汀", "辛伐他汀", "氯吡格雷", "华法林"
      ]
    },
    {
      "分类": "消化系统用药",
      "数量": 1000,
      "必填药品": [
        "奥美拉唑", "兰索拉唑", "多潘立酮", "蒙脱石散",
        "复方甘草酸苷", "熊去氧胆酸"
      ]
    },
    {
      "分类": "内分泌用药",
      "数量": 500,
      "必填药品": [
        "二甲双胍", "格列美脲", "胰岛素", "左甲状腺素",
        "甲巯咪唑", "丙硫氧嘧啶"
      ]
    }
  ]
}
```

---

## 4. 检验项目填充模板 (500项)

### 4.1 血常规 (20项)

```json
{
  "category": "血常规",
  "items": [
    {"item_id": "LAB001", "name": "白细胞计数", "unit": "10^9/L", "reference": "4-10"},
    {"item_id": "LAB002", "name": "红细胞计数", "unit": "10^12/L", "reference": "4-5.5"},
    {"item_id": "LAB003", "name": "血红蛋白", "unit": "g/L", "reference": "120-160"},
    {"item_id": "LAB004", "name": "血细胞比容", "unit": "%", "reference": "40-50"},
    {"item_id": "LAB005", "name": "平均红细胞体积", "unit": "fL", "reference": "80-100"},
    {"item_id": "LAB006", "name": "平均血红蛋白量", "unit": "pg", "reference": "27-34"},
    {"item_id": "LAB007", "name": "平均血红蛋白浓度", "unit": "g/L", "reference": "320-360"},
    {"item_id": "LAB008", "name": "血小板计数", "unit": "10^9/L", "reference": "100-300"},
    {"item_id": "LAB009", "name": "中性粒细胞百分比", "unit": "%", "reference": "50-70"},
    {"item_id": "LAB010", "name": "淋巴细胞百分比", "unit": "%", "reference": "20-40"},
    {"item_id": "LAB011", "name": "单核细胞百分比", "unit": "%", "reference": "3-8"},
    {"item_id": "LAB012", "name": "嗜酸性粒细胞百分比", "unit": "%", "reference": "0.5-5"},
    {"item_id": "LAB013", "name": "嗜碱性粒细胞百分比", "unit": "%", "reference": "0-1"},
    {"item_id": "LAB014", "name": "中性粒细胞计数", "unit": "10^9/L", "reference": "2-7"},
    {"item_id": "LAB015", "name": "淋巴细胞计数", "unit": "10^9/L", "reference": "0.8-4"},
    {"item_id": "LAB016", "name": "单核细胞计数", "unit": "10^9/L", "reference": "0.12-0.8"},
    {"item_id": "LAB017", "name": "嗜酸性粒细胞计数", "unit": "10^9/L", "reference": "0.05-0.5"},
    {"item_id": "LAB018", "name": "嗜碱性粒细胞计数", "unit": "10^9/L", "reference": "0-0.1"},
    {"item_id": "LAB019", "name": "红细胞分布宽度", "unit": "%", "reference": "11.5-14.5"},
    {"item_id": "LAB020", "name": "血小板分布宽度", "unit": "%", "reference": "15-17"}
  ]
}
```

### 4.2 生化检验 (69项)

```json
{
  "category": "生化检验",
  "subcategories": {
    "肝功能": [
      {"item_id": "LAB021", "name": "丙氨酸转氨酶", "unit": "U/L", "reference": "0-40"},
      {"item_id": "LAB022", "name": "天冬氨酸转氨酶", "unit": "U/L", "reference": "0-40"},
      {"item_id": "LAB023", "name": "γ-谷氨酰转肽酶", "unit": "U/L", "reference": "0-50"},
      {"item_id": "LAB024", "name": "碱性磷酸酶", "unit": "U/L", "reference": "40-150"},
      {"item_id": "LAB025", "name": "总胆红素", "unit": "μmol/L", "reference": "5-21"},
      {"item_id": "LAB026", "name": "直接胆红素", "unit": "μmol/L", "reference": "0-8"},
      {"item_id": "LAB027", "name": "间接胆红素", "unit": "μmol/L", "reference": "0-16"},
      {"item_id": "LAB028", "name": "白蛋白", "unit": "g/L", "reference": "40-55"},
      {"item_id": "LAB029", "name": "球蛋白", "unit": "g/L", "reference": "20-40"},
      {"item_id": "LAB030", "name": "白球比", "unit": "", "reference": "1.2-2.4"},
      {"item_id": "LAB031", "name": "前白蛋白", "unit": "mg/L", "reference": "200-400"},
      {"item_id": "LAB032", "name": "胆碱酯酶", "unit": "U/L", "reference": "4000-12000"},
      {"item_id": "LAB033", "name": "总胆汁酸", "unit": "μmol/L", "reference": "0-15"},
      {"item_id": "LAB034", "name": "甘胆酸", "unit": "mg/L", "reference": "<2.5"},
      {"item_id": "LAB035", "name": "透明质酸", "unit": "ng/mL", "reference": "0-120"}
    ],
    "肾功能": [
      {"item_id": "LAB036", "name": "肌酐", "unit": "μmol/L", "reference": "44-133"},
      {"item_id": "LAB037", "name": "尿素氮", "unit": "mmol/L", "reference": "2.9-8.2"},
      {"item_id": "LAB038", "name": "尿酸", "unit": "μmol/L", "reference": "150-420"},
      {"item_id": "LAB039", "name": "胱抑素C", "unit": "mg/L", "reference": "0.6-1.2"},
      {"item_id": "LAB040", "name": "β2微球蛋白", "unit": "mg/L", "reference": "1-3"},
      {"item_id": "LAB041", "name": "视黄醇结合蛋白", "unit": "mg/L", "reference": "25-70"},
      {"item_id": "LAB042", "name": "尿微量白蛋白", "unit": "mg/L", "reference": "<30"},
      {"item_id": "LAB043", "name": "尿肌酐", "unit": "mmol/L", "reference": "根据饮食"},
      {"item_id": "LAB044", "name": "尿白蛋白/肌酐比值", "unit": "mg/g", "reference": "<30"},
      {"item_id": "LAB045", "name": "肾小球滤过率", "unit": "mL/min", "reference": ">90"}
    ],
    "血糖": [
      {"item_id": "LAB046", "name": "空腹血糖", "unit": "mmol/L", "reference": "3.9-6.1"},
      {"item_id": "LAB047", "name": "餐后2小时血糖", "unit": "mmol/L", "reference": "<7.8"},
      {"item_id": "LAB048", "name": "随机血糖", "unit": "mmol/L", "reference": "<11.1"},
      {"item_id": "LAB049", "name": "糖化血红蛋白", "unit": "%", "reference": "4-6"},
      {"item_id": "LAB050", "name": "糖化血清白蛋白", "unit": "%", "reference": "10-17"},
      {"item_id": "LAB051", "name": "胰岛素", "unit": "mIU/L", "reference": "2-20"},
      {"item_id": "LAB052", "name": "C肽", "unit": "ng/mL", "reference": "0.8-4"},
      {"item_id": "LAB053", "name": "酮体", "unit": "mmol/L", "reference": "阴性"}
    ],
    "血脂": [
      {"item_id": "LAB054", "name": "总胆固醇", "unit": "mmol/L", "reference": "<5.2"},
      {"item_id": "LAB055", "name": "甘油三酯", "unit": "mmol/L", "reference": "<1.7"},
      {"item_id": "LAB056", "name": "高密度脂蛋白胆固醇", "unit": "mmol/L", "reference": ">1.0"},
      {"item_id": "LAB057", "name": "低密度脂蛋白胆固醇", "unit": "mmol/L", "reference": "<3.4"},
      {"item_id": "LAB058", "name": "极低密度脂蛋白胆固醇", "unit": "mmol/L", "reference": "0.2-1.0"},
      {"item_id": "LAB059", "name": "载脂蛋白A1", "unit": "g/L", "reference": "1.0-1.6"},
      {"item_id": "LAB060", "name": "载脂蛋白B", "unit": "g/L", "reference": "0.6-1.1"},
      {"item_id": "LAB061", "name": "脂蛋白a", "unit": "mg/L", "reference": "<300"}
    ],
    "电解质": [
      {"item_id": "LAB062", "name": "钾", "unit": "mmol/L", "reference": "3.5-5.5"},
      {"item_id": "LAB063", "name": "钠", "unit": "mmol/L", "reference": "135-145"},
      {"item_id": "LAB064", "name": "氯", "unit": "mmol/L", "reference": "96-108"},
      {"item_id": "LAB065", "name": "钙", "unit": "mmol/L", "reference": "2.25-2.75"},
      {"item_id": "LAB066", "name": "磷", "unit": "mmol/L", "reference": "0.8-1.5"},
      {"item_id": "LAB067", "name": "镁", "unit": "mmol/L", "reference": "0.7-1.1"},
      {"item_id": "LAB068", "name": "二氧化碳结合力", "unit": "mmol/L", "reference": "22-31"},
      {"item_id": "LAB069", "name": "阴离子间隙", "unit": "mmol/L", "reference": "8-16"}
    ],
    "心肌酶": [
      {"item_id": "LAB070", "name": "肌酸激酶", "unit": "U/L", "reference": "38-174"},
      {"item_id": "LAB071", "name": "肌酸激酶同工酶MB", "unit": "U/L", "reference": "0-25"},
      {"item_id": "LAB072", "name": "乳酸脱氢酶", "unit": "U/L", "reference": "100-240"},
      {"item_id": "LAB073", "name": "α-羟丁酸脱氢酶", "unit": "U/L", "reference": "90-220"},
      {"item_id": "LAB074", "name": "肌钙蛋白T", "unit": "ng/mL", "reference": "<0.1"},
      {"item_id": "LAB075", "name": "肌钙蛋白I", "unit": "ng/mL", "reference": "<0.5"},
      {"item_id": "LAB076", "name": "肌红蛋白", "unit": "ng/mL", "reference": "<70"},
      {"item_id": "LAB077", "name": "天门冬氨酸转氨酶", "unit": "U/L", "reference": "0-40"}
    ]
  }
}
```

---

## 5. 肿瘤标志物 (30项)

```json
{
  "category": "肿瘤标志物",
  "items": [
    {"item_id": "LAB201", "name": "癌胚抗原", "unit": "ng/mL", "reference": "<5"},
    {"item_id": "LAB202", "name": "甲胎蛋白", "unit": "ng/mL", "reference": "<20"},
    {"item_id": "LAB203", "name": "糖类抗原19-9", "unit": "U/mL", "reference": "<37"},
    {"item_id": "LAB204", "name": "糖类抗原125", "unit": "U/mL", "reference": "<35"},
    {"item_id": "LAB205", "name": "糖类抗原15-3", "unit": "U/mL", "reference": "<30"},
    {"item_id": "LAB206", "name": "糖类抗原72-4", "unit": "U/mL", "reference": "<6"},
    {"item_id": "LAB207", "name": "糖类抗原50", "unit": "U/mL", "reference": "<20"},
    {"item_id": "LAB208", "name": "糖类抗原242", "unit": "U/mL", "reference": "<20"},
    {"item_id": "LAB209", "name": "前列腺特异抗原", "unit": "ng/mL", "reference": "<4"},
    {"item_id": "LAB210", "name": "游离PSA", "unit": "ng/mL", "reference": "<1"},
    {"item_id": "LAB211", "name": "PSA比值", "unit": "%", "reference": ">25"},
    {"item_id": "LAB212", "name": "细胞角蛋白19片段", "unit": "ng/mL", "reference": "<3.3"},
    {"item_id": "LAB213", "name": "神经元特异烯醇化酶", "unit": "ng/mL", "reference": "<16.3"},
    {"item_id": "LAB214", "name": "鳞状细胞癌抗原", "unit": "ng/mL", "reference": "<1.5"},
    {"item_id": "LAB215", "name": "人附睾蛋白4", "unit": "pmol/L", "reference": "<70"},
    {"item_id": "LAB216", "name": "胃蛋白酶原I", "unit": "ng/mL", "reference": "70-165"},
    {"item_id": "LAB217", "name": "胃蛋白酶原II", "unit": "ng/mL", "reference": "3-15"},
    {"item_id": "LAB218", "name": "PGI/PGII比值", "unit": "", "reference": ">7"},
    {"item_id": "LAB219", "name": "胃泌素17", "unit": "pmol/L", "reference": "1-15"},
    {"item_id": "LAB220", "name": "异常糖链糖蛋白", "unit": "U/mL", "reference": "<10"},
    {"item_id": "LAB221", "name": "铁蛋白", "unit": "ng/mL", "reference": "15-200"},
    {"item_id": "LAB222", "name": "β2微球蛋白", "unit": "mg/L", "reference": "1-3"},
    {"item_id": "LAB223", "name": "S100蛋白", "unit": "μg/L", "reference": "<0.105"},
    {"item_id": "LAB224", "name": "骨胶质蛋白", "unit": "ng/mL", "reference": "<4.5"}
  ]
}
```

---

## 6. 病理报告模板 (5000份)

### 6.1 细胞学报告模板 (2000份)

```json
{
  "template": {
    "report_id": "PR00001",
    "report_type": "cytology",
    "specimen_type": "宫颈液基薄层细胞学(TCT)",
    "result_categories": [
      {
        "category": "阴性",
        "percentage": 70,
        "diagnosis": "未见上皮内病变或恶性病变",
        "microscopic": "鳞状上皮细胞成熟，未见异常；宫颈管柱状上皮细胞及化生细胞可见"
      },
      {
        "category": "意义不明的非典型鳞状细胞",
        "percentage": 15,
        "diagnosis": "ASC-US",
        "microscopic": "可见少量非典型鳞状上皮细胞，核略增大，无明显异型性"
      },
      {
        "category": "低度鳞状上皮内病变",
        "percentage": 8,
        "diagnosis": "LSIL",
        "microscopic": "可见轻度异型细胞，核浆比轻度增加"
      },
      {
        "category": "高度鳞状上皮内病变",
        "percentage": 5,
        "diagnosis": "HSIL",
        "microscopic": "可见中-重度异型细胞，核浆比明显增加"
      },
      {
        "category": "鳞状细胞癌",
        "percentage": 2,
        "diagnosis": "SCC",
        "microscopic": "可见明显恶性细胞，核异型性显著"
      }
    ]
  }
}
```

### 6.2 组织学报告模板 (2500份)

```json
{
  "template": {
    "report_id": "PR02001",
    "report_type": "histology",
    "specimen_types": [
      {
        "type": "内镜活检标本",
        "count": 800,
        "examples": ["胃黏膜活检", "肠黏膜活检", "支气管黏膜活检"]
      },
      {
        "type": "手术切除标本",
        "count": 1000,
        "examples": ["肺叶切除", "胃大部切除", "乳腺肿块切除"]
      },
      {
        "type": "根治性手术标本",
        "count": 400,
        "examples": ["胃癌根治术", "结直肠癌根治术", "乳腺癌根治术"]
      },
      {
        "type": "其他",
        "count": 300
      }
    ],
    "diagnosis_distribution": [
      {"diagnosis": "炎症/良性病变", "percentage": 50},
      {"diagnosis": "癌前病变", "percentage": 15},
      {"diagnosis": "恶性肿瘤", "percentage": 30},
      {"diagnosis": "其他", "percentage": 5}
    ]
  }
}
```

---

## 7. 科室治疗档案模板 (每科室50份)

### 7.1 心血管内科治疗档案示例

```json
{
  "department": "心血管内科",
  "template": {
    "case_id": "CARDIO001",
    "patient_info": {
      "age": "55岁",
      "gender": "男"
    },
    "diagnosis": {
      "primary": "急性心肌梗死",
      "icd_code": "I21.9",
      "subtype": "ST段抬高型心肌梗死"
    },
    "treatment": {
      "emergency": [
        "阿司匹林300mg嚼服",
        "氯吡格雷300mg负荷量",
        "阿托伐他汀80mg",
        "急诊PCI术"
      ],
      "medication": [
        "阿司匹林 100mg qd",
        "氯吡格雷 75mg qd",
        "美托洛尔 12.5mg bid",
        "培哚普利 4mg qd",
        "阿托伐他汀 20mg qn"
      ],
      "procedures": [
        {
          "name": "经皮冠状动脉介入术",
          "details": "LAD近中段植入支架1枚",
          "outcome": "成功"
        }
      ]
    },
    "outcome": {
      "result": "好转",
      "length_of_stay": 7,
      "complications": ["无"],
      "followup_plan": "术后1个月复查"
    }
  }
}
```

### 7.2 普外科治疗档案示例

```json
{
  "department": "普外科",
  "template": {
    "case_id": "SURGERY001",
    "diagnosis": {
      "primary": "急性阑尾炎",
      "icd_code": "K35.8"
    },
    "treatment": {
      "surgery": {
        "name": "腹腔镜阑尾切除术",
        "anesthesia": "全身麻醉",
        "duration": "45分钟",
        "blood_loss": "10mL"
      },
      "medication": [
        "头孢呋辛 1.5g bid",
        "甲硝唑 0.5g bid"
      ]
    },
    "pathology": {
      "diagnosis": "急性化脓性阑尾炎",
      "perforation": "无"
    },
    "outcome": {
      "result": "治愈",
      "length_of_stay": 3
    }
  }
}
```

---

## 8. 随访数据模板 (10000条记录)

```json
{
  "followup_records_template": {
    "record_id": "FR00001",
    "plan_id": "FP00001",
    "patient_id": "P00001",
    "followup_date": "2026-03-26",
    "followup_type": "phone",
    "data": {
      "blood_pressure": {"systolic": 128, "diastolic": 78, "heart_rate": 72},
      "medication_adherence": "good",
      "symptoms": [],
      "side_effects": [],
      "lifestyle": {
        "diet": "基本控制",
        "exercise": "每周3次",
        "smoking": "已戒烟",
        "drinking": "偶尔"
      }
    },
    "doctor_assessment": {
      "control_status": "达标",
      "adjustment": "继续当前方案",
      "next_followup": "2026-04-26"
    }
  }
}
```

---

## 9. 数据填充检查清单

### 9.1 填充前检查

- [ ] 数据库表结构已创建
- [ ] 必填字段已确认
- [ ] 数据来源已确定
- [ ] 数据验证规则已定义
- [ ] 备份方案已准备

### 9.2 填充中检查

- [ ] 主键唯一性
- [ ] 外键完整性
- [ ] 数据格式正确
- [ ] 必填字段完整
- [ ] 参考数据准确

### 9.3 填充后检查

- [ ] 数量达标
- [ ] 分布合理
- [ ] 关联正确
- [ ] 索引已创建
- [ ] 性能测试通过
