async function load() {
  await initChrome(load);
  const stats = document.getElementById("accounts-stats");
  const list = document.getElementById("accounts-list");
  const companyId = getActiveCompanyId();

  try {
    const accounts = await apiGet("/companies/" + companyId + "/accounts");
    renderStats(stats, accounts);
    renderList(list, accounts);
  } catch (e) {
    showError(stats, e);
    showError(list, e);
  }
}

function renderStats(el, accounts) {
  clearNode(el);
  const byCurrency = {};
  accounts.forEach((acc) => {
    byCurrency[acc.currency] = (byCurrency[acc.currency] || 0) + acc.balance;
  });

  const cards = Object.keys(byCurrency).map((currency) => ({
    label: "Остаток в " + currency,
    value: fmtMoney(byCurrency[currency], currency),
    hint: "по всем счетам в этой валюте",
  }));

  cards.push({
    label: "Всего счетов",
    value: String(accounts.length),
    hint: "открыто у компании",
  });

  cards.forEach((card) => {
    const box = document.createElement("div");
    box.className = "stat-card";
    box.innerHTML =
      '<div class="stat-label">' + escapeHtml(card.label) + "</div>" +
      '<div class="stat-value">' + escapeHtml(card.value) + "</div>" +
      '<div class="stat-hint">' + escapeHtml(card.hint) + "</div>";
    el.appendChild(box);
  });
}

function renderList(el, accounts) {
  clearNode(el);
  if (!accounts.length) {
    showEmpty(el, "У компании нет счетов");
    return;
  }

  const table = document.createElement("table");
  table.className = "table";
  table.innerHTML =
    "<thead><tr>" +
    "<th>Счёт</th><th>Тип</th><th>Валюта</th>" +
    "<th class=\"num\">Остаток</th><th class=\"num\">Оборот за месяц</th>" +
    "<th>Статус</th><th>Открыт</th>" +
    "</tr></thead><tbody></tbody>";

  const tbody = table.querySelector("tbody");
  accounts.forEach((acc) => {
    const tr = document.createElement("tr");
    tr.innerHTML =
      "<td>" + escapeHtml(acc.name) + "</td>" +
      "<td>" + escapeHtml(acc.type) + "</td>" +
      "<td>" + escapeHtml(acc.currency) + "</td>" +
      '<td class="num">' + escapeHtml(fmtMoney(acc.balance, acc.currency)) + "</td>" +
      '<td class="num">' + escapeHtml(fmtMoney(acc.turnover_month, acc.currency)) + "</td>" +
      '<td><span class="badge ' + (acc.status === "Активен" ? "opp" : "neutral") + '">' + escapeHtml(acc.status) + "</span></td>" +
      "<td>" + escapeHtml(fmtDate(acc.opened_at)) + "</td>";
    tbody.appendChild(tr);
  });

  el.appendChild(table);
}

load();
