# 页面跳转提示功能 - 实现方案

## 功能概述
在聊天结束后，根据识别的意图向用户展示"是否跳转到相关功能页面"的提示卡片。

---

## 功能映射表

| 意图 (Intent) | 功能名称 | 跳转页面 | 页面ID |
|--------------|---------|---------|--------|
| symptom_inquiry | 症状咨询 | 症状咨询页面 | `page-symptom` |
| department_query | 科室查询 | 科室推荐页面 | `page-department` |
| medication_consult | 用药咨询 | 用药咨询页面 | `page-medication` |
| appointment | 预约挂号 | 预约挂号页面 | `page-appointment` |
| health_education | 健康教育 | 健康教育页面 | `page-health` |
| report_interpret | 报告解读 | 报告解读页面 | `page-report` |
| my_appointment | 预约查询 | 预约查询页面 | `page-myappointment` |
| followup | 预约随访 | 随访管理页面 | `page-followup` |
| records | 治疗档案 | 治疗档案页面 | `page-records` |
| greeting | 问候 | 聊天页面 | `page-chat` |
| unknown | 未知 | 聊天页面 | `page-chat` |

---

## 后端修改

### 1. 修改 API 响应模型

**文件**: `web_api_server.py`

```python
# 修改 ChatResponse 模型，添加页面推荐字段
class ChatResponse(BaseModel):
    """聊天响应"""
    response: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    skill_invoked: Optional[str] = None
    timestamp: str
    suggested_page: Optional[Dict[str, str]] = None  # 新增
```

### 2. 添加意图到页面映射函数

```python
def get_suggested_page(intent: str, confidence: float) -> Optional[Dict[str, str]]:
    """
    根据意图和置信度返回推荐页面
    """
    # 置信度过低时不推荐跳转
    if confidence < 0.5:
        return None

    page_mapping = {
        "symptom_inquiry": {
            "page_id": "page-symptom",
            "page_name": "症状咨询",
            "page_icon": "🔍",
            "description": "使用专业的症状分析工具"
        },
        "department_query": {
            "page_id": "page-department",
            "page_name": "科室推荐",
            "page_icon": "🏥",
            "description": "智能匹配最合适的科室"
        },
        "medication_consult": {
            "page_id": "page-medication",
            "page_name": "用药咨询",
            "page_icon": "💊",
            "description": "查询药品信息和用药指导"
        },
        "appointment": {
            "page_id": "page-appointment",
            "page_name": "预约挂号",
            "page_icon": "📅",
            "description": "在线预约医生门诊"
        },
        "health_education": {
            "page_id": "page-health",
            "page_name": "健康教育",
            "page_icon": "📚",
            "description": "健康知识科普和预防建议"
        },
        "report_interpret": {
            "page_id": "page-report",
            "page_name": "报告解读",
            "page_icon": "📋",
            "description": "专业解读检查报告"
        },
        "my_appointment": {
            "page_id": "page-myappointment",
            "page_name": "我的预约",
            "page_icon": "📋",
            "description": "查看和管理预约记录"
        },
        "followup": {
            "page_id": "page-followup",
            "page_name": "随访管理",
            "page_icon": "📝",
            "description": "管理患者随访记录"
        },
        "records": {
            "page_id": "page-records",
            "page_name": "治疗档案",
            "page_icon": "📂",
            "description": "查看完整健康档案"
        }
    }

    return page_mapping.get(intent)
```

### 3. 修改聊天端点

```python
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求"""
    # ... 现有代码 ...

    # 获取推荐页面
    suggested_page = None
    if intent_result and intent_result.confidence >= 0.5:
        suggested_page = get_suggested_page(
            intent_result.intent.value,
            intent_result.confidence
        )

    return ChatResponse(
        response=response,
        intent=intent_result.intent.value if intent_result else None,
        confidence=intent_result.confidence if intent_result else None,
        skill_invoked=intent_result.target_skill if intent_result else None,
        timestamp=datetime.now().isoformat(),
        suggested_page=suggested_page  # 新增
    )
```

---

## 前端修改

### 1. 添加页面跳转提示卡片样式

**文件**: `frontend/index.html`

```css
/* 页面跳转提示卡片 */
.page-suggestion-card {
    margin: 15px 0;
    padding: 16px;
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border: 2px solid #0ea5e9;
    border-radius: 12px;
    animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(-10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.page-suggestion-header {
    display: flex;
    align-items: center;
    margin-bottom: 12px;
}

.page-suggestion-icon {
    font-size: 28px;
    margin-right: 10px;
}

.page-suggestion-title {
    font-weight: 600;
    color: #0369a1;
    font-size: 15px;
}

.page-suggestion-desc {
    color: #555;
    font-size: 13px;
    margin-bottom: 12px;
    line-height: 1.4;
}

.page-suggestion-actions {
    display: flex;
    gap: 10px;
}

.page-suggestion-btn {
    flex: 1;
    padding: 10px 16px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
}

.page-suggestion-btn.primary {
    background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
    color: white;
}

.page-suggestion-btn.primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);
}

.page-suggestion-btn.secondary {
    background: white;
    color: #555;
    border: 1px solid #ddd;
}

.page-suggestion-btn.secondary:hover {
    background: #f5f5f5;
}
```

### 2. 添加显示页面跳转提示的函数

```javascript
/**
 * 显示页面跳转提示卡片
 * @param {Object} pageInfo - 页面信息对象
 * @param {string} pageInfo.page_id - 页面ID
 * @param {string} pageInfo.page_name - 页面名称
 * @param {string} pageInfo.page_icon - 页面图标
 * @param {string} pageInfo.description - 页面描述
 */
function showPageSuggestion(pageInfo) {
    const messagesDiv = document.getElementById('chat-messages');

    const suggestionCard = document.createElement('div');
    suggestionCard.className = 'message assistant';
    suggestionCard.innerHTML = `
        <div class="page-suggestion-card">
            <div class="page-suggestion-header">
                <span class="page-suggestion-icon">${pageInfo.page_icon}</span>
                <span class="page-suggestion-title">为您推荐：${pageInfo.page_name}</span>
            </div>
            <div class="page-suggestion-desc">${pageInfo.description}</div>
            <div class="page-suggestion-actions">
                <button class="page-suggestion-btn primary" onclick="navigateToPage('${pageInfo.page_id}')">
                    ✨ 前往${pageInfo.page_name}
                </button>
                <button class="page-suggestion-btn secondary" onclick="dismissSuggestion(this)">
                    留在聊天
                </button>
            </div>
        </div>
    `;

    messagesDiv.appendChild(suggestionCard);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

/**
 * 跳转到指定页面
 * @param {string} pageId - 页面ID
 */
function navigateToPage(pageId) {
    // 隐藏所有页面
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });

    // 显示目标页面
    const targetPage = document.getElementById(pageId);
    if (targetPage) {
        targetPage.classList.add('active');

        // 更新菜单激活状态
        document.querySelectorAll('.menu-item').forEach(item => {
            item.classList.remove('active');
        });

        // 找到对应的菜单项并激活
        const menuItems = document.querySelectorAll('.menu-item');
        const pageMap = {
            'page-symptom': 0,
            'page-department': 1,
            'page-medication': 2,
            'page-appointment': 3,
            'page-health': 4
        };

        const menuIndex = pageMap[pageId];
        if (menuIndex !== undefined && menuItems[menuIndex]) {
            menuItems[menuIndex].classList.add('active');
        }
    }
}

/**
 * 关闭页面跳转提示
 * @param {HTMLElement} btn - 关闭按钮元素
 */
function dismissSuggestion(btn) {
    const card = btn.closest('.message');
    if (card) {
        card.style.opacity = '0';
        card.style.transform = 'translateY(-10px)';
        setTimeout(() => card.remove(), 300);
    }
}
```

### 3. 修改流式响应处理，检测 suggested_page

```javascript
// 在 streamRequestWithProcess 函数中
async function streamRequestWithProcess(message, sessionId, contentDiv, processDiv) {
    // ... 现有代码 ...

    let suggestedPage = null; // 新增：存储推荐页面信息

    for (const line of lines) {
        if (line.trim() && line.startsWith('data: ')) {
            try {
                const data = JSON.parse(line.slice(6));

                // ... 现有的事件处理 ...

                // 检测页面推荐（新增）
                else if (data.type === 'page_suggestion') {
                    suggestedPage = data.page_info;
                }

                // ... 其他事件处理 ...
            }
        }
    }

    // 在响应完成后显示页面跳转提示（新增）
    if (suggestedPage) {
        setTimeout(() => {
            showPageSuggestion(suggestedPage);
        }, 500);
    }
}
```

---

## 流式响应事件

在流式响应中添加新的事件类型：

**文件**: `web_api_server.py`

```python
# 在 generate() 函数中，响应完成后添加页面推荐事件
if state.llm_enabled and state.llm_service and LLM_AVAILABLE:
    async for event in state.llm_service.generate_response_stream(...):
        yield event
else:
    # 使用本地Agent
    response = await state.agent.process(...)
    yield {"type": "content", "content": response}
    yield {"type": "done", "content": ""}

    # 添加页面推荐事件（新增）
    suggested_page = get_suggested_page(
        intent_result.intent.value if intent_result else "",
        intent_result.confidence if intent_result else 0
    )
    if suggested_page:
        yield {
            "type": "page_suggestion",
            "page_info": suggested_page
        }
```

---

## 完整测试用例

| 场景 | 输入 | 预期意图 | 预期跳转页面 |
|------|------|---------|------------|
| 症状咨询 | "我头痛好几天了" | symptom_inquiry | 症状咨询页面 |
| 科室查询 | "头痛挂什么科" | department_query | 科室推荐页面 |
| 用药咨询 | "阿莫西林怎么吃" | medication_consult | 用药咨询页面 |
| 预约挂号 | "我想挂个号" | appointment | 预约挂号页面 |
| 健康教育 | "怎么预防高血压" | health_education | 健康教育页面 |
| 问候 | "你好" | greeting | 无跳转 |
| 低置信度 | "asdasd" | unknown (< 0.5) | 无跳转 |

---

## 实现顺序

1. ✅ 后端：修改 `web_api_server.py` 添加页面推荐逻辑
2. ✅ 前端：添加 CSS 样式
3. ✅ 前端：添加 JavaScript 函数
4. ✅ 前端：修改流式响应处理
5. ✅ 测试验证所有场景
6. ✅ 重启服务并部署
