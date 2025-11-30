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

### 2. 数据波形生成器 (`数据波形生成器.py`)

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

**WAV 转 C 数组工具：**
- 仅需 Python 标准库（`os`, `textwrap`）

**数据波形生成器：**
- `tkinter`（通常随 Python 安装）
- `matplotlib`

安装依赖：

```bash
pip install matplotlib
```

---

## 📝 注意事项

### WAV 转 C 数组工具

- 生成的数组包含完整的 WAV 文件数据（包括文件头）
- 变量名会自动处理特殊字符（`-`、空格等会替换为 `_`）
- 数组大小在声明时已指定，无需额外的长度变量
- 默认只处理指定目录的第一层，如需递归处理子目录，设置 `recursive=True`

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

