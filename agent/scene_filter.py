"""
场景过滤器 - 意图识别前置过滤层

实现三层过滤机制：
1. 恶意检测（SQL注入、XSS攻击、命令注入）
2. 场景过滤（非医疗场景识别）
3. 敏感内容过滤（政治/色情/暴力/违禁）
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================
# 数据模型
# ============================================================

class FilterCategory(Enum):
    """过滤分类"""
    MALICIOUS_INTENT = "malicious_intent"      # 恶意内容
    OUT_OF_SCOPE = "out_of_scope"             # 非医疗场景
    SENSITIVE_CONTENT = "sensitive_content"   # 敏感内容
    PASSED = "passed"                          # 通过过滤


@dataclass
class FilterResult:
    """
    过滤结果

    Attributes:
        passed: 是否通过过滤
        intent_category: 意图分类（如未通过则为对应的过滤分类）
        rejection_reason: 拒绝原因
        suggested_response: 建议响应
        filter_level: 触发的过滤层级（1/2/3，0表示通过）
        detected_patterns: 检测到的模式列表
    """
    passed: bool
    intent_category: Optional[str] = None
    rejection_reason: Optional[str] = None
    suggested_response: Optional[str] = None
    filter_level: int = 0
    detected_patterns: List[str] = field(default_factory=list)

    def __post_init__(self):
        """初始化后处理"""
        if self.passed:
            self.intent_category = None
            self.rejection_reason = None
            self.suggested_response = None
            self.filter_level = 0


# ============================================================
# 场景过滤器
# ============================================================

class SceneFilter:
    """
    场景过滤器 - 意图识别前置过滤

    三层过滤流程：
    1. 恶意检测（Security Filter）- SQL注入、XSS攻击、命令注入
    2. 场景过滤（Scope Filter）- 非医疗场景识别
    3. 敏感内容过滤（Content Filter）- 政治/色情/暴力/违禁
    """

    # ========================================================
    # 第一层：恶意检测模式
    # ========================================================

    # SQL注入模式
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bor\b.*=.*\bor\b)",
        r"(\band\b.*=.*\band\b)",
        r"(;.*\bdrop\b)",
        r"(;.*\bdelete\b)",
        r"(;.*\binsert\b)",
        r"(;.*\bupdate\b)",
        r"(\bexec\b|\bexecute\b)",
        r"(\bxp_\w+)",
        r"(\'|\").*(\bor|\band).*=",
        r"(\/\*.*\*\/)",
        r"(--.*$)",
        r"(#.*$)",
        r"(<script[^>]*>)",
        r"(javascript:)",
        r"(on\w+\s*=)",
        r"(eval\s*\()",
        r"(expression\s*\()",
    ]

    # XSS攻击模式
    XSS_PATTERNS = [
        r"(<script[^>]*>.*?</script>)",
        r"(javascript\s*:)",
        r"(vbscript\s*:)",
        r"(onload\s*=)",
        r"(onerror\s*=)",
        r"(onclick\s*=)",
        r"(onmouseover\s*=)",
        r"(<iframe[^>]*>)",
        r"(<embed[^>]*>)",
        r"(<object[^>]*>)",
        r"(<link[^>]*>)",
        r"(<meta[^>]*>)",
        r"(&lt;script|&gt;)",
        r"(%3Cscript|%3E)",
    ]

    # 命令注入模式
    COMMAND_INJECTION_PATTERNS = [
        r"(;.*\bcat\b)",
        r"(;.*\bls\b)",
        r"(;.*\bchmod\b)",
        r"(;.*\bwget\b)",
        r"(;.*\bcurl\b)",
        r"(;.*\bnc\b)",
        r"(;.*\bnetcat\b)",
        r"(;.*\bbash\b)",
        r"(;.*\bsh\b)",
        r"(;.*\bpython\b)",
        r"(\|\s*\w+)",
        r"(&\s*\w+)",
        r"(\`.*\`)",
        r"(\$\(.*\))",
        r"(>\s*\/)",
        r"(<\s*\/)",
    ]

    # 路径遍历模式
    PATH_TRAVERSAL_PATTERNS = [
        r"(\.\.\/)",
        r"(\.\.\\)",
        r"(%2e%2e%2f)",
        r"(%2e%2e\\)",
        r"(\.\.%2f)",
        r"(\.\.%5c)",
    ]

    # ========================================================
    # 第二层：非医疗场景模式
    # ========================================================

    OUT_OF_SCOPE_PATTERNS = {
        "weather": {
            "patterns": [
                r"\b天气\b", r"\b气温\b", r"\b下雨\b", r"\b下雪\b",
                r"\b刮风\b", r"\b晴天\b", r"\b阴天\b", r"\b多云\b",
                r"\b温度\b.*\b几度\b", r"\b气温\b.*\b多少\b",
                r"\bweather\b", r"\bforecast\b", r"\b温度\b"
            ],
            "response": "抱歉，我是医疗健康助手，无法查询天气信息。请问有什么健康问题需要咨询吗？"
        },
        "stock": {
            "patterns": [
                r"\b股票\b", r"\b基金\b", r"\b汇率\b", r"\b理财\b",
                r"\b投资\b", r"\b炒股\b", r"\b股市\b", r"\b涨停\b",
                r"\b跌停\b", r"\bK线\b", r"\b牛市\b", r"\b熊市\b",
                r"\bstock\b", r"\bmarket\b", r"\b股价\b"
            ],
            "response": "抱歉，我不提供财经资讯服务。如有健康或医疗问题，我很乐意为您解答。"
        },
        "news": {
            "patterns": [
                r"\b新闻\b", r"\b热点\b", r"\b时事\b", r"\b资讯\b",
                r"\b头条\b", r"\b报道\b", r"\b消息\b.*\b今天\b",
                r"\b今天\b.*\b发生了\b", r"\b最近\b.*\b新闻\b",
                r"\bnews\b", r"\bbreaking\b"
            ],
            "response": "抱歉，我不是新闻资讯助手。我可以帮您解答医疗健康相关的问题。"
        },
        "entertainment": {
            "patterns": [
                r"\b电影\b", r"\b电视剧\b", r"\b综艺\b", r"\b明星\b",
                r"\b演员\b", r"\b歌手\b", r"\b娱乐圈\b", r"\b影视\b",
                r"\b游戏\b", r"\b动漫\b", r"\b小说\b", r"\b漫画\b",
                r"\b追剧\b", r"\b番剧\b", r"\bmovie\b", r"\bgames\b"
            ],
            "response": "抱歉，我对娱乐信息不太了解。如果您有健康问题，我可以为您提供专业建议。"
        },
        "technology": {
            "patterns": [
                r"\b电脑\b.*\b问题\b", r"\b手机\b.*\b问题\b", r"\b软件\b.*\b安装\b",
                r"\b网络\b.*\b连接\b", r"\b编程\b", r"\b代码\b", r"\b开发\b",
                r"\b算法\b", r"\b数据库\b", r"\b服务器\b", r"\b修电脑\b",
                r"\b修手机\b", r"\bapp\b.*\b问题\b", r"\b程序\b"
            ],
            "response": "抱歉，我无法提供技术支持。如果您有医疗健康方面的问题，我很乐意帮助您。"
        },
        "life_service": {
            "patterns": [
                r"\b快递\b", r"\b外卖\b", r"\b打车\b", r"\b订餐\b",
                r"\b购物\b", r"\b优惠\b", r"\b团购\b", r"\b优惠券\b",
                r"\b配送\b", r"\b取件\b", r"\b寄件\b", r"\bdelivery\b"
            ],
            "response": "抱歉，我不提供生活服务。如有健康咨询需求，请随时告诉我。"
        },
        "general_knowledge": {
            "patterns": [
                r"\b为什么\b.*(?!医疗|健康|症状|疾病|身体|药|治疗)",
                r"\b什么是\b.*(?!医疗|健康|症状|疾病|身体|药|治疗)",
                r"\b怎么\b.*(?!做|治|吃|医|药|预防|保健)",
            ],
            "response": "抱歉，我专注于医疗健康领域。请问我能为您解答哪些健康问题？"
        }
    }

    # ========================================================
    # 第三层：敏感内容模式
    # ========================================================

    SENSITIVE_PATTERNS = {
        "political": {
            "patterns": [
                r"\b政治\b", r"\b政府\b", r"\b选举\b", r"\b示威\b",
                r"\b抗议\b", r"\b游行\b", r"\b政党\b", r"\b领导人\b",
                r"\b政治人物\b", r"\bpolicy\b", r"\bgovernment\b"
            ],
            "response": "抱歉，我不参与政治话题讨论。如有健康问题，我很乐意为您服务。"
        },
        "adult": {
            "patterns": [
                r"\b色情\b", r"\b淫秽\b", r"\b裸体\b", r"\b性\b.*\b服务\b",
                r"\b成人\b.*\b内容\b", r"\b黄色\b", r"\b情色\b",
                r"\bporn\b", r"\badult\b", r"\bxxx\b"
            ],
            "response": "抱歉，此类内容不符合服务规范。请咨询健康相关问题。"
        },
        "violence": {
            "patterns": [
                r"\b杀人\b", r"\b暴力\b", r"\b打架\b", r"\b伤害\b.*\b他人\b",
                r"\b攻击\b.*\b人\b", r"\b武器\b", r"\b炸弹\b", r"\b恐怖\b",
                r"\bviolence\b", r"\bkill\b", r"\battack\b"
            ],
            "response": "抱歉，此类内容不符合服务规范。如遇紧急情况，请拨打110或120。"
        },
        "illegal": {
            "patterns": [
                r"\b毒品\b", r"\b吸毒\b", r"\b走私\b", r"\b赌博\b",
                r"\b非法\b", r"\b违禁品\b", r"\b假药\b.*\b哪里买\b",
                r"\bdrugs\b", r"\bgambling\b", r"\billegal\b"
            ],
            "response": "抱歉，此类内容不符合服务规范。如有健康问题，请通过正规渠道咨询。"
        },
        "discriminatory": {
            "patterns": [
                r"\b歧视\b", r"\b种族\b", r"\b侮辱\b", r"\b谩骂\b",
                r"\b攻击\b.*\b群体\b", r"\bdiscrimination\b"
            ],
            "response": "抱歉，请保持文明交流。如有健康问题需要咨询，请直接描述。"
        }
    }

    # ========================================================
    # 初始化
    # ========================================================

    def __init__(self, strict_mode: bool = False):
        """
        初始化场景过滤器

        Args:
            strict_mode: 严格模式，严格模式下更敏感的检测
        """
        self.strict_mode = strict_mode

        # 编译正则表达式
        self._compile_patterns()

        logger.info("SceneFilter initialized with strict_mode=%s", strict_mode)

    def _compile_patterns(self):
        """编译正则表达式以提高性能"""
        # 编译恶意模式
        self._compiled_sql = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self._compiled_xss = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
        self._compiled_command = [re.compile(p, re.IGNORECASE) for p in self.COMMAND_INJECTION_PATTERNS]
        self._compiled_path = [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS]

        # 编译非医疗场景模式
        self._compiled_out_of_scope = {}
        for category, config in self.OUT_OF_SCOPE_PATTERNS.items():
            self._compiled_out_of_scope[category] = [
                re.compile(p, re.IGNORECASE) for p in config["patterns"]
            ]

        # 编译敏感内容模式
        self._compiled_sensitive = {}
        for category, config in self.SENSITIVE_PATTERNS.items():
            self._compiled_sensitive[category] = [
                re.compile(p, re.IGNORECASE) for p in config["patterns"]
            ]

    # ========================================================
    # 主过滤方法
    # ========================================================

    async def filter(self, user_input: str) -> FilterResult:
        """
        执行三层过滤

        Args:
            user_input: 用户输入文本

        Returns:
            FilterResult: 过滤结果
        """
        if not user_input or not user_input.strip():
            return FilterResult(
                passed=True,
                intent_category=None
            )

        # 规范化输入
        normalized_input = self._normalize_input(user_input)

        # 第一层：恶意检测
        malicious_result = self._check_malicious(normalized_input)
        if not malicious_result.passed:
            return malicious_result

        # 第二层：场景过滤
        scope_result = self._check_out_of_scope(normalized_input)
        if not scope_result.passed:
            return scope_result

        # 第三层：敏感内容过滤
        sensitive_result = self._check_sensitive_content(normalized_input)
        if not sensitive_result.passed:
            return sensitive_result

        # 通过所有过滤
        return FilterResult(
            passed=True,
            intent_category=None
        )

    def _normalize_input(self, text: str) -> str:
        """
        规范化输入文本

        Args:
            text: 原始文本

        Returns:
            str: 规范化后的文本
        """
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text)
        # 去除特殊字符（保留中文、英文、数字）
        # text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        return text.strip()

    # ========================================================
    # 第一层：恶意检测
    # ========================================================

    def _check_malicious(self, text: str) -> FilterResult:
        """
        检查恶意内容

        Args:
            text: 输入文本

        Returns:
            FilterResult: 检测结果
        """
        detected_patterns = []

        # 检查SQL注入
        for pattern in self._compiled_sql:
            if pattern.search(text):
                detected_patterns.append(f"SQL注入: {pattern.pattern}")

        # 检查XSS攻击
        for pattern in self._compiled_xss:
            if pattern.search(text):
                detected_patterns.append(f"XSS攻击: {pattern.pattern}")

        # 检查命令注入
        for pattern in self._compiled_command:
            if pattern.search(text):
                detected_patterns.append(f"命令注入: {pattern.pattern}")

        # 检查路径遍历
        for pattern in self._compiled_path:
            if pattern.search(text):
                detected_patterns.append(f"路径遍历: {pattern.pattern}")

        if detected_patterns:
            logger.warning(f"检测到恶意输入: {detected_patterns}")
            return FilterResult(
                passed=False,
                intent_category=FilterCategory.MALICIOUS_INTENT.value,
                rejection_reason="检测到恶意输入，可能存在安全风险",
                suggested_response="抱歉，您的输入包含不安全内容。请输入正常的健康咨询问题。",
                filter_level=1,
                detected_patterns=detected_patterns
            )

        return FilterResult(passed=True)

    # ========================================================
    # 第二层：场景过滤
    # ========================================================

    def _check_out_of_scope(self, text: str) -> FilterResult:
        """
        检查非医疗场景

        Args:
            text: 输入文本

        Returns:
            FilterResult: 检测结果
        """
        # 先检查是否包含医疗关键词（混合判断）
        medical_keywords = [
            "症状", "病", "疼", "痛", "治疗", "药", "医生", "医院",
            "健康", "身体", "不适", "难受", "检查", "诊断", "手术",
            "symptom", "doctor", "hospital", "medicine", "health"
        ]

        has_medical_keyword = any(kw in text.lower() for kw in medical_keywords)

        # 检查非医疗场景
        for category, patterns in self._compiled_out_of_scope.items():
            for pattern in patterns:
                if pattern.search(text):
                    # 如果同时包含医疗关键词，可能是医疗相关咨询，通过
                    if has_medical_keyword and category in ["general_knowledge"]:
                        continue

                    logger.info(f"检测到非医疗场景: {category}")
                    return FilterResult(
                        passed=False,
                        intent_category=FilterCategory.OUT_OF_SCOPE.value,
                        rejection_reason=f"检测到非医疗场景: {category}",
                        suggested_response=self.OUT_OF_SCOPE_PATTERNS[category]["response"],
                        filter_level=2,
                        detected_patterns=[f"场景: {category}"]
                    )

        return FilterResult(passed=True)

    # ========================================================
    # 第三层：敏感内容过滤
    # ========================================================

    def _check_sensitive_content(self, text: str) -> FilterResult:
        """
        检查敏感内容

        Args:
            text: 输入文本

        Returns:
            FilterResult: 检测结果
        """
        for category, patterns in self._compiled_sensitive.items():
            for pattern in patterns:
                if pattern.search(text):
                    logger.warning(f"检测到敏感内容: {category}")
                    return FilterResult(
                        passed=False,
                        intent_category=FilterCategory.SENSITIVE_CONTENT.value,
                        rejection_reason=f"检测到敏感内容: {category}",
                        suggested_response=self.SENSITIVE_PATTERNS[category]["response"],
                        filter_level=3,
                        detected_patterns=[f"敏感: {category}"]
                    )

        return FilterResult(passed=True)

    # ========================================================
    # 辅助方法
    # ========================================================

    def get_filter_stats(self, text: str) -> Dict[str, any]:
        """
        获取过滤统计信息（调试用）

        Args:
            text: 输入文本

        Returns:
            Dict: 统计信息
        """
        stats = {
            "input_length": len(text),
            "has_malicious": False,
            "out_of_scope_category": None,
            "sensitive_category": None,
            "normalized": self._normalize_input(text)
        }

        malicious_result = self._check_malicious(text)
        stats["has_malicious"] = not malicious_result.passed

        if malicious_result.passed:
            scope_result = self._check_out_of_scope(text)
            if not scope_result.passed:
                stats["out_of_scope_category"] = scope_result.detected_patterns[0] if scope_result.detected_patterns else None

            if scope_result.passed:
                sensitive_result = self._check_sensitive_content(text)
                if not sensitive_result.passed:
                    stats["sensitive_category"] = sensitive_result.detected_patterns[0] if sensitive_result.detected_patterns else None

        return stats

    def add_custom_pattern(
        self,
        category: str,
        patterns: List[str],
        response: str,
        filter_type: str = "out_of_scope"
    ):
        """
        添加自定义过滤模式

        Args:
            category: 分类名称
            patterns: 正则模式列表
            response: 拒绝响应
            filter_type: 过滤类型（out_of_scope或sensitive）
        """
        if filter_type == "out_of_scope":
            self.OUT_OF_SCOPE_PATTERNS[category] = {
                "patterns": patterns,
                "response": response
            }
            self._compiled_out_of_scope[category] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        elif filter_type == "sensitive":
            self.SENSITIVE_PATTERNS[category] = {
                "patterns": patterns,
                "response": response
            }
            self._compiled_sensitive[category] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        else:
            raise ValueError(f"不支持的过滤类型: {filter_type}")

        logger.info(f"添加自定义{filter_type}模式: {category}")


# ============================================================
# 紧急情况检测器
# ============================================================

class EmergencyDetector:
    """
    紧急情况检测器

    检测用户输入中的紧急医疗情况
    """

    # 紧急关键词和对应的级别
    EMERGENCY_KEYWORDS = {
        "critical": [  # E级：危急
            "意识丧失", "昏迷", "不省人事", "呼吸停止", "心跳停止",
            "大出血", "严重外伤", "中毒", "自杀", "想死",
            "unconscious", "not breathing", "severe bleeding"
        ],
        "urgent": [  # A级：紧急
            "胸痛", "呼吸困难", "喘不过气", "严重过敏", "过敏性休克",
            "高热惊厥", "抽搐", "癫痫发作", "脑卒中", "中风",
            "chest pain", "can't breathe", "severe allergic"
        ],
        "semi_urgent": [  # B级：较急
            "高烧", "高热", "剧烈头痛", "严重呕吐", "脱水",
            "高烧不退", "持续高烧"
        ]
    }

    def __init__(self):
        """初始化紧急检测器"""
        self._compile_patterns()

    def _compile_patterns(self):
        """编译正则表达式"""
        self._compiled_keywords = {}
        for level, keywords in self.EMERGENCY_KEYWORDS.items():
            self._compiled_keywords[level] = [
                re.compile(rf"\b{kw}\b", re.IGNORECASE) for kw in keywords
            ]

    def detect(self, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        检测紧急情况

        Args:
            text: 输入文本

        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (是否紧急, 紧急级别, 建议响应)
        """
        for level, patterns in self._compiled_keywords.items():
            for pattern in patterns:
                if pattern.search(text):
                    response = self._get_emergency_response(level)
                    return True, level, response

        return False, None, None

    def _get_emergency_response(self, level: str) -> str:
        """获取紧急响应"""
        if level == "critical":
            return """🚨 **检测到紧急情况**

根据您描述的症状，请立即执行以下步骤：

## 立即行动
1. **拨打120**：告知地址和患者情况
2. **检查呼吸**：看胸廓起伏，听呼吸音
3. **开始CPR**：如无呼吸，立即开始心肺复苏

## CPR操作要点
- 位置：两乳头连线中点
- 深度：5-6厘米
- 频率：100-120次/分钟
- 比例：30次按压:2次人工呼吸

⏱️ **持续进行直到急救人员到达**

> 正在为您定位最近的急救中心..."""

        elif level == "urgent":
            return """🚨 **紧急情况**

根据您描述的症状，建议：

## 立即行动
1. **立即急诊**：不要等待，马上前往最近的医院急诊科
2. **拨打120**：如无法自行前往，立即拨打急救电话
3. **保持冷静**：尽量保持患者平静，避免剧烈活动

## 注意事项
- 如有家属陪同，请协助照顾
- 携带既往病史和用药记录
- 如症状加重，立即呼叫急救

> 建议立即就医，不要拖延！"""

        else:  # semi_urgent
            return """⚠️ **需要就医**

根据您的症状，建议：

## 就医建议
1. **尽快就医**：建议今天内前往医院就诊
2. **选择科室**：可根据症状选择相应科室或急诊
3. **注意观察**：密切观察症状变化

## 临时处理
- 多休息，避免剧烈活动
- 记录症状变化
- 如症状加重，请立即急诊

> 建议及时就医，获得专业诊疗。"""


# ============================================================
# 导出
# ============================================================

__all__ = [
    "SceneFilter",
    "EmergencyDetector",
    "FilterResult",
    "FilterCategory"
]
