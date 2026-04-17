# W2R Cattoon (Desktop Vocabulary Overlay)

[中文说明](README.md) | English

A lightweight Windows desktop overlay app for vocabulary learning, with custom lexicons, auto/manual playback, and English/Japanese TTS support.

## Highlights
- Floating vocabulary window that stays out of your way
- Lexicon switching with automatic EN/JA language detection
- Quick controls via mouse, keyboard, and context menu
- Customizable UI: theme, fonts, word/counter colors, opacity slider
- Daily progress counter and favorites support

## Requirements
- Windows 10 / 11
- Python 3.10+

## Quick Start
```powershell
cd catword
python -m pip install -r requirements.txt
python W2R.py
```

## Usage
### Basic Controls
- Move window: drag with left mouse button
- Next word: double-click / `Space` / `Right`
- Previous word: `Left`
- Replay current word: `R`
- Resize: mouse wheel
- Open settings: right-click on the window

### Context Menu
- `Playback Mode`: Manual / Auto
- `Playback Order`: Sequential / Random
- `Playback Speed`
- `Read Current Word`, `Auto Read`
- `Reset Daily Count`
- `Copy Word`, `Favorite Word`
- `Word Color`, `Counter Color`, `Theme`, `Font`, `Opacity Slider`
- `Switch Lexicon`
- `Save Preferences`, `Restore Preferences`

## Custom Lexicon
Put your `.txt` lexicon files in `catword/`, then use `Switch Lexicon` from the context menu.

Recommended format (one entry per line, tab-separated):
```text
reinforcement learning	强化学习（RL）
policy optimization	策略优化
```

## Japanese TTS (Voice Pack)
The app auto-detects lexicon language. If your lexicon is Japanese but no Japanese voice is installed, it falls back to English voice.

### Install Japanese Speech Pack (Windows 11)
1. Open `Settings -> Time & language -> Language & region`
2. Add `Japanese`
3. Open `Japanese -> Language options`
4. Install `Speech`
5. Restart Windows and run the app again

### Install Japanese Speech Pack (Windows 10)
1. Open `Settings -> Time & Language -> Language`
2. Add `Japanese`
3. Open language options and install `Speech`
4. Restart Windows and run the app again

Note: Japanese voice packs are system-level Windows components and cannot be reliably bundled inside this repository.

## Packaging (Optional)
Run from project root:
```powershell
pyinstaller --noconfirm --clean W2R_Cattoon_PySide6.spec
```

## Project Structure
```text
catword/                  # Main application source
  W2R.py                  # Entry point
  assets/                 # Icons and theme resources
  *.txt                   # Lexicon files
README.md                 # Chinese docs
README_EN.md              # English docs
W2R_Cattoon_PySide6.spec  # PyInstaller spec
```
