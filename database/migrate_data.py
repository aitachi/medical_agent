#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移脚本 - 将 JSON 数据导入 MySQL
"""

import json
import pymysql
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',  # 根据实际情况修改
    'database': 'medical_agent',
    'charset': 'utf8mb4'
}


class DataMigrator:
    """数据迁移器"""

    def __init__(self, config: Dict):
        """初始化迁移器"""
        self.config = config
        self.conn = None
        self.cursor = None
        self.stats = {
            'drugs': 0,
            'diseases': 0,
            'symptoms': 0,
            'departments': 0,
            'drug_interactions': 0,
            'synonyms': 0,
            'emergency_patterns': 0,
            'training_samples': 0
        }

    def connect(self):
        """连接数据库"""
        try:
            self.conn = pymysql.connect(**self.config)
            self.cursor = self.conn.cursor()
            print(f"[SUCCESS] 已连接到数据库 {self.config['database']}")
        except Exception as e:
            print(f"[ERROR] 数据库连接失败: {e}")
            raise

    def close(self):
        """关闭连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("[INFO] 数据库连接已关闭")

    def migrate_drugs(self, drugs_data: Dict):
        """迁移药品数据"""
        print(f"\n[INFO] 开始迁移药品数据...")

        sql = """INSERT IGNORE INTO drugs
            (generic_name, english_name, category, indications, contraindications,
             side_effects, dosage, interactions, warnings, common_allergens)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""

        for name, data in drugs_data.items():
            try:
                self.cursor.execute(sql, (
                    name,
                    data.get('english_name'),
                    data.get('category'),
                    json.dumps(data.get('indications', []), ensure_ascii=False),
                    json.dumps(data.get('contraindications', []), ensure_ascii=False),
                    json.dumps(data.get('side_effects', []), ensure_ascii=False),
                    data.get('dosage'),
                    json.dumps(data.get('interactions', []), ensure_ascii=False),
                    data.get('warnings'),
                    json.dumps(data.get('common_allergens', []), ensure_ascii=False)
                ))
                self.stats['drugs'] += 1
            except Exception as e:
                print(f"[ERROR] 药品 {name} 插入失败: {e}")

        self.conn.commit()
        print(f"[SUCCESS] 药品数据迁移完成，共 {self.stats['drugs']} 条")

    def migrate_diseases(self, diseases_data: Dict):
        """迁移疾病数据"""
        print(f"\n[INFO] 开始迁移疾病数据...")

        sql = """INSERT IGNORE INTO diseases
            (name, category, description, symptoms, risk_factors,
             common_departments, prevention_advice)
            VALUES (%s, %s, %s, %s, %s, %s, %s)"""

        for name, data in diseases_data.items():
            try:
                self.cursor.execute(sql, (
                    name,
                    data.get('category'),
                    data.get('description'),
                    json.dumps(data.get('symptoms', []), ensure_ascii=False),
                    json.dumps(data.get('risk_factors', []), ensure_ascii=False),
                    json.dumps(data.get('common_departments', []), ensure_ascii=False),
                    data.get('prevention_advice')
                ))
                self.stats['diseases'] += 1
            except Exception as e:
                print(f"[ERROR] 疾病 {name} 插入失败: {e}")

        self.conn.commit()
        print(f"[SUCCESS] 疾病数据迁移完成，共 {self.stats['diseases']} 条")

    def migrate_symptoms(self, symptoms_data: Dict):
        """迁移症状数据"""
        print(f"\n[INFO] 开始迁移症状数据...")

        sql = """INSERT IGNORE INTO symptoms
            (name, body_part, description, common_diseases, severity, department_hint)
            VALUES (%s, %s, %s, %s, %s, %s)"""

        for name, data in symptoms_data.items():
            try:
                self.cursor.execute(sql, (
                    name,
                    data.get('body_part'),
                    data.get('description'),
                    json.dumps(data.get('common_diseases', []), ensure_ascii=False),
                    data.get('severity'),
                    data.get('department_hint')
                ))
                self.stats['symptoms'] += 1
            except Exception as e:
                print(f"[ERROR] 症状 {name} 插入失败: {e}")

        self.conn.commit()
        print(f"[SUCCESS] 症状数据迁移完成，共 {self.stats['symptoms']} 条")

    def migrate_departments(self, departments_data: Dict):
        """迁移科室数据"""
        print(f"\n[INFO] 开始迁移科室数据...")

        sql = """INSERT IGNORE INTO departments
            (name, alias, description, common_diseases, common_symptoms)
            VALUES (%s, %s, %s, %s, %s)"""

        for name, data in departments_data.items():
            try:
                self.cursor.execute(sql, (
                    name,
                    json.dumps(data.get('alias', []), ensure_ascii=False),
                    data.get('description'),
                    json.dumps(data.get('common_diseases', []), ensure_ascii=False),
                    json.dumps(data.get('common_symptoms', []), ensure_ascii=False)
                ))
                self.stats['departments'] += 1
            except Exception as e:
                print(f"[ERROR] 科室 {name} 插入失败: {e}")

        self.conn.commit()
        print(f"[SUCCESS] 科室数据迁移完成，共 {self.stats['departments']} 条")

    def migrate_drug_interactions(self, interactions_data: Dict):
        """迁移药物相互作用数据"""
        print(f"\n[INFO] 开始迁移药物相互作用数据...")

        sql = """INSERT IGNORE INTO drug_interactions
            (drug_a, drug_b, severity, description, recommendation)
            VALUES (%s, %s, %s, %s, %s)"""

        for key, data in interactions_data.items():
            try:
                # key 格式通常是 "drug_a-drug_b"
                if '-' in key:
                    drug_a, drug_b = key.split('-', 1)
                    self.cursor.execute(sql, (
                        drug_a,
                        drug_b,
                        data.get('severity', 'moderate'),
                        data.get('description'),
                        data.get('recommendation')
                    ))
                    self.stats['drug_interactions'] += 1
            except Exception as e:
                print(f"[ERROR] 药物相互作用 {key} 插入失败: {e}")

        self.conn.commit()
        print(f"[SUCCESS] 药物相互作用数据迁移完成，共 {self.stats['drug_interactions']} 条")

    def migrate_synonyms(self, synonyms_data: Dict):
        """迁移同义词数据"""
        print(f"\n[INFO] 开始迁移同义词数据...")

        sql = """INSERT IGNORE INTO synonyms (term, synonym, category)
            VALUES (%s, %s, %s)"""

        for term, synonyms_list in synonyms_data.items():
            try:
                for synonym in synonyms_list if isinstance(synonyms_list, list) else [synonyms_list]:
                    # 推断类别
                    category = None
                    if term in self.get_drug_names():
                        category = 'drug'
                    elif term in self.get_disease_names():
                        category = 'disease'
                    elif term in self.get_symptom_names():
                        category = 'symptom'

                    self.cursor.execute(sql, (term, synonym, category))
                    self.stats['synonyms'] += 1
            except Exception as e:
                print(f"[ERROR] 同义词 {term} 插入失败: {e}")

        self.conn.commit()
        print(f"[SUCCESS] 同义词数据迁移完成，共 {self.stats['synonyms']} 条")

    def migrate_emergency_patterns(self, patterns_data: Dict):
        """迁移急救模式数据"""
        print(f"\n[INFO] 开始迁移急救模式数据...")

        sql = """INSERT IGNORE INTO emergency_patterns
            (pattern, severity, action_advice, call_120)
            VALUES (%s, %s, %s, %s)"""

        for severity, patterns in patterns_data.items():
            try:
                for pattern in patterns if isinstance(patterns, list) else [patterns]:
                    self.cursor.execute(sql, (
                        pattern,
                        severity,
                        patterns.get('advice') if isinstance(patterns, dict) else '请立即就医',
                        patterns.get('call_120', False) if isinstance(patterns, dict) else False
                    ))
                    self.stats['emergency_patterns'] += 1
            except Exception as e:
                print(f"[ERROR] 急救模式插入失败: {e}")

        self.conn.commit()
        print(f"[SUCCESS] 急救模式数据迁移完成，共 {self.stats['emergency_patterns']} 条")

    def migrate_training_samples(self, data_source: str):
        """迁移训练样本数据"""
        print(f"\n[INFO] 开始迁移训练样本数据...")

        sql = """INSERT IGNORE INTO training_samples
            (text, intent, scenario, difficulty, confidence, metadata, source_file)
            VALUES (%s, %s, %s, %s, %s, %s, %s)"""

        if data_source.endswith('.jsonl'):
            # JSONL 格式
            with open(data_source, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        self.cursor.execute(sql, (
                            data.get('text'),
                            data.get('intent'),
                            data.get('scenario'),
                            data.get('difficulty', 'medium'),
                            data.get('confidence', 1.0),
                            json.dumps(data.get('metadata'), ensure_ascii=False),
                            os.path.basename(data_source)
                        ))
                        self.stats['training_samples'] += 1
                    except Exception as e:
                        print(f"[ERROR] 训练样本行插入失败: {e}")
        else:
            # JSON 格式
            with open(data_source, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        try:
                            self.cursor.execute(sql, (
                                item.get('text'),
                                item.get('intent'),
                                item.get('scenario'),
                                item.get('difficulty', 'medium'),
                                item.get('confidence', 1.0),
                                json.dumps(item.get('metadata'), ensure_ascii=False),
                                os.path.basename(data_source)
                            ))
                            self.stats['training_samples'] += 1
                        except Exception as e:
                            print(f"[ERROR] 训练样本插入失败: {e}")

        self.conn.commit()
        print(f"[SUCCESS] 训练样本数据迁移完成，共 {self.stats['training_samples']} 条")

    def get_drug_names(self):
        """获取药品名称列表（缓存）"""
        if not hasattr(self, '_drug_names'):
            self.cursor.execute("SELECT generic_name FROM drugs")
            self._drug_names = [row[0] for row in self.cursor.fetchall()]
        return self._drug_names

    def get_disease_names(self):
        """获取疾病名称列表（缓存）"""
        if not hasattr(self, '_disease_names'):
            self.cursor.execute("SELECT name FROM diseases")
            self._disease_names = [row[0] for row in self.cursor.fetchall()]
        return self._disease_names

    def get_symptom_names(self):
        """获取症状名称列表（缓存）"""
        if not hasattr(self, '_symptom_names'):
            self.cursor.execute("SELECT name FROM symptoms")
            self._symptom_names = [row[0] for row in self.cursor.fetchall()]
        return self._symptom_names

    def print_stats(self):
        """打印统计信息"""
        print("\n" + "="*60)
        print("数据迁移统计")
        print("="*60)
        for key, value in self.stats.items():
            print(f"{key:20s}: {value:6d} 条")
        print("="*60)
        print(f"总计: {sum(self.stats.values()):6d} 条")


def main():
    """主函数"""
    print("="*60)
    print("医疗智能助手 - 数据迁移工具")
    print("="*60)

    # 初始化迁移器
    migrator = DataMigrator(DB_CONFIG)

    try:
        # 连接数据库
        migrator.connect()

        # 1. 迁移知识库数据
        knowledge_base_file = os.path.join(os.path.dirname(__file__), '../data/knowledge_base.json')
        if os.path.exists(knowledge_base_file):
            print(f"\n[INFO] 加载知识库文件: {knowledge_base_file}")
            with open(knowledge_base_file, 'r', encoding='utf-8') as f:
                kb_data = json.load(f)

            # 迁移各类数据
            if 'drugs' in kb_data:
                migrator.migrate_drugs(kb_data['drugs'])
                migrator._drug_names = None  # 清除缓存

            if 'diseases' in kb_data:
                migrator.migrate_diseases(kb_data['diseases'])
                migrator._disease_names = None

            if 'symptoms' in kb_data:
                migrator.migrate_symptoms(kb_data['symptoms'])
                migrator._symptom_names = None

            if 'departments' in kb_data:
                migrator.migrate_departments(kb_data['departments'])

            if 'drug_interactions' in kb_data:
                migrator.migrate_drug_interactions(kb_data['drug_interactions'])

            if 'synonyms' in kb_data:
                migrator.migrate_synonyms(kb_data['synonyms'])

            if 'emergency_patterns' in kb_data:
                migrator.migrate_emergency_patterns(kb_data['emergency_patterns'])

        # 2. 迁移训练数据
        training_files = [
            '../tests/algorithem/test_dataset_5000_simple.jsonl',
            '../tests/algorithem/extended_training_data.json'
        ]

        for training_file in training_files:
            file_path = os.path.join(os.path.dirname(__file__), training_file)
            if os.path.exists(file_path):
                print(f"\n[INFO] 加载训练文件: {file_path}")
                migrator.migrate_training_samples(file_path)

        # 打印统计
        migrator.print_stats()

    except Exception as e:
        print(f"\n[ERROR] 迁移过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        migrator.close()


if __name__ == "__main__":
    main()
