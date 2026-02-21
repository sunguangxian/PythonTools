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
    hex_list = [f"0x{b:02x}" for b in data]
    
    # 按行格式化，每行 12 个字节以适应大多数显示器
    rows = [", ".join(hex_list[i:i+12]) for i in range(0, len(hex_list), 12)]
    hex_body = ",\n    ".join(rows)

    # 生成安全的变量名
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", base_name)
    var_name = f"{var_prefix}_{safe_name}"

    array_lines = [
        f"// Original File: {os.path.basename(input_path)}",
        f"const unsigned char {var_name}[] = {{",
        f"    {hex_body}",
        f"}};",
        f"const unsigned int {var_name}_len = {len(data)};",
        ""
    ]
    return "\n".join(array_lines)


def c_array_to_wav(c_file_path, output_dir):
    """从 C 文件中解析数组并还原为 WAV 文件"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(c_file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # 匹配模式：// Original File: name.wav \n const unsigned char var[] = { data };
    pattern = re.compile(
        r"//\s*Original\s*File:\s*(?P<filename>.*?)\s*\n"
        r"const\s+unsigned\s+char\s+\w+\[\]\s*=\s*\{(?P<data>.*?)\};",
        re.DOTALL
    )

    matches = list(pattern.finditer(content))
    if not matches:
        return 0

    count = 0
    for match in matches:
        filename = match.group("filename").strip()
        hex_data_str = match.group("data")
        hex_values = re.findall(r"0x[0-9a-fA-F]{2}", hex_data_str)
        byte_data = bytes([int(h, 16) for h in hex_values])
        
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "wb") as f:
            f.write(byte_data)
        count += 1
    return count


# ================= UI 界面部分 =================

class WavCConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WAV <-> C 数组互转工具")
        self.root.geometry("700x550")
        self.root.minsize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        # 风格设置
        style = ttk.Style()
        style.configure("Action.TButton", font=("Microsoft YaHei", 10, "bold"))

        # 创建选项卡
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)

        # === 选项卡 1：WAV 转 C 数组 ===
        self.tab1 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text="  WAV -> C 数组  ")
        self.setup_tab1()

        # === 选项卡 2：C 数组 转 WAV ===
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab2, text="  C 数组 -> WAV  ")
        self.setup_tab2()

        # === 日志区域 ===
        log_frame = ttk.LabelFrame(self.root, text=" 操作日志 ")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', font=("Consolas", 9), background="#f8f9fa")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_tab1(self):
        container = ttk.Frame(self.tab1, padding=20)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(1, weight=1)

        ttk.Label(container, text="WAV 源路径:").grid(row=0, column=0, sticky="e", pady=10)
        self.wav_path_var = tk.StringVar()
        ttk.Entry(container, textvariable=self.wav_path_var).grid(row=0, column=1, sticky="ew", padx=10)
        
        btn_group = ttk.Frame(container)
        btn_group.grid(row=0, column=2)
        ttk.Button(btn_group, text="选择目录", command=lambda: self.browse_dir(self.wav_path_var)).pack(side=tk.LEFT, padx=2)

        ttk.Label(container, text="输出文件名:").grid(row=1, column=0, sticky="e", pady=10)
        self.out_c_var = tk.StringVar(value="audio_data.c")
        ttk.Entry(container, textvariable=self.out_c_var).grid(row=1, column=1, sticky="ew", padx=10)

        ttk.Button(container, text="执行批量转换", style="Action.TButton", command=self.run_wav_to_c).grid(row=2, column=0, columnspan=3, pady=20)

    def setup_tab2(self):
        container = ttk.Frame(self.tab2, padding=20)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(1, weight=1)

        ttk.Label(container, text="C 源文件:").grid(row=0, column=0, sticky="e", pady=10)
        self.in_c_var = tk.StringVar()
        ttk.Entry(container, textvariable=self.in_c_var).grid(row=0, column=1, sticky="ew", padx=10)
        ttk.Button(container, text="浏览", command=self.browse_c_file).grid(row=0, column=2)

        ttk.Label(container, text="输出目录:").grid(row=1, column=0, sticky="e", pady=10)
        self.out_wav_dir_var = tk.StringVar(value="restored_wav")
        ttk.Entry(container, textvariable=self.out_wav_dir_var).grid(row=1, column=1, sticky="ew", padx=10)
        ttk.Button(container, text="选择", command=lambda: self.browse_dir(self.out_wav_dir_var)).grid(row=1, column=2)

        ttk.Button(container, text="执行还原转换", style="Action.TButton", command=self.run_c_to_wav).grid(row=2, column=0, columnspan=3, pady=20)

    def log(self, msg):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f">>> {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update()

    def browse_dir(self, var):
        path = filedialog.askdirectory()
        if path: var.set(path)

    def browse_c_file(self):
        path = filedialog.askopenfilename(filetypes=[("C Files", "*.c"), ("All Files", "*.*")])
        if path:
            self.in_c_var.set(path)
            # 自动设置输出目录为 C 文件同级目录下的 restored_wavs 文件夹
            default_out_dir = os.path.join(os.path.dirname(path), "restored_wavs")
            self.out_wav_dir_var.set(default_out_dir)

    def run_wav_to_c(self):
        in_dir = self.wav_path_var.get().strip()
        out_name = self.out_c_var.get().strip()
        if not in_dir or not os.path.isdir(in_dir):
            messagebox.showwarning("警告", "请输入有效的源目录")
            return

        wav_files = [f for f in os.listdir(in_dir) if f.lower().endswith(".wav")]
        if not wav_files:
            self.log("未找到 WAV 文件")
            return

        # 确保输出路径在输入目录同级
        out_path = os.path.join(in_dir, out_name)
        all_content = ["// Auto-generated audio data", "#include <stdint.h>\n"]
        
        for f in wav_files:
            self.log(f"转换中: {f}")
            all_content.append(wav_to_c_array(os.path.join(in_dir, f)))

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(all_content))
        
        self.log(f"完成！已生成: {out_path}")
        messagebox.showinfo("成功", f"转换完成，共处理 {len(wav_files)} 个文件")

    def run_c_to_wav(self):
        in_c = self.in_c_var.get().strip()
        out_dir = self.out_wav_dir_var.get().strip()
        if not os.path.isfile(in_c):
            messagebox.showwarning("警告", "请输入有效的 C 源文件")
            return

        count = c_array_to_wav(in_c, out_dir)
        if count > 0:
            self.log(f"还原完成！共输出 {count} 个文件到 {out_dir}")
            messagebox.showinfo("成功", f"成功还原 {count} 个文件")
        else:
            self.log("错误：未在文件中找到匹配的数组格式")
            messagebox.showerror("失败", "未找到有效的数组数据")

if __name__ == "__main__":
    root = tk.Tk()
    WavCConverterApp(root)
    root.mainloop()