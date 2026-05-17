# 酷和弦 — Cool Chord EDM Synthesizer

Python 桌面 EDM 和弦合成器，集成 Serum 风格波表引擎、智能和弦生成器、鼓机和效果器。

## 功能

| 模块 | 功能 |
|------|------|
| **波表合成器** | Serum 风格双波表振荡器 (10 套波表 × 64 帧), 6 种 Warp 模式, 7-voice Unison 齐奏, 子振荡器, 噪声源 |
| **调制矩阵** | 16 槽任意源→目标调制, LFO × 2, 滤波器/放大器 ADSR |
| **鼓机** | 10 种鼓音色 (Kick/Snare/HH/Clap/Crash/Toms/Rim), 6 套预设 (909/808/EDM/Trap/Lo-Fi/Acoustic), 16 步音序器, 一键推送到钢琴卷帘 |
| **和弦生成** | 10 种 EDM 风格 (House/Trance/Techno/Dubstep 等), 智能声部配置, 一键推送到钢琴卷帘 |
| **钢琴卷帘** | QGraphicsView 编辑器, 拖拽/缩放/量化/撤销重做, 播放进度线, 鼓组 MIDI 支持 |
| **效果器** | 3-band EQ → Reverb → Delay → Chorus → BitCrusher → Distortion → Compressor 效果链, 带 Bypass |
| **导出** | WAV 立体声 + 分轨 (Synth/Drums/Master), MIDI 单轨/多轨 |
| **MIDI** | 实时 MIDI I/O, CC Learn 映射 |
| **预设** | 21 个 Serum 风格预设 (Bass/Lead/Pad/Pluck/Keys/FX) |

## 技术栈

- **Python** 3.11
- **音频** sounddevice + numpy + scipy (实时 DSP 回调, 44.1kHz, 512 block, float32)
- **GUI** PySide6 (QGraphicsView 钢琴卷帘, QTabWidget 右侧面板, 自定义旋钮)
- **MIDI** mido + python-rtmidi
- **音乐理论** music21
- **导出** soundfile

## 快速启动

```bash
source .venv/Scripts/activate   # Git Bash
python src/main.py              # 启动程序

pytest tests/ -x                # 运行测试 (221 tests)
black --line-length 120 src/ tests/   # 格式化
ruff check src/ tests/          # Lint
mypy src/                       # 类型检查
```

## 项目结构

```
src/
├── audio/        DSP 引擎 (波表/振荡器/滤波器/包络/LFO/效果器/压缩器/鼓合成/鼓音色)
├── midi/         MIDI I/O (实时处理/文件读写/事件)
├── chord/        和弦生成引擎 (音乐理论/风格/生成器/鼓模式)
├── sequencer/    音序器 (钢琴卷帘/鼓模式/鼓音序器/传输/轨道)
├── ui/           PySide6 GUI (主窗口/钢琴卷帘/键盘/合成器/鼓面板/和弦面板/效果器面板/调制矩阵/步进音序器/波形显示)
├── export/       WAV 和 MIDI 导出
└── utils/        配置/日志/资源路径

tests/            26 测试文件, 221 测试
resources/        预设 (21 JSON), 风格定义, 鼓组, 波表
```

## 架构

- **多线程**: GUI (PySide6 主线程) + 音频 (sounddevice 回调) + MIDI (rtmidi)
- **线程安全**: queue.Queue 通信
- **向量化 DSP**: scipy lfilter (BiquadFilter), numpy 批量运算, 预分配缓冲区
- **离线渲染**: `engine.render_offline()` / `render_offline_stems()` 用于导出

## 质量

| 门禁 | 状态 |
|------|------|
| black | pass (80 files) |
| ruff | pass |
| mypy strict | pass (57 source files) |
| pytest | 221 passed |

## 更新日志

### v1.1.0 — Serum 改造 + 性能优化 + UI 改进
- Serum 风格波表引擎 (10 套 × 64 帧), 6 种 Warp, 7-voice Unison
- 16 槽调制矩阵
- 6 个新 Serum 预设 (WT Bass, Dubstep Growl, WT Lead, Jaws Supersaw, WT Pad, WT Stab)
- BiquadFilter 矢量化 (scipy lfilter), EQ/Compressor 优化, BitCrusher 矢量化
- 右侧面板 QTabWidget 布局, 各面板独立 QScrollArea 滚动
- 鼓机 → 钢琴卷帘一键推送 (GM MIDI 映射)
- 钢琴卷帘动态场景矩形 + 播放进度线

### v1.0.0 — 全部 12 Phase 完成
