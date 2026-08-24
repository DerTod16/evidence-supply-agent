# Evidence Supply Agent

> 一个证据优先的供应商研究 Agent：输出候选、评分、风险和可回溯资料，而不是把语言模型的猜测伪装成采购结论。

![License](https://img.shields.io/badge/license-MIT-0b7f65) ![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)

## 为什么做它

采购场景中，“推荐一个供应商”本身不够。这个项目强制区分 `verified`、`lead`、`pending_review`，并把每项候选的支持证据和缺失证据同时呈现。所有示例供应商、报价和证书都为合成演示数据。

## 能力

- 结合问题、元数据和资料内容进行可解释检索
- 用确定性评分工具处理预算、交期、地区、认证和核验状态
- 返回带资料摘录的候选卡片与审计记录
- 用测试锁定两个关键安全行为：优先已验证候选、显式标注线索型候选
- 使用 `LLM_MODE=demo` 时离线可运行；`.env.example` 预留模型网关配置

## 架构

```text
Browser UI -> FastAPI -> retrieval + supplier_scorecard -> cited response
                       -> synthetic catalog / quote / certificate records
```

`apps/api/app/service.py` 是可替换的编排边界：生产部署中可将词法检索替换为混合检索，将确定性摘要替换为受 JSON Schema 约束的模型输出，但评分、证据与状态检查仍应在服务端执行。

## 运行

```bash
python -m pip install -e ".[dev]"
uvicorn app.main:app --app-dir apps/api --reload
```

访问 `http://127.0.0.1:8000`。或运行 `docker compose up --build`。

## 验证

```bash
pytest -q
```

## 评测方向

| 维度 | 当前检查 | 下一步 |
| --- | --- | --- |
| 检索 | 回归测试中应返回报价材料 | RAGAS/人工标注召回率 |
| 事实依据 | 每个候选带资料引用 | 引用蕴含关系打分 |
| 业务规则 | 线索状态不可伪装为已验证 | 引入策略测试集 |
| 性能 | 本地单进程演示 | 记录 p50/p95 延迟与 token 成本 |

## 边界与安全

- 不提交 `.env`、密钥、真实供应商合同或个人数据。
- 本项目不执行采购、下单或写入第三方系统。
- 对任何真实供应商都应核验主体、证书有效性、报价、库存、物流与合规。

## 目录

```text
apps/api/app/     API、评分工具与演示资料
apps/web/         无构建步骤的展示 UI
tests/            业务和检索回归测试
.github/          GitHub Actions
```

MIT License.
