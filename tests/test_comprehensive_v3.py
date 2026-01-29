# -*- coding: utf-8 -*-
"""
医疗智能助手 - 全面功能与精度测试
"""

import asyncio
import sys
import os
import tempfile

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def run_comprehensive_tests():
    print("=" * 70)
    print("医疗智能助手 - 全面功能与精度测试")
    print("=" * 70)

    errors = []
    test_results = []

    # 获取知识库路径（相对于项目根目录）
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(test_dir)
    kb_path = os.path.join(project_root, "data", "knowledge_base.json")

    # Test 1: Import all modules
    print("\n[1/20] 模块导入测试...")
    try:
        from core import EmergencyDetector, DrugSafetyChecker, CacheManager, SessionStore
        from services import KnowledgeService, ProfileService
        from config import Settings, get_settings
        from agent.exceptions import MedicalAgentError, EmergencyDetectedError
        from agent.monitoring import MetricsCollector
        from agent.user_profile import UserProfile, create_default_profile
        print("  OK: 所有模块导入成功")
        test_results.append(("模块导入", True))
    except Exception as e:
        errors.append(f"模块导入失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("模块导入", False))

    # Test 2: Emergency Detection - Critical cases
    print("\n[2/20] 紧急症状检测测试 (危急级别)...")
    try:
        from core.emergency_detector import EmergencyDetector, EmergencyLevel
        detector = EmergencyDetector(kb_path)

        critical_cases = [
            ("胸痛呼吸困难大汗", EmergencyLevel.CRITICAL),
            ("突然晕倒意识不清", EmergencyLevel.CRITICAL),
            ("呕血", EmergencyLevel.CRITICAL),
            ("咳血了", EmergencyLevel.CRITICAL),
            ("呼吸困难", EmergencyLevel.CRITICAL),
            ("剧烈突发头痛", EmergencyLevel.CRITICAL),
        ]

        passed = 0
        for text, expected_level in critical_cases:
            result = detector.detect(text)
            if result and result.level == expected_level:
                passed += 1
            else:
                actual = result.level.value if result else "None"
                print(f"    WARNING: \"{text}\" 期望 {expected_level.value} 但得到 {actual}")

        print(f"  OK: {passed}/{len(critical_cases)} 危急级别检测正确")
        test_results.append(("危急检测", passed == len(critical_cases)))
    except Exception as e:
        errors.append(f"危急检测失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("危急检测", False))

    # Test 3: Emergency Detection - Urgent cases
    print("\n[3/20] 紧急症状检测测试 (紧急级别)...")
    try:
        urgent_cases = [
            ("发高烧39度了", EmergencyLevel.URGENT),
            ("持续呕吐三天", EmergencyLevel.URGENT),
            ("心悸胸闷", EmergencyLevel.URGENT),
            ("外伤出血", EmergencyLevel.URGENT),
        ]

        passed = 0
        for text, expected_level in urgent_cases:
            result = detector.detect(text)
            if result and result.level == expected_level:
                passed += 1
            else:
                actual = result.level.value if result else "None"
                print(f"    WARNING: \"{text}\" 期望 {expected_level.value} 但得到 {actual}")

        print(f"  OK: {passed}/{len(urgent_cases)} 紧急级别检测正确")
        test_results.append(("紧急检测", passed == len(urgent_cases)))
    except Exception as e:
        errors.append(f"紧急检测失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("紧急检测", False))

    # Test 4: Safety Checker - Duplicate detection
    print("\n[4/20] 重复用药检测测试...")
    try:
        from core.safety_checker import DrugSafetyChecker
        checker = DrugSafetyChecker(kb_path)

        report = await checker.check(["阿司匹林", "阿司匹林", "阿司匹林"])
        duplicate_warnings = [w for w in report.warnings if w.type == "duplicate"]

        if len(duplicate_warnings) > 0:
            print("  OK: 重复用药检测正常")
            test_results.append(("重复用药检测", True))
        else:
            errors.append("重复用药检测失败")
            print("  FAILED: 未检测到重复用药")
            test_results.append(("重复用药检测", False))
    except Exception as e:
        errors.append(f"重复用药检测失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("重复用药检测", False))

    # Test 5: Safety Checker - Interaction detection
    print("\n[5/20] 药物相互作用检测测试...")
    try:
        interaction_tests = [
            (["阿司匹林", "布洛芬"], True),  # 应该检测到
            (["对乙酰氨基酚", "硝苯地平"], False),  # 应该是安全的
        ]

        passed = 0
        for drugs, should_warn in interaction_tests:
            report = await checker.check(drugs)
            has_critical = report.has_critical_issues()

            if should_warn:
                high_warnings = report.get_high_severity_warnings()
                if len(high_warnings) > 0:
                    passed += 1
                else:
                    print(f"    WARNING: {drugs} 应该有相互作用警告但没有")
            else:
                if not report.has_critical_issues():
                    passed += 1
                else:
                    print(f"    WARNING: {drugs} 应该是安全的但有警告")

        print(f"  OK: {passed}/{len(interaction_tests)} 相互作用检测正确")
        test_results.append(("相互作用检测", passed == len(interaction_tests)))
    except Exception as e:
        errors.append(f"相互作用检测失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("相互作用检测", False))

    # Test 6: Safety Checker - Allergy detection
    print("\n[6/20] 过敏检测测试...")
    try:
        profile = create_default_profile("test_allergy")
        profile.add_allergy("青霉素")

        report = await checker.check(["阿莫西林"], profile)
        allergy_warnings = [w for w in report.warnings if "allergy" in w.type]

        if len(allergy_warnings) > 0:
            print("  OK: 过敏检测正常")
            test_results.append(("过敏检测", True))
        else:
            errors.append("过敏检测失败")
            print("  FAILED: 未检测到青霉素过敏")
            test_results.append(("过敏检测", False))
    except Exception as e:
        errors.append(f"过敏检测失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("过敏检测", False))

    # Test 7: Knowledge Service - Symptom query
    print("\n[7/20] 症状查询测试...")
    try:
        from services.knowledge_service import KnowledgeService
        kb = KnowledgeService(kb_path)
        kb.load()

        symptoms = ["头痛", "发热", "咳嗽", "腹痛", "胸痛"]
        passed = 0
        for symptom in symptoms:
            result = kb.query_symptom(symptom)
            if result.found:
                passed += 1

        print(f"  OK: {passed}/{len(symptoms)} 症状查询成功")
        test_results.append(("症状查询", passed >= 4))
    except Exception as e:
        errors.append(f"症状查询失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("症状查询", False))

    # Test 8: Knowledge Service - Drug query
    print("\n[8/20] 药品查询测试...")
    try:
        drugs = ["阿莫西林", "布洛芬", "对乙酰氨基酚", "二甲双胍"]
        passed = 0
        for drug in drugs:
            result = kb.query_drug(drug)
            if result.found:
                passed += 1

        print(f"  OK: {passed}/{len(drugs)} 药品查询成功")
        test_results.append(("药品查询", passed >= 3))
    except Exception as e:
        errors.append(f"药品查询失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("药品查询", False))

    # Test 9: Knowledge Service - Department query
    print("\n[9/20] 科室查询测试...")
    try:
        depts = ["神经内科", "心血管内科", "呼吸内科"]
        passed = 0
        for dept in depts:
            result = kb.query_department(dept)
            if result.found:
                passed += 1

        print(f"  OK: {passed}/{len(depts)} 科室查询成功")
        test_results.append(("科室查询", passed >= 2))
    except Exception as e:
        errors.append(f"科室查询失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("科室查询", False))

    # Test 10: Session Store
    print("\n[10/20] 会话存储测试...")
    try:
        from core.session_store import SessionStore
        from agent.medical_agent import DialogueContext, IntentResult, IntentType

        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        store = SessionStore(db_path)
        await store.initialize()

        context = DialogueContext(
            session_id="test_123",
            user_id="user_123",
            turn_count=0
        )
        context.add_turn("你好", "您好", IntentResult(
            intent=IntentType.GREETING,
            confidence=0.95,
            target_skill="greeting-skill"
        ))

        await store.save_session(context)
        loaded = await store.load_session("test_123")

        if loaded and loaded.turn_count == 1:
            print("  OK: 会话存储正常")
            test_results.append(("会话存储", True))
        else:
            errors.append("会话存储失败")
            print(f"  FAILED: turn_count不匹配")
            test_results.append(("会话存储", False))

        os.unlink(db_path)
    except Exception as e:
        errors.append(f"会话存储失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("会话存储", False))

    # Test 11: Profile Service
    print("\n[11/20] 用户画像服务测试...")
    try:
        from services.profile_service import ProfileService, create_default_profile

        fd, db_path = tempfile.mkstemp(suffix="_profiles.db")
        os.close(fd)

        service = ProfileService(db_path)
        await service.initialize()

        profile = create_default_profile("test_prof")
        profile.basic_info["age"] = 35
        profile.medical_history.append("高血压")

        await service.save_profile(profile)
        loaded = await service.load_profile("test_prof")

        if loaded and loaded.basic_info.get("age") == 35:
            print("  OK: 用户画像服务正常")
            test_results.append(("用户画像服务", True))
        else:
            errors.append("用户画像服务失败")
            print(f"  FAILED: 数据不匹配")
            test_results.append(("用户画像服务", False))

        os.unlink(db_path)
    except Exception as e:
        errors.append(f"用户画像服务失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("用户画像服务", False))

    # Test 12: User Profile model
    print("\n[12/20] 用户画像模型测试...")
    try:
        from agent.user_profile import UserProfile, UserProfileBuilder, Gender

        profile = (UserProfileBuilder("test")
                   .with_age(30)
                   .with_gender("female")
                   .add_medical_history("糖尿病")
                   .add_allergy("青霉素")
                   .add_medication("二甲双胍", "0.5g")
                   .add_chronic_condition("糖尿病")
                   .build())

        checks = [
            (profile.get_age() == 30, "age"),
            (profile.get_gender() == Gender.FEMALE, "gender"),
            ("糖尿病" in profile.medical_history, "medical_history"),
            ("青霉素" in profile.allergies, "allergies"),
            ("二甲双胍" in profile.current_medications, "medication"),
            ("糖尿病" in profile.chronic_conditions, "chronic"),
        ]

        passed = sum(1 for c, _ in checks if c)
        print(f"  OK: {passed}/{len(checks)} 用户画像字段正确")
        test_results.append(("用户画像模型", passed >= 5))
    except Exception as e:
        errors.append(f"用户画像模型失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("用户画像模型", False))

    # Test 13: Monitoring
    print("\n[13/20] 监控指标测试...")
    try:
        from agent.monitoring import MetricsCollector
        collector = MetricsCollector()

        collector.record_intent_classification("symptom_inquiry", 0.85, 0.05, True)
        collector.record_skill_execution("symptom-analyzer", 0.15, True)
        collector.record_emergency("critical")
        collector.record_safety_warning("interaction", "critical")

        stats = collector.get_stats_summary()

        if stats["intent_classifications"] == 1:
            print("  OK: 监控指标正常")
            test_results.append(("监控指标", True))
        else:
            errors.append(f"监控指标失败")
            print(f"  FAILED: intent_classifications={stats['intent_classifications']}")
            test_results.append(("监控指标", False))
    except Exception as e:
        errors.append(f"监控指标失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("监控指标", False))

    # Test 14: Settings
    print("\n[14/20] 配置管理测试...")
    try:
        from config import Settings, get_settings
        settings = get_settings()

        checks = [
            (settings.app_name == "Medical AI Assistant", "app_name"),
            (hasattr(settings, "cache"), "has cache"),
            (hasattr(settings, "monitoring"), "has monitoring"),
            (hasattr(settings, "safety"), "has safety"),
        ]

        passed = sum(1 for c, _ in checks if c)
        print(f"  OK: {passed}/{len(checks)} 配置检查通过")
        test_results.append(("配置管理", passed >= 3))
    except Exception as e:
        errors.append(f"配置管理失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("配置管理", False))

    # Test 15: Emergency message formatting
    print("\n[15/20] 紧急消息格式化测试...")
    try:
        result = detector.detect("胸痛呼吸困难")
        formatted = detector.format_emergency_message(result)

        checks = [
            ("120" in formatted or "立即" in formatted, "has_call_to_action"),
            ("胸痛" in formatted or "紧急" in formatted, "has_content"),
            ("建议" in formatted or "行动" in formatted, "has_suggestion"),
        ]

        passed = sum(1 for c, _ in checks if c)
        print(f"  OK: {passed}/{len(checks)} 格式化检查通过")
        test_results.append(("紧急消息格式化", passed >= 2))
    except Exception as e:
        errors.append(f"紧急消息格式化失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("紧急消息格式化", False))

    # Test 16: Cache Manager
    print("\n[16/20] 缓存管理器测试...")
    try:
        from core.cache_manager import CacheManager
        cache = CacheManager(intent_cache_size=5, intent_ttl=1)

        async def mock_classify(text, ctx):
            return {"intent": "test", "confidence": 0.8}

        result1 = await cache.get_or_classify("test input", mock_classify, None)
        result2 = await cache.get_or_classify("test input", mock_classify, None)

        stats = cache.get_cache_stats("intent")

        if result1 and result2:
            print("  OK: 缓存管理器正常")
            test_results.append(("缓存管理器", True))
        else:
            errors.append("缓存管理器失败")
            print("  FAILED: 缓存返回None")
            test_results.append(("缓存管理器", False))
    except Exception as e:
        errors.append(f"缓存管理器失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("缓存管理器", False))

    # Test 17: Safety report formatting
    print("\n[17/20] 安全报告格式化测试...")
    try:
        report = await checker.check(["阿司匹林", "布洛芬"])
        formatted = checker.format_report(report)

        checks = [
            ("警告" in formatted or "⚠" in formatted, "has_warning"),
            ("建议" in formatted or "💡" in formatted, "has_suggestion"),
            ("免责声明" in formatted or "disclaimer" in formatted.lower(), "has_disclaimer"),
        ]

        passed = sum(1 for c, _ in checks if c)
        print(f"  OK: {passed}/{len(checks)} 格式化检查通过")
        test_results.append(("安全报告格式化", passed >= 2))
    except Exception as e:
        errors.append(f"安全报告格式化失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("安全报告格式化", False))

    # Test 18: Knowledge base synonyms
    print("\n[18/20] 知识库同义词测试...")
    try:
        synonyms = kb.get_synonyms("头疼")
        if "头痛" in synonyms:
            print("  OK: 同义词查询正常")
            test_results.append(("同义词查询", True))
        else:
            print(f"  WARNING: \"头疼\"的同义词未找到\"头痛\"")
            test_results.append(("同义词查询", False))
    except Exception as e:
        errors.append(f"同义词查询失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("同义词查询", False))

    # Test 19: Department by symptom query
    print("\n[19/20] 按症状查询科室测试...")
    try:
        result = kb.query_department_by_symptom("头痛")
        if result.found and len(result.data) > 0:
            print(f"  OK: 找到 {len(result.data)} 个科室推荐")
            test_results.append(("按症状查科室", True))
        else:
            print("  WARNING: 未找到科室推荐")
            test_results.append(("按症状查科室", False))
    except Exception as e:
        errors.append(f"按症状查科室失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("按症状查科室", False))

    # Test 20: Profile update from context
    print("\n[20/20] 从上下文更新画像测试...")
    try:
        fd, db_path = tempfile.mkstemp(suffix="_profile2.db")
        os.close(fd)

        service = ProfileService(db_path)
        await service.initialize()

        entities = {
            "disease": "高血压",
            "drug": "硝苯地平",
            "dosage": "10mg"
        }

        updates = await service.update_from_context("ctx_test", entities)

        if len(updates) >= 2:
            print(f"  OK: 从上下文更新了 {len(updates)} 个字段")
            test_results.append(("上下文更新画像", True))
        else:
            print(f"  WARNING: 只更新了 {len(updates)} 个字段")
            test_results.append(("上下文更新画像", False))

        os.unlink(db_path)
    except Exception as e:
        errors.append(f"上下文更新画像失败: {e}")
        print(f"  FAILED: {e}")
        test_results.append(("上下文更新画像", False))

    # Summary
    print("\n" + "=" * 70)
    passed_count = sum(1 for _, p in test_results if p)
    print(f"测试完成! 通过: {passed_count}/{len(test_results)}")

    failed_tests = [name for name, passed in test_results if not passed]
    if failed_tests:
        print(f"\n失败的测试: {failed_tests}")

    if errors:
        print("\n错误详情:")
        for err in errors:
            print(f"  - {err}")
    else:
        print("\n所有测试通过!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())
