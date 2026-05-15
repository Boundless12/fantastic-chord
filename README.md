# 酷和弦 — Cool Chord EDM Synthesizer

Python 桌面 EDM 和弦合成器，集成实时合成引擎、和弦生成器、鼓机和效果器。

## 功能

| 模块 | 功能 |
|------|------|
| **合成器** | 双振荡器 + 噪声 + FM，多模式滤波器，4 级包络 (AMP + Filter)，2 LFO，滑音 |
| **鼓机** | 10 种鼓音色 (Kick/Snare/HH/Clap/Crash/Toms/Rim)，6 套预设 (909/808/EDM/Trap/Lo-Fi/Acoustic)，16 步音序器 |
| **和弦生成** | 10 种 EDM 风格 (House/Trance/Techno/Dubstep 等)，智能声部配置，一键推送到钢琴卷帘 |
| **钢琴卷帘** | QGraphicsView 编辑器，支持拖拽/缩放/量化/撤销重做，MIDI 导入 |
| **效果器** | Reverb / Delay / Chorus / Distortion 全局效果混音台，带 Bypass |
| **导出** | WAV 立体声 + 分轨 (Synth/Drums/Master)，MIDI 单轨/多轨 |
| **MIDI** | 实时 MIDI I/O，CC Learn 映射 |

## 技术栈

- **Python** 3.11
- **音频** sounddevice + numpy (实时 DSP 回调, 44.1kHz, 512 block, float32)
- **GUI** PySide6 (QGraphicsView 钢琴卷帘, 自定义 QWidget 旋钮)
- **MIDI** mido + python-rtmidi
- **音乐理论** music21
- **导出** soundfile

## 快速启动

```bash
# 激活虚拟环境
source .venv/Scripts/activate   # Git Bash / WSL
# .venv\Scripts\activate        # CMD

# 安装依赖
pip install -r requirements.txt

# 运行
python src/main.py

# 测试
pytest tests/ -x

# 代码检查
black --line-length 120 src/ tests/
ruff check src/ tests/
mypy src/
```

## 项目结构

```
src/
├── audio/        DSP 引擎 (振荡器/滤波器/包络/效果器/鼓合成/鼓音色)
├── midi/         MIDI I/O (实时处理/文件读写/事件)
├── chord/        和弦生成引擎 (音乐理论/风格/生成器/声部配置)
├── sequencer/    音序器 (钢琴卷帘/鼓音序器/传输/模式)
├── ui/           PySide6 GUI (主窗口/钢琴卷帘/键盘/合成器面板/鼓面板/和弦面板/效果器面板)
├── export/       WAV 和 MIDI 导出
└── utils/        配置/日志/资源路径

tests/            26 测试文件, 221 测试
resources/        风格定义 JSON, 预设, 鼓组, 波表
```

## 架构

- **多线程**: GUI (PySide6 主线程) + 音频 (sounddevice 回调) + MIDI (rtmidi)
- **线程安全通信**: queue.Queue
- **块 DSP**: 纯 numpy, BLOCK_SIZE=512, SAMPLE_RATE=44100, float32
- **离线渲染**: `engine.render_offline()` / `render_offline_stems()` 用于导出

## 质量

| 门禁 | 状态 |
|------|------|
| black --check | pass |
| ruff check | pass |
| mypy strict | pass (53 source files) |
| pytest | 221 passed |

## 版本

1.0.0 — 全部 12 Phase 完成 (项目脚手架 → 打磨)
