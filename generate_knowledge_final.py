# -*- coding: utf-8 -*-
"""
医学知识库生成器 - 最终版本
生成症状和疾病知识数据
"""

import asyncio
import aiohttp
import json
import re
import sys
from pathlib import Path

# 设置控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置
API_KEY = "sk-a9a4edb1b4214016baa11c9be3b9fec4"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen-max"
DATA_DIR = Path("d:/Users/liu.liu/Desktop/github/medical/data")


class MedicalKnowledgeGenerator:
    def __init__(self):
        self.session = None
        self.success_count = 0
        self.fail_count = 0

    async def start(self):
        timeout = aiohttp.ClientTimeout(total=120)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def stop(self):
        if self.session:
            await self.session.close()

    async def call_llm(self, prompt: str):
        """调用LLM API"""
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        system_prompt = """你是专业的医学数据生成专家。请严格按照要求生成医学数据。
输出必须是纯JSON格式，不要有任何其他文字，不要使用markdown格式。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4000
        }

        try:
            async with self.session.post(
                f"{BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    return None

                result = await response.json()
                content = result["choices"][0]["message"]["content"]

                # 清理
                content = content.strip()
                if content.startswith("```"):
                    content = re.sub(r'```(?:json)?\n?', '', content)
                    content = re.sub(r'\n```$', '', content)

                return json.loads(content)

        except Exception:
            return None

    def save_json(self, data, filepath):
        full_path = DATA_DIR / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return full_path

    async def generate_symptom(self, name: str, category: str, sid: int):
        """生成单条症状"""
        prompt = f"""为症状"{name}"({category}类)生成知识数据：

{{
  "id": "SYM{sid:03d}",
  "name": "{name}",
  "aliases": ["别名1", "别名2"],
  "category": "{category}",
  "description": "症状描述(30-50字)",
  "common_causes": ["原因1", "原因2", "原因3", "原因4", "原因5"],
  "red_flags": ["危险信号1", "危险信号2"],
  "recommended_department": "首选科室",
  "alternative_departments": ["备选科室1", "备选科室2"],
  "self_care": ["护理建议1", "护理建议2"],
  "severity_levels": {{"mild": "轻度", "moderate": "中度", "severe": "重度"}}
}}
纯JSON输出。"""

        return await self.call_llm(prompt)

    async def generate_symptoms_batch(self, symptoms_data):
        """批量生成症状"""
        all_symptoms = []
        sid = 1

        for category, symptoms in symptoms_data:
            print(f"\n{category}:")
            for name in symptoms:
                print(f"  {name}...", end=" ", flush=True)

                # 尝试3次
                for attempt in range(3):
                    data = await self.generate_symptom(name, category, sid)
                    if data:
                        all_symptoms.append(data)
                        self.success_count += 1
                        sid += 1
                        print("OK")
                        break
                    else:
                        if attempt < 2:
                            await asyncio.sleep(1)
                else:
                    self.fail_count += 1
                    print("FAIL")

                # 每生成10条保存一次
                if len(all_symptoms) % 10 == 0:
                    self.save_json({"total": len(all_symptoms), "symptoms": all_symptoms}, "knowledge/symptoms.json")
                    print(f"    已保存 {len(all_symptoms)} 条")

        return all_symptoms

    async def generate_disease(self, name: str, category: str, icd: str, did: int):
        """生成单条疾病"""
        prompt = f"""为疾病"{name}"({category}类，ICD-10: {icd})生成知识数据：

{{
  "id": "DIS{did:03d}",
  "name": "{name}",
  "aliases": ["别名"],
  "icd_code": "{icd}",
  "category": "{category}",
  "description": "疾病描述(50字内)",
  "diagnostic_criteria": {{"definite": "确诊标准", "suspected": "疑诊标准"}},
  "symptoms": {{"typical": ["典型症状"], "atypical": ["不典型"], "complications": ["并发症"]}},
  "treatment": {{"medication": ["药物方案"], "lifestyle": ["生活方式"]}},
  "prevention": {{"primary": ["一级预防"], "secondary": ["二级预防"]}}
}}
纯JSON输出。"""

        return await self.call_llm(prompt)

    async def generate_diseases_batch(self, diseases_data):
        """批量生成疾病"""
        all_diseases = []
        did = 1

        for name, category, icd in diseases_data:
            print(f"  {name}...", end=" ", flush=True)

            for attempt in range(3):
                data = await self.generate_disease(name, category, icd, did)
                if data:
                    all_diseases.append(data)
                    self.success_count += 1
                    did += 1
                    print("OK")
                    break
                else:
                    if attempt < 2:
                        await asyncio.sleep(1)
            else:
                self.fail_count += 1
                print("FAIL")

            if len(all_diseases) % 10 == 0:
                self.save_json({"total": len(all_diseases), "diseases": all_diseases}, "knowledge/diseases.json")

        return all_diseases


async def main():
    generator = MedicalKnowledgeGenerator()
    await generator.start()

    try:
        print("="*60)
        print("医学知识库生成器")
        print("="*60)

        # 症状列表（扩展到200+）
        symptoms_data = [
            # 全身症状
            ("全身症状", ["发热", "乏力", "水肿", "消瘦", "肥胖", "盗汗", "畏寒", "潮热", "全身不适", "淋巴结肿大", "体重下降", "体重增加", "食欲不振", "食欲亢进", "口干", "口渴"]),
            # 呼吸系统
            ("呼吸系统", ["咳嗽", "咳痰", "呼吸困难", "胸痛", "咯血", "喘息", "胸闷", "气短", "紫绀", "鼻塞", "流涕", "打鼾", "喉咙痛", "声音嘶哑", "咽异物感", "鼻出血", "嗅觉减退", "呼吸急促", "呼吸困难", "咳嗽伴胸痛"]),
            # 心血管
            ("心血管系统", ["心悸", "胸闷", "胸痛", "晕厥", "发绀", "血压升高", "血压降低", "心前区不适", "脉搏异常", "心慌", "心跳不规则", "心动过速", "心动过缓", "水肿(心源性)", "夜间阵发性呼吸困难"]),
            # 消化系统
            ("消化系统", ["腹痛", "恶心", "呕吐", "腹泻", "便秘", "黄疸", "呕血", "黑便", "反酸", "烧心", "吞咽困难", "腹胀", "肝区痛", "口苦", "嗳气", "呃逆", "便血", "腹部包块", "里急后重", "消化不良"]),
            # 神经系统
            ("神经系统", ["头痛", "头晕", "失眠", "嗜睡", "抽搐", "意识障碍", "记忆力减退", "肢体麻木", "行走不稳", "震颤", "肌肉萎缩", "肌肉无力", "感觉异常", "眩晕", "晕厥先兆", "认知障碍", "言语障碍", "吞咽困难", "视力模糊", "复视"]),
            # 内分泌代谢
            ("内分泌代谢", ["多饮", "多尿", "多食", "怕热", "畏寒", "毛发脱落", "毛发增多", "色素沉着", "多汗", "少汗", "皮肤干燥", "皮肤湿润", "体型改变", "生长发育异常", "性早熟", "性发育延迟"]),
            # 泌尿生殖
            ("泌尿生殖", ["尿频", "尿急", "尿痛", "血尿", "排尿困难", "尿失禁", "少尿", "多尿", "夜尿增多", "尿液浑浊", "尿液异味", "腰痛", "下腹痛", "阴囊肿大", "睾丸疼痛", "性交痛", "白带异常", "月经不调", "痛经", "闭经"]),
            # 血液系统
            ("血液系统", ["贫血", "出血", "瘀斑", "紫癜", "淋巴结肿大", "脾肿大", "面色苍白", "面色潮红", "乏力(贫血)", "易疲劳", "易出血", "牙龈出血", "鼻出血", "皮肤瘀点", "血肿"]),
            # 运动系统
            ("运动系统", ["关节痛", "肌肉痛", "活动受限", "晨僵", "关节肿胀", "关节畸形", "背痛", "颈痛", "腰痛", "四肢痛", "骨痛", "肌无力", "肌肉萎缩", "运动障碍", "步态异常"]),
            # 五官症状
            ("五官症状", ["视力下降", "眼痛", "流泪", "眼干", "眼痒", "畏光", "复视", "听力下降", "耳鸣", "耳痛", "耳闷", "鼻痒", "打喷嚏", "咽痒", "咽异物感", "声音嘶哑", "味觉异常", "口腔溃疡", "牙痛", "牙龈出血"]),
            # 精神心理
            ("精神心理", ["焦虑", "抑郁", "烦躁", "淡漠", "幻觉", "妄想", "强迫症状", "恐惧", "情绪不稳", "易怒", "情绪低落", "兴趣减退", "注意力不集中", "思维迟缓", "记忆力下降"]),
            # 皮肤症状
            ("皮肤症状", ["皮疹", "瘙痒", "脱发", "多汗", "皮肤干燥", "皮肤脱屑", "红斑", "丘疹", "水疱", "脓疱", "结节", "风团", "紫癜", "瘀斑", "色素沉着", "色素脱失", "皮肤溃疡", "皮肤增厚", "皮肤萎缩", "蜘蛛痣"]),
            # 妇科症状
            ("妇科症状", ["月经量多", "月经量少", "经期延长", "经期缩短", "经间期出血", "白带增多", "白带减少", "白带异味", "外阴瘙痒", "外阴疼痛", "乳房胀痛", "乳房肿块", "乳头溢液", "下腹坠胀", "性交出血"]),
            # 儿科症状
            ("儿科症状", ["夜啼", "喂养困难", "生长迟缓", "出牙延迟", "囟门未闭", "鸡胸", "漏斗胸", "脐疝", "腹股沟疝", "鞘膜积液", "隐睾", "包茎", "包皮过长", "遗尿", "多动"])
        ]

        # 疾病列表（100+）
        diseases_data = [
            # 心血管 (15)
            ("高血压", "心血管", "I10"), ("冠心病", "心血管", "I25"), ("急性心肌梗死", "心血管", "I21"),
            ("心力衰竭", "心血管", "I50"), ("心律失常", "心血管", "I49"), ("风湿性心脏病", "心血管", "I05"),
            ("肺源性心脏病", "心血管", "I27"), ("感染性心内膜炎", "心血管", "I33"), ("心肌炎", "心血管", "I40"),
            ("心包炎", "心血管", "I31"), ("主动脉瓣狭窄", "心血管", "I35"), ("二尖瓣关闭不全", "心血管", "I34"),
            ("主动脉夹层", "心血管", "I71"), ("阵发性室上性心动过速", "心血管", "I47"), ("病态窦房结综合征", "心血管", "I49"),
            # 呼吸 (12)
            ("慢性阻塞性肺疾病", "呼吸", "J44"), ("肺炎", "呼吸", "J18"), ("支气管哮喘", "呼吸", "J45"),
            ("急性支气管炎", "呼吸", "J20"), ("慢性支气管炎", "呼吸", "J42"), ("肺栓塞", "呼吸", "I26"),
            ("肺结核", "呼吸", "A15"), ("胸膜炎", "呼吸", "I26"), ("气胸", "呼吸", "J93"),
            ("睡眠呼吸暂停综合征", "呼吸", "G47"), ("急性呼吸窘迫综合征", "呼吸", "J80"), ("支气管扩张", "呼吸", "J47"),
            # 消化 (15)
            ("急性胃炎", "消化", "K29"), ("慢性胃炎", "消化", "K29"), ("消化性溃疡", "消化", "K25"),
            ("胃食管反流病", "消化", "K21"), ("肝硬化", "消化", "K74"), ("急性胰腺炎", "消化", "K85"),
            ("慢性胰腺炎", "消化", "K86"), ("胆囊炎", "消化", "K80"), ("胆石症", "消化", "K80"),
            ("脂肪肝", "消化", "K76"), ("溃疡性结肠炎", "消化", "K51"), ("克罗恩病", "消化", "K50"),
            ("肠梗阻", "消化", "K56"), ("急性阑尾炎", "消化", "K35"), ("痔疮", "消化", "K64"),
            # 内分泌 (10)
            ("2型糖尿病", "内分泌", "E11"), ("1型糖尿病", "内分泌", "E10"), ("甲状腺功能亢进症", "内分泌", "E05"),
            ("甲状腺功能减退症", "内分泌", "E03"), ("痛风", "内分泌", "M10"), ("骨质疏松症", "内分泌", "M80"),
            ("库欣综合征", "内分泌", "E24"), ("原发性醛固酮增多症", "内分泌", "E26"), ("嗜铬细胞瘤", "内分泌", "D35"),
            ("甲状旁腺功能亢进症", "内分泌", "E21"),
            # 神经 (12)
            ("脑梗死", "神经", "I63"), ("脑出血", "神经", "I61"), ("短暂性脑缺血发作", "神经", "G45"),
            ("偏头痛", "神经", "G43"), ("紧张性头痛", "神经", "G44"), ("帕金森病", "神经", "G20"),
            ("癫痫", "神经", "G40"), ("阿尔茨海默病", "神经", "G30"), ("面神经炎", "神经", "G51"),
            ("三叉神经痛", "神经", "G50"), ("重症肌无力", "神经", "G70"), ("吉兰-巴雷综合征", "神经", "G61"),
            # 泌尿 (8)
            ("肾结石", "泌尿", "N20"), ("输尿管结石", "泌尿", "N20"), ("膀胱炎", "泌尿", "N30"),
            ("肾盂肾炎", "泌尿", "N10"), ("前列腺增生", "泌尿", "N40"), ("前列腺炎", "泌尿", "N41"),
            ("慢性肾炎", "泌尿", "N03"), ("肾病综合征", "泌尿", "N04"),
            # 血液 (6)
            ("缺铁性贫血", "血液", "D50"), ("巨幼细胞性贫血", "血液", "D53"), ("再生障碍性贫血", "血液", "D61"),
            ("急性白血病", "血液", "C91"), ("慢性白血病", "血液", "C92"), ("淋巴瘤", "血液", "C81"),
            # 风湿 (8)
            ("类风湿关节炎", "风湿", "M05"), ("系统性红斑狼疮", "风湿", "M32"), ("强直性脊柱炎", "风湿", "M45"),
            ("干燥综合征", "风湿", "M35"), ("皮肌炎", "风湿", "M33"), ("系统性硬化症", "风湿", "M34"),
            ("骨关节炎", "风湿", "M15"), ("银屑病关节炎", "风湿", "M07"),
            # 其他 (14)
            ("流行性感冒", "感染", "J11"), ("病毒性肝炎", "感染", "B15"), ("细菌性肺炎", "感染", "J15"),
            ("尿路感染", "感染", "N39"), ("抑郁症", "精神", "F32"), ("焦虑症", "精神", "F41"),
            ("带状疱疹", "感染", "B02"), ("过敏性紫癜", "血液", "D69"), ("特发性血小板减少性紫癜", "血液", "D69"),
            ("糖尿病肾病", "内分泌", "E11"), ("糖尿病视网膜病变", "内分泌", "E11"), ("糖尿病足", "内分泌", "E11"),
            ("代谢综合征", "内分泌", "E88")
        ]

        # 生成症状
        print("\n生成症状数据...")
        symptoms = await generator.generate_symptoms_batch(symptoms_data)
        generator.save_json({"total": len(symptoms), "symptoms": symptoms}, "knowledge/symptoms.json")

        # 生成疾病
        print("\n生成疾病数据...")
        diseases = await generator.generate_diseases_batch(diseases_data)
        generator.save_json({"total": len(diseases), "diseases": diseases}, "knowledge/diseases.json")

        # 总结
        print("\n" + "="*60)
        print("生成完成!")
        print(f"症状: {len(symptoms)} 条")
        print(f"疾病: {len(diseases)} 条")
        print(f"成功: {generator.success_count}")
        print(f"失败: {generator.fail_count}")
        print("="*60)

    finally:
        await generator.stop()


if __name__ == "__main__":
    asyncio.run(main())
