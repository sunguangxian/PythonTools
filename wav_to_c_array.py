"""
WAV 文件与 C 数组 双向转换工具 (带UI版)

功能说明：
    1. WAV -> C数组：支持选择【单个WAV文件】或【整个目录】转换为 C 语言数组。
    2. C数组 -> WAV：从生成的 C 源文件中解析出数据，还原成完全一致的 WAV 音频文件。
    
保证相互转换的数据内容完全一致（字节级 100% 匹配）。
"""

import os
import re
import textwrap
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# ================= 核心逻辑部分 =================

def wav_to_c_array(input_path, var_prefix="pcm_data"):
    """将 WAV 文件转成 C 数组字符串"""
    with open(input_path, "rb") as f:
        data = f.read()

    # 转成 0xXX 格式
    hex_list = [f"0x{b:02X}" for b in data]
    hex_body = ", ".join(hex_list)

    # 按行格式化，每行 16 个字节
    hex_lines = textwrap.wrap(hex_body, 16 * 6)

    # 生成安全的变量名
    name = os.path.splitext(os.path.basename(input_path))[0]
    name = name.replace("-", "_").replace(" ", "_")
    var_name = f"{var_prefix}_{name}"

    array_lines = []
    array_lines.append(f"// File: {os.path.basename(input_path)}")
    array_lines.append(f"const unsigned char {var_name}[{len(data)}] = {{")

    for line in hex_lines:
        array_lines.append("    " + line)

    array_lines.append("};")
    array_lines.append("")

    return "\n".join(array_lines)


def c_array_to_wav(c_file_path, output_dir, var_prefix="pcm_data"):
    """从 C 文件中解析数组并还原为 WAV 文件，返回还原的文件数量"""
    with open(c_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 使用正则表达式匹配所有的 C 数组
    # 匹配规则: const unsigned char 变量名[大小] = { 数据 };
    pattern = re.compile(r'unsigned\s+char\s+([a-zA-Z0-9_]+)\s*\[.*?\]\s*=\s*\{([^}]*)\}', re.DOTALL)
    matches = pattern.findall(content)

    if not matches:
        return 0

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    count = 0
    for var_name, array_data in matches:
        # 提取所有的 0xXX 十六进制数值
        hex_values = re.findall(r'0x[0-9a-fA-F]{1,2}', array_data)
        if not hex_values:
            continue
            
        # 转换为字节流
        byte_data = bytearray(int(x, 16) for x in hex_values)

        # 尝试从变量名中恢复原始文件名
        filename = var_name
        if filename.startswith(f"{var_prefix}_"):
            filename = filename[len(f"{var_prefix}_"):]
        filename += ".wav"

        out_path = os.path.join(output_dir, filename)
        with open(out_path, "wb") as f:
            f.write(byte_data)
            
        count += 1

    return count


# ================= UI 界面部分 =================

class WavCConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WAV <-> C 数组双向转换工具")
        self.root.geometry("680x500")
        self.root.minsize(600, 450)

        self.setup_ui()

    def setup_ui(self):
        # 创建选项卡
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)

        # === 选项卡 1：WAV 转 C 数组 ===
        self.tab1 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text=" WAV -> C数组 ")
        self.setup_tab1()

        # === 选项卡 2：C 数组 转 WAV ===
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab2, text=" C数组 -> WAV ")
        self.setup_tab2()

        # === 底部：日志窗口 (共享) ===
        log_frame = ttk.LabelFrame(self.root, text="操作日志")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_tab1(self):
        self.tab1.columnconfigure(1, weight=1)

        ttk.Label(self.tab1, text="WAV 路径:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.wav_path_var = tk.StringVar()
        ttk.Entry(self.tab1, textvariable=self.wav_path_var).grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        
        # 按钮容器，放置“选文件”和“选目录”
        btn_frame = ttk.Frame(self.tab1)
        btn_frame.grid(row=0, column=2, padx=10, pady=10)
        ttk.Button(btn_frame, text="选文件", command=self.browse_wav_file, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="选目录", command=lambda: self.browse_dir(self.wav_path_var), width=6).pack(side=tk.LEFT, padx=2)

        ttk.Label(self.tab1, text="输出 C 文件名:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.out_c_var = tk.StringVar(value="audio_data.c")
        ttk.Entry(self.tab1, textvariable=self.out_c_var).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.recursive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.tab1, text="包含子目录 (仅选目录时有效)", variable=self.recursive_var).grid(row=1, column=2, padx=10, pady=5, sticky="w")

        ttk.Button(self.tab1, text="开始生成 C 文件", command=self.run_wav_to_c).grid(row=2, column=0, columnspan=3, pady=15)

    def setup_tab2(self):
        self.tab2.columnconfigure(1, weight=1)

        ttk.Label(self.tab2, text="输入 C 文件:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.in_c_var = tk.StringVar()
        ttk.Entry(self.tab2, textvariable=self.in_c_var).grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        ttk.Button(self.tab2, text="浏览...", command=self.browse_c_file).grid(row=0, column=2, padx=10, pady=10)

        ttk.Label(self.tab2, text="输出 WAV 目录:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.out_wav_dir_var = tk.StringVar()
        ttk.Entry(self.tab2, textvariable=self.out_wav_dir_var).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(self.tab2, text="浏览...", command=lambda: self.browse_dir(self.out_wav_dir_var)).grid(row=1, column=2, padx=10, pady=5)

        ttk.Button(self.tab2, text="开始解析还原 WAV", command=self.run_c_to_wav).grid(row=2, column=0, columnspan=3, pady=15)

    # === 事件与辅助函数 ===
    def log(self, message):
        """向日志窗口输出信息"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update()

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

    def browse_wav_file(self):
        """选择单个 WAV 文件"""
        selected_file = filedialog.askopenfilename(title="选择WAV文件", filetypes=[("WAV Files", "*.wav"), ("All Files", "*.*")])
        if selected_file:
            self.wav_path_var.set(selected_file)

    def browse_dir(self, string_var):
        """选择目录"""
        selected_dir = filedialog.askdirectory(title="选择文件夹")
        if selected_dir:
            string_var.set(selected_dir)

    def browse_c_file(self):
        """选择 C 文件用于还原"""
        selected_file = filedialog.askopenfilename(title="选择C文件", filetypes=[("C/C++ Files", "*.c *.h *.cpp"), ("All Files", "*.*")])
        if selected_file:
            self.in_c_var.set(selected_file)
            # 自动推断输出目录为C文件同级的 extracted_wavs 文件夹
            if not self.out_wav_dir_var.get():
                self.out_wav_dir_var.set(os.path.join(os.path.dirname(selected_file), "extracted_wavs"))

    # === 执行逻辑 ===
    def run_wav_to_c(self):
        input_path = self.wav_path_var.get().strip()
        output_name = self.out_c_var.get().strip() or "audio_data.c"
        is_recursive = self.recursive_var.get()

        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("错误", "请选择有效的 WAV 文件或目录！")
            return

        self.clear_log()
        all_arrays = []
        file_count = 0

        try:
            # 判断是单文件还是目录
            if os.path.isfile(input_path):
                # ===== 处理单个文件 =====
                if not input_path.lower().endswith(".wav"):
                    messagebox.showerror("错误", "所选文件不是 WAV 格式！")
                    return
                
                output_file_path = os.path.join(os.path.dirname(input_path), output_name)
                self.log(f"【WAV -> C】 模式: 单文件转换")
                self.log(f"读取: {os.path.basename(input_path)}")
                
                all_arrays.append(wav_to_c_array(input_path))
                file_count = 1
            else:
                # ===== 处理整个目录 =====
                output_file_path = os.path.join(input_path, output_name)
                self.log(f"【WAV -> C】 模式: 目录批量转换")
                self.log(f"开始扫描目录: {input_path}")
                
                for root_dir, _, files in os.walk(input_path):
                    for file in files:
                        if file.lower().endswith(".wav"):
                            path = os.path.join(root_dir, file)
                            self.log(f"读取: {file}")
                            all_arrays.append(wav_to_c_array(path))
                            file_count += 1

                    if not is_recursive:
                        break

            # 统一写入文件
            if file_count == 0:
                self.log("⚠️ 未找到任何 WAV 文件。")
                return

            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write("// Auto-generated WAV <-> C arrays\n\n")
                f.write("#include <stdint.h>\n\n")
                f.write("\n\n".join(all_arrays))

            self.log(f"\n✔ 成功！共打包 {file_count} 个 WAV 到 C 文件:\n{output_file_path}")
            messagebox.showinfo("完成", f"成功生成 C 文件！\n共处理 {file_count} 个 WAV 文件。")
            
        except Exception as e:
            self.log(f"\n❌ 错误: {str(e)}")
            messagebox.showerror("错误", str(e))


    def run_c_to_wav(self):
        c_file = self.in_c_var.get().strip()
        out_dir = self.out_wav_dir_var.get().strip()

        if not c_file or not os.path.isfile(c_file):
            messagebox.showerror("错误", "请选择有效的 C 文件！")
            return
        if not out_dir:
            messagebox.showerror("错误", "请选择输出 WAV 目录！")
            return

        self.clear_log()
        self.log(f"【C -> WAV】 开始解析文件: {os.path.basename(c_file)}")

        try:
            count = c_array_to_wav(c_file, out_dir)
            if count > 0:
                self.log(f"\n✔ 还原成功！共从 C 文件中提取 {count} 个 WAV 文件。")
                self.log(f"输出目录: {out_dir}")
                messagebox.showinfo("完成", f"成功还原 WAV 文件！\n共提取出 {count} 个音频文件。")
            else:
                self.log("\n⚠️ 未在指定文件中找到符合格式的 C 数组数据。")
                messagebox.showwarning("提示", "未找到 C 数组数据，请确保是本工具生成的标准格式。")
                
        except Exception as e:
            self.log(f"\n❌ 错误: {str(e)}")
            messagebox.showerror("错误", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = WavCConverterApp(root)
    root.mainloop()