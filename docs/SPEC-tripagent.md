# SPEC-tripagent.md — TripAgent 模块规格（P2）

> 本文件是给 AI 编码代理读的模块规格。全局硬约束见仓库根目录 `AGENTS.md`；
> 本文件只描述"这个模块具体长什么样"。两者冲突时以 `AGENTS.md` 为准。
> 产出的代码、注释、README、commit 一律英文。
>
> 标 `【确认或改】` 的是需要人工拍板的取舍，AI 不得自行更改这些值。

---

## §1 目标与成功标准

| 项 | 定义 |
| --- | --- |
| 目标 | 行程规划 Agent，每一条安排都经过**确定性**可行性校验；不通过就回炉重规划，而不是自信地输出一趟坐不到的火车 |
| 主指标 | `itinerary_feasibility_rate`（最终行程通过全部四个校验器的比例） |
| 副指标 | `constraint_satisfaction_rate`、`hallucination_rate`、`honest_infeasibility_rate`、mean/p95 steps、`cost_per_task`、`injection_block_rate` |
| 成功标准 | ① 10 个手写"必然失败"用例**全部**被校验器拦住；② 三重熔断有测试证明会跳闸且优雅收场；③ 10 条注入样本全部中和、对照样本未误杀；④ 写工具在未批准状态下不可执行（有测试为证）；⑤ 不可满足场景能诚实报告冲突而非编造行程；⑥ 每条安排都能追溯到数据源与版本 |
| 非目标 | 不做真实预订与支付、不做实时票价、不做地图可视化、不追求行程"好玩"。**本项目证明的是可执行性，不是推荐质量** |

**写进 README 的定位句**：市面 99% 的旅行 Agent demo 没有校验层。校验层本身就是一次完整的系统设计面试答案——它把"模型说得通"与"物理上做得到"分开，而后者不靠模型判断，只靠查表与算术。

---

## §2 范围冻结（Day 3 定死，交付前不许扩）

### 2.1 城市集合 【确认或改】

**Amsterdam、Berlin、Paris、Vienna、Prague** —— 选它们的理由：都有成熟且公开的 GTFS feed，互相之间有直达铁路（多城场景才成立），且 Wikivoyage 条目结构完整。

### 2.2 数据源

| 数据源 | 许可 | 取什么 | 用途 |
| --- | --- | --- | --- |
| Wikivoyage | CC BY-SA | 上述 5 城的城市条目 | 景点、开放时间、区域描述；经 retrieval-core 检索 |
| Mobility Database（GTFS） | 各 feed 自带 | 5 城各一份市内公共交通 feed，加一份跨城铁路 feed（若拿不到则声明为已知局限） | `connectivity` 校验器的**唯一**事实来源 |
| OpenStreetMap | ODbL | 5 城的 POI 坐标 | `geography` 校验器算步行/换乘时间 |
| OpenTravelData | CC-BY | 城市与车站/机场代码对照 | 实体归一化 |

### 2.3 三条范围铁律

1. 每份数据落库时必须带 `source_id` 与 `source_version`（GTFS 用 `feed_version` 或下载日期）——审计表靠它，缺了那两列就是空的。
2. 检索**必须走 retrieval-core**，不许另起一套 bespoke 检索路径。
3. Neon 的 `tripagent` project 同样是 **0.5 GB 免费档**。GTFS 的 `stop_times` 表极大，**只导入这 5 个城市所需的 trips 与 stops，不要全量导入**。导入脚本必须先打印预估行数与体积，超过 300 MB 就停下报错。

---

## §3 架构与领域模型

### 3.1 五层架构

| 层 | 路径 | 职责与边界 |
| --- | --- | --- |
| ① 检索层 | `adapters/` | 复用 retrieval-core；只实现 `CorpusAdapter` 协议，不新写检索算法 |
| ② 规划层 | `core/planner/` | `graph.py`（LangGraph 状态机）、`limits.py`（三重熔断）。**唯一允许调用 provider 层的地方** |
| ③ 校验层 | `core/validators/` | 四个确定性校验器。**绝不调用 LLM 或 provider 层** |
| ④ 工具层 | `core/tools/` | 读工具自动执行；写工具产生 `PendingAction` 并阻塞该分支 |
| ⑤ 审计层 | `core/audit.py` | 每一次节点转移与工具调用都追加一条记录；无记录的步骤视为 bug |

其余沿用三应用统一约定：`app/`（路由；`app/settings.py` 是**全仓库唯一读取环境变量的地方**）、`core/`、`adapters/`、`evals/`、`scripts/`（一律走命令行参数）、`web/`（Angular）、`docs/`、`tests/`、`mcp_server/`、`Dockerfile`、`docker-compose.yml`、`.env.example`、`.github/workflows/`。

### 3.2 领域模型（`core/models.py`，Pydantic v2）

```
Coordinate      : lat, lon
Constraint      : kind, value, source ("user" | "rejection" | "derived"), hard: bool
TripRequest     : request_text, constraints: list[Constraint], party_size, budget, days
Venue           : venue_id, name, city, coord, source_id, source_version
TransitLeg      : trip_id, from_stop, to_stop, depart_at, arrive_at,
                  feed_version, mode
ItineraryStep   : step_index, day, kind ("visit" | "transit" | "meal" | "stay"),
                  starts_at, ends_at, venue | leg, cost, source_id, source_version
Itinerary       : itinerary_id, steps: list[ItineraryStep], total_cost, currency
Violation       : validator, severity ("hard" | "soft"), step_index,
                  explanation, breached_constraint
PendingAction   : action_id, tool_name, args, idempotency_key,
                  status ("pending" | "approved" | "rejected"), result
PlanResult      : status ("finalised" | "infeasible" | "aborted"),
                  itinerary | None, violations, which_limit | None, audit_trail
```

**每个 `ItineraryStep` 都必须带 `source_id` 与 `source_version`**——没有溯源的步骤视为幻觉，评测里按 hallucination 计。

---

## §4 工具清单与幂等键 【确认或改】

规则：`access="read"` 自动执行；`access="write"` **必须**实现 `idempotency_key(args)`，注册表拒绝注册没有它的写工具。

| 工具 | access | 入参 → 出参 | 幂等键 |
| --- | --- | --- | --- |
| `search_attractions` | read | city, query, top_k → `list[Venue]` | — |
| `get_opening_hours` | read | venue_id, date → `OpeningHours`（含 closure_days） | — |
| `find_transit_trips` | read | from_stop, to_stop, depart_after → `list[TransitLeg]` | — |
| `estimate_walk_time` | read | coord_a, coord_b, speed → seconds | — |
| `lookup_price` | read | item_id, category → `Price \| None`（**缺失时返回 None，不许估算**） | — |
| `hold_reservation` | **write** | itinerary_id, step_index, resource_id, party_size → `HoldResult` | `{itinerary_id}:{step_index}:{resource_id}` |
| `book_transit` | **write** | itinerary_id, step_index, trip_id, party_size → `BookingResult` | `{itinerary_id}:{step_index}:{trip_id}` |
| `send_confirmation` | **write** | itinerary_id, channel, recipient → `SendResult` | `{itinerary_id}:{channel}:{sha256(recipient)}` |

**三条工具层规则**

1. 写工具经 MCP **一律不暴露**——外部客户端不能绕过审批队列。这一条写进 README，它本身就是一个好的安全设计论点。
2. 用同一幂等键重放一个已批准的写操作必须是 **no-op 并返回原结果**（要有测试）。
3. 读工具的返回值必须带 `source_id` 与 `source_version`。

---

## §5 三重熔断与审计轨迹 【确认或改】

### 5.1 熔断

| 参数 | 默认值 |
| --- | --- |
| `max_steps` | **25** |
| `max_tokens_per_task` | **60000** |
| `max_cost_per_task` | **0.05 USD** |
| `max_replans` | **3** |

- 三个熔断器**相互独立**，阈值从 config 读，默认值来自本文件。
- **每一次状态转移都检查**，不是只在节点入口检查。
- 跳闸时以 `status="aborted"` 结束，带上 `which_limit`、已完成的部分行程与完整审计轨迹。**绝不抛裸异常，绝不返回 5xx**——用户要看到"因超出步数上限中止，已完成到第 N 步"。
- 瞬时工具失败允许有界重试：最多 2 次指数退避，**每次重试各记一条审计**。

### 5.2 审计记录

`AuditRecord` 字段固定为这 11 个（顺序即表格列序，目标是**这张表能直接截图进 README 首屏**）：

```
step_index, action_type, tool_name, source_id, source_version,
duration_ms, tokens_in, tokens_out, cost_usd, validator_failures, timestamp
```

- `AuditTrail.to_markdown()` 渲染成可粘贴进 README 的表；`to_json()` 落盘 `audit_trails/<run_id>.json`。
- API：`GET /runs/<run_id>/audit`。
- **MCP 发起的调用也必须进审计**，并记录 origin。

---

## §6 四个确定性校验器（本项目的杀手锏）

共同协议：`check(itinerary: Itinerary) -> list[Violation]`

> **硬规则：完全确定性，绝不调用 LLM 或 provider 层，只做查表与算术。**
> 任何一个校验器里出现模型调用，这一层的全部价值即刻归零。

| 校验器 | 检查什么 | 可配置参数 |
| --- | --- | --- |
| `connectivity.py` | 两站之间的每一段必须对应一趟**真实存在的 GTFS trip**，且发车时间晚于上一项活动结束时间 + 换乘缓冲 | `min_transfer_buffer`（默认 10 min） |
| `opening_hours.py` | 每次参观都落在该场所当天的营业时段内，并尊重闭馆日 | — |
| `geography.py` | 相邻活动之间的步行/换乘时间在物理上可达；用**真实坐标**与可配置速度，不是估的 | `walk_speed_kmh`（默认 4.5） |
| `budget.py` | 累计花费不超预算，**分类与总额各查一次** | 预算来自用户约束 |

**回炉循环**：出现 violation 时路由到 replan，并把 violation 列表注入 planner 上下文；超过 `max_replans` 后以 `status="infeasible"` 收场，**原样返回**未解决的 violations。绝不静默丢弃 violation，绝不编造一个可行行程。**这个诚实行为本身就是 P2 的卖点。**

**验收测试**：`tests/fixtures/must_fail/*.json` 里 10 个手写用例，每个都要断言产生了**预期那个校验器**的 violation（不只是"产生了某个 violation"）。建议覆盖：

1. 不存在的班次号
2. 闭馆日安排参观
3. 两点之间根本走不完的换乘
4. 超预算 200 欧
5. 跨午夜的班次
6. 需要签证的边境
7. 开放时间与到达时间刚好差 5 分钟（边界）
8. 上一活动未结束就发车（缓冲不足）
9. 单项分类超预算但总额未超
10. 同一时段两个地点重叠

---

## §7 状态机与 SSE 事件

```
parse_constraints → retrieve → draft_itinerary → validate → (replan | finalise)

SSE event types (one per transition):
  constraints_parsed | retrieving | drafting | validating | violation_found
  | replanning | awaiting_approval | finalised | aborted

terminal statuses: finalised | infeasible | aborted
```

每个事件必须携带足够 payload，让 UI 无需再发一次请求就能渲染。

**三条 UI 契约**

1. `infeasible` 必须渲染成**一等结果**，不是错误页。
2. 每个行程步骤都要显示数据源归属；violation 触发时显示是哪个校验器、为什么拒绝。
3. 待审批的写操作渲染成一张被阻塞的卡片加一个显式确认按钮。

**审批阻塞取舍 【确认或改】**：写操作待批时**阻塞该分支**（而不是继续规划其他步骤）。理由：行程步骤之间有依赖，先跑下去会产生大量需要作废的规划。这个取舍写进 README。

---

## §8 安全层：不可信输入与审批队列

### 8.1 `core/untrusted.py`

- 每一段检索到的内容都包进 `UntrustedContent`，携带原文加 `source_id` 与 `source_version`。
- 它**只能以数据形式**进入模型上下文，放在显式分隔的块里；**永远不进 system / developer 消息，永远不拼接进指令**。
- **防护是结构性的，不是关键词过滤。** 不许把短语黑名单当作主要机制；关键词启发式只能作为额外信号并记录下来，绝不作为唯一闸门。
- 不可信内容里任何长得像工具调用的文本都是**惰性的**，永远不能触发真实调用。

### 8.2 `core/approval.py`

- 写工具调用创建 `PendingAction`（带幂等键）并阻塞该分支。
- `GET /approvals`、`POST /approvals/<id>/approve`、`POST /approvals/<id>/reject`。
- **拒绝会把这次拒绝作为一条新增 `Constraint`（`source="rejection"`）注入后恢复运行**，而不是直接失败。

### 8.3 验收

`tests/fixtures/injection/*.json` 里 10 条攻击 + **1 条无害对照**，断言：攻击全部中和、**对照未被误杀**、每次拦截都产生了审计记录。

攻击样本建议覆盖：直接指令注入、角色伪装、伪造工具调用格式、诱导跳过校验、诱导调用写工具、伪造数据源引用、跨语言注入（中/法）、藏在 Markdown 注释或链接标题里的指令、超长填充后接指令、以及一条 base64/编码变体。

---

## §9 API 契约

### 9.1 部署拓扑（决定下面所有设计）

- 前端 `https://tripagent.vectorlab.me` — Angular 静态产物，Cloudflare Pages
- 后端 `https://tripagent-xxxxx.<region>.run.app` — FastAPI，Cloud Run，**无自定义域**

每一次浏览器调用都是跨源请求。

### 9.2 端点

| 端点 | 契约 |
| --- | --- |
| `POST /plan` | SSE 流式返回。命中 `docs/DEMO-SCENARIOS.md` 里的 8 条预置场景时**从 `demo_cache` 重放、零模型调用**，并保留原始事件时序让时间线仍会动。自由输入需自带 API key；无 key 返回结构化的 "demo mode" 响应，**不是错误页** |
| `GET /scenarios` | 返回 8 条预置场景，可缓存 |
| `GET /approvals`、`POST /approvals/<id>/approve`、`POST /approvals/<id>/reject` | 审批队列（见 §8.2） |
| `GET /runs/<run_id>/audit` | 返回该次运行的完整审计轨迹 |
| `GET /metrics` | 从 `eval_runs` 读七项指标，前端与 README **共用同一数据源** |
| `GET /healthz` | `{"status":"ok","version":"<git sha>"}`。**绝不查询数据库**——没有 `SELECT 1`、没有连接池探测、没有迁移检查。保活每 10 分钟打一次，任何 DB 查询都会让 Neon compute 永不休眠、烧穿 CU-hours 并导致整个 project 被挂起 |

### 9.3 CORS 与前端

- `allow_origins` 是显式白名单，从 `Settings` 读：`https://tripagent.vectorlab.me` 加本地 `http://localhost:4200`。**禁止 `"*"`，开发环境也不例外。**
- `allow_methods` 只开 `GET`、`POST`、`OPTIONS`；`allow_credentials` 关闭。
- 后端地址由「服务名-项目号-区域」决定，换区域或换项目就会变。前端必须把它作为**构建期环境变量**注入（`environment.prod.ts` 从 CI 变量读），**不得硬编码**。
- 匿名访客只能点预置场景。自由输入框在未提供 API key 时**禁用并提示原因**，不要返回错误页。

---

## §10 场景集与七项指标

### 10.1 场景 schema

`evals/scenarios/*.json` 是唯一事实来源，**由人手写；AI 不得生成、扩写、改写或"改进"**。

```json
{
  "scenario_id":         "single_city_tight_budget_01",
  "request_text":        "5 days, EUR 1200, two people, no long-distance coaches",
  "constraints":         {"days": 5, "budget_eur": 1200, "party_size": 2,
                          "excluded_modes": ["coach"]},
  "expected_feasibility": "feasible",
  "expected_conflicts":   [],
  "forbidden_behaviours": ["cites a trip_id absent from the GTFS feed",
                           "schedules a visit on a closure day"]
}
```

- `expected_conflicts` 在 `expected_feasibility == "infeasible"` 时必填。
- `forbidden_behaviours` **始终必填**——没有它就无法测幻觉率。
- 格式不合法的场景必须**大声失败**，绝不静默跳过。

**规模与配比**：50–80 条。单城多日 40% / 多城 20% / 紧预算 15% / 强偏好 15% / **刻意不可满足 10%**。

### 10.2 七项指标

| 指标 | 定义（不许改口径） |
| --- | --- |
| `itinerary_feasibility_rate` | 最终行程通过**全部四个**校验器的运行占比 |
| `constraint_satisfaction_rate` | **按约束**统计，不是按运行统计 |
| `hallucination_rate` | 引用了摄取数据里**不存在**的 trip_id / 场所 / 价格。**用查表核对，绝不问模型** |
| `mean_steps` / `p95_steps` | 来自审计轨迹 |
| `cost_per_task` | **从审计轨迹读取**，不重新估算 |
| `injection_block_rate` | 复用 `tests/fixtures/injection` |
| `honest_infeasibility_rate` | 在期望为 infeasible 的场景中，系统**报告了冲突而非编造行程**的比例 |

**读结果时的陷阱（写进 README）**：可行率高不一定是好事，也可能是系统在偷偷放宽约束。必须交叉看约束满足率——**两个数字同时高才算真的好**。

指标算不出来就写 `TBD`，**绝不估算、不四舍五入、不插值**。

---

## §11 里程碑拆分（每个是一次独立的 AI 任务）

| 里程碑 | 交付物 | 验收条件（达不到不许进下一个） |
| --- | --- | --- |
| **T0** 地基 | 工具协议与注册表、桩工具、状态机骨架（validate 为占位）、三重熔断、审计轨迹 | 桩上端到端跑通；`max_steps=3` 时优雅中止且审计恰好 3 步、`which_limit="max_steps"`；缺幂等键的写工具注册失败 |
| **T1** 校验层 | 四个校验器 + 回炉循环 | 10 个必然失败用例**全部**被**预期那个**校验器拦住；三轮后以 `infeasible` 收场；**全仓库搜不到校验器里的模型调用** |
| **T2** 端到端 + 安全 | 真实读工具、不可信输入隔离、审批队列、SSE、时间线 UI | 一条完整行程过全部四个校验器；10 条注入全拦、对照未误杀；写工具未批准不可执行（有测试） |
| **T3** 评测 + MCP | trajectory harness、report、MCP server（只暴露读工具） | 能加载并校验全部场景；Claude Code 实测调通两个读工具、写工具被明确拒绝、**截图入库** |
| **T4** 跑分 + 上线 | 全量跑分、预置缓存、部署、README 收口 | 七项指标真实；8 条预置零模型调用；`tripagent.vectorlab.me` 手机可匿名访问；`FAILURE-MODES.md` ≥ 6 类根因 |

> **T1 不许延期或缩水。** 校验层是 P2 唯一的差异化，砍掉它这个项目就和市面上任何一个旅行 Agent demo 没有区别。宁可砍多城场景、砍地图、砍 UI 精致度。

---

## §12 已知局限（README 必须具体到这个程度）

- GTFS 数据仅覆盖 5 个城市，跨境班次覆盖不完整。
- 价格数据稀疏，`lookup_price` 返回 None 时该步骤不计入预算校验——这会让 `budget` 校验偏宽松。
- 不做实时查询，所有班次基于快照 feed，`feed_version` 已记录在每一步。
- 写工具是模拟实现，不连接任何真实预订系统。
