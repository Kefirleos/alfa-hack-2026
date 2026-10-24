async function load() {
  await initChrome(load);
  const stats = document.getElementById("dashboard-stats");
  const previews = document.getElementById("dashboard-previews");
  const companyId = getActiveCompanyId();

  try {
    const analytics = await apiGet("/companies/" + companyId + "/analytics");
    renderStats(stats, analytics);
  } catch (e) {
    showError(stats, e);
  }

  try {
    const feed = await apiGet("/companies/" + companyId + "/feed");
    renderPreviews(previews, feed);
  } catch (e) {
    showError(previews, e);
  }
}

function renderStats(el, data) {
  clearNode(el);
  const cards = [
    {
      label: "Поступления",
      value: fmtMoney(data.total_income, data.currency),
      hint: "за выбранный период",
      accent: "ok",
    },
    {
      label: "Списания",
      value: fmtMoney(data.total_expense, data.currency),
      hint: "за выбранный период",
      accent: "bad",
    },
    {
      label: "Чистый поток",
      value: fmtMoney(data.net, data.currency),
      hint: data.net >= 0 ? "денежный поток положительный" : "денежный поток отрицательный",
      accent: data.net >= 0 ? "ok" : "bad",
    },
    {
      label: "Остаток на счетах",
      value: fmtMoney(data.total_balance, data.currency),
      hint: data.accounts_count + " счетов открыто",
      accent: "plain",
    },
    {
      label: "Кредитный лимит",
      value: fmtMoney(data.credit_limit_total, data.currency),
      hint: "использовано " + fmtMoney(data.credit_used_total, data.currency),
      accent: "plain",
    },
    {
      label: "Уровень риска",
      value: data.risk_level,
      hint: data.risk_notes.length + " замечаний по данным",
      accent: data.risk_level === "Низкий" ? "ok" : "bad",
    },
  ];

  cards.forEach((card) => {
    const box = document.createElement("div");
    box.className = "stat-card" + (card.accent !== "plain" ? " stat-" + card.accent : "");
    box.innerHTML =
      '<div class="stat-label">' + escapeHtml(card.label) + "</div>" +
      '<div class="stat-value">' + escapeHtml(card.value) + "</div>" +
      '<div class="stat-hint">' + escapeHtml(card.hint) + "</div>";
    el.appendChild(box);
  });
}

function renderPreviews(el, feed) {
  clearNode(el);
  if (!feed.length) {
    showEmpty(el, "Для этой компании пока нет инсайтов");
    return;
  }
  feed.slice(0, 3).forEach((item) => {
    const a = document.createElement("a");
    a.className = "insight-preview";
    a.href = "insight.html?id=" + encodeURIComponent(item.insight_id);
    a.innerHTML =
      '<div class="preview-top">' +
      '<span class="badge ' + kindBadgeClass(item.kind) + '">' + kindRu(item.kind) + "</span>" +
      '<span class="meta">Релевантность ' + Math.round(item.relevance * 100) + "%</span>" +
      "</div>" +
      '<div class="preview-title">' + escapeHtml(item.title) + "</div>" +
      '<div class="preview-sub">' + escapeHtml((item.why_for_you || []).join(" • ")) + "</div>";
    el.appendChild(a);
  });
}

load();
