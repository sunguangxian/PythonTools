"""
LVGL 字体管理与转换助手 (GUI)
功能：
1. 逆向解析：从已有 LVGL C 字库文件提取所有字符和图标码点。
2. 源码扫描：自动扫描项目 C/H 文件提取所有出现的汉字。
3. 字符追加：支持手动编辑字符集或通过 Unicode 码点追加图标。
4. 官方转换：配置 TTF、Size、BPP 后，一键调用 lv_font_conv 生成标准 C 字库。
"""

import os
import re
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

class LVGLFontTool:
    def __init__(self, root):
        self.root = root
        self.root.title("LVGL 字体助手")
        self.root.geometry("800x750")
        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style()
        style.configure("Big.TButton", font=("Microsoft YaHei", 10, "bold"), padding=10)
        
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 1. 字符准备区域 ---
        group1 = ttk.LabelFrame(main_frame, text=" 1. 提取已有字符 ", padding=10)
        group1.pack(fill="x", pady=5)
        
        ttk.Label(group1, text="选择源文件(C字库)或源码目录:").grid(row=0, column=0, sticky="w")
        self.src_path = tk.StringVar()
        ttk.Entry(group1, textvariable=self.src_path).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(group1, text="浏览", command=self.select_src).grid(row=0, column=2)
        
        btn_frame = ttk.Frame(group1)
        btn_frame.grid(row=1, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="🔍 从源码提取汉字", command=self.extract_from_src).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="🔄 逆向解析现有C字库", command=self.extract_from_c_font).pack(side="left", padx=10)

        # --- 2. 字符集编辑区域 ---
        group2 = ttk.LabelFrame(main_frame, text=" 2. 待转换字符集 (可直接编辑) ", padding=10)
        group2.pack(fill="both", expand=True, pady=5)
        
        self.char_text = scrolledtext.ScrolledText(group2, height=10, font=("Consolas", 11))
        self.char_text.pack(fill="both", expand=True, pady=5)
        
        icon_frame = ttk.Frame(group2)
        icon_frame.pack(fill="x")
        ttk.Label(icon_frame, text="追加图标 (Unicode码点, 如 f015):").pack(side="left")
        self.icon_code = tk.StringVar()
        ttk.Entry(icon_frame, textvariable=self.icon_code, width=10).pack(side="left", padx=5)
        ttk.Button(icon_frame, text="添加图标", command=self.add_icon).pack(side="left")
        ttk.Button(icon_frame, text="清空全部", command=lambda: self.char_text.delete("1.0", tk.END)).pack(side="right")

        # --- 3. 转换参数配置 ---
        group3 = ttk.LabelFrame(main_frame, text=" 3. 转换设置 ", padding=10)
        group3.pack(fill="x", pady=5)
        
        # TTF 选择
        ttk.Label(group3, text="TTF 字体文件:").grid(row=0, column=0, sticky="w", pady=5)
        self.ttf_path = tk.StringVar()
        ttk.Entry(group3, textvariable=self.ttf_path).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(group3, text="选择字体", command=self.select_ttf).grid(row=0, column=2)
        
        # 参数设置
        params = ttk.Frame(group3)
        params.grid(row=1, column=0, columnspan=3, sticky="w", pady=10)
        
        ttk.Label(params, text="字号(px):").pack(side="left")
        self.font_size = tk.StringVar(value="16")
        ttk.Entry(params, textvariable=self.font_size, width=5).pack(side="left", padx=5)
        
        ttk.Label(params, text="抗锯齿(BPP):").pack(side="left", padx=(10,0))
        self.bpp = tk.StringVar(value="4")
        ttk.Combobox(params, textvariable=self.bpp, values=["1", "2", "4", "8"], width=3).pack(side="left", padx=5)
        
        ttk.Label(params, text="输出文件名:").pack(side="left", padx=(10,0))
        self.font_name = tk.StringVar(value="lv_font_custom_16")
        ttk.Entry(params, textvariable=self.font_name, width=20).pack(side="left", padx=5)

        # --- 4. 执行按钮 ---
        self.run_btn = ttk.Button(main_frame, text="🔨 调用 lv_font_conv 生成字库", style="Big.TButton", command=self.run_conversion)
        self.run_btn.pack(fill="x", pady=10)

        self.status_label = ttk.Label(main_frame, text="就绪", foreground="gray")
        self.status_label.pack(anchor="w")

    def select_src(self):
        path = filedialog.askopenfilename(title="选择文件") or filedialog.askdirectory(title="选择源码目录")
        if path: self.src_path.set(path)

    def select_ttf(self):
        path = filedialog.askopenfilename(filetypes=[("字体文件", "*.ttf *.otf *.woff")])
        if path: self.ttf_path.set(path)

    def add_icon(self):
        code = self.icon_code.get().strip()
        if code:
            try:
                self.char_text.insert(tk.END, chr(int(code, 16)))
                self.icon_code.set("")
            except:
                messagebox.showerror("错误", "无效的十六进制 Unicode 码点")

    def extract_from_src(self):
        path = self.src_path.get()
        if not path or not os.path.exists(path):
            messagebox.showwarning("提示", "请先选择有效的源码目录或文件")
            return
        
        chars = set()
        files = [path] if os.path.isfile(path) else []
        if not files:
            for r, d, fs in os.walk(path):
                for f in fs:
                    if f.endswith(('.c', '.h', '.cpp', '.hpp')):
                        files.append(os.path.join(r, f))
        
        for f_path in files:
            try:
                with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # 匹配双引号内的中文字符
                    for char in content:
                        if ord(char) > 127: chars.add(char)
            except: continue
        
        self.char_text.insert(tk.END, "".join(sorted(list(chars))))
        self.status_label.config(text=f"从源码中提取了 {len(chars)} 个非ASCII字符")

    def extract_from_c_font(self):
        path = self.src_path.get()
        if not path or not os.path.isfile(path):
            messagebox.showwarning("提示", "请先选择现有的 C 字库文件")
            return
        
        chars = set()
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # 兼容不同版本的 LVGL 注释提取
                # 模式 1: U+XXXX
                matches = re.findall(r"U\+([0-9a-fA-F]{2,6})", content)
                for m in matches:
                    chars.add(chr(int(m, 16)))
                # 模式 2: .unicode = 0xXXXX
                matches = re.findall(r"\.unicode\s*=\s*0x([0-9a-fA-F]+)", content)
                for m in matches:
                    chars.add(chr(int(m, 16)))
            
            # 清空并填入提取结果
            current = self.char_text.get("1.0", tk.END).strip()
            all_chars = "".join(sorted(list(chars | set(current))))
            self.char_text.delete("1.0", tk.END)
            self.char_text.insert("1.0", all_chars)
            self.status_label.config(text=f"从 C 文件中提取/合并了 {len(chars)} 个字符")
        except Exception as e:
            messagebox.showerror("解析失败", str(e))

    def run_conversion(self):
        ttf = self.ttf_path.get()
        size = self.font_size.get()
        bpp = self.bpp.get()
        name = self.font_name.get()
        chars = self.char_text.get("1.0", tk.END).strip()
        
        if not ttf or not os.path.exists(ttf):
            messagebox.showerror("错误", "请选择有效的 TTF 字体文件")
            return
        if not chars:
            messagebox.showerror("错误", "待转换字符集不能为空")
            return

        out_path = os.path.join(os.path.dirname(ttf), f"{name}.c")
        
        # 构建 lv_font_conv 命令
        # 使用 npx 确保不需要全局安装也能尝试运行
        cmd = [
            "npx", "lv_font_conv",
            "--font", ttf,
            "--size", size,
            "--bpp", bpp,
            "--symbols", chars,
            "--format", "lvgl",
            "-o", out_path
        ]

        self.status_label.config(text="正在转换中，请稍候...", foreground="blue")
        self.root.update()

        try:
            # shell=True 在 Windows 下调用 npx 是必须的
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                self.status_label.config(text=f"成功生成: {out_path}", foreground="green")
                messagebox.showinfo("完成", f"字库文件已成功生成！\n保存路径: {out_path}")
            else:
                self.status_label.config(text="转换失败", foreground="red")
                # 弹出详细错误信息
                err_window = tk.Toplevel(self.root)
                err_window.title("转换错误详情")
                err_txt = scrolledtext.ScrolledText(err_window, width=80, height=20)
                err_txt.insert(tk.END, f"命令: {' '.join(cmd)}\n\n错误输出:\n{result.stderr}\n\n标准输出:\n{result.stdout}")
                err_txt.pack(padx=10, pady=10)
        except Exception as e:
            self.status_label.config(text="系统错误", foreground="red")
            messagebox.showerror("错误", f"无法调用转换工具，请检查是否安装了 Node.js。\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LVGLFontTool(root)
    root.mainloop()
