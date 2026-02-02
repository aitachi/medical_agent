-- ============================================================
-- 医疗智能助手 - MySQL 数据库架构
-- 版本: 1.0.0
-- 创建日期: 2026-02-02
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS `medical_agent` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `medical_agent`;

-- ============================================================
-- 1. 知识库表
-- ============================================================

-- 药品表
CREATE TABLE IF NOT EXISTS `drugs` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `generic_name` VARCHAR(200) NOT NULL COMMENT '通用名',
  `english_name` VARCHAR(200) DEFAULT NULL COMMENT '英文名',
  `category` VARCHAR(100) DEFAULT NULL COMMENT '药品类别',
  `indications` TEXT DEFAULT NULL COMMENT '适应症(JSON数组)',
  `contraindications` TEXT DEFAULT NULL COMMENT '禁忌症(JSON数组)',
  `side_effects` TEXT DEFAULT NULL COMMENT '副作用(JSON数组)',
  `dosage` VARCHAR(500) DEFAULT NULL COMMENT '用法用量',
  `interactions` TEXT DEFAULT NULL COMMENT '药物相互作用(JSON数组)',
  `warnings` TEXT DEFAULT NULL COMMENT '警告信息',
  `common_allergens` TEXT DEFAULT NULL COMMENT '常见过敏原(JSON数组)',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_generic_name` (`generic_name`),
  KEY `idx_category` (`category`),
  KEY `idx_english_name` (`english_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='药品知识库';

-- 疾病表
CREATE TABLE IF NOT EXISTS `diseases` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(200) NOT NULL COMMENT '疾病名称',
  `category` VARCHAR(100) DEFAULT NULL COMMENT '疾病分类',
  `description` TEXT DEFAULT NULL COMMENT '疾病描述',
  `symptoms` TEXT DEFAULT NULL COMMENT '相关症状(JSON数组)',
  `risk_factors` TEXT DEFAULT NULL COMMENT '危险因素(JSON数组)',
  `common_departments` TEXT DEFAULT NULL COMMENT '相关科室(JSON数组)',
  `prevention_advice` TEXT DEFAULT NULL COMMENT '预防建议',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_name` (`name`),
  KEY `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='疾病知识库';

-- 症状表
CREATE TABLE IF NOT EXISTS `symptoms` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(200) NOT NULL COMMENT '症状名称',
  `body_part` VARCHAR(100) DEFAULT NULL COMMENT '部位',
  `description` TEXT DEFAULT NULL COMMENT '症状描述',
  `common_diseases` TEXT DEFAULT NULL COMMENT '相关疾病(JSON数组)',
  `severity` VARCHAR(50) DEFAULT NULL COMMENT '严重程度(轻微/中等/严重)',
  `department_hint` VARCHAR(200) DEFAULT NULL COMMENT '建议科室',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_name` (`name`),
  KEY `idx_body_part` (`body_part`),
  KEY `idx_severity` (`severity`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='症状知识库';

-- 科室表
CREATE TABLE IF NOT EXISTS `departments` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(200) NOT NULL COMMENT '科室名称',
  `alias` TEXT DEFAULT NULL COMMENT '别名(JSON数组)',
  `description` TEXT DEFAULT NULL COMMENT '科室描述',
  `common_diseases` TEXT DEFAULT NULL COMMENT '常见疾病(JSON数组)',
  `common_symptoms` TEXT DEFAULT NULL COMMENT '常见症状(JSON数组)',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='科室知识库';

-- 药物相互作用表
CREATE TABLE IF NOT EXISTS `drug_interactions` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `drug_a` VARCHAR(200) NOT NULL COMMENT '药物A',
  `drug_b` VARCHAR(200) NOT NULL COMMENT '药物B',
  `severity` ENUM('mild', 'moderate', 'severe') DEFAULT 'moderate' COMMENT '严重程度',
  `description` TEXT DEFAULT NULL COMMENT '相互作用描述',
  `recommendation` TEXT DEFAULT NULL COMMENT '建议',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY `idx_drug_a` (`drug_a`),
  KEY `idx_drug_b` (`drug_b`),
  KEY `idx_severity` (`severity`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='药物相互作用';

-- 同义词表
CREATE TABLE IF NOT EXISTS `synonyms` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `term` VARCHAR(200) NOT NULL COMMENT '标准术语',
  `synonym` VARCHAR(200) NOT NULL COMMENT '同义词',
  `category` VARCHAR(50) DEFAULT NULL COMMENT '类别(drug/disease/symptom)',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY `idx_term` (`term`),
  KEY `idx_synonym` (`synonym`),
  KEY `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='同义词映射';

-- 急救模式表
CREATE TABLE IF NOT EXISTS `emergency_patterns` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `pattern` VARCHAR(500) NOT NULL COMMENT '关键词模式',
  `severity` ENUM('urgent', 'emergency', 'critical') DEFAULT 'urgent' COMMENT '紧急程度',
  `action_advice` TEXT DEFAULT NULL COMMENT '处理建议',
  `call_120` BOOLEAN DEFAULT FALSE COMMENT '是否建议拨打120',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY `idx_severity` (`severity`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='急救模式识别';

-- ============================================================
-- 2. 训练数据表
-- ============================================================

-- 训练样本表
CREATE TABLE IF NOT EXISTS `training_samples` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `text` TEXT NOT NULL COMMENT '用户输入文本',
  `intent` VARCHAR(50) NOT NULL COMMENT '意图标签',
  `scenario` VARCHAR(100) DEFAULT NULL COMMENT '场景',
  `difficulty` ENUM('easy', 'medium', 'hard') DEFAULT 'medium' COMMENT '难度级别',
  `confidence` DECIMAL(3,2) DEFAULT 1.00 COMMENT '置信度',
  `metadata` TEXT DEFAULT NULL COMMENT '元数据(JSON)',
  `source_file` VARCHAR(100) DEFAULT NULL COMMENT '来源文件',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY `idx_intent` (`intent`),
  KEY `idx_scenario` (`scenario`),
  KEY `idx_difficulty` (`difficulty`),
  FULLTEXT KEY `ft_text` (`text`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='训练样本数据';

-- ============================================================
-- 3. 会话数据表
-- ============================================================

-- 会话表
CREATE TABLE IF NOT EXISTS `sessions` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `session_id` VARCHAR(100) NOT NULL COMMENT '会话ID',
  `user_id` VARCHAR(100) DEFAULT NULL COMMENT '用户ID',
  `status` ENUM('active', 'inactive', 'closed') DEFAULT 'active' COMMENT '会话状态',
  `last_intent` VARCHAR(50) DEFAULT NULL COMMENT '最后意图',
  `metadata` TEXT DEFAULT NULL COMMENT '会话元数据(JSON)',
  `message_count` INT DEFAULT 0 COMMENT '消息数量',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_session_id` (`session_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_updated_at` (`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话';

-- 对话消息表
CREATE TABLE IF NOT EXISTS `conversation_messages` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `session_id` VARCHAR(100) NOT NULL COMMENT '会话ID',
  `message_type` ENUM('user', 'assistant', 'system') NOT NULL COMMENT '消息类型',
  `content` TEXT NOT NULL COMMENT '消息内容',
  `intent` VARCHAR(50) DEFAULT NULL COMMENT '识别的意图',
  `confidence` DECIMAL(3,2) DEFAULT NULL COMMENT '意图置信度',
  `skill_invoked` VARCHAR(100) DEFAULT NULL COMMENT '调用的技能',
  `entities` TEXT DEFAULT NULL COMMENT '提取的实体(JSON)',
  `processing_time_ms` INT DEFAULT NULL COMMENT '处理时间(毫秒)',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY `idx_session_id` (`session_id`),
  KEY `idx_message_type` (`message_type`),
  KEY `idx_intent` (`intent`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_messages_session` FOREIGN KEY (`session_id`) REFERENCES `sessions`(`session_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话消息记录';

-- ============================================================
-- 4. 测试结果表
-- ============================================================

-- 测试结果表
CREATE TABLE IF NOT EXISTS `test_results` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `test_name` VARCHAR(200) NOT NULL COMMENT '测试名称',
  `test_type` VARCHAR(50) DEFAULT NULL COMMENT '测试类型',
  `total_samples` INT DEFAULT 0 COMMENT '总样本数',
  `correct_predictions` INT DEFAULT 0 COMMENT '正确预测数',
  `accuracy` DECIMAL(5,4) DEFAULT 0.0000 COMMENT '准确率',
  `intent_accuracy` DECIMAL(5,4) DEFAULT 0.0000 COMMENT '意图准确率',
  `details` TEXT DEFAULT NULL COMMENT '详细信息(JSON)',
  `test_file` VARCHAR(200) DEFAULT NULL COMMENT '测试文件',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY `idx_test_name` (`test_name`),
  KEY `idx_test_type` (`test_type`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试结果记录';

-- ============================================================
-- 5. 系统配置和日志表
-- ============================================================

-- 系统配置表
CREATE TABLE IF NOT EXISTS `system_config` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `config_key` VARCHAR(100) NOT NULL COMMENT '配置键',
  `config_value` TEXT NOT NULL COMMENT '配置值',
  `description` VARCHAR(500) DEFAULT NULL COMMENT '描述',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置';

-- API 请求日志表
CREATE TABLE IF NOT EXISTS `api_logs` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `session_id` VARCHAR(100) DEFAULT NULL COMMENT '会话ID',
  `endpoint` VARCHAR(200) NOT NULL COMMENT 'API端点',
  `method` VARCHAR(10) NOT NULL COMMENT '请求方法',
  `request_data` TEXT DEFAULT NULL COMMENT '请求数据(JSON)',
  `response_code` INT DEFAULT NULL COMMENT 'HTTP状态码',
  `response_time_ms` INT DEFAULT NULL COMMENT '响应时间(毫秒)',
  `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
  `ip_address` VARCHAR(45) DEFAULT NULL COMMENT '客户端IP',
  `user_agent` VARCHAR(500) DEFAULT NULL COMMENT '用户代理',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY `idx_session_id` (`session_id`),
  KEY `idx_endpoint` (`endpoint`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='API请求日志';

-- ============================================================
-- 索引优化
-- ============================================================

-- 为全文搜索添加全文索引
ALTER TABLE `drugs` ADD FULLTEXT INDEX `ft_drug_search` (`generic_name`, `english_name`, `indications`);
ALTER TABLE `diseases` ADD FULLTEXT INDEX `ft_disease_search` (`name`, `description`);
ALTER TABLE `symptoms` ADD FULLTEXT INDEX `ft_symptom_search` (`name`, `description`);

-- ============================================================
-- 初始化数据
-- ============================================================

-- 插入默认系统配置
INSERT IGNORE INTO `system_config` (`config_key`, `config_value`, `description`) VALUES
('intent_threshold', '0.75', '意图识别置信度阈值'),
('entity_threshold', '0.70', '实体抽取置信度阈值'),
('max_session_history', '20', '最大会话历史记录数'),
('enable_llm', 'false', '是否启用LLM增强'),
('knowledge_base_version', 'concise_v1.0', '当前知识库版本');

-- ============================================================
-- 视图定义
-- ============================================================

-- 会话统计视图
CREATE OR REPLACE VIEW `v_session_stats` AS
SELECT
    s.session_id,
    s.user_id,
    s.status,
    s.message_count,
    COUNT(cm.id) as actual_message_count,
    s.created_at,
    s.updated_at,
    TIMESTAMPDIFF(MINUTE, s.created_at, s.updated_at) as duration_minutes
FROM sessions s
LEFT JOIN conversation_messages cm ON s.session_id = cm.session_id
GROUP BY s.session_id;

-- 知识库统计视图
CREATE OR REPLACE VIEW `v_knowledge_stats` AS
SELECT
    'drugs' as category,
    COUNT(*) as total_count
FROM drugs
UNION ALL
SELECT 'diseases', COUNT(*) FROM diseases
UNION ALL
SELECT 'symptoms', COUNT(*) FROM symptoms
UNION ALL
SELECT 'departments', COUNT(*) FROM departments
UNION ALL
SELECT 'training_samples', COUNT(*) FROM training_samples;

-- ============================================================
-- 存储过程
-- ============================================================

DELIMITER //

-- 清理过期会话的存储过程
CREATE PROCEDURE `sp_cleanup_old_sessions`(IN days INT)
BEGIN
    DELETE FROM sessions
    WHERE status = 'closed'
    AND updated_at < DATE_SUB(NOW(), INTERVAL days DAY);
END //

-- 获取会话历史记录的存储过程
CREATE PROCEDURE `sp_get_session_history`(IN p_session_id VARCHAR(100))
BEGIN
    SELECT
        cm.message_type,
        cm.content,
        cm.intent,
        cm.confidence,
        cm.created_at
    FROM conversation_messages cm
    WHERE cm.session_id = p_session_id
    ORDER BY cm.created_at ASC
    LIMIT 50;
END //

DELIMITER ;
