async function load() {
  await initChrome(load);
  const stats = document.getElementById("analytics-stats");
  const companyId = getActiveCompanyId();

  try {
    const data = await apiGet("/companies/" + companyId + "/analytics");
    document.getElementById("base-currency").textContent = data.currency;
    renderStats(stats, data);
    renderCategories(document.getElementById("category-chart"), data);
    renderMonths(document.getElementById("month-chart"), data);
    renderCounterparties(document.getElementById("counterparty-chart"), data);
    renderRisk(data);
    await renderLinkedInsights(data);
  } catch (e) {
    showError(stats, e);
  }
}

function statCard(label, value, hint, accent) {
  const box = document.createElement("div");
  box.className = "stat-card" + (accent ? " stat-" + accent : "");
  box.innerHTML =
    '<div class="stat-label">' + escapeHtml(label) + "</div>" +
    '<div class="stat-value">' + escapeHtml(value) + "</div>" +
    '<div class="stat-hint">' + escapeHtml(hint) + "</div>";
  return box;
}

function renderStats(el, data) {
  clearNode(el);
  const usage = data.credit_limit_total > 0 ? data.credit_used_total / data.credit_limit_total : 0;
  [
    ["Поступления", fmtMoney(data.total_income, data.currency), data.payments_count + " операций", ""],
    ["Списания", fmtMoney(data.total_expense, data.currency), "без переводов между счетами", ""],
    ["Чистый поток", fmtMoney(data.net, data.currency), data.net >= 0 ? "поток положительный" : "поток отрицательный", data.net >= 0 ? "ok" : "bad"],
    ["Остаток", fmtMoney(data.total_balance, data.currency), data.accounts_count + " счетов", ""],
    ["Использование лимита", fmtPercent(usage), fmtMoney(data.credit_used_total, data.currency) + " из " + fmtMoney(data.credit_limit_total, data.currency), usage > 0.8 ? "bad" : "ok"],
    ["Уровень риска", data.risk_level, data.risk_notes.length + " замечаний", data.risk_level === "Низкий" ? "ok" : data.risk_level === "Высокий" ? "bad" : ""],
  ].forEach(([label, value, hint, accent]) => el.appendChild(statCard(label, value, hint, accent)));
}

function bar(label, amount, max, colorClass, currency) {
  const row = document.createElement("div");
  row.className = "bar-row";
  const width = max > 0 ? Math.min(100, (Math.abs(amount) / max) * 100) : 0;
  row.innerHTML =
    '<div class="bar-head"><span class="bar-label">' + escapeHtml(label) + "</span>" +
    '<span class="bar-value ' + (colorClass || "") + '">' + escapeHtml(fmtMoney(amount, currency)) + "</span></div>" +
    '<div class="bar-track"><div class="bar-fill ' + (colorClass || "") + '" style="width:' + width.toFixed(1) + '%"></div></div>';
  return row;
}

const MONTH_NAMES = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];

function monthTitle(month) {
  const parts = month.split("-");
  return (MONTH_NAMES[Number(parts[1]) - 1] || month) + " " + parts[0];
}

function renderCategories(el, data) {
  clearNode(el);
  if (!data.by_category.length) {
    showEmpty(el, "Нет данных по категориям");
    return;
  }
  const max = Math.max.apply(null, data.by_category.map((c) => Math.abs(c.amount)));
  data.by_category.forEach((category) => {
    const color = category.amount >= 0 ? "ok" : "bad";
    el.appendChild(bar(category.category + " · " + Math.round(category.share * 100) + "%", category.amount, max, color, data.currency));
  });
}

function renderMonths(el, data) {
  clearNode(el);
  if (!data.by_month.length) {
    showEmpty(el, "Нет данных по месяцам");
    return;
  }
  const max = Math.max.apply(null, data.by_month.map((m) => Math.max(m.income, m.expense)));
  data.by_month.forEach((month) => {
    const box = document.createElement("div");
    box.className = "month-block";
    box.innerHTML = '<div class="month-title">' + escapeHtml(monthTitle(month.month)) + "</div>";
    box.appendChild(bar("Поступления", month.income, max, "ok", data.currency));
    box.appendChild(bar("Списания", month.expense, max, "bad", data.currency));
    const net = month.income - month.expense;
    const note = document.createElement("div");
    note.className = "footer-note";
    note.textContent = "Чистый поток: " + fmtMoney(net, data.currency);
    box.appendChild(note);
    el.appendChild(box);
  });
}

function renderCounterparties(el, data) {
  clearNode(el);
  if (!data.top_counterparties.length) {
    showEmpty(el, "Нет данных по контрагентам");
    return;
  }
  const max = Math.max.apply(null, data.top_counterparties.map((c) => c.amount));
  data.top_counterparties.forEach((counterparty) => {
    el.appendChild(bar(counterparty.name, counterparty.amount, max, "", data.currency));
  });
}

function renderRisk(data) {
  const badgeBox = document.getElementById("risk-badge");
  clearNode(badgeBox);
  const cls = data.risk_level === "Низкий" ? "opp" : data.risk_level === "Высокий" ? "" : "neutral";
  badgeBox.innerHTML = '<span class="badge ' + cls + '">Уровень: ' + escapeHtml(data.risk_level) + "</span>";

  const list = document.getElementById("risk-notes");
  clearNode(list);
  data.risk_notes.forEach((note) => {
    const li = document.createElement("li");
    li.className = "list-item";
    li.innerHTML = "<div>" + escapeHtml(note) + "</div>";
    list.appendChild(li);
  });
}

async function renderLinkedInsights(data) {
  const list = document.getElementById("linked-insights");
  clearNode(list);
  const feed = await apiGet("/companies/" + encodeURIComponent(getActiveCompanyId()) + "/feed?role=" + encodeURIComponent(getRole())).catch(() => []);
  if (!feed.length) {
    showEmpty(list, "Связанных инсайтов нет");
    return;
  }
  feed.slice(0, 5).forEach((item) => {
    const li = document.createElement("li");
    li.className = "list-item";
    li.innerHTML =
      '<a class="source-link" href="insight.html?id=' + encodeURIComponent(item.insight_id) + '">' +
      escapeHtml(item.title) + "</a>";
    list.appendChild(li);
  });
}

load();
