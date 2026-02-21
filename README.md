# PythonTools - 嵌入式与数据处理工具集

本仓库包含一组专为嵌入式开发优化的 Python 脚本，旨在简化音频、字体、串口数据及发票校验等日常任务。

---

## 1. WAV <-> C 数组互转工具 (`wav_to_c_array.py`)
**专为嵌入式音频播放设计。**

- **WAV -> C数组**: 批量将目录下的 WAV 文件转换为包含完整 Header 的 C 数组。
- **C数组 -> WAV**: 100% 还原还原 C 文件中的数据到 WAV，确保字节级一致性。
- **GUI 界面**: 支持目录选择和实时转换日志。

---

## 2. LVGL 字体助手 (`lvgl_font_tool.py`)
**LVGL 界面开发的字库瘦身与管理利器。**

- **逆向解析**: 能够从现有的 LVGL `.c` 字体文件中“捞出”已有的字符和图标码点。
- **源码扫描**: 自动递归扫描项目目录，提取代码中出现的所有汉字。
- **增量更新**: 在提取结果基础上，支持手动编辑或输入 Unicode 码点追加图标（如 FontAwesome）。
- **官方转换**: 一键调用 `lv_font_conv` 生成标准 C 字库。
- **前提条件**: 需安装 Node.js 及其转换工具：`npm install -g lv_font_conv`。

---

## 3. 串口波形显示 (`serial_waveform/`)
**实时串口数据可视化工具。**

- **功能**: 接收串口数据并实时绘制波形，支持多通道显示。
- **运行**: `python serial_waveform/serial_waveform_gui.py`

---

## 4. 数据波形生成器 (`数据波形生成器.py`)
用于生成正弦波、方波等特定规律的数据，支持导出。

---

## 5. 发票检查工具 (`fapiao_check.py`)
快速校验发票信息。

---

## 环境要求
- **Python 3.x**
- **标准库**: `tkinter`, `re`, `os`, `subprocess` 等。
- **第三方库**:
  - 串口工具需安装: `pip install pyserial`
  - 若运行 `lvgl_font_tool.py` 且需要预览字体，可能需要 `pip install Pillow`。

## 运行方式
所有工具均支持直接运行：
```bash
python [文件名].py
```
