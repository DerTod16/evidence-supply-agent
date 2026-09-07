const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const STATUS_LABELS = { verified: "已验证", lead: "发现线索", pending_review: "待人工复核" };

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]
  ));
}

function citationMarkup(citation) {
  const href = citation.url
    ? `<a class="cite-link" href="${escapeHtml(citation.url)}" target="_blank" rel="noopener noreferrer">来源 ↗</a>`
    : "";
  return `<li>
    <div class="cite-head"><strong>${escapeHtml(citation.title)}</strong>${href}</div>
    <div class="cite-meta">${escapeHtml(citation.source_type)} · authority=${escapeHtml(citation.authority)}</div>
    <span class="cite-excerpt">${escapeHtml(citation.excerpt)}</span>
  </li>`;
}

function card(item) {
  const citations = item.citations.length
    ? item.citations.map(citationMarkup).join("")
    : "<li>本次没有检索到可引用的支持资料。</li>";
  const priceRow = `<span class="chip">¥${Number(item.price_cny).toFixed(2)}/件</span>
    <span class="chip">起批 ${item.min_order_qty} 件</span>`;
  return `<article class="recommendation">
    <div class="title">
      <div>
        <h2>${escapeHtml(item.product_title)}</h2>
        <p class="meta">${escapeHtml(item.supplier)} · ${escapeHtml(item.platform)} ${priceRow}</p>
      </div>
      <div class="score-wrap">
        <strong class="score">${item.score}</strong>
        <span class="badge ${item.verification_status}">${STATUS_LABELS[item.verification_status] || escapeHtml(item.verification_status)}</span>
      </div>
    </div>
    <h3>匹配依据</h3>
    <ul class="ticks">${item.why.map((entry) => `<li>${escapeHtml(entry)}</li>`).join("")}</ul>
    <h3>待核验 / 缺失证据</h3>
    <ul class="risks">${item.missing_evidence.map((entry) => `<li>${escapeHtml(entry)}</li>`).join("") || "<li>没有额外提示</li>"}</ul>
    <h3>可追溯证据</h3>
    <ul class="citations">${citations}</ul>
  </article>`;
}

async function ask() {
  const button = $("#askButton");
  button.disabled = true;
  $("#status").textContent = "正在检索货源资料并生成可审计评分…";

  const platforms = $$('input[name="platform"]:checked').map((el) => el.value);
  const body = {
    question: $("#question").value,
    requirement: {
      category: $("#category").value || null,
      max_price_cny: Number($("#price").value) || null,
      min_est_profit_cny: Number($("#profit").value) || null,
      max_min_order_qty: Number($("#minOrder").value) || null,
      drop_ship_required: $("#dropShip").checked,
      platforms: platforms.length ? platforms : null,
    },
  };

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(`请求失败（${response.status}）`);
    const data = await response.json();

    const llmBadge = data.llm_used
      ? '<span class="llm-badge on">LLM 摘要已生成</span>'
      : '<span class="llm-badge">确定性模式（未调用 LLM）</span>';
    $("#status").innerHTML = `
      <p class="answer">${escapeHtml(data.answer)}</p>
      <p class="warning">${data.warnings.map(escapeHtml).join("<br>")}</p>
      <p class="meta-line">${llmBadge}${data.llm_error ? `<span class="llm-badge warn">LLM 降级：${escapeHtml(data.llm_error)}</span>` : ""}</p>`;
    $("#result").innerHTML = data.recommendations.map(card).join("") + `
      <details class="panel"><summary>审计记录</summary><pre>${escapeHtml(JSON.stringify(data.audit, null, 2))}</pre></details>`;
  } catch (error) {
    $("#status").innerHTML = `<p class="warning">无法完成请求：${escapeHtml(error.message)}</p>`;
  } finally {
    button.disabled = false;
  }
}

$("#askButton").addEventListener("click", ask);
ask();
