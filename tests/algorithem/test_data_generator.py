# -*- coding: utf-8 -*-
"""
医疗意图识别测试数据生成器
生成5000条覆盖全面场景的测试数据
"""
import random
import json
from datetime import datetime
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict


@dataclass
class TestSample:
    """测试样本"""
    text: str
    intent: str
    scenario: str
    difficulty: str  # easy, medium, hard
    confidence: float
    metadata: Dict = None


class MedicalTestDatasetGenerator:
    """医疗意图测试数据生成器"""

    INTENTS = {
        "symptom_inquiry": "症状咨询",
        "department_query": "科室查询",
        "medication_consult": "用药咨询",
        "appointment": "预约挂号",
        "health_education": "健康教育",
        "report_interpret": "报告解读",
        "greeting": "问候",
        "unknown": "未知/无关"
    }

    # ============================================================
    # 症状相关词库
    # ============================================================
    BODY_PARTS = [
        "头", "头痛", "头晕", "头疼", "脑袋", "太阳穴",
        "眼", "眼睛", "视力", "眼花",
        "耳", "耳朵", "耳鸣", "听力",
        "鼻", "鼻子", "鼻塞", "流鼻涕", "鼻出血",
        "喉", "喉咙", "咽喉", "嗓子", "声音",
        "颈", "脖子", "颈部",
        "胸", "胸部", "胸口", "胸", "乳房",
        "腹", "肚子", "腹部", "胃", "小腹", "下腹",
        "腰", "腰部", "后腰", "腰子",
        "背", "后背", "背部", "脊柱",
        "手", "手臂", "手腕", "手指", "关节",
        "腿", "大腿", "小腿", "膝盖", "脚", "脚踝",
        "皮肤", "全身", "身体", "乏力", "没力气"
    ]

    SYMPTOMS = [
        "痛", "疼", "酸痛", "胀痛", "刺痛", "剧痛", "隐痛", "跳痛",
        "发热", "发烧", "高烧", "低烧", "体温高",
        "咳嗽", "咳", "干咳", "咳痰", "咳嗽有痰",
        "恶心", "呕吐", "反胃", "想吐",
        "腹泻", "拉肚子", "肚子泻", "大便稀",
        "便秘", "大便干", "排便困难", "拉不出",
        "失眠", "睡不着", "睡眠不好", "多梦",
        "头晕", "眩晕", "眼花", "天旋地转",
        "心慌", "心悸", "心跳快", "心跳慢", "胸闷",
        "气短", "呼吸困难", "喘不上气", "气促",
        "乏力", "没力气", "累", "疲劳", "虚弱",
        "食欲不振", "不想吃", "吃不下", "没胃口",
        "口干", "口渴", "嘴里苦",
        "皮肤痒", "痒", "起疹子", "皮疹", "红肿",
        "出汗", "盗汗", "虚汗", "出冷汗",
        "发冷", "怕冷", "畏寒",
        "水肿", "肿", "浮肿",
        "抽筋", "痉挛", "抽搐",
        "麻木", "发麻", "没知觉",
        "出血", "流血", "便血", "尿血", "咳血"
    ]

    SEVERITY = [
        "非常", "特别", "超级", "极其", "十分",
        "比较", "挺", "有点", "稍微", "略微",
        "一直", "持续", "总是", "老是", "经常",
        "偶尔", "有时", "间歇", "阵发"
    ]

    DURATIONS = [
        "一天", "两天", "三天", "好几天", "一周", "半个月",
        "一个月", "好几个月", "很久", "昨天", "今天", "早上",
        "晚上", "半夜", "凌晨"
    ]

    # ============================================================
    # 药品相关词库
    # ============================================================
    MEDICINES = [
        "阿莫西林", "头孢", "青霉素", "红霉素", "克拉霉素",
        "布洛芬", "对乙酰氨基酚", "阿司匹林", "双氯芬酸钠",
        "感冒灵", "感冒清热", "连花清瘟", "板蓝根",
        "奥美拉唑", "雷贝拉唑", "兰索拉唑",
        "二甲双胍", "格列美脲", "胰岛素",
        "硝苯地平", "氨氯地平", "缬沙坦", "厄贝沙坦",
        "阿托伐他汀", "辛伐他汀",
        "氯雷他定", "西替利嗪", "扑尔敏",
        "阿奇霉素", "罗红霉素",
        "蒙脱石散", "黄连素",
        "多潘立酮", "莫沙必利"
    ]

    MEDICATION_ACTIONS = [
        "怎么吃", "怎么用", "怎么服用", "用法", "用量",
        "一次吃多少", "每天吃几次", "饭前吃还是饭后吃",
        "副作用", "不良反应", "有什么副作用", "副作用大吗",
        "禁忌", "禁忌症", "不能吃", "哪些人不能用",
        "能一起吃吗", "相互作用", "可以和XX一起吃吗",
        "注意事项", "要注意什么", "有什么要注意的"
    ]

    # ============================================================
    # 科室相关词库
    # ============================================================
    DEPARTMENTS = [
        "内科", "外科", "儿科", "妇科", "产科", "男科",
        "神经内科", "心血管内科", "消化内科", "呼吸内科",
        "内分泌科", "肾内科", "血液科",
        "骨科", "神经外科", "心外科", "胸外科",
        "泌尿外科", "普外科",
        "眼科", "耳鼻喉科", "口腔科", "皮肤科",
        "精神科", "心理科", "传染科", "肿瘤科"
    ]

    DEPARTMENT_PATTERNS = [
        "挂什么科", "去哪个科", "看什么科", "哪个科看",
        "应该挂什么科", "要去哪个科室", "是哪个科的病",
        "哪个科室看", "找哪个科", "什么科室"
    ]

    # ============================================================
    # 预约相关词库
    # ============================================================
    APPOINTMENT_PATTERNS = [
        "我想挂号", "我要挂号", "帮我挂号", "预约挂号",
        "预约个号", "挂个号", "想挂个号",
        "预约医生", "预约门诊", "预约专家",
        "排号", "拿号", "想看病", "想看医生",
        "怎么挂号", "如何预约", "挂号流程"
    ]

    # ============================================================
    # 健康教育相关词库
    # ============================================================
    DISEASES = [
        "高血压", "糖尿病", "心脏病", "冠心病", "心梗",
        "脑梗", "中风", "感冒", "流感", "肺炎",
        "胃炎", "胃溃疡", "肠炎", "肝炎",
        "肾炎", "肾结石", "尿路感染",
        "关节炎", "痛风", "骨质疏松",
        "抑郁症", "焦虑症", "失眠症",
        "过敏", "哮喘", "支气管炎",
        "贫血", "白血病", "淋巴瘤"
    ]

    PREVENTION_PATTERNS = [
        "怎么预防", "如何预防", "怎样预防", "预防方法",
        "如何避免", "怎么避免", "防止",
        "怎么保持", "如何保持", "保持方法"
    ]

    DIET_PATTERNS = [
        "不能吃什么", "可以吃什么", "忌口", "饮食禁忌",
        "吃什么好", "饮食注意", "注意事项",
        "能吃XX吗", "可以吃XX吗", "吃了会怎样"
    ]

    EXERCISE_PATTERNS = [
        "运动建议", "锻炼建议", "什么运动好",
        "可以运动吗", "适合什么运动",
        "怎么锻炼", "如何运动"
    ]

    # ============================================================
    # 问候语词库
    # ============================================================
    GREETINGS = [
        "你好", "您好", "嗨", "hello", "hi", "hi there",
        "早上好", "下午好", "晚上好", "晚安",
        "再见", "拜拜", "bye",
        "谢谢", "感谢", "多谢", "感谢感谢"
    ]

    # ============================================================
    # 无关/未知词库
    # ============================================================
    UNRELATED_TOPICS = [
        "天气", "股票", "基金", "理财", "贷款",
        "新闻", "时事", "政治",
        "体育", "足球", "篮球", "网球",
        "娱乐", "明星", "电影", "音乐",
        "旅游", "美食", "购物",
        "游戏", "电竞", "动漫",
        "汽车", "房产", "装修"
    ]

    def __init__(self):
        self.samples = []

    def generate_symptom_samples(self, count: int = 800) -> List[TestSample]:
        """生成症状咨询样本"""
        samples = []

        # 简单症状描述 (easy)
        for _ in range(count // 3):
            body_part = random.choice(self.BODY_PARTS)
            symptom = random.choice(self.SYMPTOMS)
            samples.append(TestSample(
                text=f"我{body_part}{symptom}",
                intent="symptom_inquiry",
                scenario="简单症状描述",
                difficulty="easy",
                confidence=1.0
            ))
            samples.append(TestSample(
                text=f"{body_part}{symptom}",
                intent="symptom_inquiry",
                scenario="简单症状描述(无主语)",
                difficulty="easy",
                confidence=1.0
            ))

        # 带持续时间的症状 (medium)
        for _ in range(count // 3):
            body_part = random.choice(self.BODY_PARTS)
            symptom = random.choice(self.SYMPTOMS)
            duration = random.choice(self.DURATIONS)
            samples.append(TestSample(
                text=f"我{body_part}{symptom}{duration}了",
                intent="symptom_inquiry",
                scenario="带持续时间的症状",
                difficulty="medium",
                confidence=1.0
            ))
            samples.append(TestSample(
                text=f"{body_part}{symptom}持续{duration}",
                intent="symptom_inquiry",
                scenario="症状持续描述",
                difficulty="medium",
                confidence=1.0
            ))

        # 复杂症状描述 (hard)
        for _ in range(count // 3):
            body_part = random.choice(self.BODY_PARTS)
            symptom = random.choice(self.SYMPTOMS)
            severity = random.choice(self.SEVERITY)
            samples.append(TestSample(
                text=f"{severity}{body_part}{symptom}怎么办",
                intent="symptom_inquiry",
                scenario="复杂症状询问",
                difficulty="hard",
                confidence=1.0
            ))
            samples.append(TestSample(
                text=f"感觉{body_part}{symptom}，很{severity}",
                intent="symptom_inquiry",
                scenario="主观感受描述",
                difficulty="hard",
                confidence=1.0
            ))

        # 多症状 (hard)
        for _ in range(count // 10):
            body_part1 = random.choice(self.BODY_PARTS)
            symptom1 = random.choice(self.SYMPTOMS)
            body_part2 = random.choice(self.BODY_PARTS)
            symptom2 = random.choice(self.SYMPTOMS)
            samples.append(TestSample(
                text=f"{body_part1}{symptom1}，{body_part2}{symptom2}",
                intent="symptom_inquiry",
                scenario="多症状描述",
                difficulty="hard",
                confidence=1.0
            ))

        return samples[:count]

    def generate_department_samples(self, count: int = 600) -> List[TestSample]:
        """生成科室查询样本"""
        samples = []

        # 症状+科室查询 (easy)
        for _ in range(count // 3):
            body_part = random.choice(self.BODY_PARTS[:20])  # 常见部位
            pattern = random.choice(self.DEPARTMENT_PATTERNS)
            samples.append(TestSample(
                text=f"{body_part}{random.choice(self.SYMPTOMS[:10])}{pattern}",
                intent="department_query",
                scenario="症状科室查询",
                difficulty="easy",
                confidence=1.0
            ))

        # 直接科室查询 (medium)
        for _ in range(count // 3):
            symptom = random.choice(self.SYMPTOMS)
            pattern = random.choice(self.DEPARTMENT_PATTERNS)
            samples.append(TestSample(
                text=f"{symptom}{pattern}",
                intent="department_query",
                scenario="直接科室查询",
                difficulty="medium",
                confidence=1.0
            ))

        # 科室确认 (hard)
        for _ in range(count // 3):
            dept = random.choice(self.DEPARTMENTS)
            samples.append(TestSample(
                text=f"{dept}看什么病",
                intent="department_query",
                scenario="科室功能查询",
                difficulty="medium",
                confidence=1.0
            ))
            samples.append(TestSample(
                text=f"有没有{dept}",
                intent="department_query",
                scenario="科室存在确认",
                difficulty="hard",
                confidence=1.0
            ))

        return samples[:count]

    def generate_medication_samples(self, count: int = 700) -> List[TestSample]:
        """生成用药咨询样本"""
        samples = []

        # 药品用法 (easy)
        for _ in range(count // 3):
            medicine = random.choice(self.MEDICINES)
            action = random.choice(["怎么吃", "怎么用", "用法", "用量"])
            samples.append(TestSample(
                text=f"{medicine}{action}",
                intent="medication_consult",
                scenario="药品用法询问",
                difficulty="easy",
                confidence=1.0
            ))

        # 副作用询问 (medium)
        for _ in range(count // 3):
            medicine = random.choice(self.MEDICINES)
            samples.append(TestSample(
                text=f"{medicine}有什么副作用",
                intent="medication_consult",
                scenario="副作用询问",
                difficulty="medium",
                confidence=1.0
            ))
            samples.append(TestSample(
                text=f"{medicine}副作用大吗",
                intent="medication_consult",
                scenario="副作用程度询问",
                difficulty="medium",
                confidence=1.0
            ))

        # 禁忌和相互作用 (hard)
        for _ in range(count // 3):
            medicine = random.choice(self.MEDICINES)
            samples.append(TestSample(
                text=f"{medicine}有什么禁忌",
                intent="medication_consult",
                scenario="禁忌询问",
                difficulty="hard",
                confidence=1.0
            ))
            samples.append(TestSample(
                text=f"{medicine}能和其他药一起吃吗",
                intent="medication_consult",
                scenario="药物相互作用",
                difficulty="hard",
                confidence=1.0
            ))

        return samples[:count]

    def generate_appointment_samples(self, count: int = 500) -> List[TestSample]:
        """生成预约挂号样本"""
        samples = []

        # 直接挂号 (easy)
        for _ in range(count // 2):
            pattern = random.choice(self.APPOINTMENT_PATTERNS[:6])
            samples.append(TestSample(
                text=pattern,
                intent="appointment",
                scenario="直接挂号",
                difficulty="easy",
                confidence=1.0
            ))

        # 科室+挂号 (medium)
        for _ in range(count // 3):
            dept = random.choice(self.DEPARTMENTS)
            samples.append(TestSample(
                text=f"预约{dept}",
                intent="appointment",
                scenario="科室预约",
                difficulty="medium",
                confidence=1.0
            ))
            samples.append(TestSample(
                text=f"想挂{dept}的号",
                intent="appointment",
                scenario="挂科室号",
                difficulty="medium",
                confidence=1.0
            ))

        # 复杂预约 (hard)
        for _ in range(count // 6):
            samples.append(TestSample(
                text="我想预约明天的专家门诊",
                intent="appointment",
                scenario="具体时间预约",
                difficulty="hard",
                confidence=1.0
            ))
            samples.append(TestSample(
                text="帮我排个号",
                intent="appointment",
                scenario="排号",
                difficulty="hard",
                confidence=1.0
            ))

        return samples[:count]

    def generate_health_education_samples(self, count: int = 800) -> List[TestSample]:
        """生成健康教育样本"""
        samples = []

        # 疾病预防 (easy)
        for _ in range(count // 3):
            disease = random.choice(self.DISEASES)
            pattern = random.choice(self.PREVENTION_PATTERNS)
            samples.append(TestSample(
                text=f"{disease}{pattern}",
                intent="health_education",
                scenario="疾病预防",
                difficulty="easy",
                confidence=1.0
            ))

        # 饮食相关 (medium)
        for _ in range(count // 3):
            disease = random.choice(self.DISEASES)
            pattern = random.choice(self.DIET_PATTERNS)
            samples.append(TestSample(
                text=f"{disease}{pattern}",
                intent="health_education",
                scenario="饮食询问",
                difficulty="medium",
                confidence=1.0
            ))

        # 运动和生活方式 (hard)
        for _ in range(count // 3):
            pattern = random.choice(self.EXERCISE_PATTERNS)
            samples.append(TestSample(
                text=pattern,
                intent="health_education",
                scenario="运动建议",
                difficulty="medium",
                confidence=1.0
            ))
            samples.append(TestSample(
                text=f"保持健康的生活方式",
                intent="health_education",
                scenario="生活方式",
                difficulty="easy",
                confidence=1.0
            ))

        return samples[:count]

    def generate_greeting_samples(self, count: int = 400) -> List[TestSample]:
        """生成问候样本"""
        samples = []
        for greeting in self.GREETINGS:
            samples.append(TestSample(
                text=greeting,
                intent="greeting",
                scenario="问候",
                difficulty="easy",
                confidence=1.0
            ))
        # 添加变体
        for _ in range(count - len(samples)):
            greeting = random.choice(self.GREETINGS)
            samples.append(TestSample(
                text=greeting + "啊",
                intent="greeting",
                scenario="问候变体",
                difficulty="easy",
                confidence=1.0
            ))
        return samples[:count]

    def generate_unknown_samples(self, count: int = 700) -> List[TestSample]:
        """生成未知/无关样本"""
        samples = []

        # 否定句
        negations = [
            "不痛", "没病", "没有不舒服", "不疼", "不难受",
            "没症状", "一切正常", "身体很好"
        ]
        for neg in negations:
            samples.append(TestSample(
                text=neg,
                intent="unknown",
                scenario="否定句",
                difficulty="easy",
                confidence=1.0
            ))

        # 无意义输入
        for _ in range(100):
            chars = random.choice(["啊啊", "哦哦", "嗯嗯", "痛痛", "呵呵", "嘻嘻"])
            samples.append(TestSample(
                text=chars * random.randint(2, 5),
                intent="unknown",
                scenario="无意义输入",
                difficulty="easy",
                confidence=1.0
            ))

        # 无关话题
        for _ in range(300):
            topic = random.choice(self.UNRELATED_TOPICS)
            patterns = [
                f"{topic}怎么样",
                f"今天{topic}吗",
                f"关于{topic}",
                f"{topic}新闻",
                f"最近{topic}"
            ]
            samples.append(TestSample(
                text=random.choice(patterns),
                intent="unknown",
                scenario="无关话题",
                difficulty="medium",
                confidence=1.0
            ))

        # 模糊输入
        for _ in range(200):
            samples.append(TestSample(
                text=random.choice(["嗯", "哦", "啊", "呃", "啥", "什么"]),
                intent="unknown",
                scenario="模糊输入",
                difficulty="medium",
                confidence=1.0
            ))

        return samples[:count]

    def generate_edge_cases(self, count: int = 500) -> List[TestSample]:
        """生成边缘/困难样本"""
        samples = []

        # 同义表达
        synonyms = [
            ("肚子疼", "腹痛", "胃疼", "肚脐疼"),
            ("拉肚子", "腹泻", "肚子泻", "大便稀"),
            ("发烧", "发热", "体温高", "浑身发烫"),
            ("头疼", "头痛", "脑袋疼", "太阳穴疼")
        ]
        for original, *others in synonyms:
            samples.append(TestSample(
                text=original,
                intent="symptom_inquiry",
                scenario="同义词-标准",
                difficulty="medium",
                confidence=1.0
            ))
            for variant in others:
                samples.append(TestSample(
                    text=variant,
                    intent="symptom_inquiry",
                    scenario="同义词-变体",
                    difficulty="hard",
                    confidence=1.0
                ))

        # 错别字
        typos = [
            ("头痛", "头通", "头疼", "头腾"),
            ("发烧", "发少", "发热"),
            ("咳嗽", "咳嗍", "可嗽")
        ]
        for correct, *wrong in typos:
            for typo in wrong:
                samples.append(TestSample(
                    text=f"我{typo}",
                    intent="symptom_inquiry",
                    scenario="错别字",
                    difficulty="hard",
                    confidence=1.0
                ))

        # 混合意图 (需要主意图)
        mixed = [
            ("头痛发烧挂什么科", "department_query"),
            ("吃阿莫西林能治头痛吗", "medication_consult"),
            ("头痛怎么预防", "health_education")
        ]
        for text, intent in mixed:
            samples.append(TestSample(
                text=text,
                intent=intent,
                scenario="混合意图",
                difficulty="hard",
                confidence=0.8  # 混合意图可能有歧义
            ))

        # 极短输入
        for short in ["痛", "疼", "痒", "咳", "吐", "泻", "晕", "麻"]:
            samples.append(TestSample(
                text=short,
                intent="unknown",  # 极短输入通常无法判断
                scenario="极短输入",
                difficulty="hard",
                confidence=0.5
            ))

        return samples[:count]

    def generate_comprehensive_dataset(self, total: int = 5000) -> List[TestSample]:
        """生成综合测试数据集"""
        # 按比例分配各意图样本
        distribution = {
            "symptom_inquiry": 800,
            "department_query": 600,
            "medication_consult": 700,
            "appointment": 500,
            "health_education": 800,
            "greeting": 400,
            "unknown": 700,
            "edge_cases": 500
        }

        all_samples = []

        print("生成症状咨询样本...")
        all_samples.extend(self.generate_symptom_samples(distribution["symptom_inquiry"]))

        print("生成科室查询样本...")
        all_samples.extend(self.generate_department_samples(distribution["department_query"]))

        print("生成用药咨询样本...")
        all_samples.extend(self.generate_medication_samples(distribution["medication_consult"]))

        print("生成预约挂号样本...")
        all_samples.extend(self.generate_appointment_samples(distribution["appointment"]))

        print("生成健康教育样本...")
        all_samples.extend(self.generate_health_education_samples(distribution["health_education"]))

        print("生成问候样本...")
        all_samples.extend(self.generate_greeting_samples(distribution["greeting"]))

        print("生成未知意图样本...")
        all_samples.extend(self.generate_unknown_samples(distribution["unknown"]))

        print("生成边缘情况样本...")
        all_samples.extend(self.generate_edge_cases(distribution["edge_cases"]))

        # 打乱顺序
        random.shuffle(all_samples)

        print(f"\n总计生成 {len(all_samples)} 条测试样本")

        # 统计
        intent_count = {}
        for s in all_samples:
            intent_count[s.intent] = intent_count.get(s.intent, 0) + 1

        print("\n意图分布:")
        for intent, count in intent_count.items():
            print(f"  {self.INTENTS.get(intent, intent)}: {count} 条")

        return all_samples

    def save_dataset(self, samples: List[TestSample], filepath: str):
        """保存数据集"""
        data = {
            "metadata": {
                "total_samples": len(samples),
                "generated_at": datetime.now().isoformat(),
                "intents": list(set(s.intent for s in samples)),
                "scenarios": list(set(s.scenario for s in samples))
            },
            "samples": [asdict(s) for s in samples]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n数据集已保存到: {filepath}")


def main():
    """主函数"""
    generator = MedicalTestDatasetGenerator()

    # 生成5000条测试数据
    samples = generator.generate_comprehensive_dataset(5000)

    # 保存到文件
    import os
    output_dir = "C:/Users/ASUS/Desktop/medical/medical_agent/tests/algorithem"
    os.makedirs(output_dir, exist_ok=True)

    generator.save_dataset(samples, f"{output_dir}/test_dataset_5000.json")

    # 另外保存一个便于读取的格式
    with open(f"{output_dir}/test_dataset_5000_simple.jsonl", 'w', encoding='utf-8') as f:
        for s in samples:
            f.write(json.dumps(asdict(s), ensure_ascii=False) + '\n')

    print(f"\n简化格式数据已保存到: {output_dir}/test_dataset_5000_simple.jsonl")


if __name__ == "__main__":
    main()
