# THIRD_PARTY_NOTICES

Список сторонних материалов, данных и сервисов, которые использует прототип команды GenAlpha (Альфа-Будущее Хакатон 2026). Тексты лицензий лежат в самих пакетах и на их страницах.

## Данные и материалы организаторов

- Файлы `backend/data/raw/df_Uid_data_hack.csv`, `df_Uid_payment_hack.csv`, `df_Fid_Uid_link_hack.csv`: выгрузки Альфа-Банка для хакатона (профили компаний, платежи, связи). Используются только в рамках хакатона, хранятся в приватном репозитории и не публикуются.
- Девять PDF-отчётов аналитики Альфа-Банка в `backend/data/raw/*.pdf`: Fixed Income Strategy 3Q26, Macro Insights Policy Rate, Inflation tracker, Gold digest, Бонд Бриф, Macro stat 1H26, Consumption, Russian Steels, 7M26. Предоставлены организаторами, лежат в приватном репозитории. По ним построен текстовый индекс (`backend/data/processed/alfa_pages.jsonl`), в карточках даются ссылки на документ и страницу.
- Описание кейса от организаторов используется как справочный материал. Аналитическая записка `analytical_paper_for_Alfa_Business.md` написана командой.

## Источники новостей

Новости берутся из открытых RSS-лент. Мы сохраняем заголовок, дату, ссылку и анонс или краткий текст (до 4000 символов), полные статьи не копируем. Права на материалы принадлежат их правообладателям, в карточках есть ссылка на первоисточник.

- Банк России (новости и события): cbr.ru
- Коммерсантъ (бизнес, экономика): kommersant.ru
- Ведомости (ТЭК, промышленность, транспорт, налоги, банки, недвижимость): vedomosti.ru
- ПРАЙМ: 1prime.ru
- Интерфакс (экономика): interfax.ru
- Правительство России: government.ru

Актуальный список включённых источников задан в `backend/data/reference/sources.yaml`.

## Языковые модели

Модели используются как сервис через OpenAI-совместимый API шлюза хакатона (`LLM_BASE_URL`). Веса моделей в репозиторий не входят, ключи выдаются участникам и жюри отдельно.

- `google/gemma-4-26b-a4b-it` (Google, Gemma Terms of Use): разметка новостей
- `deepseek/deepseek-v4.1-flash` (DeepSeek): основной разбор и чат
- `qwen/qwen3.6-35b-a3b` (Alibaba Cloud, Qwen): роль WRITER, задана в настройках, в текущей версии не вызывается
- `z-ai/glm-5.3-flash` (Z.ai, Zhipu AI): роль CRITIC, задана в настройках, в текущей версии не вызывается
- `moonshotai/kimi-k2.6` (Moonshot AI): запасная модель, вызывается, если основная не ответила
- `qwen/qwen3-vl-30b-a3b-instruct` (Alibaba Cloud, Qwen): роль VISION для таблиц и графиков из PDF, задана в настройках, в текущей версии не вызывается (текст отчётов распознан через Tesseract)


## Библиотеки Python

Файл `backend/requirements.txt`:

- fastapi 0.156.3 (MIT)
- starlette 1.10.0 (BSD-3-Clause)
- uvicorn 0.54.0 (BSD-3-Clause)
- pydantic 2.14.1 и pydantic_core 2.50.1 (MIT)
- annotated-types 0.8.0 и annotated-doc 0.0.5 (MIT)
- openai 3.36.1 (Apache-2.0)
- httpx 0.28.1, httpx2 2.16.0, httpcore 1.0.9, httpcore2 2.16.0 (BSD-3-Clause)
- anyio 4.15.1, h11 0.16.0, sniffio 1.3.1 (MIT)
- click 8.5.0 (BSD-3-Clause)
- idna 3.20 (BSD-3-Clause)
- certifi 2026.10.23 (MPL-2.0)
- truststore 0.10.5 (MIT)
- jiter 0.18.0 (MIT)
- numpy 2.5.4 (BSD-3-Clause)
- feedparser 6.0.14 и feedparser-sgmllib 2.1.0 (BSD-2-Clause)
- rank-bm25 0.2.2 (Apache-2.0)
- snowballstemmer 3.1.1 (BSD-3-Clause)
- PyYAML 6.0.3 (MIT)
- python-dotenv 1.2.4 (BSD-3-Clause)
- opentelemetry-api 1.45.1 (Apache-2.0)
- typing_extensions 4.16.0 (PSF-2.0) и typing-inspection 0.4.4 (MIT)

Файл `backend/requirements-ocr.txt`. Эти библиотеки нужны только для разового распознавания PDF, в работе сервиса не участвуют:

- PyMuPDF 2.0 (AGPL-3.0 либо коммерческая лицензия Artifex). Используется только офлайн для подготовки текста отчётов, в состав сервиса не входит.
- pytesseract 0.3.13 (Apache-2.0)
- Pillow 13.0.0 (MIT-CMU)
- Tesseract OCR, внешняя программа (Apache-2.0)

Версии зафиксированы в `backend/requirements.txt`, лицензии указаны по данным пакетов.

## Docker-образы

- `python:3.14-slim` (Python Software Foundation, PSF-2.0, плюс пакеты Debian со своими лицензиями)
- `nginx:1.27-alpine` (BSD-2-Clause, плюс пакеты Alpine Linux)

## Шрифты, логотип, оформление

- Шрифт Inter, подключается с Google Fonts (SIL Open Font License 1.1).
- Логотип Альфа-Банка `frontend/assets/alfa-logo.svg` является товарным знаком АО «Альфа-Банк». Файл добавлен командой только для того, чтобы показать встраивание прототипа в интерфейс Альфа-Бизнес в рамках хакатона.
- Сторонних иконок и иллюстраций в репозитории нет, оформление сделано средствами CSS.

## Смоделированные данные

Данные витрины интерфейса (счета, платежи, кредитные предложения, курсы валют, «уровень риска») смоделированы командой по профилю клиента, код в `frontend/ext/real_data.py`, `frontend/ext/demo_data.py` и `frontend/ext/analytics_ext.py`. Это не данные банка: так они описаны в README, а в интерфейсе пометка «смоделировано» стоит в строках платежей и кредитов.

## Готовые агентные системы

Мы не использовали готовые агентные системы и фреймворки (LangChain, LangGraph, AutoGen и подобные). Цикл агента, инструменты и проверки написаны командой.
