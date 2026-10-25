let companiesCache = [];

async function load() {
  await initChrome(null);

  const selectA = document.getElementById("company-a");
  const selectB = document.getElementById("company-b");

  try {
    companiesCache = await getCompanies();
  } catch (e) {
    showError(document.getElementById("compare-metrics"), e);
    return;
  }

  if (companiesCache.length < 2) {
    showEmpty(document.getElementById("compare-metrics"), "Для сравнения нужны две компании");
    return;
  }

  const active = getActiveCompanyId();
  const startIndex = Math.max(0, companiesCache.findIndex((c) => c.id === active));

  [selectA, selectB].forEach((select) => {
    companiesCache.forEach((company, index) => {
      const option = document.createElement("option");
      option.value = company.id;
      option.textContent = company.name;
      if (index === startIndex) option.selected = true;
      select.appendChild(option);
    });
  });
  selectB.selectedIndex = (startIndex + 1) % companiesCache.length;

  const refresh = () => render(selectA.value, selectB.value);
  selectA.addEventListener("change", refresh);
  selectB.addEventListener("change", refresh);

  await refresh();
}

async function render(idA, idB) {
  if (idA === idB) {
    document.getElementById("company-b").selectedIndex =
      (document.getElementById("company-b").selectedIndex + 1) % companiesCache.length;
    idB = document.getElementById("company-b").value;
  }

  const metrics = document.getElementById("compare-metrics");
  clearNode(metrics);

  try {
    const [compare, analyticsA, analyticsB] = await Promise.all([
      apiGet("/compare?company_a=" + encodeURIComponent(idA) + "&company_b=" + encodeURIComponent(idB) + "&role=" + getRole()),
      apiGet("/companies/" + encodeURIComponent(idA) + "/analytics"),
      apiGet("/companies/" + encodeURIComponent(idB) + "/analytics"),
    ]);

    document.getElementById("title-a").textContent =
      compare.company_a.name + " · " + compare.company_a.industry;
    document.getElementById("title-b").textContent =
      compare.company_b.name + " · " + compare.company_b.industry;

    renderMetrics(metrics, compare, analyticsA, analyticsB);
    renderFeed(document.getElementById("feed-a"), compare.feed_a, "Для " + compare.company_a.name);
    renderFeed(document.getElementById("feed-b"), compare.feed_b, "Для " + compare.company_b.name);
  } catch (e) {
    showError(metrics, e);
  }
}

function renderMetrics(el, compare, a, b) {
  const rows = [
    ["Отрасль", compare.company_a.industry, compare.company_b.industry, false],
    ["Регион", compare.company_a.region, compare.company_b.region, false],
    ["Счетов", fmtNumber(a.accounts_count), fmtNumber(b.accounts_count), true],
    ["Операций", fmtNumber(a.payments_count), fmtNumber(b.payments_count), true],
    ["Поступления", fmtMoney(a.total_income, a.currency), fmtMoney(b.total_income, b.currency), true],
    ["Списания", fmtMoney(a.total_expense, a.currency), fmtMoney(b.total_expense, b.currency), true],
    ["Чистый поток", fmtMoney(a.net, a.currency), fmtMoney(b.net, b.currency), true],
    ["Остаток", fmtMoney(a.total_balance, a.currency), fmtMoney(b.total_balance, b.currency), true],
    ["Кредитный лимит", fmtMoney(a.credit_limit_total, a.currency), fmtMoney(b.credit_limit_total, b.currency), true],
    ["Уровень риска", a.risk_level, b.risk_level, false],
    ["Инсайтов", fmtNumber(a.insight_ids.length), fmtNumber(b.insight_ids.length), true],
  ];

  const table = document.createElement("table");
  table.className = "table";
  table.innerHTML =
    "<thead><tr><th>Показатель</th><th class=\"num\">" +
    escapeHtml(compare.company_a.name) +
    "</th><th class=\"num\">" +
    escapeHtml(compare.company_b.name) +
    "</th></tr></thead><tbody></tbody>";

  const tbody = table.querySelector("tbody");
  rows.forEach(([label, valueA, valueB, higherIsBetter]) => {
    const tr = document.createElement("tr");
    const parsedA = parseFloat(String(valueA).replace(/[^\d,-]/g, "").replace(",", "."));
    const parsedB = parseFloat(String(valueB).replace(/[^\d,-]/g, "").replace(",", "."));
    let classA = "";
    let classB = "";
    if (higherIsBetter && !isNaN(parsedA) && !isNaN(parsedB) && parsedA !== parsedB) {
      if (valueA !== "—") classA = parsedA > parsedB ? "num-in" : "num-out";
      if (valueB !== "—") classB = parsedB > parsedA ? "num-in" : "num-out";
    }
    tr.innerHTML =
      "<td>" + escapeHtml(label) + "</td>" +
      '<td class="num ' + classA + '">' + escapeHtml(String(valueA)) + "</td>" +
      '<td class="num ' + classB + '">' + escapeHtml(String(valueB)) + "</td>";
    tbody.appendChild(tr);
  });

  el.appendChild(table);
}

function renderFeed(el, feed, caption) {
  clearNode(el);
  if (!feed.length) {
    showEmpty(el, "Инсайтов пока нет");
    return;
  }
  const head = document.createElement("div");
  head.className = "footer-note";
  head.textContent = caption + ": " + feed.length + " событий";
  el.appendChild(head);

  feed.forEach((item) => {
    const a = document.createElement("a");
    a.className = "insight-preview";
    a.href = "insight.html?id=" + encodeURIComponent(item.insight_id);
    a.innerHTML =
      '<div class="preview-top">' +
      '<span class="badge ' + kindBadgeClass(item.kind) + '">' + kindRu(item.kind) + "</span>" +
      '<span class="meta">' + Math.round(item.relevance * 100) + "%</span>" +
      "</div>" +
      '<div class="preview-title">' + escapeHtml(item.title) + "</div>" +
      '<div class="preview-sub">' + escapeHtml((item.why_for_you || []).join(" • ")) + "</div>";
    el.appendChild(a);
  });
}

load();
