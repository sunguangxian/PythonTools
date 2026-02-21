# PythonTools - 音频与数据处理工具集

本仓库包含一组用于嵌入式开发和数据分析的 Python 脚本。

## 1. WAV <-> C 数组互转工具 (`wav_to_c_array.py`)

这是一个带有图形界面 (GUI) 的工具，专门用于在 WAV 音频文件与 C 语言字节数组之间进行双向转换。

### 主要功能
- **WAV -> C 数组**: 将一个目录下的所有 WAV 文件批量转换为一个 C 源文件。生成的 C 数组包含完整的 WAV 文件头，可直接在嵌入式系统（如 ESP32, STM32）中播放。
- **C 数组 -> WAV**: 从本工具生成的 C 文件中解析出数组，并 100% 还原为原始的 WAV 文件，确保字节级一致性。
- **图形界面**: 基于 Python 自带的 `tkinter`，无需安装额外库。

### 使用方法
直接运行脚本即可启动 GUI：
```bash
python wav_to_c_array.py
```

---

## 2. 数据波形生成器 (`数据波形生成器.py`)
用于生成特定规律的数据波形文件。

---

## 3. 发票检查工具 (`fapiao_check.py`)
用于发票信息的快速校验。

---

## 4. 串口波形显示 (`serial_waveform/`)
包含串口数据采集与波形实时显示的 GUI 工具。

### 运行
```bash
python serial_waveform/serial_waveform_gui.py
```

## 环境要求
- Python 3.x
- 标准库支持 (tkinter, re, os 等)
- 若运行串口相关工具，可能需要安装 `pyserial`:
  ```bash
  pip install -r requirements.txt
  ```
