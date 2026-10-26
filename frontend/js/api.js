/* Общий модуль фронтенда: адрес API, запросы, форматирование, шапка.
   Подключается первым на каждой странице. */

const API = "http://127.0.0.1:8000";
const API_FALLBACKS = ["http://localhost:8000"];

const COMPANY_KEY = "alfa.company";
const USER_KEY = "alfa.user";
const ROLE_KEY = "alfa.role";
const ROLES = {
  ceo: "Генеральный директор",
  cfo: "Финансовый директор",
  treasurer: "Руководитель казначейства",
  accountant: "Главный бухгалтер",
};

let _apiBase = API;
let _apiResolved = false;

/* ---------------------------------------------------------------- API --- */

async function resolveApi() {
  if (_apiResolved) return _apiBase;
  const candidates = [API].concat(API_FALLBACKS);
  for (const candidate of candidates) {
    try {
      const res = await fetch(candidate + "/health", { cache: "no-store" });
      if (res.ok) {
        _apiBase = candidate;
        _apiResolved = true;
        return _apiBase;
      }
    } catch (e) {
      /* пробуем следующий адрес */
    }
  }
  _apiResolved = true;
  return _apiBase;
}

async function apiGet(path) {
  const base = await resolveApi();
  const res = await fetch(base + path, { cache: "no-store" });
  if (!res.ok) {
    let detail = "";
    try { detail = (await res.json()).detail || ""; } catch (e) {}
    const error = new Error("HTTP " + res.status + " — " + path);
    error.status = res.status;
    error.detail = typeof detail === "string" ? detail : "";
    throw error;
  }
  return res.json();
}

async function apiPost(path, body) {
  const base = await resolveApi();
  const res = await fetch(base + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    let detail = "";
    try { detail = (await res.json()).detail || ""; } catch (e) {}
    const error = new Error("HTTP " + res.status + " — " + path);
    error.status = res.status;
    error.detail = typeof detail === "string" ? detail : "";
    throw error;
  }
  return res.json();
}

/* ------------------------------------------------------------ формат --- */

function fmtMoney(value, currency) {
  const amount = Number(value || 0);
  const code = currency || "RUB";
  try {
    return new Intl.NumberFormat("ru-RU", {
      style: "currency",
      currency: code,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch (e) {
    return amount.toFixed(0) + " " + code;
  }
}

function fmtNumber(value) {
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(Number(value || 0));
}

function fmtPercent(value) {
  return (Number(value || 0) * 100).toFixed(1).replace(".0", "") + "%";
}

/* Курсы приходят с бэкенда, чтобы не дублировать их на фронте. */
let _fx = null;

async function getFx() {
  if (_fx) return _fx;
  try {
    const data = await apiGet("/fx");
    _fx = { base: data.base || "RUB", rates: data.rates || { RUB: 1 } };
  } catch (e) {
    _fx = { base: "RUB", rates: { RUB: 1 } };
  }
  return _fx;
}

async function convertToBase(amount, currency) {
  const fx = await getFx();
  return Number(amount || 0) * (fx.rates[currency] || 1);
}

function fmtDate(value) {
  if (!value) return "—";
  const parts = String(value).split("-");
  if (parts.length === 3) return parts[2] + "." + parts[1] + "." + parts[0];
  return value;
}

function kindRu(kind) {
  if (kind === "opportunity") return "Возможность";
  if (kind === "neutral") return "Нейтрально";
  return "Риск";
}

function kindBadgeClass(kind) {
  if (kind === "opportunity") return "opp";
  if (kind === "neutral") return "neutral";
  return "";
}

function claimTypeRu(type) {
  if (type === "bank_view") return "Позиция Альфа-Банка";
  if (type === "ai_inference") return "Вывод ИИ";
  if (type === "fact") return "Факт";
  if (type === "ad") return "Банковский продукт";
  return type || "";
}

/* ---------------------------------------------------------- компания --- */

function getActiveCompanyId() {
  return localStorage.getItem(COMPANY_KEY) || "U_57706";
}

function getRole() {
  const saved = localStorage.getItem(ROLE_KEY);
  if (saved && ROLES[saved]) return saved;
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "{}").role || "cfo";
  } catch (e) {
    return "cfo";
  }
}

function setActiveCompanyId(id) {
  localStorage.setItem(COMPANY_KEY, id);
}

async function getCompanies() {
  return apiGet("/companies/demo");
}

/* ------------------------------------------------------------- шапка --- */

async function initChrome(onCompanyChange) {
  const select = document.getElementById("company-select");
  const userName = document.getElementById("user-name");
  const current = getActiveCompanyId();

  try {
    const companies = await getCompanies();
    if (companies.length && !companies.some((c) => c.id === current)) {
    setActiveCompanyId(companies[0].id);
    location.reload();
    return;
    }
    if (select) {
      select.innerHTML = "";
      companies.forEach((company) => {
        const option = document.createElement("option");
        option.value = company.id;
        option.textContent = company.name;
        if (company.id === current) option.selected = true;
        select.appendChild(option);
      });
      select.addEventListener("change", () => {
        setActiveCompanyId(select.value);
        /* страница строится заново, поэтому обработчики не копятся; разбор относится к прежнему клиенту, с него уходим в ленту */
        if (location.pathname.endsWith("/insight.html")) location.href = "insights.html";
        else location.reload();
      });
    }
  } catch (e) {
    if (select) {
      select.innerHTML = '<option value="' + current + '">Клиент недоступен</option>';
      select.disabled = true;
    }
  }

  try {
    const login = await apiPost("/auth/login", { login: "demo", password: "demo" });
    localStorage.setItem(USER_KEY, JSON.stringify(login));
    if (userName) {
      userName.textContent = login.user_name;
    }
  } catch (e) {
    if (userName) userName.textContent = "Демо-пользователь";
  }
  if (userName && !document.getElementById("role-select")) {
    const roleSelect = document.createElement("select");
    roleSelect.id = "role-select";
    roleSelect.title = "Роль";
    Object.keys(ROLES).forEach((key) => {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = ROLES[key];
      roleSelect.appendChild(option);
    });
    roleSelect.value = getRole();
    roleSelect.addEventListener("change", () => {
      localStorage.setItem(ROLE_KEY, roleSelect.value);
      location.reload();
    });
    userName.parentNode.insertBefore(roleSelect, userName);
  }
}

/* --------------------------------------------------------- сообщения --- */

function clearNode(el) {
  if (el) el.innerHTML = "";
}

function showError(el, error) {
  if (!el) return;
  let title = "Не удалось загрузить данные с сервера";
  let hint = 'Проверьте, что бэкенд запущен: <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noopener">http://127.0.0.1:8000/docs</a>';
  if (error && error.status === 503) {
    title = "Модель сейчас недоступна";
    hint = "Нет ключа LLM_API_KEY, закончился дневной лимит или модель не отвечает. Без ключа открываются только заранее подготовленные разборы для клиентов U_57706, U_9250, U_88715 и ролей «Финансовый директор» и «Генеральный директор».";
  } else if (error && error.status === 400 && error.detail) {
    title = "Не удалось обработать запрос";
    hint = escapeHtml(error.detail);
  } else if (error && error.status === 404) {
    title = "Данные не найдены";
    hint = "Проверьте клиента и роль в шапке страницы.";
  }
  el.innerHTML =
    '<div class="error-box">' +
    '<div class="error-title">' + title + "</div>" +
    '<div class="footer-note">' + hint + "</div>" +
    '<div class="footer-note">Детали: ' + escapeHtml(String(error && error.message ? error.message : error)) + "</div>" +
    "</div>";
}

function showEmpty(el, text) {
  if (!el) return;
  el.innerHTML = '<div class="empty">' + escapeHtml(text || "Нет данных") + "</div>";
}

function escapeHtml(text) {
  return String(text == null ? "" : text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
