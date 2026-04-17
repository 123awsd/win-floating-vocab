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
    from PySide6.QtGui import QAction, QColor, QCursor, QFont, QFontMetrics, QIcon, QPainter, QPainterPath, QPen, QPixmap
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
        from PyQt5.QtGui import QColor, QCursor, QFont, QFontMetrics, QIcon, QPainter, QPainterPath, QPen, QPixmap
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
APP_ICON_REL = Path("assets") / "app_icon" / "app.ico"
MIN_WINDOW_HEIGHT = 36
MAX_WINDOW_HEIGHT = 180
MIN_WINDOW_WIDTH = 180
MAX_WINDOW_WIDTH = 960


def _p(name: str) -> str:
    return str(BASE_DIR / name)


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


def _event_global_point(event) -> QPoint:
    try:
        return event.globalPosition().toPoint()
    except AttributeError:
        return event.globalPos()


class DragHandleLabel(QLabel):
    def __init__(self, text: str = "", target_window: QWidget = None, parent: QWidget = None):
        super().__init__(text, parent)
        self._target_window = target_window
        self._dragging = False
        self._drag_offset = QPoint()
        self.setCursor(Qt.OpenHandCursor)

    def _target(self):
        return self._target_window if self._target_window is not None else self.window()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            target = self._target()
            if target is not None:
                self._dragging = True
                self._drag_offset = _event_global_point(event) - target.frameGeometry().topLeft()
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.LeftButton):
            target = self._target()
            if target is not None:
                target.move(_event_global_point(event) - self._drag_offset)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self.setCursor(Qt.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)


def _transparency_to_alpha(transparency: float) -> float:
    # Keep a little visibility at max transparency so window remains operable.
    return max(0.1, min(1.0, 1.0 - float(transparency)))


def _alpha_to_transparency(alpha_value: float) -> float:
    return max(0.0, min(1.0, 1.0 - float(alpha_value)))


waitTime = 2.0
default_lexicon = ""
file = _p("单词表.txt")
bgcolor = "#FFEFD6"
fgcolor = "#4D3B36"
word_color = fgcolor
counter_color = "#F7F0E8"
ENGfont = "Consolas"
CHNfont = "宋体"
alpha = 0.96
isFullScreen = 0
auto_speak = 0
order = 0
handmode = 1
tts_language = "en"

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
    "宋体": ["Consolas", "宋体"],
    "微软雅黑": ["Consolas", "微软雅黑"],
    "苹方": ["Consolas", "苹方 常规"],
    "汉仪意宋": ["Consolas", "汉仪意宋简 Regular"],
}
DEFAULT_FONTS = dict(fonts)

alphaValues = {
    "0%": 0.0,
    "10%": 0.1,
    "20%": 0.2,
    "30%": 0.3,
    "40%": 0.4,
    "50%": 0.5,
    "60%": 0.6,
    "70%": 0.7,
    "80%": 0.8,
    "90%": 0.9,
    "100%": 1.0,
}
DEFAULT_ALPHA_VALUES = dict(alphaValues)

lexicon = {}
words = {}
word_items = []
word_index = 0
detected_lexicon_lang = "en"

_tts_worker_started = False
_tts_lock = threading.Lock()
_tts_error_hint_shown = False
_tts_latest_text = ""
_tts_request_event = threading.Event()
_tts_current_proc = None
_tts_voice_missing_warned = set()

_ENG_TTS_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\s\-\+'/]*$")
_HAS_LETTER_PATTERN = re.compile(r"[A-Za-z]")
DAILY_PROGRESS_FILE = BASE_DIR / "daily_progress.json"
daily_progress_date = ""
daily_progress_count = 0
LEARNING_PROGRESS_FILE = BASE_DIR / "learning_progress.json"
lexicon_progress = {}
lexicon_progress_loaded = False


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
    dst_icon = BASE_DIR / APP_ICON_REL
    if not dst_icon.exists():
        for root in _bundled_roots():
            src_icon = root / APP_ICON_REL
            if src_icon.exists():
                try:
                    dst_icon.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_icon, dst_icon)
                except OSError:
                    pass
                break


def resolve_app_icon_path() -> Path | None:
    candidates = [BASE_DIR / APP_ICON_REL]
    for root in _bundled_roots():
        candidates.append(root / APP_ICON_REL)
    for p in candidates:
        if p.exists():
            return p
    return None


def _is_english_word(text):
    text = (text or "").strip()
    return bool(_ENG_TTS_PATTERN.fullmatch(text)) and bool(_HAS_LETTER_PATTERN.search(text))


def _can_speak_text(text: str) -> bool:
    text = (text or "").strip()
    if not text:
        return False
    if tts_language == "ja":
        return True
    return _is_english_word(text)


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


def load_lexicon_progress() -> None:
    global lexicon_progress, lexicon_progress_loaded
    if lexicon_progress_loaded:
        return
    lexicon_progress_loaded = True
    lexicon_progress = {}
    try:
        with open(LEARNING_PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k, v in data.items():
                try:
                    lexicon_progress[str(k)] = max(0, int(v))
                except (ValueError, TypeError):
                    pass
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass


def save_lexicon_progress() -> None:
    try:
        with open(LEARNING_PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(lexicon_progress, f, ensure_ascii=False)
    except OSError:
        pass


def get_lexicon_progress(name: str) -> int:
    load_lexicon_progress()
    return int(lexicon_progress.get(str(name or ""), 0))


def set_lexicon_progress(name: str, index: int) -> None:
    if not name:
        return
    load_lexicon_progress()
    lexicon_progress[str(name)] = max(0, int(index))
    save_lexicon_progress()


def _build_tts_script():
    return (
        "$ErrorActionPreference='Stop';"
        "$text=$env:W2R_TTS_TEXT;"
        "$lang=$env:W2R_TTS_LANG;"
        "if($text -cmatch '^[A-Z]{2,6}$'){ $text = (($text.ToCharArray()) -join ' ') };"
        "$v=New-Object -ComObject SAPI.SpVoice;"
        "$voices=$v.GetVoices();"
        "$pattern='English|en-US|en-GB';"
        "$langHex='409';"
        "if($lang -eq 'ja'){ $pattern='Japanese|ja-JP|日本|日语'; $langHex='411' };"
        "$matched=$false;"
        "for($i=0;$i -lt $voices.Count;$i++){"
        "  $vi=$voices.Item($i);"
        "  $d=$vi.GetDescription();"
        "  $langAttr='';"
        "  try{ $langAttr=$vi.GetAttribute('Language') }catch{};"
        "  if($d -match $pattern -or $langAttr -match $langHex){ $v.Voice=$vi; $matched=$true; break }"
        "};"
        "if(-not $matched){ Write-Output '__W2R_NO_VOICE__' };"
        "$v.Rate = -2;"
        "[void]$v.Speak($text);"
    )


def _spawn_sapi_speak(text):
    script = _build_tts_script()
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    env = os.environ.copy()
    env["W2R_TTS_TEXT"] = text
    env["W2R_TTS_LANG"] = tts_language
    return subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        creationflags=creationflags,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _has_voice_for_language(lang: str) -> bool:
    if lang != "ja":
        return True
    script = (
        "$v=New-Object -ComObject SAPI.SpVoice;"
        "$voices=$v.GetVoices();"
        "$ok=$false;"
        "for($i=0;$i -lt $voices.Count;$i++){"
        "  $vi=$voices.Item($i);"
        "  $d=$vi.GetDescription();"
        "  $langAttr='';"
        "  try{ $langAttr=$vi.GetAttribute('Language') }catch{};"
        "  if($d -match 'Japanese|ja-JP|日本|日语' -or $langAttr -match '411'){ $ok=$true; break }"
        "};"
        "if($ok){'1'}else{'0'};"
    )
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        out = subprocess.check_output(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
            creationflags=creationflags,
            stderr=subprocess.DEVNULL,
            timeout=2.5,
            text=True,
        )
        return out.strip().endswith("1")
    except Exception:
        return False


def _stop_current_tts():
    global _tts_current_proc
    with _tts_lock:
        proc = _tts_current_proc
        _tts_current_proc = None
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
    global _tts_error_hint_shown, _tts_current_proc
    while True:
        _tts_request_event.wait()
        _tts_request_event.clear()
        while True:
            with _tts_lock:
                text = _tts_latest_text
            if not text:
                break

            try:
                proc = _spawn_sapi_speak(text)
            except Exception as exc:
                if not _tts_error_hint_shown:
                    _tts_error_hint_shown = True
                    print(f"[TTS] 语音朗读不可用，请检查系统语音环境: {exc}")
                break

            with _tts_lock:
                _tts_current_proc = proc

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


def speak_word(text: str, restart: bool = False) -> None:
    global _tts_latest_text
    text = _normalize_tts_text(text)
    if not _can_speak_text(text):
        return
    _ensure_tts_worker()
    if restart:
        _stop_current_tts()
    with _tts_lock:
        _tts_latest_text = text
    _tts_request_event.set()


def set_tts_enabled(flag: bool) -> None:
    global auto_speak
    auto_speak = 1 if flag else 0
    if not auto_speak:
        _stop_current_tts()


def set_tts_language(lang: str) -> bool:
    global tts_language
    lang = (lang or "").strip().lower()
    if lang not in {"en", "ja"}:
        return False
    if lang == "ja" and not _has_voice_for_language("ja"):
        tts_language = "en"
        return False
    tts_language = lang
    return True


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
        if "\t" not in head and " " not in head:
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
    global ui_theme, window_radius, font_scale, default_lexicon, file, tts_language
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
        tts_language = extra_pairs.get("tts_language", tts_language).strip().lower() or "en"
        if tts_language not in {"en", "ja"}:
            tts_language = "en"
        # v2: user-facing "transparency" value, where larger means more transparent.
        transparency_text = extra_pairs.get("transparency", "")
        if transparency_text:
            try:
                transparency = max(0.0, min(1.0, float(transparency_text)))
                alpha = _transparency_to_alpha(transparency)
            except ValueError:
                pass

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
        f.write(f"tts_language={tts_language}\n")
        f.write(f"transparency={_alpha_to_transparency(alpha):.2f}\n")


def _parse_words_from_file(file_path: str):
    loaded = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Preferred format: term<TAB>meaning, which supports phrase terms.
            if "\t" in line:
                eng, chn = line.split("\t", 1)
            else:
                # Backward compatibility for legacy files: term + whitespace + meaning.
                pre = line.split(maxsplit=1)
                if len(pre) < 2:
                    continue
                eng, chn = pre[0], pre[1]
            eng = eng.strip()
            chn = chn.strip()
            if not eng or not chn:
                continue
            if eng in loaded and loaded[eng] != chn:
                loaded[eng] = loaded[eng].strip() + ";" + chn
            else:
                loaded[eng] = chn
    return loaded


def _detect_language_from_terms(term_map: dict) -> str:
    if not term_map:
        return "en"
    ja_hits = 0
    en_hits = 0
    ja_re = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff\u4e00-\u9fff]")
    en_re = re.compile(r"[A-Za-z]")
    for idx, term in enumerate(term_map.keys()):
        if idx >= 120:
            break
        text = str(term)
        if ja_re.search(text):
            ja_hits += 1
        if en_re.search(text):
            en_hits += 1
    return "ja" if ja_hits > en_hits and ja_hits > 0 else "en"


def getWord():
    global file, words, word_items, word_index, default_lexicon, detected_lexicon_lang

    def _safe_exists(path_text: str) -> bool:
        try:
            return Path(path_text).exists()
        except (OSError, ValueError, TypeError):
            return False

    if not lexicon:
        loadLexiconByDir()
    if not lexicon:
        words = {}
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
    word_items = list(words.items())
    word_index = 0
    detected_lexicon_lang = _detect_language_from_terms(words)
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

        t_label = DragHandleLabel(title, target_window=self)
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
                font-family: Consolas;
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


class CuteColorDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, initial_hex: str, cat_pixmaps=None, on_change=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.resize(360, 290)

        initial = QColor(initial_hex or "#F7F0E8")
        self._selected = initial if initial.isValid() else QColor("#F7F0E8")
        self._updating = False
        self._on_change = on_change

        self.card = QWidget()
        self.card.setObjectName("card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        title_label = DragHandleLabel(title + "  (RGB)", target_window=self)
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
                font-family: Consolas;
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
        if callable(self._on_change):
            self._on_change(self._selected)

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
    def get_color(cls, parent: QWidget, title: str, initial_hex: str, cat_pixmaps=None, on_change=None):
        dlg = cls(parent, title, initial_hex, cat_pixmaps=cat_pixmaps, on_change=on_change)
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
        self.resize(420, 120)
        self._base_w = 420
        self._base_h = 120
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
        self._fitting_fonts = False
        self._history = []
        self._history_pos = -1
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
        self.chn_label = QLabel("", self)
        self.chn_label.setAlignment(Qt.AlignCenter)
        self.chn_label.setWordWrap(True)
        self.chn_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.chn_label.setMinimumSize(0, 0)
        self.cat_corner = QLabel(self)
        self.cat_corner.setFixedSize(46, 46)
        self._apply_cat_pixmap(self._badge)
        self.daily_count_label = QLabel(self)
        self.daily_count_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.daily_count_label.setFixedSize(56, 46)
        self._refresh_daily_count_label()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(4)
        layout.setSizeConstraint(QLayout.SetNoConstraint)
        layout.addWidget(self.eng_label)
        layout.addWidget(self.chn_label)
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
        self._apply_detected_tts_language(show_popup=False)

    def _current_lexicon_name(self) -> str:
        try:
            return Path(file).stem
        except Exception:
            return ""

    def _current_theme_name(self) -> str:
        for name, colors in themeColors.items():
            if len(colors) >= 2 and colors[0] == bgcolor and colors[1] == fgcolor:
                return name
        return ""

    def _current_font_name(self) -> str:
        for name, pair in fonts.items():
            if len(pair) >= 2 and pair[0] == ENGfont and pair[1] == CHNfont:
                return name
        return ""

    def _current_alpha_name(self) -> str:
        current = _alpha_to_transparency(alpha)
        best_name = next(iter(alphaValues.keys()))
        best_diff = 10.0
        for name, value in alphaValues.items():
            d = abs(float(value) - current)
            if d < best_diff:
                best_diff = d
                best_name = name
        return best_name

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

        font = QFont("Consolas", 9)
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
        chn_size = int(self.fs * font_scale)
        self.eng_label.setFont(QFont(ENGfont, eng_size))
        self.chn_label.setFont(QFont(CHNfont, chn_size))
        color = self._word_color or fgcolor
        self.eng_label.setStyleSheet(f"color: {color}; background: transparent;")
        self.chn_label.setStyleSheet(f"color: {color}; background: transparent;")
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
        chn_target = max(10, int(self.fs * font_scale))
        try:
            self._fit_label_font(self.eng_label, ENGfont, eng_target, 8, wrap=False)
            self._fit_label_font(self.chn_label, CHNfont, chn_target, 8, wrap=True)
        finally:
            self._fitting_fonts = False

    def _refresh_timer(self):
        interval = max(200, int(waitTime * 1000))
        self.auto_timer.setInterval(interval)
        self.auto_timer.start()

    def _next_word_item(self):
        global word_index
        if not word_items:
            getWord()
        if not word_items:
            return ("NoLexicon", "请在程序目录放入词库 .txt")
        if order == 1:
            item = word_items[word_index % len(word_items)]
            word_index = (word_index + 1) % len(word_items)
            return item
        return random.choice(word_items)

    def _push_history(self, eng: str, chn: str):
        if self._history_pos < len(self._history) - 1:
            self._history = self._history[: self._history_pos + 1]
        self._history.append((eng, chn))
        self._history_pos = len(self._history) - 1
        if len(self._history) > 5000:
            trim = len(self._history) - 5000
            self._history = self._history[trim:]
            self._history_pos = max(0, self._history_pos - trim)

    def _apply_word(self, eng: str, chn: str, count_progress: bool = True, track_history: bool = True):
        self.eng_label.setText(eng)
        self.chn_label.setText(chn)
        self.chn_label.setAlignment(Qt.AlignLeft if len(chn) > 16 else Qt.AlignCenter)
        self._fit_current_text_fonts()
        if not self._safe_visible_mode:
            QTimer.singleShot(0, self._fit_current_text_fonts)
        self._randomize_cat()
        if track_history:
            self._push_history(eng, chn)
        if count_progress:
            self._increment_daily_count()
        if auto_speak:
            speak_word(eng, restart=True)
        self.update()

    def next_word(self, force=False, count_progress=True):
        if handmode and not force:
            return
        eng, chn = self._next_word_item()
        self._apply_word(eng, chn, count_progress=count_progress, track_history=True)

    def _manual_next_word(self, count_progress=True):
        eng, chn = self._next_word_item()
        self._apply_word(eng, chn, count_progress=count_progress, track_history=True)

    def _show_previous_word(self):
        if self._history_pos <= 0:
            self._show_popup("提示", "已经是最早的词了")
            return
        self._history_pos -= 1
        eng, chn = self._history[self._history_pos]
        self._apply_word(eng, chn, count_progress=False, track_history=False)

    def _show_next_word(self, count_progress=True):
        # If user is browsing history, move forward inside history first.
        if self._history_pos < len(self._history) - 1:
            self._history_pos += 1
            eng, chn = self._history[self._history_pos]
            self._apply_word(eng, chn, count_progress=count_progress, track_history=False)
            return
        self._manual_next_word(count_progress=count_progress)

    def _speak_current_word(self):
        text = self.eng_label.text().strip()
        if not text:
            return
        speak_word(text, restart=True)

    def _show_popup(self, title: str, content: str):
        popup = CatPopup(self, title, content)
        center = self.geometry().center()
        popup.move(center.x() - popup.width() // 2, center.y() - popup.height() // 2)
        popup.show()
        self._popup = popup

    def _on_auto_change(self):
        self.next_word()

    def _set_order_mode(self, sequential: bool):
        global order
        order = 1 if sequential else 0
        self._show_popup("播放顺序", "顺序播放" if order == 1 else "随机播放")

    def _set_play_mode(self, manual: bool):
        global handmode
        handmode = 1 if manual else 0
        msg = "手动切换：双击、空格或右键下一词" if handmode == 1 else "自动切换已开启"
        self._show_popup("播放模式", msg)

    def _toggle_auto_speak(self, checked: bool):
        set_tts_enabled(bool(checked))
        if checked:
            self._speak_current_word()

    def _set_tts_language(self, lang: str):
        ok = set_tts_language(lang)
        if lang == "ja":
            if ok:
                self._show_popup("朗读语言", "已切换为日语朗读")
            elif "ja" not in _tts_voice_missing_warned:
                _tts_voice_missing_warned.add("ja")
                self._show_popup("朗读语言", "未检测到日语语音包，已切回英语朗读")
        else:
            self._show_popup("朗读语言", "已切换为英语朗读")

    def _apply_detected_tts_language(self, show_popup: bool = False):
        lang = detected_lexicon_lang if detected_lexicon_lang in {"en", "ja"} else "en"
        ok = set_tts_language(lang)
        if not show_popup:
            return
        if lang == "ja":
            if ok:
                self._show_popup("朗读语言", "已根据词库自动切换为日语")
            else:
                self._show_popup("朗读语言", "词库为日语，但系统无日语语音包，已使用英语")
        else:
            self._show_popup("朗读语言", "已根据词库自动切换为英语")

    def _copy_word(self):
        text = self.eng_label.text().strip()
        if not text:
            return
        if pyperclip is not None:
            pyperclip.copy(text)
        else:
            QApplication.clipboard().setText(text)
        self._show_popup("复制完成", f"已复制：{text}")

    def _favourite(self):
        try:
            with open(_p("收藏夹.txt"), "a", encoding="utf-8") as f:
                f.write(f"{self.eng_label.text()} {self.chn_label.text()}\n")
            self._show_popup("收藏成功", "当前词条已加入收藏夹")
        except OSError as exc:
            self._show_popup("收藏失败", str(exc))

    def _set_speed(self):
        global waitTime
        value, ok = QInputDialog.getDouble(
            self, "播放速度", "切换时间（秒）:", waitTime, 0.5, 30.0, 1
        )
        if ok:
            waitTime = value
            self._refresh_timer()
            self._show_popup("速度更新", f"切换间隔：{waitTime:.1f}s")

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
        self._show_popup("主题色", f"当前主题：{name}")

    def _set_font_by_name(self, name: str):
        global ENGfont, CHNfont
        if name not in fonts:
            return
        ENGfont, CHNfont = fonts[name]
        self._apply_fonts()
        self._show_popup("字体", f"当前字体：{name}")

    def _set_alpha_by_name(self, name: str):
        global alpha
        if name not in alphaValues:
            return
        transparency = float(alphaValues[name])
        alpha = _transparency_to_alpha(transparency)
        self.setWindowOpacity(alpha)
        self._show_popup("透明度", f"当前透明度：{name}")

    def _open_alpha_slider(self):
        global alpha
        origin_alpha = alpha
        dialog = QDialog(self)
        dialog.setWindowTitle("透明度调节")
        dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        dialog.setAttribute(Qt.WA_TranslucentBackground, True)
        dialog.setModal(True)
        dialog.resize(340, 170)

        card = QWidget(dialog)
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)
        title = DragHandleLabel("透明度调节（越大越透明）", target_window=dialog)
        value_label = QLabel("")
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(int(round(_alpha_to_transparency(alpha) * 100)))

        def _on_change(v: int):
            nonlocal value_label
            value_label.setText(f"当前透明度：{v}%")
            alpha_now = _transparency_to_alpha(v / 100.0)
            self.setWindowOpacity(alpha_now)
            QApplication.processEvents()

        slider.valueChanged.connect(_on_change)
        _on_change(slider.value())

        actions = QHBoxLayout()
        actions.addStretch(1)
        btn_cancel = QPushButton("取消")
        btn_ok = QPushButton("确定")
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_ok)

        def _on_cancel():
            self.setWindowOpacity(origin_alpha)
            dialog.reject()

        def _on_ok():
            global alpha
            alpha = _transparency_to_alpha(slider.value() / 100.0)
            dialog.accept()
            self._show_popup("透明度", f"当前透明度：{slider.value()}%")

        btn_cancel.clicked.connect(_on_cancel)
        btn_ok.clicked.connect(_on_ok)

        card_layout.addWidget(title)
        card_layout.addWidget(value_label)
        card_layout.addWidget(slider)
        card_layout.addLayout(actions)

        root = QVBoxLayout(dialog)
        root.setContentsMargins(8, 8, 8, 8)
        root.addWidget(card)

        dialog.setStyleSheet(
            """
            #card {
                background: #FFF7EC;
                border: 2px solid #F2C89B;
                border-radius: 14px;
            }
            QLabel { color: #6A4B3A; }
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
            """
        )
        center = self.geometry().center()
        dialog.move(center.x() - dialog.width() // 2, center.y() - dialog.height() // 2)
        if hasattr(dialog, "exec"):
            dialog.exec()
        else:
            dialog.exec_()

    def _set_word_color(self, color_hex: str, persist: bool = True):
        global word_color
        self._word_color = color_hex
        if persist:
            word_color = self._word_color
        self._apply_fonts()
        if not persist:
            QApplication.processEvents()

    def _set_counter_color(self, color_hex: str, persist: bool = True):
        global counter_color
        self._counter_color = color_hex
        if persist:
            counter_color = self._counter_color
        self._refresh_daily_count_label()
        self.update()
        if not persist:
            QApplication.processEvents()

    def _pick_color_styled(self, current: QColor, title: str, on_change=None):
        source_pixmaps = [p for p in self._cat_pixmaps if p is not None and not p.isNull()]
        if not source_pixmaps and self.cat_corner.pixmap() is not None:
            source_pixmaps = [self.cat_corner.pixmap()]
        return CuteColorDialog.get_color(
            self,
            title,
            current.name(),
            cat_pixmaps=source_pixmaps,
            on_change=on_change,
        )

    def _pick_word_color_palette(self):
        origin = self._word_color or fgcolor
        current = QColor(origin)
        chosen = self._pick_color_styled(
            current,
            "单词颜色",
            on_change=lambda c: self._set_word_color(c.name(), persist=False),
        )
        if chosen is None:
            self._set_word_color(origin, persist=False)
            return
        self._set_word_color(chosen.name(), persist=True)

    def _pick_counter_color_palette(self):
        origin = self._counter_color or "#F7F0E8"
        current = QColor(origin)
        chosen = self._pick_color_styled(
            current,
            "数字颜色",
            on_change=lambda c: self._set_counter_color(c.name(), persist=False),
        )
        if chosen is None:
            self._set_counter_color(origin, persist=False)
            return
        self._set_counter_color(chosen.name(), persist=True)

    def _set_lexicon(self, selected_name: str):
        global file, default_lexicon
        if selected_name not in lexicon:
            return
        file = lexicon[selected_name]
        default_lexicon = selected_name
        getWord()
        self._apply_detected_tts_language(show_popup=True)
        self._history = []
        self._history_pos = -1
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
        current = self._current_lexicon_name()
        for name in lexicon.keys():
            action = parent_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(name == current)
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

        # Section 1: frequently used actions (top)
        menu.addAction("朗读当前词", self._speak_current_word)
        auto_action = QAction("自动朗读", self, checkable=True)
        auto_action.setChecked(bool(auto_speak))
        auto_action.toggled.connect(self._toggle_auto_speak)
        menu.addAction(auto_action)
        menu.addAction("播放速度", self._set_speed)
        menu.addAction("复制该词", self._copy_word)
        menu.addAction("收藏该词", self._favourite)
        menu.addAction("清零今日计数", self._reset_daily_count)

        # Section 2: arrow sub-menus grouped in the middle
        menu.addSeparator()
        mode_menu = menu.addMenu("播放模式")
        mode_manual = mode_menu.addAction("手动")
        mode_manual.setCheckable(True)
        mode_manual.setChecked(handmode == 1)
        mode_manual.triggered.connect(lambda checked=False: self._set_play_mode(True))
        mode_auto = mode_menu.addAction("自动")
        mode_auto.setCheckable(True)
        mode_auto.setChecked(handmode == 0)
        mode_auto.triggered.connect(lambda checked=False: self._set_play_mode(False))

        order_menu = menu.addMenu("播放顺序")
        order_seq = order_menu.addAction("顺序")
        order_seq.setCheckable(True)
        order_seq.setChecked(order == 1)
        order_seq.triggered.connect(lambda checked=False: self._set_order_mode(True))
        order_rand = order_menu.addAction("随机")
        order_rand.setCheckable(True)
        order_rand.setChecked(order == 0)
        order_rand.triggered.connect(lambda checked=False: self._set_order_mode(False))

        word_color_menu = menu.addMenu("单词颜色")
        word_color_menu.addAction("打开调色板", self._pick_word_color_palette)
        counter_color_menu = menu.addMenu("数字颜色")
        counter_color_menu.addAction("打开调色板", self._pick_counter_color_palette)
        theme_menu = menu.addMenu("主题色")
        current_theme = self._current_theme_name()
        for theme_name in themeColors.keys():
            action = theme_menu.addAction(theme_name)
            action.setCheckable(True)
            action.setChecked(theme_name == current_theme)
            action.triggered.connect(
                lambda checked=False, n=theme_name: self._set_theme_by_name(n)
            )

        font_menu = menu.addMenu("字体")
        current_font = self._current_font_name()
        for font_name in fonts.keys():
            action = font_menu.addAction(font_name)
            action.setCheckable(True)
            action.setChecked(font_name == current_font)
            action.triggered.connect(
                lambda checked=False, n=font_name: self._set_font_by_name(n)
            )

        menu.addAction("透明度调节", self._open_alpha_slider)
        lexicon_menu = menu.addMenu("切换词库")
        self._rebuild_lexicon_menu(lexicon_menu)

        # Section 3: persistence & app control (bottom)
        menu.addSeparator()
        menu.addAction("全屏模式", self._toggle_fullscreen)
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
            self._show_next_word(count_progress=True)
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

    def keyPressEvent(self, event):
        if event.key() in {Qt.Key_Space, Qt.Key_Right}:
            self._show_next_word(count_progress=True)
            event.accept()
            return
        if event.key() == Qt.Key_Left:
            self._show_previous_word()
            event.accept()
            return
        if event.key() == Qt.Key_R:
            self._speak_current_word()
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


def main():
    _log(f"=== startup begin (frozen={getattr(sys, 'frozen', False)}, backend={QT_BACKEND}) ===")
    _log(f"base_dir={BASE_DIR}")
    _log(f"python={sys.version}")
    _log(f"argv={sys.argv}")

    bootstrap_runtime_files()
    _log("bootstrap_runtime_files ok")

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
    app.setFont(QFont("Microsoft YaHei UI", 10))
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

