# W2R Cattoon

`W2R Cattoon` 是一个桌面悬浮背词工具，支持 `Windows` 和 `Ubuntu`。

程序启动后会显示一个可拖动的悬浮窗，用来循环展示单词内容，适合放在桌面边角持续刷词。

## 功能概览

- 悬浮窗常驻桌面，支持拖动和滚轮缩放
- 手动切词 / 自动切词
- 顺序播放 / 随机播放
- 主窗口显示词、词性、词义，并可内联显示例句、拓展
- 详情弹窗显示完整词条信息
- 单词朗读、自动朗读
- 切换词库、复制单词、收藏单词
- 颜色、字体、透明度等外观设置
- Ubuntu 支持桌面图标一键安装

## 快速开始

### Ubuntu 22.04+

先安装系统依赖：

```bash
sudo apt update
sudo apt install -y libxcb-cursor0 libxkbcommon-x11-0 speech-dispatcher
```

再安装 Python 依赖：

```bash
cd catword
python3 -m pip install -r requirements.txt
```

启动程序：

```bash
cd /path/to/win-floating-vocab
./launch_w2r.sh
```

也可以直接运行主程序：

```bash
cd /path/to/win-floating-vocab/catword
python3 W2R.py
```

### Windows

安装依赖：

```powershell
cd catword
python -m pip install -r requirements.txt
```

启动程序：

```powershell
cd catword
python W2R.py
```

## Ubuntu 桌面图标

仓库根目录提供了一键安装脚本：

```bash
cd /path/to/win-floating-vocab
./install_desktop_icon.sh
```

脚本会自动：

- 按当前仓库绝对路径生成 `.desktop` 启动器
- 安装到应用菜单 `~/.local/share/applications/`
- 安装到桌面目录 `~/Desktop/`
- 尝试把桌面图标标记为可信启动器

安装后可以从两处启动：

- 应用菜单中的 `W2R Cattoon`
- 桌面图标 `W2R_Cattoon.desktop`

注意：

- 如果桌面第一次点击仍显示为不受信任，请右键图标后选择“允许启动”
- 如果你后续移动了仓库目录，请重新执行一次 `./install_desktop_icon.sh`

## 使用说明

### 基本操作

- 鼠标左键拖动窗口
- 双击窗口，或按 `空格` / `→` 切到下一个词
- 按 `←` 返回上一个已浏览的词
- 按 `R` 重新朗读当前词
- 按 `D`，或右键菜单 `查看词条详情` 打开当前词条详情
- 鼠标滚轮缩放窗口
- 右键打开完整设置菜单

### 显示逻辑

- 主窗口默认显示：词、词性、词义
- 如果词条带有 `例句` 或 `拓展`，会直接在主窗口内联显示
- `查看词条详情` 会弹出完整词条面板，显示词性、词义、例句、拓展、分类

### 右键菜单常用项

- `切换模式`：手动切换 / 自动切换
- `切换顺序`：顺序播放 / 随机播放
- `播放速度`：调整自动切词速度
- `朗读当前词`、`自动朗读`
- `清零今日计数`
- `复制该词`、`收藏该词`
- `查看词条详情`
- `单词颜色`、`数字颜色`、`主题色`、`字体`、`透明度`
- `切换词库`
- `保存配置`、`恢复配置`
- `退出`

## 自定义词库

词库文件放在 `catword/` 目录下，推荐使用 `UTF-8` 编码的 `.txt` 文件。

### 简单格式

推荐使用 `TAB` 分隔，一行一个词条：

```text
reinforcement learning	强化学习（RL）
policy optimization	策略优化
```

### 富词条格式

项目也支持更丰富的词条字段。

`my-ielts` 兼容格式：

```text
abandon|v.|放弃；抛弃|He abandoned the plan.|abandoned adj. 被遗弃的
```

扩展 `TAB` 格式：

```text
word	pos	meaning	example	extra	category
```

富词条支持这些字段：

- 词
- 词性
- 词义
- 例句
- 拓展
- 分类

导入后可在程序右键菜单里使用 `切换词库` 进行切换。

## 自带词表

- `catword/高考3500词汇表.txt`
- `catword/高考3500词汇表_乱序.txt`
- `catword/文献术语精选_280.txt`
- `catword/文献术语精选_280_乱序.txt`
- `catword/雅思词汇真经_扩展.txt`

其中 `catword/雅思词汇真经_扩展.txt` 已接入更丰富的词条内容，适合直接体验富词条显示效果。

## Ubuntu 兼容性说明

- 朗读功能优先使用 `spd-say`，会自动回退到 `espeak-ng` / `espeak`
- 缺少 `libxcb-cursor0` 时，程序会在启动前给出明确安装提示
- 程序会自动回退到系统中已安装的等宽字体和中文字体
- 收藏文件默认写入 `catword/favorites.txt`

## 仓库中的辅助脚本

- `launch_w2r.sh`：从仓库根目录快速启动 Ubuntu 版本
- `install_desktop_icon.sh`：一键安装 Ubuntu 应用菜单和桌面图标

## 打包

如果你要自己使用 `PyInstaller` 打包：

```bash
pyinstaller --noconfirm --clean W2R_Cattoon_PySide6.spec
```

`W2R_Cattoon_PySide6.spec` 已调整为兼容 Windows / Linux 的路径写法。
