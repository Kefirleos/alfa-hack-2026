let feedCache = [];

async function load() {
  await initChrome(load);
  const list = document.getElementById("insight-list");
  const companyId = getActiveCompanyId();

  try {
    feedCache = await apiGet("/companies/" + companyId + "/feed");
    render(list);
  } catch (e) {
    showError(list, e);
  }

  const sort = document.getElementById("sort-select");
  sort.addEventListener("change", () => render(list));
}

function render(list) {
  clearNode(list);
  if (!feedCache.length) {
    showEmpty(list, "Для этой компании пока нет инсайтов");
    return;
  }

  const mode = document.getElementById("sort-select").value;
  const items = feedCache.slice().sort((a, b) => {
    if (mode === "date") return String(b.date).localeCompare(String(a.date));
    if (mode === "kind") return String(a.kind).localeCompare(String(b.kind));
    return b.relevance - a.relevance;
  });

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "insight-card";

    const link = document.createElement("a");
    link.href = "insight.html?id=" + encodeURIComponent(item.insight_id);
    link.innerHTML =
      '<div class="insight-card-header">' +
      "<div>" +
      '<div class="insight-card-title">' + escapeHtml(item.title) + "</div>" +
      '<div class="meta" style="margin-top: 6px;">' +
      "<span>" + escapeHtml(fmtDate(item.date)) + "</span>" +
      "<span>•</span>" +
      "<span>Релевантность " + Math.round(item.relevance * 100) + "%</span>" +
      "</div>" +
      "</div>" +
      '<span class="badge ' + kindBadgeClass(item.kind) + '">' + kindRu(item.kind) + "</span>" +
      "</div>" +
      '<div class="preview-sub">Почему важно именно вам: ' +
      escapeHtml((item.why_for_you || []).join(" • ")) +
      "</div>" +
      '<div class="footer-note">Источник: ' + escapeHtml(item.source || "—") + "</div>";

    const feedback = document.createElement("div");
    feedback.className = "feedback-row";
    feedback.innerHTML =
      '<span class="footer-note">Полезно?</span>' +
      '<button class="btn btn-ghost btn-sm" data-useful="true">Да</button>' +
      '<button class="btn btn-ghost btn-sm" data-useful="false">Нет</button>' +
      '<span class="footer-note" data-feedback-note></span>';

    feedback.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", async () => {
        const useful = button.getAttribute("data-useful") === "true";
        const note = feedback.querySelector("[data-feedback-note]");
        try {
          await apiPost("/feedback", { insight_id: item.insight_id, useful: useful });
          note.textContent = "Спасибо, ответ отправлен";
          feedback.querySelectorAll("button").forEach((b) => (b.disabled = true));
        } catch (e) {
          note.textContent = "Не удалось отправить отзыв: " + e.message;
        }
      });
    });

    card.appendChild(link);
    card.appendChild(feedback);
    list.appendChild(card);
  });
}

load();
