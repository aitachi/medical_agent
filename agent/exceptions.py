# -*- coding: utf-8 -*-
"""
医疗智能助手 - 自定义异常体系
定义所有医疗Agent相关的异常类型
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass


class ErrorSeverity(Enum):
    """错误严重程度"""
    INFO = "info"           # 信息性，无需处理
    WARNING = "warning"     # 警告，需要注意但不影响运行
    ERROR = "error"         # 错误，影响功能但可继续
    CRITICAL = "critical"   # 严重，需要立即处理


# ============================================================
# 基础异常类
# ============================================================

class MedicalAgentError(Exception):
    """
    医疗Agent基础异常
    所有自定义异常的父类
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.severity = severity
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "details": self.details
        }

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


# ============================================================
# 意图分类异常
# ============================================================

class IntentClassificationError(MedicalAgentError):
    """
    意图分类错误
    当意图分类失败或置信度过低时抛出
    """

    def __init__(
        self,
        message: str,
        input_text: Optional[str] = None,
        confidence: Optional[float] = None,
        alternatives: Optional[List[Dict]] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if input_text:
            details['input_text'] = input_text[:100]  # 限制长度
        if confidence is not None:
            details['confidence'] = confidence
        if alternatives:
            details['alternatives'] = alternatives

        super().__init__(
            message=message,
            error_code="INTENT_001",
            severity=ErrorSeverity.WARNING,
            details=details
        )
        self.input_text = input_text
        self.confidence = confidence
        self.alternatives = alternatives or []


class AmbiguousIntentError(IntentClassificationError):
    """
    意图模糊错误
    当多个意图具有相似置信度时抛出
    """

    def __init__(
        self,
        message: str,
        candidate_intents: List[Dict[str, Any]],
        **kwargs
    ):
        details = kwargs.get('details', {})
        details['candidate_intents'] = candidate_intents

        super().__init__(
            message=message,
            error_code="INTENT_002",
            severity=ErrorSeverity.INFO,
            details=details
        )
        self.candidate_intents = candidate_intents


# ============================================================
# 知识库异常
# ============================================================

class KnowledgeBaseError(MedicalAgentError):
    """
    知识库错误
    当知识库加载、查询失败时抛出
    """

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        category: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if query:
            details['query'] = query
        if category:
            details['category'] = category

        super().__init__(
            message=message,
            error_code="KNOWLEDGE_001",
            severity=ErrorSeverity.ERROR,
            details=details
        )
        self.query = query
        self.category = category


class KnowledgeNotFoundError(KnowledgeBaseError):
    """
    知识未找到错误
    当知识库中未找到相关条目时抛出
    """

    def __init__(
        self,
        message: str,
        query: str,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        details['query'] = query
        if suggestions:
            details['suggestions'] = suggestions

        super().__init__(
            message=message,
            query=query,
            error_code="KNOWLEDGE_002",
            severity=ErrorSeverity.INFO,
            details=details
        )
        self.suggestions = suggestions or []


class KnowledgeLoadError(KnowledgeBaseError):
    """
    知识库加载错误
    当知识库文件加载失败时抛出
    """

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if file_path:
            details['file_path'] = file_path

        super().__init__(
            message=message,
            error_code="KNOWLEDGE_003",
            severity=ErrorSeverity.CRITICAL,
            details=details
        )
        self.file_path = file_path


# ============================================================
# Skill调用异常
# ============================================================

class SkillInvocationError(MedicalAgentError):
    """
    Skill调用错误
    当Skill执行失败时抛出
    """

    def __init__(
        self,
        message: str,
        skill_name: Optional[str] = None,
        input_data: Optional[Dict] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if skill_name:
            details['skill_name'] = skill_name
        if input_data:
            # 限制输入数据大小
            details['input_data'] = str(input_data)[:200]

        super().__init__(
            message=message,
            error_code="SKILL_001",
            severity=ErrorSeverity.ERROR,
            details=details
        )
        self.skill_name = skill_name
        self.input_data = input_data


class SkillNotFoundError(SkillInvocationError):
    """
    Skill未找到错误
    当请求的Skill不存在时抛出
    """

    def __init__(
        self,
        skill_name: str,
        available_skills: Optional[List[str]] = None,
        **kwargs
    ):
        message = f"Skill '{skill_name}' not found"
        details = kwargs.get('details', {})
        details['skill_name'] = skill_name
        if available_skills:
            details['available_skills'] = available_skills

        super().__init__(
            message=message,
            skill_name=skill_name,
            error_code="SKILL_002",
            severity=ErrorSeverity.ERROR,
            details=details
        )
        self.available_skills = available_skills or []


class SkillTimeoutError(SkillInvocationError):
    """
    Skill执行超时错误
    """

    def __init__(
        self,
        skill_name: str,
        timeout_seconds: float,
        **kwargs
    ):
        message = f"Skill '{skill_name}' execution timed out after {timeout_seconds}s"
        details = kwargs.get('details', {})
        details['timeout_seconds'] = timeout_seconds

        super().__init__(
            message=message,
            skill_name=skill_name,
            error_code="SKILL_003",
            severity=ErrorSeverity.WARNING,
            details=details
        )
        self.timeout_seconds = timeout_seconds


# ============================================================
# 安全检查异常
# ============================================================

class SafetyCheckError(MedicalAgentError):
    """
    安全检查错误 - 严重级别
    当检测到潜在的安全风险时抛出
    """

    def __init__(
        self,
        message: str,
        risk_type: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **kwargs
    ):
        details = kwargs.get('details', {})
        details['risk_type'] = risk_type

        super().__init__(
            message=message,
            error_code="SAFETY_001",
            severity=severity,
            details=details
        )
        self.risk_type = risk_type


class DrugInteractionError(SafetyCheckError):
    """
    药物相互作用错误
    当检测到药物相互作用风险时抛出
    """

    def __init__(
        self,
        message: str,
        drugs: List[str],
        interaction_description: str,
        severity: ErrorSeverity = ErrorSeverity.CRITICAL,
        **kwargs
    ):
        details = kwargs.get('details', {})
        details['drugs'] = drugs
        details['interaction'] = interaction_description

        super().__init__(
            message=message,
            risk_type="drug_interaction",
            severity=severity,
            details=details
        )
        self.drugs = drugs
        self.interaction_description = interaction_description


class DrugAllergyError(SafetyCheckError):
    """
    药物过敏风险错误
    """

    def __init__(
        self,
        message: str,
        drug: str,
        allergens: List[str],
        **kwargs
    ):
        details = kwargs.get('details', {})
        details['drug'] = drug
        details['allergens'] = allergens

        super().__init__(
            message=message,
            risk_type="allergy",
            severity=ErrorSeverity.CRITICAL,
            details=details
        )
        self.drug = drug
        self.allergens = allergens


class DrugDoseError(SafetyCheckError):
    """
    药物剂量错误
    """

    def __init__(
        self,
        message: str,
        drug: str,
        recommended_dose: str,
        actual_dose: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        details['drug'] = drug
        details['recommended_dose'] = recommended_dose
        if actual_dose:
            details['actual_dose'] = actual_dose

        super().__init__(
            message=message,
            risk_type="dose",
            severity=ErrorSeverity.WARNING,
            details=details
        )
        self.drug = drug
        self.recommended_dose = recommended_dose
        self.actual_dose = actual_dose


class ContraindicationError(SafetyCheckError):
    """
    禁忌症错误
    """

    def __init__(
        self,
        message: str,
        drug: str,
        contraindications: List[str],
        **kwargs
    ):
        details = kwargs.get('details', {})
        details['drug'] = drug
        details['contraindications'] = contraindications

        super().__init__(
            message=message,
            risk_type="contraindication",
            severity=ErrorSeverity.CRITICAL,
            details=details
        )
        self.drug = drug
        self.contraindications = contraindications


# ============================================================
# 紧急情况异常
# ============================================================

@dataclass
class EmergencyAction:
    """紧急处理建议"""
    action: str           # 建议行动
    urgency: str          # 紧急程度: immediate, same_day, monitor
    description: str      # 详细说明


class EmergencyDetectedError(MedicalAgentError):
    """
    紧急情况检测异常
    当检测到需要立即关注的医疗紧急情况时抛出
    """

    def __init__(
        self,
        message: str,
        severity: str,
        matched_patterns: List[str],
        suggested_action: EmergencyAction,
        symptoms: Optional[List[str]] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        details['severity'] = severity
        details['matched_patterns'] = matched_patterns
        details['suggested_action'] = {
            'action': suggested_action.action,
            'urgency': suggested_action.urgency,
            'description': suggested_action.description
        }
        if symptoms:
            details['symptoms'] = symptoms

        # 根据严重程度设置错误级别
        error_severity = ErrorSeverity.CRITICAL if severity == "critical" else ErrorSeverity.ERROR

        super().__init__(
            message=message,
            error_code="EMERGENCY_001",
            severity=error_severity,
            details=details
        )
        self.emergency_severity = severity  # critical, urgent, attention
        self.matched_patterns = matched_patterns
        self.suggested_action = suggested_action
        self.symptoms = symptoms or []


# ============================================================
# 会话异常
# ============================================================

class SessionError(MedicalAgentError):
    """
    会话错误
    """

    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if session_id:
            details['session_id'] = session_id

        super().__init__(
            message=message,
            error_code="SESSION_001",
            severity=ErrorSeverity.ERROR,
            details=details
        )
        self.session_id = session_id


class SessionNotFoundError(SessionError):
    """会话未找到"""

    def __init__(self, session_id: str, **kwargs):
        message = f"Session '{session_id}' not found"
        super().__init__(
            message=message,
            session_id=session_id,
            error_code="SESSION_002",
            severity=ErrorSeverity.WARNING,
            **kwargs
        )


class SessionExpiredError(SessionError):
    """会话已过期"""

    def __init__(self, session_id: str, expiry_time: str, **kwargs):
        message = f"Session '{session_id}' expired at {expiry_time}"
        details = kwargs.get('details', {})
        details['expiry_time'] = expiry_time

        super().__init__(
            message=message,
            session_id=session_id,
            error_code="SESSION_003",
            severity=ErrorSeverity.INFO,
            details=details
        )
        self.expiry_time = expiry_time


# ============================================================
# 配置异常
# ============================================================

class ConfigurationError(MedicalAgentError):
    """
    配置错误
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if config_key:
            details['config_key'] = config_key

        super().__init__(
            message=message,
            error_code="CONFIG_001",
            severity=ErrorSeverity.CRITICAL,
            details=details
        )
        self.config_key = config_key


# ============================================================
# 工具函数
# ============================================================

def format_error_for_user(error: MedicalAgentError) -> str:
    """
    将错误格式化为用户友好的消息

    Args:
        error: 异常对象

    Returns:
        str: 用户友好的错误消息
    """
    if isinstance(error, EmergencyDetectedError):
        return f"🚨 {error.message}\n\n建议: {error.suggested_action.description}"

    elif isinstance(error, DrugInteractionError):
        return f"⚠️ {error.message}\n\n相互作用: {error.interaction_description}"

    elif isinstance(error, DrugAllergyError):
        return f"⚠️ {error.message}\n\n过敏原: {', '.join(error.allergens)}"

    elif isinstance(error, KnowledgeNotFoundError):
        msg = f"未找到相关信息: {error.query}"
        if error.suggestions:
            msg += f"\n\n建议尝试: {', '.join(error.suggestions[:5])}"
        return msg

    elif isinstance(error, AmbiguousIntentError):
        return f"{error.message}\n\n请选择您想了解的内容"

    elif isinstance(error, SafetyCheckError):
        return f"⚠️ {error.message}"

    else:
        # 默认错误消息
        if error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR]:
            return f"抱歉，处理您的请求时遇到问题: {error.message}"
        else:
            return error.message


def get_error_recovery_suggestion(error: MedicalAgentError) -> Optional[str]:
    """
    获取错误恢复建议

    Args:
        error: 异常对象

    Returns:
        Optional[str]: 恢复建议
    """
    suggestions = {
        IntentClassificationError: "请尝试换一种说法，或更具体地描述您的问题",
        AmbiguousIntentError: "请选择您感兴趣的具体内容",
        KnowledgeNotFoundError: "请尝试其他关键词，或描述相关症状",
        SkillNotFoundError: "该功能暂未开放，请尝试其他功能",
        SafetyCheckError: "如有疑问，请咨询专业医生或药师",
        EmergencyDetectedError: "请按建议行动，必要时立即就医",
        SessionError: "请重新开始对话",
        ConfigurationError: "请联系系统管理员",
    }

    for error_class, suggestion in suggestions.items():
        if isinstance(error, error_class):
            return suggestion

    return "请稍后重试，或联系技术支持"
