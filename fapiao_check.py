"""
发票自动查重工具 (带UI版)
"""

import os
import re
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

import pandas as pd
import pdfplumber


class InvoiceDeduplicatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("发票自动查重工具")
        self.root.geometry("650x450")
        self.root.minsize(550, 400)

        self.setup_ui()

    def setup_ui(self):
        # --- 顶部：目录选择 ---
        frame_top = ttk.Frame(self.root)
        frame_top.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(frame_top, text="发票目录:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.dir_var = tk.StringVar()
        ttk.Entry(frame_top, textvariable=self.dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(frame_top, text="浏览...", command=self.browse_dir).pack(side=tk.LEFT, padx=5)

        # --- 中部：进度条和按钮 ---
        frame_mid = ttk.Frame(self.root)
        frame_mid.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.start_btn = ttk.Button(frame_mid, text="开始扫描与查重", command=self.start_processing)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(frame_mid, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- 底部：日志输出 ---
        log_frame = ttk.LabelFrame(self.root, text="处理日志")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def log(self, message):
        """向日志窗口输出信息"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        # 如果在主线程调用可以不加 update，但如果是子线程调用，Tkinter 本身不是线程安全的
        # 为简单起见，这里直接插入。严谨的做法是用 root.after

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

    def browse_dir(self):
        selected_dir = filedialog.askdirectory(title="选择包含PDF发票的目录")
        if selected_dir:
            self.dir_var.set(selected_dir)

    def extract_info(self, pdf_path):
        """核心解析逻辑"""
        info = {
            "文件名": os.path.basename(pdf_path),
            "发票代码": "",
            "发票号码": "",
            "开票日期": "",
            "金额": "",
            "购买方名称": "",
            "购买方税号": "",
            "销售方税号": "" # 修复：提前初始化该字段
        }

        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += t

            # 发票代码
            code = re.search(r'发票代码[:：]?\s*(\d{10,12})', text)
            if code:
                info["发票代码"] = code.group(1)

            # 发票号码
            number = re.search(r'发票号码[:：]?\s*(\d{8,20})', text)
            if not number:
                number = re.search(r'(\b\d{20}\b)', text)
            if number:
                info["发票号码"] = number.group(1)

            # 日期
            date = re.search(r'(\d{4}年\d{2}月\d{2}日)', text)
            if date:
                info["开票日期"] = date.group(1)

            # 金额
            amount = re.search(r'价税合计.*?([0-9]+\.[0-9]{2})', text)
            if amount:
                info["金额"] = amount.group(1)

            # 购买方、销售方识别 (找18位信用代码)
            tax_ids = re.findall(r'\b[0-9A-Z]{18}\b', text)
            if len(tax_ids) >= 2:
                info["购买方税号"] = tax_ids[0]
                info["销售方税号"] = tax_ids[1]

        except Exception as e:
            self.root.after(0, self.log, f"读取失败: {os.path.basename(pdf_path)} - {str(e)}")

        return info

    def start_processing(self):
        """启动后台线程处理数据"""
        folder = self.dir_var.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("错误", "请选择有效的发票目录！")
            return

        self.start_btn.config(state='disabled')
        self.clear_log()
        self.progress_var.set(0)
        
        # 启动后台线程，避免阻塞主UI
        thread = threading.Thread(target=self.process_invoices, args=(folder,))
        thread.daemon = True
        thread.start()

    def process_invoices(self, folder):
        try:
            pdf_files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
            total_files = len(pdf_files)

            if total_files == 0:
                self.root.after(0, self.log, "⚠️ 该目录下没有找到 PDF 文件！")
                self.root.after(0, lambda: self.start_btn.config(state='normal'))
                return

            self.root.after(0, self.log, f"找到 {total_files} 个 PDF 文件，开始解析...")
            result = []

            for i, file in enumerate(pdf_files):
                path = os.path.join(folder, file)
                self.root.after(0, self.log, f"正在解析: {file}")
                
                info = self.extract_info(path)
                result.append(info)

                # 更新进度条
                progress = ((i + 1) / total_files) * 100
                self.root.after(0, self.progress_var.set, progress)

            self.root.after(0, self.log, "\n解析完成，正在进行查重和导出 Excel...")

            # 转换为 DataFrame 并查重
            df = pd.DataFrame(result)
            df["是否重复"] = df.duplicated(subset=["发票代码", "发票号码"], keep=False)
            df.sort_values(by=["是否重复", "发票代码"], ascending=False, inplace=True)

            # 输出 Excel
            out_file = os.path.join(folder, "发票查重结果.xlsx")
            df.to_excel(out_file, index=False)

            self.root.after(0, self.log, f"✔ 成功！结果已保存至:\n{out_file}")
            self.root.after(0, messagebox.showinfo, "完成", f"处理完成！\n共处理 {total_files} 张发票。\n结果保存在目录下的 '发票查重结果.xlsx'")

        except Exception as e:
            self.root.after(0, self.log, f"\n❌ 发生严重错误: {str(e)}")
            self.root.after(0, messagebox.showerror, "错误", f"发生错误:\n{str(e)}")
        finally:
            self.root.after(0, lambda: self.start_btn.config(state='normal'))


if __name__ == "__main__":
    root = tk.Tk()
    app = InvoiceDeduplicatorApp(root)
    root.mainloop()