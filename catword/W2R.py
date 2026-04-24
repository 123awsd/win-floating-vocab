import ctypes.util
import os
import json
import random
import re
import signal
import shutil
import subprocess
import sys
import threading
import time
import traceback
from datetime import date
from datetime import datetime
from pathlib import Path

try:
    import pyperclip
except ImportError:
    pyperclip = None

QT_BACKEND = "PySide6"
_pyside6_import_error = None
try:
    from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, Qt, QTimer
    from PySide6.QtGui import (
        QAction,
        QColor,
        QCursor,
        QFont,
        QFontDatabase,
        QFontMetrics,
        QIcon,
        QPainter,
        QPainterPath,
        QPen,
        QPixmap,
    )
    from PySide6.QtWidgets import (
        QApplication,
        QDialog,
        QFormLayout,
        QGraphicsDropShadowEffect,
        QGraphicsOpacityEffect,
        QGridLayout,
        QHBoxLayout,
        QInputDialog,
        QLayout,
        QLabel,
        QMenu,
        QPushButton,
        QSlider,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
    )
except ImportError as _exc_pyside6:
    _pyside6_import_error = _exc_pyside6
    QT_BACKEND = "PyQt5"
    try:
        from PyQt5.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, Qt, QTimer
        from PyQt5.QtGui import (
            QColor,
            QCursor,
            QFont,
            QFontDatabase,
            QFontMetrics,
            QIcon,
            QPainter,
            QPainterPath,
            QPen,
            QPixmap,
        )
        from PyQt5.QtWidgets import (
            QAction,
            QApplication,
            QDialog,
            QFormLayout,
            QGraphicsDropShadowEffect,
            QGraphicsOpacityEffect,
            QGridLayout,
            QHBoxLayout,
            QInputDialog,
            QLayout,
            QLabel,
            QMenu,
            QPushButton,
            QSlider,
            QSizePolicy,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        try:
            _base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
            _boot_log = _base / "startup_error.log"
            with open(_boot_log, "a", encoding="utf-8") as _f:
                _f.write(
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"Qt import failed. PySide6={_pyside6_import_error!r}; PyQt5={exc!r}\n"
                )
        except OSError:
            pass
        raise SystemExit(
            "Qt runtime missing. Install PySide6 or PyQt5. "
            f"PySide6 error: {_pyside6_import_error!r}; "
            f"PyQt5 error: {exc!r}"
        ) from exc


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "startup_error.log"
ASSET_DIR = BASE_DIR / "assets" / "cattoon_v1"
CAT_DIR = ASSET_DIR / "cats"
APP_ICON_RELS = (
    Path("assets") / "app_icon" / "app.png",
    Path("assets") / "app_icon" / "app.ico",
)
DEFAULT_LEXICON_FILE = "word_list.txt"
FAVORITES_FILE = "favorites.txt"
MIN_WINDOW_HEIGHT = 72
MAX_WINDOW_HEIGHT = 360
MIN_WINDOW_WIDTH = 180
MAX_WINDOW_WIDTH = 960


def _p(name: str) -> str:
    return str(BASE_DIR / name)


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _is_linux() -> bool:
    return sys.platform.startswith("linux")


def _is_macos() -> bool:
    return sys.platform == "darwin"


def _has_shared_library(*names: str) -> bool:
    for name in names:
        if name and ctypes.util.find_library(name):
            return True
    return False


def _detect_missing_linux_runtime_packages() -> list[str]:
    if not _is_linux():
        return []
    qt_platform = (os.environ.get("QT_QPA_PLATFORM") or "").strip().lower()
    if qt_platform and qt_platform not in {"xcb", "wayland", "wayland-egl"}:
        return []
    use_xcb = qt_platform in {"", "xcb"} and bool(os.environ.get("DISPLAY"))
    if not use_xcb:
        return []
    missing = []
    if not _has_shared_library("xcb-cursor", "xcb_cursor"):
        missing.append("libxcb-cursor0")
    if not _has_shared_library("xkbcommon-x11"):
        missing.append("libxkbcommon-x11-0")
    return missing


def _log(message: str):
    try:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {message}\n")
    except OSError:
        pass


def _parse_bool(text: str, default: bool = False) -> bool:
    if text is None:
        return default
    value = str(text).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


waitTime = 2.0
default_lexicon = ""
file = _p(DEFAULT_LEXICON_FILE)
bgcolor = "#FFEFD6"
fgcolor = "#4D3B36"
word_color = fgcolor
counter_color = "#F7F0E8"
ENGfont = "Consolas"
CHNfont = "Sans Serif"
alpha = 0.96
isFullScreen = 0
auto_speak = 0
order = 0
handmode = 1

ui_theme = "cattoon_v1"
window_radius = 22
font_scale = 1.0

themeColors = {
    "奶油猫": ["#FFEFD6", "#4D3B36"],
    "薄荷猫": ["#E8FFF2", "#2F4A3F"],
    "天空猫": ["#EAF5FF", "#2A4059"],
}
DEFAULT_THEME_COLORS = dict(themeColors)

fonts = {
    "通用": ["Monospace", "Sans Serif"],
    "Ubuntu": ["DejaVu Sans Mono", "Noto Sans CJK SC"],
    "宋体": ["Consolas", "宋体"],
    "微软雅黑": ["Consolas", "微软雅黑"],
    "苹方": ["Consolas", "苹方 常规"],
    "汉仪意宋": ["Consolas", "汉仪意宋简 Regular"],
}
DEFAULT_FONTS = dict(fonts)

alphaValues = {
    "100%": 1.0,
    "95%": 0.95,
    "90%": 0.9,
    "85%": 0.85,
    "80%": 0.8,
    "75%": 0.75,
    "70%": 0.7,
    "60%": 0.6,
    "50%": 0.5,
}
DEFAULT_ALPHA_VALUES = dict(alphaValues)

lexicon = {}
words = []
word_items = []
word_index = 0

_tts_worker_started = False
_tts_lock = threading.Lock()
_tts_error_hint_shown = False
_tts_latest_text = ""
_tts_request_event = threading.Event()
_tts_current_proc = None
_tts_current_backend = None

_ENG_TTS_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\s\-\+'/]*$")
_HAS_LETTER_PATTERN = re.compile(r"[A-Za-z]")
DAILY_PROGRESS_FILE = BASE_DIR / "daily_progress.json"
daily_progress_date = ""
daily_progress_count = 0
EMPTY_DETAIL_VALUES = {"", "-", "—", "–", "None", "none", "null", "NULL", "N/A", "n/a"}


def _bundled_roots():
    roots = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))
    roots.append(BASE_DIR / "_internal")
    uniq = []
    seen = set()
    for r in roots:
        key = str(r).lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq


def bootstrap_runtime_files():
    if not getattr(sys, "frozen", False):
        return
    for name in ("preference.ini", "themes.ini", "fonts.ini"):
        dst = BASE_DIR / name
        if dst.exists():
            continue
        for root in _bundled_roots():
            src = root / name
            if src.exists():
                try:
                    shutil.copy2(src, dst)
                except OSError:
                    pass
                break

    dst_assets = BASE_DIR / "assets"
    if not dst_assets.exists():
        for root in _bundled_roots():
            src_assets = root / "assets"
            if src_assets.exists():
                try:
                    shutil.copytree(src_assets, dst_assets)
                except OSError:
                    pass
                break
    for rel_path in APP_ICON_RELS:
        dst_icon = BASE_DIR / rel_path
        if dst_icon.exists():
            continue
        for root in _bundled_roots():
            src_icon = root / rel_path
            if src_icon.exists():
                try:
                    dst_icon.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_icon, dst_icon)
                except OSError:
                    pass
                break


def resolve_app_icon_path() -> Path | None:
    candidates = [BASE_DIR / rel_path for rel_path in APP_ICON_RELS]
    for root in _bundled_roots():
        for rel_path in APP_ICON_RELS:
            candidates.append(root / rel_path)
    for p in candidates:
        if p.exists():
            return p
    return None


def _is_english_word(text):
    text = (text or "").strip()
    return bool(_ENG_TTS_PATTERN.fullmatch(text)) and bool(_HAS_LETTER_PATTERN.search(text))


def _normalize_tts_text(text: str) -> str:
    text = (text or "").replace("_", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _today_str() -> str:
    return date.today().isoformat()


def _sync_daily_progress_date() -> None:
    global daily_progress_date, daily_progress_count
    today = _today_str()
    if daily_progress_date != today:
        daily_progress_date = today
        daily_progress_count = 0


def load_daily_progress() -> None:
    global daily_progress_date, daily_progress_count
    daily_progress_date = _today_str()
    daily_progress_count = 0
    try:
        with open(DAILY_PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            daily_progress_date = str(data.get("date", daily_progress_date))
            daily_progress_count = int(data.get("count", 0))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    _sync_daily_progress_date()


def save_daily_progress() -> None:
    _sync_daily_progress_date()
    payload = {"date": daily_progress_date, "count": int(max(0, daily_progress_count))}
    try:
        with open(DAILY_PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except OSError:
        pass


def increment_daily_progress(step: int = 1) -> int:
    global daily_progress_count
    _sync_daily_progress_date()
    daily_progress_count = max(0, int(daily_progress_count) + int(step))
    save_daily_progress()
    return daily_progress_count


def reset_daily_progress() -> int:
    global daily_progress_count
    _sync_daily_progress_date()
    daily_progress_count = 0
    save_daily_progress()
    return daily_progress_count


def get_daily_progress_count() -> int:
    _sync_daily_progress_date()
    return int(daily_progress_count)


def _font_database_families() -> set[str]:
    try:
        return set(QFontDatabase.families())
    except TypeError:
        return set(QFontDatabase().families())


def _first_installed_font(candidates, fallback: str | None = None) -> str:
    families = _font_database_families()
    for name in candidates:
        if name in families:
            return name
    return fallback or QFont().defaultFamily()


def _default_mono_font_family() -> str:
    return _first_installed_font(
        [
            "Consolas",
            "JetBrains Mono",
            "DejaVu Sans Mono",
            "Liberation Mono",
            "Noto Sans Mono CJK SC",
            "Monospace",
        ]
    )


def _default_cjk_font_family() -> str:
    return _first_installed_font(
        [
            "Microsoft YaHei UI",
            "Microsoft YaHei",
            "微软雅黑",
            "Noto Sans CJK SC",
            "Noto Sans SC",
            "Source Han Sans SC",
            "WenQuanYi Zen Hei",
            "DejaVu Sans",
            "Sans Serif",
        ]
    )


def normalize_runtime_fonts() -> None:
    global ENGfont, CHNfont
    families = _font_database_families()
    mono = _default_mono_font_family()
    sans = _default_cjk_font_family()
    if ENGfont not in families:
        ENGfont = mono
    if CHNfont not in families:
        CHNfont = sans
    fonts["通用"] = [mono, sans]
    fonts["Ubuntu"] = [mono, sans]


def _build_tts_script():
    return (
        "$ErrorActionPreference='Stop';"
        "$text=$env:W2R_TTS_TEXT;"
        "if($text -cmatch '^[A-Z]{2,6}$'){ $text = (($text.ToCharArray()) -join ' ') };"
        "$v=New-Object -ComObject SAPI.SpVoice;"
        "$voices=$v.GetVoices();"
        "for($i=0;$i -lt $voices.Count;$i++){"
        "  $vi=$voices.Item($i);"
        "  $d=$vi.GetDescription();"
        "  if($d -match 'English|en-US|en-GB'){ $v.Voice=$vi; break }"
        "};"
        "$v.Rate = -2;"
        "[void]$v.Speak($text);"
    )


def _tts_backend_hint() -> str:
    if _is_linux():
        return "Linux/Ubuntu 请安装 speech-dispatcher（spd-say）或 espeak-ng。"
    if _is_windows():
        return "Windows 需要 PowerShell 和系统语音组件。"
    if _is_macos():
        return "macOS 需要系统自带的 say 命令。"
    return "当前平台没有可用的朗读后端。"


def _build_windows_tts_command(text: str):
    script = _build_tts_script()
    env = os.environ.copy()
    env["W2R_TTS_TEXT"] = text
    return (
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        env,
        getattr(subprocess, "CREATE_NO_WINDOW", 0),
        "windows-sapi",
    )


def _build_tts_command(text: str):
    if _is_windows():
        return _build_windows_tts_command(text)
    if _is_macos() and shutil.which("say"):
        return (["say", text], None, 0, "macos-say")
    if _is_linux():
        if shutil.which("spd-say"):
            return (["spd-say", "-w", "-r", "-20", text], None, 0, "speech-dispatcher")
        if shutil.which("espeak-ng"):
            return (["espeak-ng", "-s", "140", text], None, 0, "espeak-ng")
        if shutil.which("espeak"):
            return (["espeak", "-s", "140", text], None, 0, "espeak")
    raise RuntimeError(_tts_backend_hint())


def _spawn_tts_process(text: str):
    cmd, env, creationflags, backend = _build_tts_command(text)
    proc = subprocess.Popen(
        cmd,
        creationflags=creationflags,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc, backend


def _stop_backend_speech(backend: str | None) -> None:
    if backend == "speech-dispatcher" and shutil.which("spd-say"):
        try:
            subprocess.run(
                ["spd-say", "-S"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except OSError:
            pass


def _stop_current_tts():
    global _tts_current_backend, _tts_current_proc
    with _tts_lock:
        proc = _tts_current_proc
        _tts_current_proc = None
        backend = _tts_current_backend
        _tts_current_backend = None
    _stop_backend_speech(backend)
    if not proc:
        return
    if proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=0.3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def _tts_worker_loop():
    global _tts_current_backend, _tts_error_hint_shown, _tts_current_proc
    while True:
        _tts_request_event.wait()
        _tts_request_event.clear()
        while True:
            with _tts_lock:
                text = _tts_latest_text
            if not text:
                break

            try:
                proc, backend = _spawn_tts_process(text)
            except Exception as exc:
                if not _tts_error_hint_shown:
                    _tts_error_hint_shown = True
                    print(f"[TTS] 朗读不可用：{exc}")
                break

            with _tts_lock:
                _tts_current_proc = proc
                _tts_current_backend = backend

            interrupted = False
            while proc.poll() is None:
                if _tts_request_event.is_set():
                    interrupted = True
                    _stop_current_tts()
                    _tts_request_event.clear()
                    break
                time.sleep(0.02)

            with _tts_lock:
                if _tts_current_proc is proc:
                    _tts_current_proc = None
                    _tts_current_backend = None

            if not interrupted:
                break


def _ensure_tts_worker():
    global _tts_worker_started
    with _tts_lock:
        if _tts_worker_started:
            return
        t = threading.Thread(target=_tts_worker_loop, daemon=True)
        t.start()
        _tts_worker_started = True


def speak_word(text: str) -> None:
    global _tts_latest_text
    text = _normalize_tts_text(text)
    if not _is_english_word(text):
        return
    _ensure_tts_worker()
    with _tts_lock:
        _tts_latest_text = text
    _tts_request_event.set()


def set_tts_enabled(flag: bool) -> None:
    global auto_speak
    auto_speak = 1 if flag else 0
    if not auto_speak:
        _stop_current_tts()


def loadLexiconByDir():
    lexicon.clear()
    ignore_stems = {"requirements", "使用说明", "startup_error"}
    for item in sorted(BASE_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not (item.is_file() and item.suffix.lower() == ".txt"):
            continue
        if item.stem in ignore_stems:
            continue
        if item.name.startswith("_"):
            continue
        if item.stat().st_size < 32:
            continue
        try:
            head = item.read_text(encoding="utf-8", errors="ignore")[:240]
        except OSError:
            continue
        # A lexicon line should usually contain a separator between term and meaning.
        if "\t" not in head and "|" not in head and " " not in head:
            continue
        if "使用说明" in head and "双击" in head:
            continue
        if "pip install" in head and "requirements" in item.name.lower():
            continue
        if item.is_file() and item.suffix.lower() == ".txt":
            lexicon[item.stem] = str(item)


def _load_theme_file(path: str, target: dict):
    try:
        with open(_p(path), "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            line = line.split("\n")[0]
            t = line.split(",")
            if len(t) >= 3:
                target[t[0]] = [t[1], t[2]]
    except FileNotFoundError:
        pass


def readConfig():
    global auto_speak, waitTime, order, ENGfont, CHNfont, bgcolor, fgcolor, alpha
    global word_color, counter_color
    global ui_theme, window_radius, font_scale, default_lexicon, file
    global themeColors, fonts, alphaValues
    if not isinstance(themeColors, dict):
        themeColors = dict(DEFAULT_THEME_COLORS)
    if not isinstance(fonts, dict):
        fonts = dict(DEFAULT_FONTS)
    if not isinstance(alphaValues, dict):
        alphaValues = dict(DEFAULT_ALPHA_VALUES)
    _load_theme_file("themes.ini", themeColors)
    _load_theme_file("fonts.ini", fonts)
    loadLexiconByDir()

    try:
        with open(_p("preference.ini"), "r", encoding="utf-8") as f:
            setting = [line.strip() for line in f.readlines() if line.strip()]
        if not setting:
            return

        settinglist = setting[0].split(",")
        if len(settinglist) >= 10:
            waitTime = max(0.5, float(settinglist[2]))
            order = 1 if int(float(settinglist[3])) else 0
            ENGfont = settinglist[4] or ENGfont
            CHNfont = settinglist[5] or CHNfont
            bgcolor = settinglist[6] or bgcolor
            fgcolor = settinglist[7] or fgcolor
            alpha = min(1.0, max(0.4, float(settinglist[8])))
            auto_speak = 1 if int(float(settinglist[9])) else 0

        extra_pairs = {}
        for extra_line in setting[1:]:
            if "=" in extra_line:
                k, v = extra_line.split("=", 1)
                extra_pairs[k.strip()] = v.strip()
        ui_theme = extra_pairs.get("ui_theme", ui_theme)
        window_radius = int(float(extra_pairs.get("window_radius", window_radius)))
        font_scale = float(extra_pairs.get("font_scale", font_scale))
        default_lexicon = extra_pairs.get("default_lexicon", default_lexicon).strip()
        word_color = extra_pairs.get("word_color", word_color or fgcolor).strip() or fgcolor
        counter_color = extra_pairs.get("counter_color", counter_color).strip() or "#F7F0E8"

        if default_lexicon and default_lexicon in lexicon:
            file = lexicon[default_lexicon]
    except OSError:
        pass
    except ValueError:
        pass


def saveConfig(geometry_str: str, fs: int):
    global default_lexicon
    if file:
        file_path = Path(file)
        if file_path.exists():
            default_lexicon = file_path.stem

    with open(_p("preference.ini"), "w", encoding="utf-8") as f:
        f.write(
            ",".join(
                [
                    geometry_str,
                    str(fs),
                    str(waitTime),
                    str(order),
                    str(ENGfont),
                    str(CHNfont),
                    str(bgcolor),
                    str(fgcolor),
                    str(alpha),
                    str(auto_speak),
                ]
            )
            + "\n"
        )
        f.write(f"ui_theme={ui_theme}\n")
        f.write(f"window_radius={window_radius}\n")
        f.write(f"font_scale={font_scale}\n")
        f.write(f"default_lexicon={default_lexicon}\n")
        f.write(f"word_color={word_color}\n")
        f.write(f"counter_color={counter_color}\n")


def _clean_detail_text(text: str) -> str:
    value = str(text or "").strip()
    return "" if value in EMPTY_DETAIL_VALUES else value


def _split_word_aliases(text: str) -> list[str]:
    source = str(text or "").strip()
    if not source:
        return []
    aliases = [part.strip() for part in source.split("/") if part.strip()]
    return aliases or [source]


def _build_word_entry(
    word_text: str,
    meaning_text: str,
    pos_text: str = "",
    example_text: str = "",
    extra_text: str = "",
    category_text: str = "",
):
    aliases = _split_word_aliases(word_text)
    meaning = _clean_detail_text(meaning_text)
    if not aliases or not meaning:
        return None
    primary = aliases[0]
    return {
        "word": primary,
        "display_word": " / ".join(aliases),
        "aliases": aliases,
        "pos": _clean_detail_text(pos_text),
        "meaning": meaning,
        "example": _clean_detail_text(example_text),
        "extra": _clean_detail_text(extra_text),
        "category": _clean_detail_text(category_text),
    }


def _format_entry_meta(entry: dict) -> str:
    parts = []
    if entry.get("pos"):
        parts.append(entry["pos"])
    if entry.get("category"):
        parts.append(entry["category"])
    return " · ".join(parts)


def _format_entry_detail(entry: dict) -> str:
    lines = [entry.get("display_word") or entry.get("word") or ""]
    if entry.get("pos"):
        lines.append(f"词性: {entry['pos']}")
    if entry.get("meaning"):
        lines.append(f"词义: {entry['meaning']}")
    if entry.get("example"):
        lines.append(f"例句: {entry['example']}")
    if entry.get("extra"):
        lines.append(f"拓展: {entry['extra']}")
    if entry.get("category"):
        lines.append(f"分类: {entry['category']}")
    return "\n".join(line for line in lines if line)


def _empty_entry(word_text: str, meaning_text: str):
    return {
        "word": word_text,
        "display_word": word_text,
        "aliases": [word_text] if word_text else [],
        "pos": "",
        "meaning": meaning_text,
        "example": "",
        "extra": "",
        "category": "",
    }


def _parse_words_from_file(file_path: str):
    loaded = []
    current_category = ""
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line in {"===", "+++", "---"}:
                continue

            entry = None

            # my-ielts source format: word|pos|meaning|example|extra
            if "|" in line:
                parts = [part.strip() for part in line.split("|")]
                entry = _build_word_entry(
                    parts[0] if len(parts) > 0 else "",
                    parts[2] if len(parts) > 2 else "",
                    parts[1] if len(parts) > 1 else "",
                    parts[3] if len(parts) > 3 else "",
                    parts[4] if len(parts) > 4 else "",
                    current_category,
                )
            elif "\t" in line:
                # Rich TAB format:
                # word <TAB> pos <TAB> meaning <TAB> example <TAB> extra <TAB> category
                parts = [part.strip() for part in line.split("\t")]
                if len(parts) >= 3:
                    entry = _build_word_entry(
                        parts[0],
                        parts[2],
                        parts[1],
                        parts[3] if len(parts) > 3 else "",
                        parts[4] if len(parts) > 4 else "",
                        parts[5] if len(parts) > 5 else current_category,
                    )
                elif len(parts) >= 2:
                    entry = _build_word_entry(parts[0], parts[1], category_text=current_category)
            else:
                # Backward compatibility for legacy files: term + whitespace + meaning.
                pre = line.split(maxsplit=1)
                if len(pre) >= 2:
                    entry = _build_word_entry(pre[0], pre[1], category_text=current_category)
                else:
                    current_category = line
                    continue

            if entry is not None:
                loaded.append(entry)
    return loaded


def getWord():
    global file, words, word_items, word_index, default_lexicon

    def _safe_exists(path_text: str) -> bool:
        try:
            return Path(path_text).exists()
        except (OSError, ValueError, TypeError):
            return False

    if not lexicon:
        loadLexiconByDir()
    if not lexicon:
        words = []
        word_items = []
        return

    if not _safe_exists(file):
        if default_lexicon and default_lexicon in lexicon:
            file = lexicon[default_lexicon]
        else:
            file = next(iter(lexicon.values()))
    _log(f"getWord: selected file={file}")

    try:
        words = _parse_words_from_file(file)
    except (OSError, UnicodeDecodeError):
        if default_lexicon and default_lexicon in lexicon:
            file = lexicon[default_lexicon]
        else:
            file = next(iter(lexicon.values()))
        words = _parse_words_from_file(file)

    # Fallback: if selected file is not a real lexicon, switch to the first non-empty lexicon.
    if not words:
        for name, candidate in lexicon.items():
            try:
                parsed = _parse_words_from_file(candidate)
            except (OSError, UnicodeDecodeError):
                continue
            if parsed:
                file = candidate
                default_lexicon = name
                words = parsed
                _log(f"getWord: fallback switched to file={file}")
                break

    default_lexicon = Path(file).stem
    word_items = list(words)
    word_index = 0
    _log(f"getWord: final count={len(word_items)}")


class CatPopup(QDialog):
    def __init__(self, parent: QWidget, title: str, content: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)
        self.resize(280, 140)

        card = QWidget(self)
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(10)

        t_label = QLabel(title)
        t_label.setObjectName("title")
        m_label = QLabel(content)
        m_label.setWordWrap(True)
        m_label.setObjectName("message")
        cat_label = QLabel("/\\_/\\  (=^.^=)")
        cat_label.setObjectName("cat")

        card_layout.addWidget(t_label)
        card_layout.addWidget(m_label)
        card_layout.addWidget(cat_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(card)

        self.setStyleSheet(
            """
            #card {
                background: #FFF7EC;
                border: 2px solid #F2C89B;
                border-radius: 18px;
            }
            #title {
                color: #6A4B3A;
                font-size: 15px;
                font-weight: 700;
            }
            #message {
                color: #6A4B3A;
                font-size: 13px;
            }
            #cat {
                color: #D58A62;
                font-family: monospace;
                font-size: 13px;
            }
            """
        )

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 7)
        shadow.setColor(QColor(0, 0, 0, 80))
        card.setGraphicsEffect(shadow)

        self.opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)
        self.anim = QPropertyAnimation(self.opacity, b"opacity", self)
        self.anim.setDuration(220)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

        QTimer.singleShot(2400, self.close)

    def showEvent(self, event):
        super().showEvent(event)
        self.anim.start()


class WordDetailDialog(QDialog):
    def __init__(self, parent: QWidget, entry: dict):
        super().__init__(parent)
        self.setWindowTitle("词条详情")
        self.setModal(False)
        self.resize(520, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(entry.get("display_word") or entry.get("word") or "")
        title_font = QFont(ENGfont, 18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setWordWrap(True)
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignTop | Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)

        def add_row(label_text: str, value: str):
            value = (value or "").strip()
            if not value:
                return
            label = QLabel(label_text)
            value_label = QLabel(value)
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form.addRow(label, value_label)

        add_row("词性", entry.get("pos", ""))
        add_row("词义", entry.get("meaning", ""))
        add_row("例句", entry.get("example", ""))
        add_row("拓展", entry.get("extra", ""))
        add_row("分类", entry.get("category", ""))
        layout.addLayout(form)

        actions = QHBoxLayout()
        actions.addStretch(1)
        copy_btn = QPushButton("复制全部")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(_format_entry_detail(entry)))
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(copy_btn)
        actions.addWidget(close_btn)
        layout.addLayout(actions)

        self.setStyleSheet(
            """
            QDialog {
                background: #FFF7EC;
                color: #6A4B3A;
            }
            QLabel {
                color: #6A4B3A;
            }
            QPushButton {
                background: #FFE7CC;
                border: 1px solid #E6B082;
                border-radius: 8px;
                padding: 6px 12px;
                color: #6A4B3A;
            }
            QPushButton:hover {
                background: #FFD9B2;
            }
            """
        )


class CuteColorDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, initial_hex: str, cat_pixmaps=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.resize(360, 290)

        initial = QColor(initial_hex or "#F7F0E8")
        self._selected = initial if initial.isValid() else QColor("#F7F0E8")
        self._updating = False

        self.card = QWidget()
        self.card.setObjectName("card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        title_label = QLabel(title + "  (RGB)")
        title_label.setObjectName("title")
        cat_pixmaps = [p for p in (cat_pixmaps or []) if p is not None and not p.isNull()]
        top_row.addWidget(title_label, 1)

        self.preview = QLabel("")
        self.preview.setFixedHeight(34)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setObjectName("preview")

        self.r_slider = self._build_slider()
        self.g_slider = self._build_slider()
        self.b_slider = self._build_slider()
        self.r_value = QLabel("0")
        self.g_value = QLabel("0")
        self.b_value = QLabel("0")
        self.r_slider.valueChanged.connect(lambda v: self._on_slider_changed("R", v))
        self.g_slider.valueChanged.connect(lambda v: self._on_slider_changed("G", v))
        self.b_slider.valueChanged.connect(lambda v: self._on_slider_changed("B", v))

        rgb_grid = QGridLayout()
        rgb_grid.setHorizontalSpacing(8)
        rgb_grid.setVerticalSpacing(6)
        rgb_grid.addWidget(QLabel("R"), 0, 0)
        rgb_grid.addWidget(self.r_slider, 0, 1)
        rgb_grid.addWidget(self.r_value, 0, 2)
        rgb_grid.addWidget(QLabel("G"), 1, 0)
        rgb_grid.addWidget(self.g_slider, 1, 1)
        rgb_grid.addWidget(self.g_value, 1, 2)
        rgb_grid.addWidget(QLabel("B"), 2, 0)
        rgb_grid.addWidget(self.b_slider, 2, 1)
        rgb_grid.addWidget(self.b_value, 2, 2)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel_btn = QPushButton("取消")
        ok_btn = QPushButton("确定")
        cancel_btn.clicked.connect(self.reject)
        ok_btn.clicked.connect(self.accept)
        actions.addWidget(cancel_btn)
        actions.addWidget(ok_btn)

        card_layout.addLayout(top_row)
        card_layout.addWidget(self.preview)
        card_layout.addLayout(rgb_grid)
        card_layout.addLayout(actions)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.addWidget(self.card)

        self._cat_deco_labels = []
        self._cat_sources = []
        if cat_pixmaps:
            deco_count = 9
            for i in range(deco_count):
                lbl = QLabel(self.card)
                lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                base = cat_pixmaps[i % len(cat_pixmaps)]
                self._cat_sources.append(base)
                lbl.lower()
                self._cat_deco_labels.append(lbl)

        self.setStyleSheet(
            """
            #card {
                background: #FFF7EC;
                border: 2px solid #F2C89B;
                border-radius: 18px;
            }
            #title {
                color: #6A4B3A;
                font-size: 15px;
                font-weight: 700;
            }
            #preview {
                border: 2px solid #E6B082;
                border-radius: 10px;
                color: #6A4B3A;
                background: #FFFFFF;
                font-family: monospace;
            }
            QSlider::groove:horizontal {
                border: 1px solid #E8C8A9;
                height: 8px;
                background: #FFFDF9;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #E6B082;
                border: 1px solid #C98955;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QPushButton {
                background: #FFE7CC;
                border: 1px solid #E6B082;
                border-radius: 8px;
                padding: 5px 12px;
                color: #6A4B3A;
            }
            QPushButton:hover {
                background: #FFD9B2;
            }
            """
        )

        self._set_color(self._selected)
        self._layout_cat_decorations()

    def _build_slider(self):
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 255)
        slider.setSingleStep(1)
        return slider

    def _refresh_preview(self):
        hex_name = self._selected.name().upper()
        self.preview.setText("")
        self.preview.setStyleSheet(
            f"border: 2px solid #E6B082; border-radius: 10px; background: {hex_name}; color: #6A4B3A;"
        )

    def _set_color(self, color: QColor):
        if not color.isValid():
            return
        self._updating = True
        self._selected = color
        self.r_slider.setValue(color.red())
        self.g_slider.setValue(color.green())
        self.b_slider.setValue(color.blue())
        self.r_value.setText(str(color.red()))
        self.g_value.setText(str(color.green()))
        self.b_value.setText(str(color.blue()))
        self._refresh_preview()
        self._updating = False

    def _on_slider_changed(self, channel: str, value: int):
        if channel == "R":
            self.r_value.setText(str(value))
        elif channel == "G":
            self.g_value.setText(str(value))
        else:
            self.b_value.setText(str(value))
        if self._updating:
            return
        color = QColor(self.r_slider.value(), self.g_slider.value(), self.b_slider.value())
        self._set_color(color)

    @staticmethod
    def _make_translucent_cat(cat_pixmap: QPixmap, opacity: float, size: int = 34) -> QPixmap:
        src = cat_pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        out = QPixmap(src.size())
        out.fill(Qt.transparent)
        painter = QPainter(out)
        painter.setOpacity(max(0.0, min(1.0, opacity)))
        painter.drawPixmap(0, 0, src)
        painter.end()
        return out

    def _layout_cat_decorations(self):
        if not self._cat_deco_labels:
            return
        w = self.card.width()
        h = self.card.height()
        pad = 10
        grid_w = max(30, w - pad * 2)
        grid_h = max(30, h - pad * 2)
        cell_w = grid_w / 3.0
        cell_h = grid_h / 3.0
        icon_size = int(max(26, min(72, min(cell_w, cell_h) * 0.88)))

        for i, lbl in enumerate(self._cat_deco_labels):
            src = self._cat_sources[i % len(self._cat_sources)] if self._cat_sources else None
            if src is not None and not src.isNull():
                lbl.setPixmap(self._make_translucent_cat(src, 0.16, size=icon_size))
                lbl.resize(lbl.pixmap().size())
            row = i // 3
            col = i % 3
            cx = pad + col * cell_w + cell_w * 0.5
            cy = pad + row * cell_h + cell_h * 0.5
            x = int(cx - lbl.width() * 0.5)
            y = int(cy - lbl.height() * 0.5)
            x = max(pad, min(x, w - pad - lbl.width()))
            y = max(pad, min(y, h - pad - lbl.height()))
            lbl.move(x, y)
            lbl.lower()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_cat_decorations()

    @classmethod
    def get_color(cls, parent: QWidget, title: str, initial_hex: str, cat_pixmaps=None):
        dlg = cls(parent, title, initial_hex, cat_pixmaps=cat_pixmaps)
        if hasattr(dlg, "exec"):
            ok = dlg.exec()
        else:
            ok = dlg.exec_()
        if ok:
            return dlg._selected
        return None


class WordWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(560, 220)
        self._base_w = 560
        self._base_h = 220
        self._scale = 1.0
        self.fs = 28
        self.word_radius = window_radius
        self._drag_start = QPoint()
        self._dragging = False
        self._is_full_screen = False
        self._normal_geometry = self.geometry()
        self._active_bg = bgcolor
        self._active_fg = fgcolor
        self._word_color = word_color or fgcolor
        self._counter_color = counter_color
        self._current_entry = _empty_entry("", "")
        self._detail_dialog = None
        self._fitting_fonts = False
        self._word_history = []
        self._history_index = -1
        self._cat_pixmaps = self._load_cat_pixmaps()
        self._badge = self._cat_pixmaps[0] if self._cat_pixmaps else self._load_badge_pixmap()
        _log(f"cat assets loaded={len(self._cat_pixmaps)} frozen={getattr(sys, 'frozen', False)}")

        # Use a normal top-level frameless window so it is easier to surface on Windows.
        # In packaged mode, prioritize visibility over fancy transparency to avoid
        # rare cases where frameless translucent windows are not rendered.
        # Only keep this compatibility mode for frozen PyQt5 builds.
        # Frozen PySide6 should keep the same appearance as source mode.
        self._safe_visible_mode = bool(
            getattr(sys, "frozen", False) and QT_BACKEND == "PyQt5"
        )
        if self._safe_visible_mode:
            # Keep a normal window first; some systems mishandle always-on-top on startup.
            self.setWindowFlags(Qt.Window)
            self.setAttribute(Qt.WA_TranslucentBackground, False)
            self.setWindowOpacity(1.0)
        else:
            self.setWindowFlags(
                Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Window
            )
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setWindowOpacity(alpha)
        self.setFocusPolicy(Qt.StrongFocus)

        self.eng_label = QLabel("", self)
        self.eng_label.setAlignment(Qt.AlignCenter)
        self.eng_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.eng_label.setMinimumSize(0, 0)
        self.meta_label = QLabel("", self)
        self.meta_label.setAlignment(Qt.AlignCenter)
        self.meta_label.setWordWrap(True)
        self.meta_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.meta_label.setMinimumSize(0, 0)
        self.chn_label = QLabel("", self)
        self.chn_label.setAlignment(Qt.AlignCenter)
        self.chn_label.setWordWrap(True)
        self.chn_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.chn_label.setMinimumSize(0, 0)
        self.example_label = QLabel("", self)
        self.example_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.example_label.setWordWrap(True)
        self.example_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.example_label.setMinimumSize(0, 0)
        self.extra_label = QLabel("", self)
        self.extra_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.extra_label.setWordWrap(True)
        self.extra_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.extra_label.setMinimumSize(0, 0)
        self.cat_corner = QLabel(self)
        self.cat_corner.setFixedSize(46, 46)
        self._apply_cat_pixmap(self._badge)
        self.daily_count_label = QLabel(self)
        self.daily_count_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.daily_count_label.setFixedSize(56, 46)
        self._refresh_daily_count_label()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(2)
        layout.setSizeConstraint(QLayout.SetNoConstraint)
        layout.addWidget(self.eng_label)
        layout.addWidget(self.meta_label)
        layout.addWidget(self.chn_label)
        layout.addWidget(self.example_label)
        layout.addWidget(self.extra_label)
        if self._safe_visible_mode:
            self.setStyleSheet("background:#FFEFD6; border:1px solid #F2C89B;")
        self._apply_fonts()

        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self._on_auto_change)
        self._refresh_timer()

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._apply_saved_geometry()
        self.next_word(force=True, count_progress=False)

    def _load_badge_pixmap(self):
        # Prefer PNG assets first. In frozen Windows builds, some Qt5 SVG
        # parser paths are unstable and can cause native crashes.
        badge_candidates = [
            CAT_DIR / "cat_000.png",
            CAT_DIR / "cat_001.png",
            ASSET_DIR / "cat_badge.png",
        ]
        pix = QPixmap()
        for candidate in badge_candidates:
            if candidate.exists():
                candidate_pix = QPixmap(str(candidate))
                if not candidate_pix.isNull():
                    pix = candidate_pix
                    break
        if pix.isNull():
            pix = QPixmap(44, 44)
            pix.fill(Qt.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor("#D58A62"), 2))
            painter.drawEllipse(4, 4, 36, 36)
            painter.drawText(QRect(0, 0, 44, 44), Qt.AlignCenter, "cat")
            painter.end()
        return pix

    def _load_cat_pixmaps(self):
        pixmaps = []
        if CAT_DIR.exists():
            # In packaged mode, prioritize PNG only for stability.
            if getattr(sys, "frozen", False):
                patterns = ["*.png"]
            else:
                patterns = ["*.png", "*.svg"]
            seen = set()
            for pattern in patterns:
                for path in sorted(CAT_DIR.glob(pattern), key=lambda p: p.name.lower()):
                    key = path.stem.lower()
                    if key in seen:
                        continue
                    p = QPixmap(str(path))
                    if not p.isNull():
                        pixmaps.append(p)
                        seen.add(key)
        if not pixmaps:
            p = self._load_badge_pixmap()
            if not p.isNull():
                pixmaps.append(p)
        return pixmaps

    def _apply_cat_pixmap(self, pixmap):
        if pixmap is None or pixmap.isNull():
            return
        self.cat_corner.setPixmap(
            pixmap.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _randomize_cat(self):
        if not self._cat_pixmaps:
            return
        self._apply_cat_pixmap(random.choice(self._cat_pixmaps))

    def _refresh_daily_count_label(self):
        text = str(get_daily_progress_count())
        self.daily_count_label.setPixmap(self._build_paw_counter_pixmap(text))
        self.daily_count_label.move(10, 8)

    def _build_paw_counter_pixmap(self, text: str) -> QPixmap:
        w, h = 56, 46
        pix = QPixmap(w, h)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        paw_color = QColor("#FFD8B3")
        border_color = QColor("#E2AA7B")
        text_color = QColor(self._counter_color or "#F7F0E8")

        painter.setBrush(paw_color)
        painter.setPen(QPen(border_color, 1.6))
        painter.drawEllipse(15, 15, 28, 22)  # main pad
        painter.drawEllipse(8, 8, 9, 9)      # toe 1
        painter.drawEllipse(18, 4, 9, 9)     # toe 2
        painter.drawEllipse(30, 4, 9, 9)     # toe 3
        painter.drawEllipse(40, 8, 9, 9)     # toe 4

        font = QFont(_default_mono_font_family(), 9)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(text_color)
        painter.drawText(QRect(15, 17, 28, 18), Qt.AlignCenter, text)
        painter.end()
        return pix

    def _increment_daily_count(self):
        increment_daily_progress(1)
        self._refresh_daily_count_label()

    def _reset_daily_count(self):
        reset_daily_progress()
        self._refresh_daily_count_label()
        self._show_popup("今日计数", "已清零")

    def _apply_saved_geometry(self):
        try:
            with open(_p("preference.ini"), "r", encoding="utf-8") as f:
                lines = f.readlines()
            if not lines:
                self._base_w = self.width()
                self._base_h = self.height()
                self._scale = 1.0
                return
            items = lines[0].strip().split(",")
            if len(items) < 2:
                self._base_w = self.width()
                self._base_h = self.height()
                self._scale = 1.0
                return
            geom = items[0]
            fs = int(float(items[1]))
            g = re.fullmatch(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", geom)
            if g:
                w, h, x, y = map(int, g.groups())
                screen = QApplication.primaryScreen()
                if screen is not None:
                    avail = screen.availableGeometry()
                    w = max(MIN_WINDOW_WIDTH, min(MAX_WINDOW_WIDTH, w))
                    h = max(MIN_WINDOW_HEIGHT, min(MAX_WINDOW_HEIGHT, h))
                    max_x = avail.x() + max(0, avail.width() - w)
                    max_y = avail.y() + max(0, avail.height() - h)
                    x = min(max(x, avail.x()), max_x)
                    y = min(max(y, avail.y()), max_y)
                self.setGeometry(x, y, w, h)
            if self._safe_visible_mode:
                # Ensure packaged app window is immediately visible on the screen
                # where the user is currently operating (cursor screen).
                screen = QApplication.screenAt(QCursor.pos())
                if screen is None:
                    screen = QApplication.primaryScreen()
                if screen is not None:
                    avail = screen.availableGeometry()
                    self.move(
                        avail.center().x() - self.width() // 2,
                        avail.center().y() - self.height() // 2,
                    )
            self.fs = max(10, min(56, fs))
            self._apply_fonts()
            self._base_w = self.width()
            self._base_h = self.height()
            self._scale = 1.0
        except (OSError, ValueError):
            self._base_w = self.width()
            self._base_h = self.height()
            self._scale = 1.0

    def _apply_fonts(self):
        eng_size = int(self.fs * font_scale)
        meta_size = max(9, int(self.fs * font_scale * 0.45))
        chn_size = max(10, int(self.fs * font_scale * 0.68))
        detail_size = max(9, int(self.fs * font_scale * 0.44))
        self.eng_label.setFont(QFont(ENGfont, eng_size))
        meta_font = QFont(CHNfont, meta_size)
        meta_font.setItalic(True)
        self.meta_label.setFont(meta_font)
        self.chn_label.setFont(QFont(CHNfont, chn_size))
        self.example_label.setFont(QFont(CHNfont, detail_size))
        self.extra_label.setFont(QFont(CHNfont, detail_size))
        color = self._word_color or fgcolor
        self.eng_label.setStyleSheet(f"color: {color}; background: transparent;")
        self.meta_label.setStyleSheet("color: #8E6D5A; background: transparent;")
        self.chn_label.setStyleSheet(f"color: {color}; background: transparent;")
        self.example_label.setStyleSheet("color: #7A5B4B; background: transparent;")
        self.extra_label.setStyleSheet("color: #9A6A4C; background: transparent;")
        self._fit_current_text_fonts()
        self.update()

    def _fit_label_font(self, label: QLabel, family: str, target_size: int, min_size: int, wrap: bool):
        text = label.text() or ""
        if not text:
            return

        avail_w = max(40, label.width() - 8)
        avail_h = max(16, label.height() - 4)
        flags = Qt.TextWordWrap if wrap else Qt.TextSingleLine

        best = min_size
        for size in range(max(min_size, target_size), min_size - 1, -1):
            font = QFont(family, size)
            fm = QFontMetrics(font)
            if wrap:
                rect = fm.boundingRect(QRect(0, 0, avail_w, 10000), flags, text)
                fits = rect.height() <= avail_h
            else:
                fits = fm.horizontalAdvance(text) <= avail_w and fm.height() <= avail_h
            if fits:
                best = size
                break
        current_size = label.font().pointSize()
        if current_size != best:
            label.setFont(QFont(family, best))

    def _fit_current_text_fonts(self):
        if self._fitting_fonts:
            return
        self._fitting_fonts = True
        eng_target = max(10, int(self.fs * font_scale))
        meta_target = max(9, int(self.fs * font_scale * 0.45))
        chn_target = max(10, int(self.fs * font_scale * 0.68))
        detail_target = max(9, int(self.fs * font_scale * 0.44))
        try:
            self._fit_label_font(self.eng_label, ENGfont, eng_target, 8, wrap=False)
            self._fit_label_font(self.meta_label, CHNfont, meta_target, 8, wrap=True)
            self._fit_label_font(self.chn_label, CHNfont, chn_target, 8, wrap=True)
            self._fit_label_font(self.example_label, CHNfont, detail_target, 8, wrap=True)
            self._fit_label_font(self.extra_label, CHNfont, detail_target, 8, wrap=True)
        finally:
            self._fitting_fonts = False

    def _content_height_hint(self) -> int:
        avail_w = max(220, self.width() - 48)
        visible_labels = [
            self.eng_label,
            self.meta_label,
            self.chn_label,
            self.example_label,
            self.extra_label,
        ]
        total = 40
        count = 0
        for label in visible_labels:
            # Child widgets report isVisible() == False before the parent window is
            # shown, so use the explicit hidden state here. This keeps startup
            # layout sizing accurate for example/extra inline text.
            if label.isHidden() or not (label.text() or "").strip():
                continue
            count += 1
            fm = QFontMetrics(label.font())
            flags = Qt.TextWordWrap if label.wordWrap() else Qt.TextSingleLine
            rect = fm.boundingRect(QRect(0, 0, avail_w, 10000), flags, label.text())
            total += max(rect.height(), fm.height()) + 6
        total += max(0, count - 1) * 2
        return max(MIN_WINDOW_HEIGHT, min(MAX_WINDOW_HEIGHT, total))

    def _ensure_content_height(self):
        if self._is_full_screen:
            return
        desired_height = self._content_height_hint()
        if self.height() >= desired_height:
            return
        geom = self.geometry()
        self.setGeometry(geom.x(), geom.y(), geom.width(), desired_height)
        self._base_w = self.width()
        self._base_h = self.height()

    def _sync_content_layout(self, defer_visible_refit: bool = False):
        layout = self.layout()
        if layout is not None:
            layout.activate()
        self._ensure_content_height()
        self._fit_current_text_fonts()
        if defer_visible_refit:
            QTimer.singleShot(0, self._sync_visible_content_layout)

    def _sync_visible_content_layout(self):
        if not self.isVisible():
            return
        layout = self.layout()
        if layout is not None:
            layout.activate()
        self._ensure_content_height()
        self._fit_current_text_fonts()

    def _refresh_timer(self):
        interval = max(200, int(waitTime * 1000))
        self.auto_timer.setInterval(interval)
        self.auto_timer.start()

    def _next_word_item(self):
        global word_index
        if not word_items:
            getWord()
        if not word_items:
            return _empty_entry("NoLexicon", "请在程序目录放入词库 .txt")
        if order == 1:
            item = word_items[word_index % len(word_items)]
            word_index = (word_index + 1) % len(word_items)
            return item
        return random.choice(word_items)

    def _show_history_item(self, index: int, count_progress: bool = False):
        if not (0 <= index < len(self._word_history)):
            return
        self._history_index = index
        entry = self._word_history[index]
        self._apply_word(entry, count_progress=count_progress)

    def _advance_word(self, count_progress: bool = True):
        next_index = self._history_index + 1
        if next_index < len(self._word_history):
            self._show_history_item(next_index, count_progress=False)
            return

        entry = self._next_word_item()
        if self._history_index < len(self._word_history) - 1:
            self._word_history = self._word_history[: self._history_index + 1]
        self._word_history.append(entry)
        self._history_index = len(self._word_history) - 1
        self._apply_word(entry, count_progress=count_progress)

    def _previous_word(self):
        if self._history_index <= 0:
            return
        self._show_history_item(self._history_index - 1, count_progress=False)

    def _apply_word(self, entry: dict, count_progress: bool = True):
        self._current_entry = entry
        display_word = entry.get("display_word") or entry.get("word") or ""
        meaning = entry.get("meaning") or ""
        meta_text = _format_entry_meta(entry)
        example_text = entry.get("example") or ""
        extra_text = entry.get("extra") or ""
        self.eng_label.setText(display_word)
        self.meta_label.setText(meta_text)
        self.meta_label.setVisible(bool(meta_text))
        self.chn_label.setText(meaning)
        self.chn_label.setAlignment(Qt.AlignLeft if len(meaning) > 16 else Qt.AlignCenter)
        self.example_label.setText(f"例句: {example_text}" if example_text else "")
        self.example_label.setVisible(bool(example_text))
        self.extra_label.setText(f"拓展: {extra_text}" if extra_text else "")
        self.extra_label.setVisible(bool(extra_text))
        self._sync_content_layout(defer_visible_refit=not self._safe_visible_mode)
        self._randomize_cat()
        if count_progress:
            self._increment_daily_count()
        if auto_speak:
            speak_word(entry.get("word", ""))
        self.update()

    def next_word(self, force=False, count_progress=True):
        if handmode and not force:
            return
        self._advance_word(count_progress=count_progress)

    def _manual_next_word(self, count_progress=True):
        self._advance_word(count_progress=count_progress)

    def _speak_current_word(self):
        text = (self._current_entry or {}).get("word", "").strip()
        if not text:
            return
        speak_word(text)

    def _show_word_details(self):
        entry = self._current_entry or {}
        if not entry.get("word"):
            return
        dlg = WordDetailDialog(self, entry)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        self._detail_dialog = dlg

    def _show_popup(self, title: str, content: str):
        popup = CatPopup(self, title, content)
        center = self.geometry().center()
        popup.move(center.x() - popup.width() // 2, center.y() - popup.height() // 2)
        popup.show()
        self._popup = popup

    def _on_auto_change(self):
        self.next_word()

    def _toggle_order(self):
        global order
        order = (order + 1) % 2
        self._show_popup("播放顺序", "顺序播放" if order == 1 else "随机播放")

    def _toggle_mode(self):
        global handmode
        handmode = (handmode + 1) % 2
        msg = "手动切换: 双击或空格换词" if handmode == 1 else "自动切换已开启"
        self._show_popup("播放模式", msg)

    def _toggle_auto_speak(self, checked: bool):
        set_tts_enabled(bool(checked))
        if checked:
            self._speak_current_word()

    def _copy_word(self):
        text = (self._current_entry or {}).get("display_word", "").strip()
        if not text:
            return
        if pyperclip is not None:
            pyperclip.copy(text)
        else:
            QApplication.clipboard().setText(text)
        self._show_popup("复制完成", f"已复制: {text}")

    def _favourite(self):
        try:
            with open(_p(FAVORITES_FILE), "a", encoding="utf-8") as f:
                entry = self._current_entry or {}
                row = [
                    entry.get("display_word", ""),
                    entry.get("pos", ""),
                    entry.get("meaning", ""),
                    entry.get("example", ""),
                    entry.get("extra", ""),
                    entry.get("category", ""),
                ]
                f.write("\t".join(row).rstrip() + "\n")
            self._show_popup("收藏成功", "当前单词已加入收藏")
        except OSError as exc:
            self._show_popup("收藏失败", str(exc))

    def _set_speed(self):
        global waitTime
        value, ok = QInputDialog.getDouble(
            self, "播放速度", "切换时间(秒):", waitTime, 0.5, 30.0, 1
        )
        if ok:
            waitTime = value
            self._refresh_timer()
            self._show_popup("速度更新", f"切换间隔: {waitTime:.1f}s")

    def _set_theme_by_name(self, name: str):
        global bgcolor, fgcolor
        if name not in themeColors:
            return
        colors = themeColors[name]
        bgcolor = colors[0]
        fgcolor = colors[1]
        self._active_bg = bgcolor
        self._active_fg = fgcolor
        if not self._word_color:
            self._word_color = fgcolor
        self.update()

    def _set_font_by_name(self, name: str):
        global ENGfont, CHNfont
        if name not in fonts:
            return
        ENGfont, CHNfont = fonts[name]
        self._apply_fonts()

    def _set_alpha_by_name(self, name: str):
        global alpha
        if name not in alphaValues:
            return
        alpha = alphaValues[name]
        self.setWindowOpacity(alpha)

    def _set_word_color(self, color_hex: str):
        global word_color
        self._word_color = color_hex
        word_color = self._word_color
        self._apply_fonts()

    def _set_counter_color(self, color_hex: str):
        global counter_color
        self._counter_color = color_hex
        counter_color = self._counter_color
        self._refresh_daily_count_label()
        self.update()

    def _pick_color_styled(self, current: QColor, title: str):
        source_pixmaps = [p for p in self._cat_pixmaps if p is not None and not p.isNull()]
        if not source_pixmaps and self.cat_corner.pixmap() is not None:
            source_pixmaps = [self.cat_corner.pixmap()]
        return CuteColorDialog.get_color(self, title, current.name(), cat_pixmaps=source_pixmaps)

    def _pick_word_color_palette(self):
        current = QColor(self._word_color or fgcolor)
        chosen = self._pick_color_styled(current, "单词颜色")
        if chosen is None:
            return
        self._set_word_color(chosen.name())

    def _pick_counter_color_palette(self):
        current = QColor(self._counter_color or "#F7F0E8")
        chosen = self._pick_color_styled(current, "数字颜色")
        if chosen is None:
            return
        self._set_counter_color(chosen.name())

    def _set_lexicon(self, selected_name: str):
        global file, default_lexicon
        if selected_name not in lexicon:
            return
        file = lexicon[selected_name]
        default_lexicon = selected_name
        getWord()
        self._manual_next_word(count_progress=False)
        geom = self.geometry()
        geometry_str = f"{geom.width()}x{geom.height()}+{geom.x()}+{geom.y()}"
        saveConfig(geometry_str, self.fs)
        self._show_popup("词库已切换", selected_name)

    def _toggle_fullscreen(self):
        global isFullScreen
        if not self._is_full_screen:
            self._normal_geometry = self.geometry()
            self.showFullScreen()
            self._is_full_screen = True
            isFullScreen = 1
        else:
            self.showNormal()
            self.setGeometry(self._normal_geometry)
            self._is_full_screen = False
            isFullScreen = 0
        self.update()

    def _save_pref(self):
        geom = self.geometry()
        geometry_str = f"{geom.width()}x{geom.height()}+{geom.x()}+{geom.y()}"
        saveConfig(geometry_str, self.fs)
        self._show_popup("保存成功", "配置已保存")

    def _restore_pref(self):
        readConfig()
        self._apply_saved_geometry()
        self.setWindowOpacity(alpha)
        self._active_bg = bgcolor
        self._active_fg = fgcolor
        self._word_color = word_color or fgcolor
        self._counter_color = counter_color or "#F7F0E8"
        self._apply_fonts()
        self._refresh_daily_count_label()
        self._refresh_timer()
        self.update()
        self._show_popup("恢复完成", "已载入配置")

    def _rebuild_lexicon_menu(self, parent_menu: QMenu):
        loadLexiconByDir()
        parent_menu.clear()
        if not lexicon:
            action = parent_menu.addAction("未找到词库")
            action.setEnabled(False)
            return
        for name in lexicon.keys():
            action = parent_menu.addAction(name)
            action.triggered.connect(lambda checked=False, n=name: self._set_lexicon(n))

    def _show_context_menu(self, pos):
        global themeColors, fonts, alphaValues
        if not isinstance(themeColors, dict):
            themeColors = dict(DEFAULT_THEME_COLORS)
        if not isinstance(fonts, dict):
            fonts = dict(DEFAULT_FONTS)
        if not isinstance(alphaValues, dict):
            alphaValues = dict(DEFAULT_ALPHA_VALUES)
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background: #FFF7EC;
                border: 2px solid #F2C89B;
                border-radius: 14px;
                padding: 8px;
            }
            QMenu::item {
                border-radius: 8px;
                padding: 7px 22px;
                color: #6A4B3A;
            }
            QMenu::item:selected {
                background: #FFE0BA;
            }
            """
        )

        menu.addAction("切换模式", self._toggle_mode)
        menu.addAction("切换顺序", self._toggle_order)
        menu.addAction("播放速度", self._set_speed)
        menu.addAction("朗读当前词", self._speak_current_word)

        auto_action = QAction("自动朗读", self, checkable=True)
        auto_action.setChecked(bool(auto_speak))
        auto_action.toggled.connect(self._toggle_auto_speak)
        menu.addAction(auto_action)
        menu.addAction("清零今日计数", self._reset_daily_count)

        menu.addSeparator()
        menu.addAction("复制该词", self._copy_word)
        menu.addAction("收藏该词", self._favourite)
        menu.addAction("查看词条详情", self._show_word_details)

        menu.addSeparator()
        word_color_menu = menu.addMenu("单词颜色")
        word_color_menu.addAction("打开调色板", self._pick_word_color_palette)
        counter_color_menu = menu.addMenu("数字颜色")
        counter_color_menu.addAction("打开调色板", self._pick_counter_color_palette)
        theme_menu = menu.addMenu("主题色")
        for theme_name in themeColors.keys():
            action = theme_menu.addAction(theme_name)
            action.triggered.connect(
                lambda checked=False, n=theme_name: self._set_theme_by_name(n)
            )

        font_menu = menu.addMenu("字体")
        for font_name in fonts.keys():
            action = font_menu.addAction(font_name)
            action.triggered.connect(
                lambda checked=False, n=font_name: self._set_font_by_name(n)
            )

        alpha_menu = menu.addMenu("透明度")
        for alpha_name in alphaValues.keys():
            action = alpha_menu.addAction(alpha_name)
            action.triggered.connect(
                lambda checked=False, n=alpha_name: self._set_alpha_by_name(n)
            )
        menu.addAction("全屏模式", self._toggle_fullscreen)

        menu.addSeparator()
        lexicon_menu = menu.addMenu("切换词库")
        self._rebuild_lexicon_menu(lexicon_menu)

        menu.addSeparator()
        menu.addAction("保存配置", self._save_pref)
        menu.addAction("恢复配置", self._restore_pref)
        menu.addAction("退出", self._request_quit)
        if hasattr(menu, "exec"):
            menu.exec(self.mapToGlobal(pos))
        else:
            menu.exec_(self.mapToGlobal(pos))

    def _request_quit(self):
        app = QApplication.instance()
        if app is not None:
            _log("quit requested from menu")
            app.quit()
        else:
            self.close()

    def paintEvent(self, event):
        if self._safe_visible_mode:
            return super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)

        path = QPainterPath()
        path.addRoundedRect(rect, self.word_radius, self.word_radius)
        painter.fillPath(path, QColor(self._active_bg))

        painter.setPen(QPen(QColor("#F2C89B"), 2))
        painter.drawPath(path)

        blossom = QColor("#FFD7E5")
        painter.setPen(Qt.NoPen)
        painter.setBrush(blossom)
        for x, y in [(26, 28), (58, 20), (84, 34), (324, 18), (352, 34)]:
            painter.drawEllipse(x, y, 4, 4)
            painter.drawEllipse(x + 4, y + 2, 4, 4)
            painter.drawEllipse(x + 2, y + 6, 4, 4)

        self.cat_corner.move(self.width() - self.cat_corner.width() - 8, 8)
        super().paintEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            self._drag_start = gp - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and not self._is_full_screen:
            gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            self.move(gp - self._drag_start)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._manual_next_word()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        if self._is_full_screen:
            return
        if event.angleDelta().y() > 0:
            self._scale *= 1.08
        else:
            self._scale *= 0.92
        self._scale = max(0.30, min(1.60, self._scale))

        new_h = int(self._base_h * self._scale)
        new_h = max(MIN_WINDOW_HEIGHT, min(MAX_WINDOW_HEIGHT, new_h))
        new_w = int(self._base_w * self._scale)
        new_w = max(MIN_WINDOW_WIDTH, min(MAX_WINDOW_WIDTH, new_w))
        self.fs = max(10, min(56, int(new_h / 3.6)))
        center = self.geometry().center()
        self.setGeometry(
            center.x() - new_w // 2,
            center.y() - new_h // 2,
            new_w,
            new_h,
        )
        self._apply_fonts()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_current_text_fonts()
        self._refresh_daily_count_label()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_content_layout(defer_visible_refit=not self._safe_visible_mode)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self._manual_next_word()
            event.accept()
            return
        if event.key() == Qt.Key_Right:
            self._manual_next_word()
            event.accept()
            return
        if event.key() == Qt.Key_Left:
            self._previous_word()
            event.accept()
            return
        if event.key() == Qt.Key_R:
            self._speak_current_word()
            event.accept()
            return
        if event.key() == Qt.Key_D:
            self._show_word_details()
            event.accept()
            return
        super().keyPressEvent(event)


def ensure_assets():
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    CAT_DIR.mkdir(parents=True, exist_ok=True)
    default_assets = {
        "cat_badge.svg": """<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128">
<circle cx="64" cy="64" r="60" fill="#FFE9CD" stroke="#E0A878" stroke-width="5"/>
<circle cx="44" cy="54" r="7" fill="#6A4B3A"/>
<circle cx="84" cy="54" r="7" fill="#6A4B3A"/>
<path d="M56 78 C64 88 72 88 80 78" stroke="#6A4B3A" stroke-width="5" fill="none" stroke-linecap="round"/>
<path d="M16 36 L34 16 L42 36 Z" fill="#FFDAB8" stroke="#E0A878" stroke-width="4"/>
<path d="M86 36 L94 16 L112 36 Z" fill="#FFDAB8" stroke="#E0A878" stroke-width="4"/>
</svg>
""",
        "popup_bg.svg": """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360">
<rect width="640" height="360" fill="#FFF7EC"/>
<circle cx="80" cy="80" r="18" fill="#FFD7E5"/>
<circle cx="100" cy="96" r="16" fill="#FFD7E5"/>
<circle cx="90" cy="114" r="15" fill="#FFD7E5"/>
<circle cx="560" cy="64" r="18" fill="#CCE9FF"/>
<circle cx="584" cy="82" r="16" fill="#CCE9FF"/>
<circle cx="572" cy="102" r="15" fill="#CCE9FF"/>
</svg>
""",
        "button_tile.svg": """<svg xmlns="http://www.w3.org/2000/svg" width="320" height="100">
<rect x="4" y="4" width="312" height="92" rx="24" ry="24" fill="#FFE4C4" stroke="#E6B082" stroke-width="6"/>
</svg>
""",
    }
    for filename, content in default_assets.items():
        path = ASSET_DIR / filename
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
    default_cat = CAT_DIR / "cat_000.svg"
    if not default_cat.exists():
        with open(default_cat, "w", encoding="utf-8") as f:
            f.write(
                """<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128">
<circle cx="64" cy="64" r="60" fill="#FFE9CD" stroke="#E0A878" stroke-width="5"/>
<circle cx="44" cy="54" r="7" fill="#6A4B3A"/>
<circle cx="84" cy="54" r="7" fill="#6A4B3A"/>
<path d="M56 78 C64 88 72 88 80 78" stroke="#6A4B3A" stroke-width="5" fill="none" stroke-linecap="round"/>
<path d="M16 36 L34 16 L42 36 Z" fill="#FFDAB8" stroke="#E0A878" stroke-width="4"/>
<path d="M86 36 L94 16 L112 36 Z" fill="#FFDAB8" stroke="#E0A878" stroke-width="4"/>
</svg>
"""
            )


def ensure_platform_runtime_ready() -> None:
    missing = _detect_missing_linux_runtime_packages()
    if not missing:
        return
    install_cmd = f"sudo apt install {' '.join(missing)}"
    message = (
        "Ubuntu 缺少 Qt 图形运行时依赖："
        + ", ".join(missing)
        + f"。请先执行：{install_cmd}"
    )
    _log(message)
    raise SystemExit(message)


def main():
    _log(f"=== startup begin (frozen={getattr(sys, 'frozen', False)}, backend={QT_BACKEND}) ===")
    _log(f"base_dir={BASE_DIR}")
    _log(f"python={sys.version}")
    _log(f"argv={sys.argv}")

    bootstrap_runtime_files()
    _log("bootstrap_runtime_files ok")
    ensure_platform_runtime_ready()
    _log("ensure_platform_runtime_ready ok")

    readConfig()
    _log("readConfig ok")
    getWord()
    _log(f"getWord ok: loaded={len(word_items)}")
    ensure_assets()
    _log("ensure_assets ok")
    load_daily_progress()
    _log("load_daily_progress ok")

    app = QApplication(sys.argv)
    app.setApplicationName("W2R-Cattoon")
    normalize_runtime_fonts()
    app.setFont(QFont(_default_cjk_font_family(), 10))
    app.setQuitOnLastWindowClosed(False)
    icon_path = resolve_app_icon_path()
    if icon_path is not None:
        icon = QIcon(str(icon_path))
        app.setWindowIcon(icon)
        _log(f"app icon loaded: {icon_path}")
    else:
        icon = QIcon()
        _log("app icon not found")
    _log("QApplication created")
    app.aboutToQuit.connect(lambda: _log("aboutToQuit signal"))

    # Allow Ctrl+C to terminate when launched from a terminal.
    def _handle_sigint(_signum, _frame):
        _log("SIGINT received, quitting app")
        app.quit()

    signal.signal(signal.SIGINT, _handle_sigint)
    sigint_pump = QTimer()
    sigint_pump.timeout.connect(lambda: None)
    sigint_pump.start(200)

    window = WordWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    _log("WordWindow created")
    window.show()
    window.raise_()
    window.activateWindow()
    QTimer.singleShot(120, lambda: (window.raise_(), window.activateWindow()))
    # Rescue activation loop: force visible/normal in the first few seconds.
    _rescue_tick = {"n": 0}

    def _rescue_window():
        _rescue_tick["n"] += 1
        try:
            window.showNormal()
            state = window.windowState() & ~Qt.WindowMinimized
            window.setWindowState(state)
            window.show()
            window.raise_()
            window.activateWindow()
            g = window.geometry()
            _log(
                f"rescue#{_rescue_tick['n']} visible={window.isVisible()} "
                f"active={window.isActiveWindow()} geometry={g.x()},{g.y()},{g.width()}x{g.height()}"
            )
        except Exception:
            _log(f"rescue#{_rescue_tick['n']} error: {traceback.format_exc()}")
        if _rescue_tick["n"] < 8:
            QTimer.singleShot(400, _rescue_window)

    QTimer.singleShot(250, _rescue_window)
    _log("window show/raise/activate issued")
    g = window.geometry()
    _log(f"window geometry={g.x()},{g.y()},{g.width()}x{g.height()} visible={window.isVisible()}")

    def _watchdog():
        try:
            if not window.isVisible():
                _log("watchdog: window hidden, force show")
                window.showNormal()
                window.show()
                window.raise_()
                window.activateWindow()
        except Exception:
            _log(f"watchdog error: {traceback.format_exc()}")

    watchdog_timer = QTimer()
    watchdog_timer.timeout.connect(_watchdog)
    watchdog_timer.start(1200)
    _log("watchdog started")
    exec_fn = app.exec if hasattr(app, "exec") else app.exec_
    rc = exec_fn()
    _log(f"app exec finished, return_code={rc}")
    sys.exit(rc)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log("FATAL EXCEPTION in __main__")
        _log(traceback.format_exc())
        raise
