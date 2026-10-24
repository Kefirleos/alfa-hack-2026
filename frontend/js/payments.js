let paymentsCache = [];
let fxRates = null;

async function load() {
  await initChrome(load);
  const stats = document.getElementById("payments-stats");
  const list = document.getElementById("payments-list");
  const companyId = getActiveCompanyId();

  try {
    const fx = await getFx();
    fxRates = fx.rates;
    paymentsCache = await apiGet("/companies/" + companyId + "/payments");
    populateCategories();
    render(stats, list);
  } catch (e) {
    showError(stats, e);
    showError(list, e);
  }

  document.getElementById("direction-filter").addEventListener("change", () => render(stats, list));
  document.getElementById("category-filter").addEventListener("change", () => render(stats, list));
}

function baseAmount(row) {
  return Number(row.amount || 0) * ((fxRates && fxRates[row.currency]) || 1);
}

function populateCategories() {
  const select = document.getElementById("category-filter");
  const categories = [...new Set(paymentsCache.map((p) => p.category))].sort();
  categories.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    select.appendChild(option);
  });
}

function filtered() {
  const direction = document.getElementById("direction-filter").value;
  const category = document.getElementById("category-filter").value;
  return paymentsCache.filter((p) => {
    if (direction !== "all" && p.direction !== direction) return false;
    if (category !== "all" && p.category !== category) return false;
    return true;
  });
}

function render(stats, list) {
  const rows = filtered();

  const income = rows.filter((p) => p.direction === "incoming").reduce((sum, p) => sum + baseAmount(p), 0);
  const expense = rows.filter((p) => p.direction === "outgoing").reduce((sum, p) => sum + baseAmount(p), 0);

  clearNode(stats);
  [
    { label: "Поступления", value: fmtMoney(income, "RUB"), hint: rows.length + " операций в выборке" },
    { label: "Списания", value: fmtMoney(expense, "RUB"), hint: "с учётом валютных платежей" },
    { label: "Итог", value: fmtMoney(income - expense, "RUB"), hint: "поступления минус списания" },
  ].forEach((card) => {
    const box = document.createElement("div");
    box.className = "stat-card";
    box.innerHTML =
      '<div class="stat-label">' + escapeHtml(card.label) + "</div>" +
      '<div class="stat-value">' + escapeHtml(card.value) + "</div>" +
      '<div class="stat-hint">' + escapeHtml(card.hint) + "</div>";
    stats.appendChild(box);
  });

  document.getElementById("payments-count").textContent =
    "(" + rows.length + " из " + paymentsCache.length + ")";

  clearNode(list);
  if (!rows.length) {
    showEmpty(list, "Под выбранные фильтры ничего не подошло");
    return;
  }

  const table = document.createElement("table");
  table.className = "table";
  table.innerHTML =
    "<thead><tr>" +
    "<th>Дата</th><th>Контрагент</th><th>Категория</th>" +
    "<th class=\"num\">Сумма</th><th>Статус</th><th>Комментарий</th>" +
    "</tr></thead><tbody></tbody>";

  const tbody = table.querySelector("tbody");
  rows.forEach((row) => {
    const sign = row.direction === "incoming" ? "+" : "−";
    const tr = document.createElement("tr");
    tr.innerHTML =
      "<td>" + escapeHtml(fmtDate(row.date)) + "</td>" +
      "<td>" + escapeHtml(row.counterparty) + "</td>" +
      '<td><span class="tag">' + escapeHtml(row.category) + "</span></td>" +
      '<td class="num ' + (row.direction === "incoming" ? "num-in" : "num-out") + '">' +
      escapeHtml(sign + " " + fmtMoney(row.amount, row.currency)) +
      "</td>" +
      '<td><span class="badge ' + (row.status === "Проведён" ? "opp" : "neutral") + '">' + escapeHtml(row.status) + "</span></td>" +
      '<td class="footer-note">' + escapeHtml(row.comment) + "</td>";
    tbody.appendChild(tr);
  });

  list.appendChild(table);
}

load();
