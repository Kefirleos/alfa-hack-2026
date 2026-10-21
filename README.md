# alfa-hack-2026

(Пока для запуска не требуется, игнорируйте строчку ниже)

Скопируйте .env.example в .env и задайте API-ключ LLM_API_KEY=

## Запуск бэкенда

Требуется версия Python 3.11 и выше, проверить это можно командой `python --version`

1. Клонируйте репозиторий на компьютер: `git clone https://github.com/Kefirleos/alfa-hack-2026`
2. Перейдите в папку: `cd alfa-hack-2026/backend`
3. Создайте окружение: `python -m venv .venv`
4. Включите его в любой консоли: (советую Git Bash)
- В Git Bash: `source .venv/Scripts/activate`
- В PowerShell: `.venv\Scripts\Activate.ps1`
5. Установите библиотеки: `pip install -r requirements.txt`
6. Запустите локально: `uvicorn app.main:app --reload` (в Git Bash Ctrl+C останавливает процессы в терминале, скопируйте ссылку ниже в шаге 7)
7. Откройте в браузере `http://127.0.0.1:8000/docs`

При каждом запуске терминала повторяйте шаг 4, шаги 3 и 5 нужны единожды, команду из 6 шага стоит запускать в папке backend.
