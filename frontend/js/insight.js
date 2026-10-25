function getId() {
  const p = new URLSearchParams(location.search);
  return p.get("id") || "ins_001";
}

function renderList(id, items) {
  const el = document.getElementById(id);
  if (!el) return;
  clearNode(el);
  (items || []).forEach((c) => {
    const li = document.createElement("li");
    li.className = "list-item";
    li.innerHTML =
      '<div class="list-item-top">' +
      "<div>" + escapeHtml(c.text) + "</div>" +
      '<span class="tag">' + escapeHtml(claimTypeRu(c.type)) + "</span>" +
      "</div>" +
      ((c.features && c.features.length) ? '<div class="footer-note">Признаки: ' + escapeHtml(c.features.join(", ")) + "</div>" : "") +
      ((c.sources && c.sources.length) ? '<div class="footer-note">Источник: ' + escapeHtml(c.sources.map((s) => s.title).join(", ")) + "</div>" : "");
    el.appendChild(li);
  });
}

async function load() {
  await initChrome(load);
  const id = getId();

  try {
    document.getElementById("insight-title").textContent = "Строим разбор, это может занять до минуты…";
    const data = await apiGet("/insights/" + encodeURIComponent(id));
    document.getElementById("insight-title").textContent = data.event.title;
    document.getElementById("insight-date").textContent = data.event.date;
    document.getElementById("insight-relevance").textContent = "Релевантность " + Math.round(data.relevance * 100) + "%";
    renderList("event-list", data.event.summary);
    renderList("why-list", data.why_it_matters);
    renderList("risks-list", data.risks);
    renderList("opp-list", data.opportunities);
    renderList("actions-list", data.actions);
    renderList("bank-list", data.bank_view);

    const src = document.getElementById("sources-list");
    clearNode(src);
    const all = [];
    (data.event.summary || []).forEach((x) => (x.sources || []).forEach((s) => all.push(s)));
    (data.bank_view || []).forEach((x) => (x.sources || []).forEach((s) => all.push(s)));
    if (!all.length) {
      src.innerHTML = '<div class="footer-note">Источники не указаны</div>';
    } else {
      all.forEach((s) => {
        const a = document.createElement("a");
        a.className = "source-link";
        a.href = s.url || "#";
        a.target = s.url ? "_blank" : "_self";
        a.rel = "noopener";
        a.textContent = s.title + (s.doc ? " • " + s.doc : "");
        src.appendChild(a);
      });
    }

    const fl = document.getElementById("features-list");
    clearNode(fl);
    const feats = [];
    (data.why_it_matters || []).forEach((x) => (x.features || []).forEach((f) => feats.push(f)));
    const unique = [...new Set(feats)];
    if (!unique.length) {
      fl.innerHTML = '<li class="footer-note">Не указаны</li>';
    } else {
      unique.forEach((f) => {
        const li = document.createElement("li");
        li.className = "list-item";
        li.innerHTML = "<div>" + escapeHtml(f) + "</div>";
        fl.appendChild(li);
      });
    }
    document.getElementById("uncertainty").textContent = data.uncertainty ? "Неопределённость: " + data.uncertainty : "";
  } catch (e) {
    document.getElementById("insight-title").textContent = "Не удалось загрузить инсайт";
    showError(document.getElementById("event-list"), e);
  }

  try {
    const trace = await apiGet("/insights/" + encodeURIComponent(id) + "/trace");
    const list = document.getElementById("trace-list");
    clearNode(list);
    trace.forEach((step) => {
      const li = document.createElement("li");
      li.className = "list-item";
      li.innerHTML =
        '<div class="list-item-top">' +
        "<div><strong>Шаг " + step.step + ". " + escapeHtml(step.name) + "</strong></div>" +
        (step.tool ? '<span class="tag">' + escapeHtml(step.tool) + "</span>" : "") +
        "</div>" +
        '<div class="footer-note">' + escapeHtml(step.result) + "</div>";
      list.appendChild(li);
    });
  } catch (e) {
    const list = document.getElementById("trace-list");
    if (list) showEmpty(list, "Трассировка недоступна");
  }

  const send = document.getElementById("question-send");
  const input = document.getElementById("question-input");
  const ans = document.getElementById("chat-answer");
  if (send) {
    send.addEventListener("click", async () => {
      const question = (input.value || "").trim();
      if (!question) return;
      send.disabled = true;
      send.textContent = "Отправляю...";
      clearNode(ans);
      try {
        const res = await apiPost("/insights/" + encodeURIComponent(id) + "/chat", { message: question });
        const ul = document.createElement("ul");
        ul.className = "list";
        (res.answer || []).forEach((claim) => {
          const li = document.createElement("li");
          li.className = "list-item";
          li.innerHTML =
            '<div class="list-item-top">' +
            "<div>" + escapeHtml(claim.text) + "</div>" +
            '<span class="tag">' + escapeHtml(claimTypeRu(claim.type)) + "</span>" +
            "</div>";
          ul.appendChild(li);
        });
        ans.appendChild(ul);
      } catch (e) {
        showError(ans, e);
      } finally {
        send.disabled = false;
        send.textContent = "Отправить";
      }
    });
    input.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") {
        ev.preventDefault();
        send.click();
      }
    });
  }
}

load();
