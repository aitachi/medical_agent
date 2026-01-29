# -*- coding: utf-8 -*-
"""
医疗智能助手 - 知识库服务
加载和查询外部JSON知识库
"""

import json
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import threading


@dataclass
class KnowledgeResult:
    """知识查询结果"""
    found: bool
    category: str
    data: Any = None
    suggestions: List[str] = None
    metadata: Dict[str, Any] = None


class KnowledgeService:
    """
    知识库服务
    负责加载、缓存和查询外部知识库
    """

    def __init__(self, knowledge_base_path: str = "data/knowledge_base.json"):
        """
        初始化知识库服务

        Args:
            knowledge_base_path: 知识库文件路径
        """
        self.knowledge_base_path = Path(knowledge_base_path)
        self._knowledge_base: Dict[str, Any] = {}
        self._loaded = False
        self._load_time: Optional[datetime] = None
        self._lock = threading.RLock()
        self._version = None

    def load(self, force_reload: bool = False) -> bool:
        """
        加载知识库

        Args:
            force_reload: 是否强制重新加载

        Returns:
            bool: 是否加载成功
        """
        with self._lock:
            if self._loaded and not force_reload:
                return True

            try:
                if not self.knowledge_base_path.exists():
                    import warnings
                    warnings.warn(f"Knowledge base file not found: {self.knowledge_base_path}")
                    return False

                with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                    self._knowledge_base = json.load(f)

                self._loaded = True
                self._load_time = datetime.now()
                self._version = self._knowledge_base.get('version', 'unknown')

                return True

            except Exception as e:
                import warnings
                warnings.warn(f"Failed to load knowledge base: {e}")
                return False

    async def load_async(self, force_reload: bool = False) -> bool:
        """异步加载知识库"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.load, force_reload
        )

    def is_loaded(self) -> bool:
        """检查是否已加载"""
        return self._loaded

    def get_version(self) -> Optional[str]:
        """获取知识库版本"""
        return self._version

    def get_load_time(self) -> Optional[datetime]:
        """获取加载时间"""
        return self._load_time

    def reload(self) -> bool:
        """重新加载知识库"""
        return self.load(force_reload=True)

    # ========== 症状查询 ==========

    def query_symptom(self, symptom: str) -> KnowledgeResult:
        """
        查询症状信息

        Args:
            symptom: 症状名称

        Returns:
            KnowledgeResult: 查询结果
        """
        if not self._loaded:
            self.load()

        symptoms = self._knowledge_base.get('symptoms', {})

        # 精确匹配
        if symptom in symptoms:
            return KnowledgeResult(
                found=True,
                category="symptom",
                data=symptoms[symptom],
                metadata={"match_type": "exact"}
            )

        # 别名匹配
        for symptom_name, symptom_data in symptoms.items():
            aliases = symptom_data.get('aliases', [])
            if symptom in aliases:
                return KnowledgeResult(
                    found=True,
                    category="symptom",
                    data=symptom_data,
                    metadata={"match_type": "alias", "canonical_name": symptom_name}
                )

        # 模糊匹配
        matches = []
        for symptom_name, symptom_data in symptoms.items():
            if symptom in symptom_name or symptom_name in symptom:
                matches.append(symptom_name)
            # 检查别名
            for alias in symptom_data.get('aliases', []):
                if symptom in alias or alias in symptom:
                    matches.append(symptom_name)
                    break

        if matches:
            return KnowledgeResult(
                found=True,
                category="symptom",
                data=symptoms[matches[0]],
                suggestions=matches[1:5],
                metadata={"match_type": "fuzzy", "matches": matches}
            )

        # 未找到
        return KnowledgeResult(
            found=False,
            category="symptom",
            suggestions=list(symptoms.keys())[:10]
        )

    def get_all_symptoms(self) -> List[str]:
        """获取所有症状列表"""
        if not self._loaded:
            self.load()

        symptoms = self._knowledge_base.get('symptoms', {})
        return list(symptoms.keys())

    # ========== 药品查询 ==========

    def query_drug(self, drug_name: str) -> KnowledgeResult:
        """
        查询药品信息

        Args:
            drug_name: 药品名称

        Returns:
            KnowledgeResult: 查询结果
        """
        if not self._loaded:
            self.load()

        drugs = self._knowledge_base.get('drugs', {})

        # 精确匹配
        if drug_name in drugs:
            return KnowledgeResult(
                found=True,
                category="drug",
                data=drugs[drug_name],
                metadata={"match_type": "exact"}
            )

        # 通用名/英文名匹配
        for name, drug_data in drugs.items():
            if drug_name.lower() == drug_data.get('english_name', '').lower():
                return KnowledgeResult(
                    found=True,
                    category="drug",
                    data=drug_data,
                    metadata={"match_type": "english_name", "canonical_name": name}
                )

        # 模糊匹配
        matches = []
        for name in drugs.keys():
            if drug_name in name or name in drug_name:
                matches.append(name)

        if matches:
            return KnowledgeResult(
                found=True,
                category="drug",
                data=drugs[matches[0]],
                suggestions=matches[1:5],
                metadata={"match_type": "fuzzy", "matches": matches}
            )

        # 未找到
        return KnowledgeResult(
            found=False,
            category="drug",
            suggestions=list(drugs.keys())[:10]
        )

    def get_all_drugs(self) -> List[str]:
        """获取所有药品列表"""
        if not self._loaded:
            self.load()

        drugs = self._knowledge_base.get('drugs', {})
        return list(drugs.keys())

    # ========== 科室查询 ==========

    def query_department(self, department: str) -> KnowledgeResult:
        """
        查询科室信息

        Args:
            department: 科室名称

        Returns:
            KnowledgeResult: 查询结果
        """
        if not self._loaded:
            self.load()

        departments = self._knowledge_base.get('departments', {})

        # 精确匹配
        if department in departments:
            return KnowledgeResult(
                found=True,
                category="department",
                data=departments[department],
                metadata={"match_type": "exact"}
            )

        # 子科室匹配
        matches = []
        for dept_name, dept_data in departments.items():
            if department in dept_name or dept_name in department:
                matches.append(dept_name)
            # 检查子科室
            for sub_dept in dept_data.get('sub_departments', []):
                if department in sub_dept or sub_dept in department:
                    matches.append(dept_name)
                    break

        if matches:
            return KnowledgeResult(
                found=True,
                category="department",
                data=departments[matches[0]],
                suggestions=matches[1:3],
                metadata={"match_type": "fuzzy", "matches": matches}
            )

        # 未找到
        return KnowledgeResult(
            found=False,
            category="department",
            suggestions=list(departments.keys())[:10]
        )

    def query_department_by_symptom(self, symptom: str) -> KnowledgeResult:
        """
        根据症状查询推荐科室

        Args:
            symptom: 症状名称

        Returns:
            KnowledgeResult: 查询结果
        """
        if not self._loaded:
            self.load()

        departments = self._knowledge_base.get('departments', {})

        recommendations = []

        for dept_name, dept_data in departments.items():
            common_symptoms = dept_data.get('common_symptoms', [])
            for s in common_symptoms:
                if symptom in s or s in symptom:
                    recommendations.append({
                        "department": dept_name,
                        "symptom": s,
                        "description": dept_data.get('description', '')
                    })
                    break

        if recommendations:
            return KnowledgeResult(
                found=True,
                category="department",
                data=recommendations,
                metadata={"query_type": "by_symptom"}
            )

        return KnowledgeResult(
            found=False,
            category="department",
            suggestions=[]
        )

    def get_all_departments(self) -> List[str]:
        """获取所有科室列表"""
        if not self._loaded:
            self.load()

        departments = self._knowledge_base.get('departments', {})
        return list(departments.keys())

    # ========== 紧急模式查询 ==========

    def get_emergency_patterns(self) -> Dict[str, List[Dict]]:
        """获取紧急模式"""
        if not self._loaded:
            self.load()

        return self._knowledge_base.get('emergency_patterns', {})

    # ========== 疾病预防查询 ==========

    def query_disease_prevention(self, disease: str) -> KnowledgeResult:
        """
        查询疾病预防知识

        Args:
            disease: 疾病名称

        Returns:
            KnowledgeResult: 查询结果
        """
        if not self._loaded:
            self.load()

        prevention = self._knowledge_base.get('disease_prevention', {})

        # 精确匹配
        if disease in prevention:
            return KnowledgeResult(
                found=True,
                category="prevention",
                data=prevention[disease],
                metadata={"match_type": "exact"}
            )

        # 模糊匹配
        for disease_name, data in prevention.items():
            if disease in disease_name or disease_name in disease:
                return KnowledgeResult(
                    found=True,
                    category="prevention",
                    data=data,
                    metadata={"match_type": "fuzzy", "canonical_name": disease_name}
                )

        # 未找到
        return KnowledgeResult(
            found=False,
            category="prevention",
            suggestions=list(prevention.keys())[:10]
        )

    # ========== 饮食禁忌查询 ==========

    def query_food_restrictions(self, condition: str) -> KnowledgeResult:
        """
        查询饮食禁忌

        Args:
            condition: 疾病或状况名称

        Returns:
            KnowledgeResult: 查询结果
        """
        if not self._loaded:
            self.load()

        restrictions = self._knowledge_base.get('food_restrictions', {})

        # 精确匹配
        if condition in restrictions:
            return KnowledgeResult(
                found=True,
                category="food_restrictions",
                data=restrictions[condition],
                metadata={"match_type": "exact"}
            )

        # 模糊匹配
        for cond_name, data in restrictions.items():
            if condition in cond_name or cond_name in condition:
                return KnowledgeResult(
                    found=True,
                    category="food_restrictions",
                    data=data,
                    metadata={"match_type": "fuzzy", "canonical_name": cond_name}
                )

        # 未找到
        return KnowledgeResult(
            found=False,
            category="food_restrictions",
            suggestions=list(restrictions.keys())[:10]
        )

    # ========== 同义词查询 ==========

    def get_synonyms(self, term: str) -> List[str]:
        """
        获取同义词

        Args:
            term: 术语

        Returns:
            List[str]: 同义词列表
        """
        if not self._loaded:
            self.load()

        synonyms = self._knowledge_base.get('synonyms', {})

        # 检查是否是主词
        if term in synonyms:
            return synonyms[term]

        # 检查是否是同义词
        for main_term, syn_list in synonyms.items():
            if term in syn_list:
                result = [main_term] + [s for s in syn_list if s != term]
                return result

        return []

    # ========== 通用查询 ==========

    def search(self, keyword: str, categories: List[str] = None) -> Dict[str, List[str]]:
        """
        搜索关键词

        Args:
            keyword: 关键词
            categories: 搜索类别，None表示搜索所有

        Returns:
            Dict[str, List[str]]: 每个类别的匹配结果
        """
        if not self._loaded:
            self.load()

        if categories is None:
            categories = ['symptoms', 'drugs', 'departments']

        results = {}

        for category in categories:
            if category == 'symptoms':
                matches = [s for s in self.get_all_symptoms() if keyword in s]
                results['symptoms'] = matches[:10]

            elif category == 'drugs':
                matches = [d for d in self.get_all_drugs() if keyword in d]
                results['drugs'] = matches[:10]

            elif category == 'departments':
                matches = [d for d in self.get_all_departments() if keyword in d]
                results['departments'] = matches[:10]

        return results

    # ========== 批量查询 ==========

    async def batch_query(self, queries: List[tuple]) -> List[KnowledgeResult]:
        """
        批量查询

        Args:
            queries: 查询列表，每个元素为 (category, keyword) 元组

        Returns:
            List[KnowledgeResult]: 查询结果列表
        """
        tasks = []
        for category, keyword in queries:
            if category == 'symptom':
                task = asyncio.get_event_loop().run_in_executor(
                    None, self.query_symptom, keyword
                )
            elif category == 'drug':
                task = asyncio.get_event_loop().run_in_executor(
                    None, self.query_drug, keyword
                )
            elif category == 'department':
                task = asyncio.get_event_loop().run_in_executor(
                    None, self.query_department, keyword
                )
            else:
                task = asyncio.get_event_loop().run_in_executor(
                    None, lambda: KnowledgeResult(found=False, category=category)
                )
            tasks.append(task)

        return await asyncio.gather(*tasks)

    # ========== 统计信息 ==========

    def get_stats(self) -> Dict[str, Any]:
        """
        获取知识库统计信息

        Returns:
            Dict: 统计信息
        """
        if not self._loaded:
            self.load()

        return {
            "version": self._version,
            "load_time": self._load_time.isoformat() if self._load_time else None,
            "symptoms_count": len(self._knowledge_base.get('symptoms', {})),
            "drugs_count": len(self._knowledge_base.get('drugs', {})),
            "departments_count": len(self._knowledge_base.get('departments', {})),
            "prevention_count": len(self._knowledge_base.get('disease_prevention', {})),
            "emergency_patterns_count": len(self._knowledge_base.get('emergency_patterns', {})),
        }


# ============================================================
# 全局知识库服务实例
# ============================================================

_global_knowledge_service: Optional[KnowledgeService] = None


def get_knowledge_service(knowledge_base_path: str = "data/knowledge_base.json") -> KnowledgeService:
    """获取全局知识库服务"""
    global _global_knowledge_service
    if _global_knowledge_service is None:
        _global_knowledge_service = KnowledgeService(knowledge_base_path)
        _global_knowledge_service.load()
    return _global_knowledge_service


def reset_knowledge_service():
    """重置全局知识库服务"""
    global _global_knowledge_service
    _global_knowledge_service = None


# ============================================================
# 测试代码
# ============================================================

if __name__ == "__main__":
    import asyncio

    async def test():
        print("知识库服务测试")
        print("=" * 60)

        # 创建服务
        service = KnowledgeService("data/knowledge_base.json")
        await service.load_async()

        # 打印统计
        print("\n1. 知识库统计:")
        stats = service.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # 症状查询
        print("\n2. 症状查询（头痛）:")
        result = service.query_symptom("头痛")
        print(f"  找到: {result.found}")
        if result.found:
            print(f"  描述: {result.data.get('description', 'N/A')[:50]}...")

        # 药品查询
        print("\n3. 药品查询（阿莫西林）:")
        result = service.query_drug("阿莫西林")
        print(f"  找到: {result.found}")
        if result.found:
            print(f"  类别: {result.data.get('category', 'N/A')}")

        # 科室查询
        print("\n4. 科室查询（神经内科）:")
        result = service.query_department("神经内科")
        print(f"  找到: {result.found}")
        if result.found:
            print(f"  描述: {result.data.get('description', 'N/A')}")

        # 按症状查询科室
        print("\n5. 按症状查询科室（头痛）:")
        result = service.query_department_by_symptom("头痛")
        print(f"  找到: {result.found}")
        if result.found and result.data:
            print(f"  推荐: {result.data[0].get('department', 'N/A')}")

        # 同义词查询
        print("\n6. 同义词查询（头疼）:")
        synonyms = service.get_synonyms("头疼")
        print(f"  同义词: {synonyms}")

        # 批量查询
        print("\n7. 批量查询:")
        queries = [
            ('symptom', '发热'),
            ('drug', '布洛芬'),
            ('department', '内科'),
        ]
        results = await service.batch_query(queries)
        for (category, keyword), result in zip(queries, results):
            print(f"  {category}({keyword}): {'找到' if result.found else '未找到'}")

    asyncio.run(test())
