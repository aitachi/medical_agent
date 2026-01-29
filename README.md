# 医疗智能助手 (Medical AI Assistant)

基于多Agent架构的医疗场景智能对话系统，包含完整的意图识别、实体抽取、槽位填充、Hooks机制、Skill调用和MCP工具整合。

## 作者信息

**作者:** Aitachi
**微信:** 18116011230
**邮箱:** 44158892@qq.com
**GitHub:** https://github.com/aitachi/medical_agent

## 项目结构

```
medical/
├── 医疗智能助手产品文档.md      # 完整产品设计文档
├── README.md                     # 本文件
├── config/
│   └── agent_config.yaml         # Agent配置文件
└── code/
    ├── agent_framework.py        # Agent框架核心实现
    └── mcp_server_example.py     # MCP Server实现示例
```

## 核心功能

### 1. Agent 处理框架

完整的七步处理流程：

```
输入 → 预处理 → 意图识别 → 实体抽取 → 槽位填充 → 决策分发 → Skill执行 → 响应生成
```

### 2. 意图识别 (Intent Detection)

支持8种意图类型：
- `SYMPTOM_INQUIRY` - 症状咨询
- `DEPARTMENT_QUERY` - 科室查询
- `MEDICATION_CONSULT` - 用药咨询
- `APPOINTMENT_BOOK` - 挂号预约
- `REPORT_INTERPRET` - 报告解读
- `HEALTH_EDU` - 健康教育
- `CHITCHAT` - 闲聊
- `UNKNOWN` - 未知意图

### 3. 实体抽取 (Entity Extraction)

支持7种医学实体类型：
- `BODY_PART` - 身体部位
- `SYMPTOM` - 症状描述
- `DISEASE` - 疾病名称
- `MEDICINE` - 药物名称
- `TIME_DURATION` - 时间时长
- `SEVERITY` - 严重程度
- `VITAL_SIGN` - 生命体征

### 4. 槽位填充 (Slot Filling)

- 必填/可选槽位定义
- 多轮对话收集
- 自动追问生成
- 槽位冲突处理

### 5. Hooks 机制

20+个Hook点，支持全流程自定义：

| 阶段 | Hook名称 | 说明 |
|------|----------|------|
| 预处理 | `before_preprocess` | 输入预处理前 |
| 意图识别 | `before_intent` / `after_intent` | 意图识别前后 |
| 意图识别 | `intent_fallback` | 意图置信度不足时 |
| 实体抽取 | `before_extract` / `after_extract` | 实体抽取前后 |
| 实体抽取 | `entity_normalize` | 实体标准化 |
| 槽位填充 | `before_fill` / `after_fill` | 槽位填充前后 |
| 槽位填充 | `slot_required` | 需要必填槽位时 |
| 槽位填充 | `slot_conflict` | 槽位冲突时 |
| 决策分发 | `before_dispatch` / `after_dispatch` | 分发前后 |
| 决策分发 | `skill_select` | 选择Skill时 |
| Skill执行 | `before_execute` / `after_execute` | Skill执行前后 |
| Skill执行 | `on_error` | Skill执行出错时 |
| 响应生成 | `before_response` / `after_response` | 响应生成前后 |
| 响应生成 | `format_response` | 响应格式化 |

### 6. Skill 调用

内置Skill：
- `symptom_analyzer` - 症状分析
- `department_recommender` - 科室推荐
- `medication_advisor` - 用药咨询
- `appointment_service` - 挂号服务
- `report_interpreter` - 报告解读
- `health_qa` - 健康问答

### 7. MCP 工具整合

三个MCP Server：
- `medical_knowledge` - 医学知识库
- `hospital_system` - 医院信息系统
- `drug_database` - 药品数据库

## 快速开始

### 1. 安装依赖

```bash
pip install asyncio dataclasses pyyaml
```

### 2. 运行Agent框架

```bash
cd code
python agent_framework.py
```

### 3. 运行MCP Server

```bash
cd code
python mcp_server_example.py
```

## 使用示例

```python
import asyncio
from agent_framework import MedicalAgent, DialogueContext

async def main():
    # 创建Agent
    agent = MedicalAgent(config)
    await agent.initialize()

    # 创建上下文
    context = DialogueContext(
        session_id="session_001",
        user_id="user_001"
    )

    # 处理用户输入
    response = await agent.process("我头疼三天了", context)
    print(response)

asyncio.run(main())
```

## 配置说明

配置文件位于 `config/agent_config.yaml`，主要配置项：

```yaml
# Agent基础配置
agent:
  intent:
    threshold: 0.75        # 意图识别置信度阈值
  entity:
    threshold: 0.70        # 实体抽取置信度阈值
  slot:
    max_turns: 5           # 最大追问轮数

# MCP服务器配置
mcp_servers:
  medical_knowledge:
    enabled: true
    endpoint: "http://localhost:3001"
  hospital_system:
    enabled: true
    endpoint: "http://localhost:3002"
```

## 扩展开发

### 添加新意图

在 `agent_config.yaml` 中添加：

```yaml
intents:
  NEW_INTENT:
    description: "新意图描述"
    priority: 7
    confidence_threshold: 0.75
    skill: "new_skill"
```

### 添加新Skill

```python
class NewSkill(Skill):
    def __init__(self, mcp_manager, hook_manager):
        super().__init__(
            name="new_skill",
            description="新技能描述",
            mcp_manager=mcp_manager,
            hook_manager=hook_manager
        )

    async def execute(self, parameters, context):
        # 实现逻辑
        return SkillResult(success=True, response="结果")

# 注册
agent.skill_registry.register(
    NewSkill(agent.mcp_manager, agent.hook_manager),
    [IntentType.NEW_INTENT]
)
```

### 添加新Hook

```python
@hook("before_execute")
async def my_hook(skill_name, params, context):
    # Hook逻辑
    print(f"Executing {skill_name}")
    return params
```

## 安全与合规

- 所有医疗建议附带免责声明
- 紧急情况自动识别并引导就医
- 用户数据加密存储
- 对话历史定期清理

## 免责声明

本项目仅用于技术演示和学习目的。实际医疗应用需要：

1. 遵守当地医疗法规
2. 通过相关医疗认证
3. 使用经过验证的医学知识库
4. 配备专业医疗人员审核

## License

MIT License
