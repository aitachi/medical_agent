#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据导入脚本 - 将 JSON 数据导入 SQLite
"""

import sys
import os
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager_sqlite import get_db


def import_knowledge_base():
    """导入知识库数据"""
    db = get_db()
    stats = {
        'drugs': 0,
        'diseases': 0,
        'symptoms': 0,
        'departments': 0
    }

    print("="*60)
    print("导入知识库数据")
    print("="*60)

    # 读取知识库文件
    kb_file = os.path.join(os.path.dirname(__file__), '../data/knowledge_base.json')
    if not os.path.exists(kb_file):
        print(f"[ERROR] 知识库文件不存在: {kb_file}")
        return stats

    with open(kb_file, 'r', encoding='utf-8') as f:
        kb_data = json.load(f)

    # 导入药品
    if 'drugs' in kb_data:
        print(f"\n[INFO] 导入药品数据...")
        count = db.bulk_insert_drugs(kb_data['drugs'])
        stats['drugs'] = count
        print(f"[SUCCESS] 药品数据导入完成，共 {count} 条")

    # 导入疾病
    if 'diseases' in kb_data:
        print(f"\n[INFO] 导入疾病数据...")
        count = db.bulk_insert_diseases(kb_data['diseases'])
        stats['diseases'] = count
        print(f"[SUCCESS] 疾病数据导入完成，共 {count} 条")

    # 导入症状
    if 'symptoms' in kb_data:
        print(f"\n[INFO] 导入症状数据...")
        count = db.bulk_insert_symptoms(kb_data['symptoms'])
        stats['symptoms'] = count
        print(f"[SUCCESS] 症状数据导入完成，共 {count} 条")

    # 导入科室
    if 'departments' in kb_data:
        print(f"\n[INFO] 导入科室数据...")
        count = db.bulk_insert_departments(kb_data['departments'])
        stats['departments'] = count
        print(f"[SUCCESS] 科室数据导入完成，共 {count} 条")

    return stats


def verify_import():
    """验证导入结果"""
    db = get_db()
    print("\n" + "="*60)
    print("数据验证")
    print("="*60)

    stats = db.get_statistics()
    for table, count in stats.items():
        print(f"{table:25s}: {count:6d} 条")

    print("="*60)
    print(f"总计: {sum(stats.values()):6d} 条")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("医疗智能助手 - 数据导入工具")
    print("="*60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 导入知识库
        stats = import_knowledge_base()

        # 验证导入
        verify_import()

        print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n[SUCCESS] 数据导入完成")

    except Exception as e:
        print(f"\n[ERROR] 导入过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
