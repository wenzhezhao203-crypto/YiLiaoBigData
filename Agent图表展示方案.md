# AI Agent 图表展示方案

## 1. 页面职责

- `BI 大屏`：展示固定的整体运营、患者、医院、疾病和 Top 10 汇总视图，适合快速浏览。
- `AI 分析助手`：处理自然语言问题，返回文字洞察、实际工具调用记录和与问题对应的一张或多张动态图表。

AI 页面采用左侧会话、右侧图表工作区的布局。每次对话完成后，右侧替换或追加当前问题的图表；文字回答与图表使用同一份工具结果，保证数值一致。

## 2. 生成原则

不能让大模型直接生成 JavaScript 或任意 ECharts 配置。推荐链路：

```text
用户问题
-> LLM 判断意图并选择白名单工具与图表类型
-> Flask 返回真实聚合数据
-> Agent 服务的图表构建器按模板生成 ECharts option
-> 返回 reply、tool_calls、charts
-> 前端将 option 交给 EChart 组件渲染
```

LLM 只允许选择受控的 `chart_kind`，不拥有 SQL、HTTP 地址、图表脚本或任意配置的写入权限。

## 3. 图表白名单

| chart_kind | 对应工具 | 图表类型 | 数据字段 |
|---|---|---|---|
| `payment_donut` | `get_payment` | 环形图 | 支付方式、出院人次、占比 |
| `age_gender_bar` | `get_age_gender` | 年龄组-性别堆叠柱状图 | 年龄组、性别、出院人次 |
| `admission_emergency_bar` | `get_admission_emergency` | 入院类型堆叠柱状图 | 入院类型、急诊标记、出院人次 |
| `hospital_ranking_bar` | `get_hospital_ranking` | 横向排名条形图 | 医院、出院量或指定运营指标 |
| `disease_system_bar` | `get_disease_systems` | 疾病系统横向条形图 | MDC 描述、出院人次 |
| `top_diagnoses_bar` | `get_top_diagnoses` | 高发疾病 Top N 横向条形图 | CCSR 描述、出院人次 |
| `severity_bar` | `get_severity` | 病情严重程度柱状图 | 严重程度、出院人次 |
| `kpi_emergency_compare` | `get_kpi` | 急诊/非急诊收费成本分组柱状图 | 收费、成本、急诊状态 |

一期每个问题最多返回两张图，避免会话页面出现重复或难以比较的可视化。

## 4. Agent 返回协议（二期）

在现有 `reply` 与 `tool_calls` 基础上增加 `charts`。其中 `option` 由服务端图表构建器生成，不由模型原样输出。

```json
{
  "reply": "Medicare 和 Medicaid 是主要支付来源，合计占比约 70%。",
  "tool_calls": [
    { "name": "get_payment", "status": "success" }
  ],
  "charts": [
    {
      "id": "payment-distribution",
      "title": "主要支付方式分布",
      "chart_kind": "payment_donut",
      "source_tool": "get_payment",
      "option": { "series": [] }
    }
  ]
}
```

## 5. 实施顺序

1. 扩展 Pydantic 响应模型，增加受控的 `ChartInstruction`。
2. 在 Agent 服务增加 `chart_builders.py`，为白名单图表编写确定性 ECharts 模板。
3. 在系统提示词中要求模型仅选择 `chart_kind`，且只在工具结果足以表达时选择图表。
4. 工具调用结束后，按模型选择和真实结果构建 `charts`，再与文字回答一同流式完成事件返回。
5. 前端将 Agent 工作区右侧占位区域替换为 `EChart` 列表，支持加载、无图表和错误状态。
6. 增加筛选同步：后续从问题中识别区域、县、医院并透传至 Flask 工具，图表与文字使用同一筛选范围。

## 6. 不应生成图表的情况

- 用户询问助手能力、模型信息或使用范围。
- 问题超出住院数据分析范围，或属于临床诊疗建议。
- 工具调用失败、无数据，或返回结果不足以构成可靠图表。
- 用户只要求简短的单一数值，且图表没有额外解释价值。
