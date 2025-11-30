"""
WAV 文件转 C 数组工具

功能说明：
    本工具用于将 WAV 音频文件转换为 C 语言数组格式，方便在嵌入式系统中使用音频数据。
    
主要功能：
    1. wav_to_c_array(): 将单个 WAV 文件转换为 C 数组字符串
    2. generate_single_c_file(): 批量处理目录中的 WAV 文件，生成统一的 C 源文件
    
使用方法：
    直接运行脚本，或导入模块调用相应函数。
    
输出格式：
    生成的 C 数组包含：
    - const unsigned char 数组（音频数据）
    
作者：Auto-generated
"""

import os
import binascii
import textwrap

def wav_to_c_array(input_path, var_prefix="pcm_data"):
    """将 WAV 文件转成 C 数组字符串（不写文件，返回字符串）"""
    with open(input_path, "rb") as f:
        data = f.read()

    # 转成 0xXX 格式
    hex_list = [f"0x{b:02X}" for b in data]
    hex_body = ", ".join(hex_list)

    # 按行格式化
    hex_lines = textwrap.wrap(hex_body, 16 * 6)

    # 安全的变量名
    name = os.path.splitext(os.path.basename(input_path))[0]
    name = name.replace("-", "_").replace(" ", "_")

    array_lines = []
    array_lines.append(f"// File: {os.path.basename(input_path)}")
    array_lines.append(f"const unsigned char {var_prefix}_{name}[{len(data)}] = {{")

    for line in hex_lines:
        array_lines.append("    " + line)

    array_lines.append("};")
    array_lines.append("")

    return "\n".join(array_lines)


def generate_single_c_file(input_dir, output_c_file="audio_data.c", recursive=False):
    """批量读取 WAV，并统一写入一个 C 文件"""
    all_arrays = []

    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(".wav"):
                path = os.path.join(root, file)
                print(f"处理: {path}")
                array_str = wav_to_c_array(path)
                all_arrays.append(array_str)

        if not recursive:
            break  # 不递归

    # 汇总写入单一 C 文件
    with open(output_c_file, "w", encoding="utf-8") as f:
        f.write("// Auto-generated WAV → C arrays\n\n")
        f.write("#include <stdint.h>\n\n")
        f.write("\n\n".join(all_arrays))

    print(f"\n✔ 已生成 C 文件: {output_c_file}")


if __name__ == "__main__":
    input_directory = ""
    if input_directory == "":
        input_directory = input("请输入输入目录: ")
        if os.path.exists(input_directory):
            print(f"输入目录: {input_directory}")
            input_directory = input_directory
        else:
            print(f"输入目录不存在: {input_directory}")
            exit(1)
    else:
        print(f"输入目录: {input_directory}")
        input_directory = input_directory
    generate_single_c_file(input_directory, f"{input_directory}/audio_data.c", recursive=False)

