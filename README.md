# PythonTools

Python 实用工具集合，包含多个便捷的开发辅助工具。

## 📦 工具列表

### 1. WAV 转 C 数组工具 (`wav_to_c_array.py`)

将 WAV 音频文件转换为 C 语言数组格式，方便在嵌入式系统中使用音频数据。

#### 功能特点

- ✅ 支持单个 WAV 文件转换
- ✅ 支持批量处理目录中的 WAV 文件
- ✅ 自动生成符合 C 语言规范的数组代码
- ✅ 自动处理变量名（去除特殊字符，确保合法性）
- ✅ 可配置变量名前缀

#### 使用方法

**方式一：直接运行脚本**

修改脚本中的 `input_directory` 路径，然后运行：

```bash
python wav_to_c_array.py
```

**方式二：作为模块导入使用**

```python
from wav_to_c_array import wav_to_c_array, generate_single_c_file

# 转换单个文件
c_array_str = wav_to_c_array("audio.wav", var_prefix="pcm_data")
print(c_array_str)

# 批量转换目录中的所有 WAV 文件
generate_single_c_file(
    input_dir="./audio_files",
    output_c_file="audio_data.c",
    recursive=False  # True 表示递归处理子目录
)
```

#### 输出格式

生成的 C 文件示例：

```c
// Auto-generated WAV → C arrays

#include <stdint.h>

// File: audio.wav
const unsigned char pcm_data_audio[1234] = {
    0x52, 0x49, 0x46, 0x46, 0x24, 0x08, 0x00, 0x00,
    0x57, 0x41, 0x56, 0x45, 0x66, 0x6D, 0x74, 0x20,
    ...
};

// File: beep.wav
const unsigned char pcm_data_beep[5678] = {
    ...
};
```

#### 参数说明

- `input_path`: WAV 文件路径
- `var_prefix`: 变量名前缀（默认：`"pcm_data"`）
- `input_dir`: 输入目录路径
- `output_c_file`: 输出的 C 文件路径（默认：`"audio_data.c"`）
- `recursive`: 是否递归处理子目录（默认：`False`）

---

### 2. 串口实时波形显示工具 (`serial_waveform/serial_waveform_gui.py`)

基于 Tkinter 和 Matplotlib 的串口数据实时波形可视化工具，支持实时显示串口接收的数据波形。

#### 功能特点

- ✅ 实时串口数据波形显示
- ✅ 自动检测可用串口
- ✅ 支持多种波特率（9600, 19200, 38400, 57600, 115200, 230400, 460800）
- ✅ 自动连接功能
- ✅ 暂停/继续显示
- ✅ Y 轴自动缩放
- ✅ 手动缩放控制（Y+、Y-、Reset）
- ✅ 清空缓冲区
- ✅ ALC/AGC 参数设置（支持 AT 命令配置）
- ✅ 配置自动保存和恢复
- ✅ 支持多种数据格式（自动提取数字）

#### 使用方法

**方式一：直接运行脚本**

```bash
cd serial_waveform
python serial_waveform_gui.py
```

**方式二：从项目根目录运行**

```bash
python serial_waveform/serial_waveform_gui.py
```

#### 使用步骤

1. 选择串口和波特率
2. 点击 "Connect" 连接串口
3. 串口数据会自动显示为实时波形
4. 使用 "Pause" 暂停显示，使用 "Resume" 继续
5. 使用 "Y+"、"Y-" 调整 Y 轴缩放，使用 "Reset" 重置视图
6. 勾选 "Auto Y" 启用自动 Y 轴缩放
7. 点击 "ALC设置" 可以配置 ALC/AGC 参数（需要设备支持 AT 命令）

#### 数据格式

工具会自动从串口接收的数据中提取数字，支持以下格式：
- 单行单个数字：`1234`
- 单行多个数字：`1234 5678 9012`
- 混合格式：`Value: 1234, 5678\n9012`

#### 配置说明

配置文件 `serial_waveform_gui.json` 会自动保存以下设置：
- 串口端口
- 波特率
- 自动连接选项
- 自动缩放选项

---

### 3. 数据波形生成器 (`数据波形生成器.py`)

基于 Tkinter 和 Matplotlib 的图形化数据波形可视化工具。

#### 功能特点

- ✅ 图形化界面，操作简单
- ✅ 支持多种分隔符（空格、逗号、换行）
- ✅ 实时绘制数据波形图
- ✅ 右键菜单支持（剪切、复制、粘贴、全选）
- ✅ 固定 Y 轴范围，便于对比

#### 使用方法

直接运行脚本：

```bash
python 数据波形生成器.py
```

#### 使用步骤

1. 在文本框中输入数据，支持以下格式：
   - 空格分隔：`1 2 3 4 5`
   - 逗号分隔：`1,2,3,4,5`
   - 换行分隔：每行一个数字
   - 混合分隔：`1, 2 3\n4,5`

2. 点击"生成波形"按钮查看波形图

3. 点击"清除输入"按钮清空文本框

#### 示例输入

```
10, 20, 30, 25, 15, 5, 10, 20, 30, 40, 50, 45, 35, 25, 15
```

---

## 🔧 环境要求

### Python 版本

- Python 3.6+

### 依赖库

项目已提供 `requirements.txt` 文件，包含所有依赖。

**安装所有依赖：**

```bash
pip install -r requirements.txt
```

**各工具依赖说明：**

- **WAV 转 C 数组工具**：仅需 Python 标准库（`os`, `textwrap`, `binascii`）
- **串口实时波形显示工具**：需要 `pyserial`, `numpy`, `matplotlib`, `tkinter`
- **数据波形生成器**：需要 `matplotlib`, `tkinter`（通常随 Python 安装）

**主要依赖包：**

- `pyserial>=3.5` - 串口通信
- `numpy>=1.20.0` - 数值计算
- `matplotlib>=3.5.0` - 数据可视化

---

## 📁 项目结构

```
PythonTools/
├── serial_waveform/          # 串口实时波形显示工具
│   ├── serial_waveform_gui.py
│   ├── serial_waveform_gui.json
│   └── alc/                   # ALC/AGC 参数配置模块
│       ├── __init__.py
│       └── alc_config.py
├── wav_to_c_array.py          # WAV 转 C 数组工具
├── 数据波形生成器.py          # 数据波形生成器
├── requirements.txt           # 项目依赖
└── README.md                  # 项目说明
```

## 📝 注意事项

### WAV 转 C 数组工具

- 生成的数组包含完整的 WAV 文件数据（包括文件头）
- 变量名会自动处理特殊字符（`-`、空格等会替换为 `_`）
- 数组大小在声明时已指定，无需额外的长度变量
- 默认只处理指定目录的第一层，如需递归处理子目录，设置 `recursive=True`

### 串口实时波形显示工具

- 需要串口设备支持，确保串口驱动已正确安装
- 数据缓冲区大小为 1024 个采样点
- Y 轴默认范围为 -32768 到 32767（16 位整数范围）
- ALC 参数设置功能需要设备支持 AT 命令协议
- 配置文件会自动保存在工具所在目录

### 数据波形生成器

- Y 轴范围固定为 -10 到 100
- 输入数据必须是整数
- 如果输入格式不正确，会显示错误提示

---

## 📄 许可证

本项目为实用工具集合，可自由使用和修改。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📧 联系方式

如有问题或建议，请通过 Issue 反馈。

