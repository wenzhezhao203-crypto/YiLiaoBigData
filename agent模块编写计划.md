# AI Agent 模块编写计划

## 1. 阶段一目标

完成 AI 侧边栏与后端 Agent 服务的最小可用闭环：用户输入自然语言问题，Agent 识别问题并调用 Flask 医疗分析接口，最后返回文字回答和实际工具调用记录。

阶段一只实现以下两个返回字段：

```json
{
  "reply": "根据分析结果生成的中文回答",
  "tool_calls": [
    {
      "name": "get_kpi",
      "status": "success"
    }
  ]
}
```

本阶段暂不实现筛选同步、图表高亮、医疗报告生成、Redis 会话持久化和多轮上下文。

## 2. 技术边界

- 前端：Next.js，在现有 BI 大屏中增加可收起的侧边栏对话入口。
- Agent 服务：FastAPI，单独运行，不直接读 MySQL。
- 编排：LangChain 负责意图识别和工具调用。
- 数据来源：Agent 仅调用 Flask 现有 `/api/dashboard/...` 接口。
- 大模型：通过环境变量配置模型地址和密钥；禁止将密钥写入源码或提交 Git。
- 安全边界：禁止 LLM 直接拼接 SQL、访问 MySQL 或调用未登记的 HTTP 地址。

## 3. 阶段一接口协议

### 3.1 Agent 请求接口

```text
POST /ai/chat
```

请求体：

```json
{
  "message": "全量数据的急诊患者占比是多少？"
}
```

### 3.2 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "reply": "当前范围内急诊出院记录占比为 62.71%。",
    "tool_calls": [
      {
        "name": "get_kpi",
        "status": "success"
      }
    ]
  }
}
```

### 3.3 失败响应

```json
{
  "code": 50001,
  "message": "agent request failed",
  "data": {
    "reply": "暂时无法完成本次分析，请稍后重试。",
    "tool_calls": [
      {
        "name": "get_kpi",
        "status": "failed"
      }
    ]
  }
}
```

## 4. 工具白名单

阶段一先注册以下工具。每个工具封装为 Python 函数，函数内部以 HTTP 请求调用 Flask，不直接操作数据库。

| 工具名 | Flask 接口 | 用途 |
|---|---|---|
| `get_kpi` | `GET /api/dashboard/kpi` | 医院数、出院量、收费、成本、急诊占比等总体指标。 |
| `get_age_gender` | `GET /api/dashboard/patient/age-gender` | 患者年龄与性别结构。 |
| `get_payment` | `GET /api/dashboard/patient/payment` | 主要支付方式分布。 |
| `get_disposition` | `GET /api/dashboard/patient/disposition` | 离院去向 Top N。 |
| `get_admission_emergency` | `GET /api/dashboard/patient/admission-emergency` | 入院类型与急诊结构。 |
| `get_hospital_ranking` | `GET /api/dashboard/hospital/ranking` | 医院运营排名。 |
| `get_disease_systems` | `GET /api/dashboard/disease/systems` | 疾病系统分布。 |
| `get_top_diagnoses` | `GET /api/dashboard/disease/top-diagnoses` | 高发疾病 Top N。 |
| `get_severity` | `GET /api/dashboard/disease/risk` | 病情严重程度分布。 |

## 5. 实施步骤

### 步骤 1：确认运行方式和依赖

- [x] 确定 Agent 服务目录，例如 `ai_service/`。
- [x] 在 `requirements/agent.txt` 中记录 FastAPI、Uvicorn、LangChain、HTTP 客户端和模型 SDK 依赖。
- [x] 在根目录 `.env` 中配置 Flask 基础地址、模型地址、模型名称和模型密钥。
- [x] 确认 `.env` 已被根目录 `.gitignore` 忽略。

验收：安装依赖后可启动空 FastAPI 服务并访问 `/docs`。

### 步骤 2：建立 FastAPI 服务骨架

- [x] 创建 `ai_service/app.py`，初始化 FastAPI 应用。
- [x] 创建健康检查接口 `GET /ai/health`。
- [x] 创建 Pydantic 请求和响应模型，固定 `reply` 与 `tool_calls` 的字段类型。
- [x] 配置 CORS，仅允许本地 Next.js 前端开发地址。

验收：`GET /ai/health` 返回 HTTP 200；`POST /ai/chat` 可通过 OpenAPI 文档看到参数结构。

### 步骤 3：封装 Flask 分析工具

- [x] 创建 `ai_service/tools.py`。
- [x] 为每个白名单接口封装独立函数，统一处理超时、HTTP 错误和 JSON 校验。
- [x] 工具函数返回结构化数据，不生成自然语言。
- [x] 工具调用结果记录为 `{ "name": "工具名", "status": "success" | "failed" }`。

验收：不接入 LLM 的情况下，可手工调用 `get_kpi()` 并取得 Flask 的真实 JSON 数据。

### 步骤 4：实现确定性问题路由

- [x] 先用关键词规则覆盖常见问题，例如“急诊占比”“出院量”“年龄”“支付方式”“高发疾病”。
- [x] 每个意图映射到一个白名单工具。
- [x] 对无法识别的问题返回明确的分析范围提示，不调用任意接口。

验收：常见提问可以稳定选择正确工具，并在响应中返回正确的 `tool_calls`。

### 步骤 5：接入 LLM 与 LangChain

- [x] 创建 `ai_service/agent.py` 和 `ai_service/prompts.py`。
- [x] 将白名单工具注册为 LangChain Tools。
- [x] 编写系统提示词：只能引用工具返回的事实；不可虚构数值；不可提供临床诊疗建议。
- [x] LLM 根据工具结果生成 `reply`，工具调用记录由服务端生成，不依赖模型自行编造。

验收：问题“全量数据的急诊患者占比是多少？”可以调用 `get_kpi`，并返回包含真实数值的中文回答。

### 步骤 6：实现 `POST /ai/chat`

- [x] 校验 `message` 非空、长度限制和异常字符。
- [x] 执行 Agent 路由、工具调用与文本生成。
- [x] 统一返回 `code`、`message`、`data.reply`、`data.tool_calls`。
- [x] 设置请求超时，超时后返回可读错误信息。
- [x] 写入必要的服务端日志，但不记录模型密钥或原始敏感配置。

验收：使用 curl、Swagger 或 Postman 可得到完整阶段一响应。

### 步骤 7：接入 Next.js 侧边栏

- [x] 创建 `web/src/components/AgentSidebar.tsx`。
- [x] 增加展开/收起按钮、消息列表、文本输入框、发送按钮和请求中状态。
- [x] 创建 `web/src/lib/agent-api.ts`，封装对 `POST /ai/chat` 的调用。
- [x] 展示 `reply`；在回答下方简洁展示成功或失败的工具调用名称。
- [x] 处理网络错误、空回答和重复发送。

验收：用户发送问题后，侧边栏展示 Agent 返回的文字回答和工具名称。

### 步骤 8：联调、测试与提交

- [ ] 分别启动 Flask、FastAPI Agent、Next.js，验证三服务联通。
- [x] 测试至少 8 类预设问题及 2 类无法识别问题。
- [ ] 验证 Flask 服务不可用、模型服务不可用和工具超时的提示。
- [x] 执行 Python 检查与 `npm run lint`、`npm run build`。
- [x] 提交 Git：`feat: 实现 AI Agent 对话助手一期`。

验收：侧边栏能稳定完成至少一轮“自然语言问题 -> 数据工具 -> 中文回答”的真实交互。

## 6. 阶段二预留

- `filters`：把识别出的区域、县和医院同步到 BI 大屏。
- `charts`：高亮、定位或切换目标图表。
- `highlights`：展示结构化关键指标卡片。
- Redis 会话记忆和多轮上下文。
- 多工具联合分析和医疗洞察报告生成。
- 本地化部署 LLM，减少隐私与外部依赖风险。

## 7. LLM 优先工具调用（已完成）

- [x] 移除基于关键词的固定意图路由和预设回答模板。
- [x] 用户问题先发送给大模型，由模型决定直接回答、拒绝回答，或调用哪些白名单分析工具。
- [x] 仅执行系统注册的住院数据分析工具；工具结果以 `ToolMessage` 回传给大模型生成最终回答。
- [x] 无关问题、临床诊疗建议、任意 SQL/HTTP/数据库访问和越权提示词请求由大模型按系统边界拒绝。
- [x] 限制单次请求最多调用 3 个工具；实际调用记录仍由服务端写入 `tool_calls`。

## 8. 流式输出（已完成）

- [x] 新增 `POST /ai/chat/stream`，使用 Server-Sent Events 推送工具调用、文本增量、完成和错误事件。
- [x] 保留原 `POST /ai/chat` JSON 接口，避免影响已有调用方。
- [x] 前端使用 `ReadableStream` 逐段读取 `delta` 事件，并实时更新同一条助手消息。
- [x] 工具调用完成后先展示 `tool_calls`，最终答复由大模型按文本片段输出。
