let creditsCache = [];
let fxRates = null;

function baseAmount(value, currency) {
  return Number(value || 0) * ((fxRates && fxRates[currency]) || 1);
}

async function load() {
  await initChrome(load);
  const stats = document.getElementById("credits-stats");
  const list = document.getElementById("credits-list");
  const companyId = getActiveCompanyId();

  try {
    const fx = await getFx();
    fxRates = fx.rates;
    creditsCache = await apiGet("/companies/" + companyId + "/credits");
    renderStats(stats, creditsCache);
    renderList(list, creditsCache);
  } catch (e) {
    showError(stats, e);
    showError(list, e);
  }
}

function renderStats(el, credits) {
  clearNode(el);
  const totalLimit = credits.reduce((sum, c) => sum + baseAmount(c.limit, c.currency), 0);
  const totalUsed = credits.reduce((sum, c) => sum + baseAmount(c.used, c.currency), 0);

  [
    { label: "Общий лимит", value: fmtMoney(totalLimit, "RUB"), hint: credits.length + " кредитных продуктов" },
    { label: "Задействовано", value: fmtMoney(totalUsed, "RUB"), hint: "использовано из доступного лимита" },
    { label: "Свободно", value: fmtMoney(totalLimit - totalUsed, "RUB"), hint: "можно взять сейчас" },
    {
      label: "Средняя ставка",
      value: credits.length ? fmtPercent(credits.reduce((s, c) => s + c.rate, 0) / credits.length) : "—",
      hint: "по активным и доступным продуктам",
    },
  ].forEach((card) => {
    const box = document.createElement("div");
    box.className = "stat-card";
    box.innerHTML =
      '<div class="stat-label">' + escapeHtml(card.label) + "</div>" +
      '<div class="stat-value">' + escapeHtml(card.value) + "</div>" +
      '<div class="stat-hint">' + escapeHtml(card.hint) + "</div>";
    el.appendChild(box);
  });
}

function renderList(el, credits) {
  clearNode(el);
  if (!credits.length) {
    showEmpty(el, "У компании нет кредитных продуктов");
    return;
  }

  credits.forEach((credit) => {
    const usedShare = credit.limit > 0 ? credit.used / credit.limit : 0;
    const badgeClass = credit.status === "Активен" ? "" : "opp";

    const card = document.createElement("div");
    card.className = "credit-card";
    card.innerHTML =
      '<div class="credit-head">' +
      "<div>" +
      '<div class="preview-title">' + escapeHtml(credit.product) + "</div>" +
      '<div class="meta" style="margin-top: 6px;">' +
      "<span>Ставка " + escapeHtml(fmtPercent(credit.rate)) + " годовых</span>" +
      "<span>•</span>" +
      "<span>Срок " + escapeHtml(credit.term_months + " мес") + "</span>" +
      "</div>" +
      "</div>" +
      '<span class="badge ' + badgeClass + '">' + escapeHtml(credit.status) + "</span>" +
      "</div>" +
      '<div class="credit-numbers">' +
      '<div><div class="stat-label">Лимит</div><div class="stat-value">' + escapeHtml(fmtMoney(credit.limit, credit.currency)) + "</div></div>" +
      '<div><div class="stat-label">Использовано</div><div class="stat-value">' + escapeHtml(fmtMoney(credit.used, credit.currency)) + "</div></div>" +
      '<div><div class="stat-label">Свободно</div><div class="stat-value">' + escapeHtml(fmtMoney(credit.limit - credit.used, credit.currency)) + "</div></div>" +
      "</div>" +
      '<div class="bar-track"><div class="bar-fill" style="width:' + Math.min(100, usedShare * 100).toFixed(1) + '%"></div></div>' +
      '<div class="footer-note">Использовано ' + escapeHtml(fmtPercent(usedShare)) + " лимита</div>" +
      '<div class="recommendation">' +
      '<span class="badge ' + (credit.recommendation === "Рекомендуется" ? "opp" : credit.recommendation === "На рассмотрении" ? "neutral" : "") + '">' +
      escapeHtml(credit.recommendation) +
      "</span>" +
      '<div class="footer-note">' + escapeHtml(credit.reason) + "</div>" +
      "</div>";

    el.appendChild(card);
  });
}

load();
