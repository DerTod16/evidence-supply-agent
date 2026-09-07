# Evidence Sourcing Agent

> 证据优先的**电商货源选品 Agent**：为新手卖家输出带评分、带核验状态、带可回溯资料的货源候选，
> 而不是把语言模型的猜测伪装成选品结论。

本仓库由 [evidence-supply-agent](https://github.com/DerTod16/evidence-supply-agent)（MIT）改造而来：
领域从 B2B 供应商合规尽调转为**电商货源选品**（面向 1688 / 义乌购 / 拼多多批发与闲鱼等销售侧新手卖家），
并把其 README 中声明的"生产方向"落地了一部分：接入真实 LLM 网关（默认 DeepSeek）、资料库改为可插拔导入、
测试覆盖 LLM 降级路径。评分与核验状态仍由服务端确定性工具裁决，LLM 无法改写结论。

## 为什么做它

货源选品里，"推荐一批商品"本身不够。真正的结论要能回答三个问题：

1. 这个候选**凭什么**排前面？（评分依据）
2. 它**缺什么**证据？（缺失证据显式声明，而不是藏起来）
3. 它到底是**已核实**、**发现线索**还是**待人工复核**？（状态三态，禁止伪装）

内置所有商品、档口、报价、动销与质检记录均为**合成演示数据**。

## 能力

- 多平台货源候选检索：1688 / 义乌购 / 拼多多批发（可限定目标平台）
- 确定性选品评分：类目匹配、拿货价预算、参考毛利空间、起批量、一件代发支持、近期动销线索
- **状态三态裁决**：`verified` / `lead` / `pending_review`，lead 与 pending 强制进入"待核验"声明并降分
- 每候选带**可追溯证据**（offer 快照 / 报价 / 质检等资料摘录 + 来源链接）与**审计记录**
- LLM（默认 DeepSeek）仅生成受 JSON Schema 约束的摘要与候选解读；失败自动降级为纯确定性回答
- `LLM_MODE=demo` 离线可运行；`POST /api/dataset/import` 可导入自有货源资料（替换演示数据）
- 测试锁定安全行为：已验证候选优先、线索型候选显式标注、LLM 失败不阻断服务

## 架构

```
Browser UI ──> FastAPI ──> retrieval + sourcing_scorecard ──> cited, audited response
                          (服务端裁决：评分/状态/证据/缺失)
                          └─> llm gateway (remote 模式，仅摘要，schema 校验)
                          └─> dataset: demo 样本 / 导入的真实资料
```

`apps/api/app/service.py` 是编排边界：词法检索可替换为向量/混合检索，但评分、核验状态与证据检查
**必须留在服务端**——这正是"LLM 生成 + 服务端裁决"的落点：LLM 输出中即使声称"已验证/满分"，
也会被 schema 丢弃，不会进入推荐卡片。

## 快速开始

```bash
python -m pip install -e ".[dev]"
uvicorn app.main:app --app-dir apps/api --reload
```

访问 <http://127.0.0.1:8000>。或 `docker compose up --build`。

## 启用真实 LLM 摘要（可选）

默认 `LLM_MODE=demo` 全离线。要启用 DeepSeek：

```bash
cp .env.example .env   # 填入 LLM_API_KEY，LLM_MODE 改 remote
uvicorn app.main:app --app-dir apps/api
```

网关是 OpenAI 兼容协议：改 `LLM_BASE_URL` / `LLM_MODEL` 可切换到任意兼容厂商。
**注意**：即便 remote 模式，推荐卡片的分数、核验徽章、证据清单仍全部来自服务端裁决，LLM 只负责写摘要。

## 导入真实货源资料

内置数据是合成样本。接入你自己的货源资料（例如把 1688 offer 快照、报价单、质检记录整理成 JSON）：

```bash
curl -X POST http://127.0.0.1:8000/api/dataset/import \
  -H "Content-Type: application/json" \
  -d @examples/dataset.example.json
```

导入后：`/api/health` 状态变为 `imported-dataset`，回答与审计不再标记"演示样本"；
`POST /api/dataset/reset` 可恢复演示数据。字段与约束见 `examples/dataset.example.json`。

## 验证

```bash
pytest -q
```

覆盖：评分边界、verified 优先 / lead 显式标注、pending 不可静默为已验证、
平台过滤、LLM 失败降级、schema 丢弃越权字段、HTTP 契约、导入一致性校验。

## 评测方向

| 维度 | 当前检查 | 下一步 |
| --- | --- | --- |
| 检索 | 回归测试中应返回 offer/报价资料 | 替换向量检索并评估召回率 |
| 事实依据 | 每候选带资料引用与缺失声明 | 引用蕴含关系打分 |
| 业务规则 | 线索不可伪装为已验证（测试锁定） | 引入策略测试集（利润/季节/竞争度） |
| 数据 | demo 样本 + JSON 导入 | 货源站采集适配器（需遵守平台条款与登录态） |
| 性能 | 本地单进程演示 | 记录 p50/p95 延迟与 token 成本 |

## 边界与安全

- 不提交 `.env`、密钥、真实供应商合同/报价/含个人信息的数据；
- 本项目不执行下单、不写入任何第三方交易系统；
- demo 数据全为合成样本；真实货源请按导入通道自备资料；
- 对任何真实货源，上架前请自行核验档口主体、真实库存、售后、物流时效与图片版权；
- 公网部署前收紧 CORS 与鉴权（见 SECURITY.md）。

## 目录

```
apps/api/app/     FastAPI 入口、领域模型、评分工具、检索、LLM 网关、编排、数据导入
apps/web/         无构建步骤的选品面板 UI
tests/            业务/安全/LLM 降级/API/导入回归测试
examples/         真实资料导入格式示例
.github/          GitHub Actions CI + Dependabot
```

## License

MIT。本仓库为 [evidence-supply-agent](https://github.com/DerTod16/evidence-supply-agent) 的衍生改造，
版权与致谢见 [LICENSE](./LICENSE)。
