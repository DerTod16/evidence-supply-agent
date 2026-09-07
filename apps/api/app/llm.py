"""LLM 网关（OpenAI 兼容，默认 DeepSeek）。

只做两件事：
1. 接收服务端已裁决的事实（评分/状态/缺失证据/引用），生成买家视角的摘要与解读；
2. 输出受 LlmSummary JSON Schema 约束，服务端强校验，任何分数/状态类字段都会被丢弃。

LLM_MODE=demo 时不发起任何外部调用（离线可运行）；LLM_MODE=remote 时才联网，
需在 .env 提供 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL。
"""

from __future__ import annotations

import json
import os

import httpx

from .models import LlmSummary, Recommendation, Requirement

DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"

_SYSTEM_PROMPT = """你是电商新手卖家的货源选品助手。你只被允许做三件事：
1. 用一段不超过 120 字的话总结候选结果与最值得关注的取舍（answer）；
2. 如资料允许，补充一句市场背景（market_context），拿不准就输出 null；
3. 对每个候选给出候选级的一句话解读（candidate_notes，键为 product_id）。

硬性约束：
- 你不掌握、也不得编造评分、核验状态、价格、起批量等事实——它们由服务端裁决，
  题目中会提供给你参考，但你输出的 JSON 里绝不能包含这些字段；
- 只能依据题目提供的证据摘要发言，证据不足时明确说"资料不足"，禁止脑补；
- 输出必须是合法 JSON 对象，结构为
  {"answer": str, "market_context": str|null, "candidate_notes": {product_id: str}}。"""


class LLMError(RuntimeError):
    """网关调用或解析失败。调用方应捕获并降级为纯确定性回答。"""


def llm_enabled() -> bool:
    return os.getenv("LLM_MODE", "demo").strip().lower() == "remote" and bool(os.getenv("LLM_API_KEY", "").strip())


def _model_name() -> str:
    return os.getenv("LLM_MODEL", "").strip() or DEFAULT_MODEL


def _base_url() -> str:
    return os.getenv("LLM_BASE_URL", "").strip().rstrip("/") or DEFAULT_BASE_URL


def _build_user_prompt(requirement: Requirement, recommendations: list[Recommendation]) -> str:
    lines = ["【本次选品需求】", requirement.model_dump(exclude_none=True, exclude={"platforms"}), ""]
    if requirement.platforms:
        lines.append(f"目标平台：{'、'.join(requirement.platforms)}")
    lines.append("")
    lines.append("【服务端已裁决的候选事实（仅供你解读参考，不得复述为你的结论）】")
    for rec in recommendations:
        lines.append(
            f"- {rec.product_id} | {rec.product_title} | 状态:{rec.verification_status} | "
            f"价 ¥{rec.price_cny:.2f} | 起批 {rec.min_order_qty}"
        )
        lines.append(f"    匹配依据：{'；'.join(rec.why)}")
        if rec.missing_evidence:
            lines.append(f"    待核验/缺失：{'；'.join(rec.missing_evidence)}")
        for c in rec.citations[:2]:
            lines.append(f"    证据《{c.title}》：{c.excerpt[:90]}")
    lines.append("")
    lines.append("请输出上述 JSON 对象。")
    return "\n".join(lines)


def generate_summary(requirement: Requirement, recommendations: list[Recommendation]) -> LlmSummary:
    """调用远程模型生成结构化摘要。失败抛 LLMError。"""
    if not llm_enabled():
        raise LLMError("LLM_MODE 未设为 remote 或缺少 LLM_API_KEY")

    headers = {
        "Authorization": f"Bearer {os.getenv('LLM_API_KEY', '').strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _model_name(),
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(requirement, recommendations)},
        ],
        "response_format": {"type": "json_object"},
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response = client.post(f"{_base_url()}/chat/completions", headers=headers, json=payload)
            if response.status_code == 400 and "response_format" in str(response.text):
                # 个别 OpenAI 兼容网关不支持 response_format，降级重试一次
                payload.pop("response_format", None)
                response = client.post(f"{_base_url()}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
    except httpx.HTTPError as exc:
        raise LLMError(f"网关调用失败：{exc}") from exc
    except (KeyError, IndexError, ValueError) as exc:
        raise LLMError(f"网关响应格式异常：{exc}") from exc

    try:
        data = json.loads(content)
        return LlmSummary.model_validate(data)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LLMError(f"模型输出未通过 JSON Schema 校验：{exc}") from exc
