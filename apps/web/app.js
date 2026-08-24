const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value).replace(/[&<>"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[char]);
}

function card(item) {
  const citations = item.citations.length
    ? item.citations.map((citation) => `<li><strong>${escapeHtml(citation.title)}</strong><br><span>${escapeHtml(citation.excerpt)}</span></li>`).join("")
    : "<li>本次没有检索到可引用材料。</li>";
  return `<article class="recommendation">
    <div class="title"><div><h2>${escapeHtml(item.supplier_name)}</h2><span class="badge ${item.verification_status}">${escapeHtml(item.verification_status)}</span></div><strong class="score">${item.score}</strong></div>
    <h3>匹配依据</h3><ul>${item.why.map((entry) => `<li>${escapeHtml(entry)}</li>`).join("")}</ul>
    <h3>待核验项</h3><ul class="risks">${item.missing_evidence.map((entry) => `<li>${escapeHtml(entry)}</li>`).join("") || "<li>没有额外提示</li>"}</ul>
    <h3>可追溯证据</h3><ul class="citations">${citations}</ul>
  </article>`;
}

async function ask() {
  const button = $("#askButton");
  button.disabled = true;
  $("#status").textContent = "正在检索演示资料并生成可审计评分…";
  const body = {
    question: $("#question").value,
    requirement: {
      category: $("#category").value || null,
      max_unit_price_usd: Number($("#price").value) || null,
      max_lead_time_days: Number($("#leadTime").value) || null,
      required_certifications: $("#certs").value.split(",").map((value) => value.trim()).filter(Boolean),
    },
  };
  try {
    const response = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!response.ok) throw new Error("请求失败");
    const data = await response.json();
    $("#status").innerHTML = `<p class="answer">${escapeHtml(data.answer)}</p><p class="warning">${data.warnings.map(escapeHtml).join("<br>")}</p>`;
    $("#result").innerHTML = data.recommendations.map(card).join("") + `<details><summary>审计记录</summary><pre>${escapeHtml(JSON.stringify(data.audit, null, 2))}</pre></details>`;
  } catch (error) {
    $("#status").textContent = `无法完成请求：${error.message}`;
  } finally { button.disabled = false; }
}

$("#askButton").addEventListener("click", ask);
ask();
