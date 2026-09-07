# Security Policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

## Reporting a vulnerability

本仓库不执行真实采购、下单或写入第三方交易系统；演示数据全为合成样本。
若你发现以下问题，请开 Issue 而非公开细节，避免放大风险：

- 真实资料导入/查询端点（`/api/dataset/import`、`/api/ask`）存在注入或越权；
- 部署配置（CORS、密钥、.env 处理）存在泄露面；
- 依赖存在已知高危 CVE 且影响本项目运行。

请提供：影响面、可复现步骤、建议修复方案。处置目标：main 分支 7 天内修复或给出缓解措施。

## 部署红线

- 绝不提交 `.env`、真实 API Key、真实供应商合同、报价或含个人信息的资料；
- 对外提供服务前必须关闭/收紧 CORS（当前默认 `allow_origins=["*"]` 仅适合本地演示）；
- `/api/products`、`/api/documents` 会把当前内存数据集整体暴露，公网部署前需加鉴权或禁用。
