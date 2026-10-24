"""Launcher for the Alfa-Business Hackathon stack - lives next to the frontend.

Started by `start.bat` (or by the root `run_all.bat`, it delegates here).
The whole `frontend` folder is meant to be copied into the root of the team
repository: the backend is found automatically (usually `../backend`), and
missing endpoints are added on top of it from `ext/` without touching the
repository code.

  * creates the virtualenv and installs requirements (once),
  * frees the ports,
  * starts FastAPI (repo app + ext routes) and the static frontend server,
  * waits until both answer,
  * opens the browser,
  * streams the logs of both servers into this one console.

Ctrl+C stops everything.
"""

import ctypes
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent
ROOT = FRONTEND.parent
EXT_DIR = FRONTEND / "ext"

sys.path.insert(0, str(FRONTEND))

from ext.backend_locator import find_backend  # noqa: E402

BACKEND = find_backend(FRONTEND)

VENV_DIR = None
VENV_PY = None
REQUIREMENTS = None

BACK_PORT = 8000
FRONT_PORT = 5173
BACK_URL = "http://127.0.0.1:%d" % BACK_PORT
FRONT_URL = "http://127.0.0.1:%d" % FRONT_PORT
PAGE_URL = FRONT_URL + "/index.html"

# Автоперезапуск бэкенда при правке кода (можно выключить переменной окружения).
RELOAD = os.environ.get("ALFA_RELOAD", "1") != "0"

IS_WIN = os.name == "nt"

_children = []
_stop = threading.Event()


# --------------------------------------------------------------------------
# console
# --------------------------------------------------------------------------
def enable_utf8_console() -> None:
    """Make the Windows console show Cyrillic instead of mojibake."""
    if not IS_WIN:
        return
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def log(message: str = "", tag: str = "") -> None:
    stamp = time.strftime("%H:%M:%S")
    prefix = "[%s] " % tag if tag else ""
    sys.stdout.write("%s %s%s\n" % (stamp, prefix, message))
    sys.stdout.flush()


def fail(message: str) -> None:
    log("")
    log("!! %s" % message, "ОШИБКА")
    log("")
    wait_enter()
    sys.exit(1)


def wait_enter() -> None:
    """Keep the console open so the user can read the error."""
    if os.environ.get("ALFA_NO_PAUSE") == "1":
        return
    try:
        input("Нажмите Enter, чтобы закрыть окно... ")
    except Exception:
        time.sleep(10)


# --------------------------------------------------------------------------
# ports
# --------------------------------------------------------------------------
def pids_on_port(port: int) -> list:
    if not IS_WIN:
        return []
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            errors="replace",
            timeout=20,
        ).stdout
    except Exception:
        return []
    pids = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        if not parts[1].endswith(":%d" % port):
            continue
        if parts[3].upper() != "LISTENING":
            continue
        try:
            pid = int(parts[4])
        except ValueError:
            continue
        if pid not in pids:
            pids.append(pid)
    return pids


def free_port(port: int) -> None:
    pids = pids_on_port(port)
    for pid in pids:
        log("Освобождаю порт %d (PID %d)..." % (port, pid))
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if pids:
        time.sleep(0.6)

    # Windows отпускает сокет не мгновенно: без ожидания новый сервер может
    # занять порт, а запросы будут уходить в уже убитый процесс.
    deadline = time.time() + 15
    while time.time() < deadline:
        if not pids_on_port(port):
            return
        time.sleep(0.3)
    fail("Порт %d всё ещё занят после остановки процессов. Закрой программу, которая его держит." % port)


# --------------------------------------------------------------------------
# http
# --------------------------------------------------------------------------
def http_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 400
    except urllib.error.HTTPError as exc:
        return 200 <= exc.code < 400
    except Exception:
        return False


def wait_http(url: str, label: str, timeout: float = 90.0) -> bool:
    deadline = time.time() + timeout
    step = 0
    while time.time() < deadline:
        if _stop.is_set():
            return False
        if http_ok(url):
            log("%s отвечает: %s" % (label, url), "ГОТОВО")
            return True
        step += 1
        if step % 5 == 0:
            log("%s ещё не отвечает, жду... (%ds)" % (label, int(time.time() - (deadline - timeout))), "ЖДУ")
        time.sleep(1)
    return False


# --------------------------------------------------------------------------
# venv
# --------------------------------------------------------------------------
def ensure_venv() -> Path:
    if VENV_PY.exists():
        log("Виртуальное окружение найдено: %s" % VENV_DIR, "venv")
        return VENV_PY

    log("Создаю виртуальное окружение: %s" % VENV_DIR, "venv")
    result = subprocess.run(
        [sys.executable, "-m", "venv", str(VENV_DIR)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    if result.returncode != 0 or not VENV_PY.exists():
        fail("Не удалось создать виртуальное окружение.\n%s" % (result.stdout or "").strip())
    log("Готово.", "venv")
    return VENV_PY


def deps_installed(python_exe: Path) -> bool:
    result = subprocess.run(
        [str(python_exe), "-c", "import fastapi, uvicorn, pydantic, starlette"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def ensure_deps(python_exe: Path) -> None:
    if deps_installed(python_exe):
        log("Зависимости уже установлены.", "deps")
        return

    if REQUIREMENTS is None or not REQUIREMENTS.exists():
        fail("Не нашёл requirements.txt бэкенда (ожидал %s)." % (BACKEND / "requirements.txt"))

    log("Устанавливаю зависимости из %s (первый запуск, 1-3 минуты)..." % REQUIREMENTS, "deps")
    result = subprocess.run(
        [str(python_exe), "-m", "pip", "install", "--upgrade", "pip", "-q"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    if result.returncode != 0:
        log("pip upgrade не удался, продолжаю.", "deps")

    result = subprocess.run(
        [str(python_exe), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    if result.returncode != 0:
        fail("Не удалось установить зависимости:\n%s" % (result.stdout or "").strip()[-2000:])
    log("Зависимости установлены.", "deps")


def preflight(python_exe: Path) -> None:
    """Проверяю, что приложение команды импортируется и ext к нему цепляется."""
    log("Проверяю связку «бэкенд репозитория + ext»...", "БЭК")
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(FRONTEND) + (os.pathsep + existing if existing else "")
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [str(python_exe), "-c", "import ext.app_ext as m; print(m.BACKEND)"],
        cwd=str(BACKEND),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        fail(
            "Бэкенд не запускается вместе с ext.\n"
            "Полный вывод:\n%s" % (result.stdout or "").strip()[-3000:]
        )
    log("Связка в порядке.", "БЭК")


# --------------------------------------------------------------------------
# servers
# --------------------------------------------------------------------------
def pump(stream, tag: str) -> None:
    try:
        for raw in iter(stream.readline, ""):
            if not raw:
                break
            line = raw.rstrip("\r\n")
            if line:
                log(line, tag)
    except Exception:
        pass
    finally:
        try:
            stream.close()
        except Exception:
            pass


def spawn(args, cwd: Path, tag: str) -> subprocess.Popen:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"

    creationflags = 0
    if IS_WIN:
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    process = subprocess.Popen(
        args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
        creationflags=creationflags,
    )
    _children.append(process)
    threading.Thread(target=pump, args=(process.stdout, tag), daemon=True).start()
    return process


def stop_children() -> None:
    _stop.set()
    for process in _children:
        if process.poll() is not None:
            continue
        try:
            if IS_WIN:
                # /T kills the whole tree (uvicorn --reload spawns a child)
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                process.terminate()
        except Exception:
            pass
    time.sleep(0.8)
    for process in _children:
        if process.poll() is not None:
            continue
        try:
            process.kill()
        except Exception:
            pass
    for process in _children:
        try:
            process.wait(timeout=5)
        except Exception:
            pass


# --------------------------------------------------------------------------
# check mode
# --------------------------------------------------------------------------
CHECK_PAGES = [
    "/index.html",
    "/insights.html",
    "/insight.html",
    "/accounts.html",
    "/payments.html",
    "/credits.html",
    "/analytics.html",
    "/compare.html",
    "/css/style.css",
    "/js/api.js",
]

CHECK_API = [
    "/health",
    "/fx",
    "/companies/demo",
    "/companies/U_demo1",
    "/companies/U_demo1/feed",
    "/companies/U_demo1/accounts",
    "/companies/U_demo1/payments",
    "/companies/U_demo1/credits",
    "/companies/U_demo1/analytics",
    "/insights/ins_001",
    "/insights/ins_001/trace",
    "/compare?company_a=U_demo1&company_b=U_demo2",
]


def verify_pages() -> list:
    problems = []
    for path in CHECK_API:
        url = BACK_URL + path
        try:
            with urllib.request.urlopen(url, timeout=8) as response:
                response.read()
                log("API  %s -> %s" % (path, response.status), "ПРОВЕРКА")
        except Exception as exc:
            problems.append("API не ответил: %s (%s)" % (url, exc))

    for path in CHECK_PAGES:
        url = FRONT_URL + path
        try:
            with urllib.request.urlopen(url, timeout=8) as response:
                body = response.read()
                body.decode("utf-8")
                ctype = response.headers.get("Content-Type", "")
                if "charset=utf-8" not in ctype.lower():
                    problems.append("Страница отдана без charset=utf-8: %s" % path)
                log("СТР %s -> %s, %d bytes" % (path, response.status, len(body)), "ПРОВЕРКА")
        except Exception as exc:
            problems.append("Страница не ответила: %s (%s)" % (url, exc))
    return problems


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    global BACKEND, VENV_DIR, VENV_PY, REQUIREMENTS

    check_only = "--check" in sys.argv[1:]
    enable_utf8_console()

    log("=" * 66, "СТАРТ")
    log(" Alfa-Business Hackathon - лаунчер", "СТАРТ")
    log("=" * 66, "СТАРТ")
    log("Фронтенд    : %s" % FRONTEND)
    log("Бэкенд      : %s" % (BACKEND or "не найден"))
    log("API         : %s" % BACK_URL)
    log("Сайт        : %s" % FRONT_URL)
    log("")

    if not (FRONTEND / "index.html").exists():
        fail("Фронтенд не найден: %s" % (FRONTEND / "index.html"))

    if BACKEND is None:
        fail(
            "Не нашёл папку бэкенда.\n"
            "Положи папку frontend в корень репозитория, где лежит backend/app/main.py,\n"
            "или укажи путь переменной окружения ALFA_BACKEND."
        )
    if not (BACKEND / "app" / "main.py").exists():
        fail("Бэкенд не найден: %s" % (BACKEND / "app" / "main.py"))
    if not EXT_DIR.exists():
        fail("Не найдена папка ext рядом с лаунчером: %s" % EXT_DIR)

    VENV_DIR = BACKEND / ".venv"
    VENV_PY = VENV_DIR / "Scripts" / "python.exe"
    REQUIREMENTS = BACKEND / "requirements.txt"

    python_exe = ensure_venv()
    ensure_deps(python_exe)
    preflight(python_exe)

    log("Освобождаю порты %d и %d..." % (BACK_PORT, FRONT_PORT))
    free_port(BACK_PORT)
    free_port(FRONT_PORT)

    log("Запускаю бэкенд: приложение репозитория + ручки из ext", "БЭК")
    backend_args = [
        str(python_exe),
        "-m",
        "uvicorn",
        "ext.app_ext:app",
        "--app-dir",
        str(FRONTEND),
        "--host",
        "127.0.0.1",
        "--port",
        str(BACK_PORT),
    ]
    if RELOAD:
        backend_args += ["--reload", "--reload-dir", str(BACKEND), "--reload-dir", str(EXT_DIR)]
    backend_proc = spawn(backend_args, cwd=BACKEND, tag="БЭК")
    if not wait_http(BACK_URL + "/health", "Бэкенд", timeout=90):
        stop_children()
        fail("Бэкенд не поднялся. Смотри логи [БЭК] выше.")

    log("Запускаю фронтенд: serve.py --port %d" % FRONT_PORT, "ФРОНТ")
    frontend_proc = spawn(
        [str(python_exe), "serve.py", "--port", str(FRONT_PORT), "--host", "127.0.0.1"],
        cwd=FRONTEND,
        tag="ФРОНТ",
    )
    if not wait_http(FRONT_URL + "/index.html", "Фронтенд", timeout=30):
        stop_children()
        fail("Фронтенд не поднялся. Смотри логи [ФРОНТ] выше.")

    log("")
    log("=" * 66, "ГОТОВО")
    log(" Сайт        : %s" % PAGE_URL, "ГОТОВО")
    log(" API         : %s" % BACK_URL, "ГОТОВО")
    log(" Документация: %s/docs" % BACK_URL, "ГОТОВО")
    log("=" * 66, "ГОТОВО")
    log("Логи бэкенда и фронтенда идут ниже. Остановить всё - Ctrl+C.", "ГОТОВО")
    log("")

    if os.environ.get("ALFA_NO_BROWSER") == "1":
        log("Браузер не открываю (ALFA_NO_BROWSER=1). Адрес: %s" % PAGE_URL, "ГОТОВО")
    else:
        try:
            webbrowser.open(PAGE_URL)
            log("Браузер открыт: %s" % PAGE_URL, "ГОТОВО")
        except Exception as exc:
            log("Не удалось открыть браузер автоматически (%s). Откройте вручную: %s" % (exc, PAGE_URL), "ГОТОВО")

    if check_only:
        log("")
        log("Режим --check: проверяю страницы...", "ПРОВЕРКА")
        problems = verify_pages()
        log("")
        if problems:
            for problem in problems:
                log("!! %s" % problem, "ПРОВЕРКА")
            stop_children()
            free_port(BACK_PORT)
            free_port(FRONT_PORT)
            wait_enter()
            return 1
        log("Все страницы отвечают.", "ПРОВЕРКА")
        stop_children()
        free_port(BACK_PORT)
        free_port(FRONT_PORT)
        log("Остановлено.", "ПРОВЕРКА")
        return 0

    try:
        while not _stop.is_set():
            if backend_proc.poll() is not None:
                fail("Бэкенд неожиданно завершился (код %s). Смотри логи [БЭК]." % backend_proc.returncode)
            if frontend_proc.poll() is not None:
                fail("Фронтенд неожиданно завершился (код %s). Смотри логи [ФРОНТ]." % frontend_proc.returncode)
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        log("")
        log("Останавливаю серверы...", "СТОП")
        stop_children()
        free_port(BACK_PORT)
        free_port(FRONT_PORT)
        log("Остановлено. Можно закрыть окно.", "СТОП")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        stop_children()
        raise SystemExit(0)
    except SystemExit:
        raise
    except Exception:
        import traceback

        enable_utf8_console()
        log("")
        log("Непредвиденная ошибка лаунчера:", "ОШИБКА")
        for line in traceback.format_exc().splitlines():
            log("  " + line)
        log("")
        wait_enter()
        stop_children()
        raise SystemExit(1)
