import tkinter as tk
from tkinter import messagebox
from matplotlib import rcParams
import matplotlib.pyplot as plt
import re  # 正则表达式库，用于处理多种分隔符
from matplotlib.ticker import MaxNLocator  # 控制y轴的刻度

# 创建主窗口
root = tk.Tk()
root.title("数据波形生成器")

# 设置字体为 SimHei（黑体）
rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体
rcParams['axes.unicode_minus'] = False    # 解决负号显示为方块的问题

# 定义标签
label = tk.Label(root, text="请输入数据 (用空格、逗号或换行分隔):")
label.pack(pady=10)

# 创建一个框架用于放置 Text 和 Scrollbar
text_frame = tk.Frame(root)
text_frame.pack(expand=True, fill='both', padx=20, pady=10)

# 创建 Text 组件
text_input = tk.Text(text_frame, height=10)
text_input.pack(side=tk.LEFT, expand=True, fill='both')

# 创建滚动条
scrollbar = tk.Scrollbar(text_frame, command=text_input.yview)
scrollbar.pack(side=tk.RIGHT, fill='y')

# 将滚动条与 Text 组件关联
text_input.config(yscrollcommand=scrollbar.set)

# 创建右键菜单
right_click_menu = tk.Menu(root, tearoff=0)
right_click_menu.add_command(label="剪切", command=lambda: text_input.event_generate("<<Cut>>"))
right_click_menu.add_command(label="复制", command=lambda: text_input.event_generate("<<Copy>>"))
right_click_menu.add_command(label="粘贴", command=lambda: text_input.event_generate("<<Paste>>"))
right_click_menu.add_command(label="全选", command=lambda: text_input.tag_add("sel", "1.0", "end"))

# 绑定右键点击事件
def show_right_click_menu(event):
    right_click_menu.post(event.x_root, event.y_root)

# 将右键菜单绑定到 Text 组件
text_input.bind("<Button-3>", show_right_click_menu)

# 定义生成波形的函数
def generate_waveform():
    data_str = text_input.get("1.0", "end").strip()  # 获取 Text 中的内容
    try:
        # 使用正则表达式同时处理空格、逗号、换行符等分隔符
        data_list = list(map(int, re.split(r'[,\s]+', data_str)))
        
        # 绘制波形图
        fig, ax = plt.subplots()
        ax.plot(data_list, marker='o')
        ax.set_title("数据波形")
        ax.set_xlabel("数据点")
        ax.set_ylabel("值")
        ax.grid(True)

        # 设置y轴的范围和精度，限制y轴的上下限
        ymin = -10  # 固定y轴下限
        ymax = 100  # 固定y轴上限
        ax.set_ylim(ymin, ymax)  # 手动设置y轴范围
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))  # 固定y轴为整数

        # 连接缩放事件以固定y轴
        def on_zoom(event):
            cur_ylim = ax.get_ylim()  # 获取当前y轴的范围
            ax.set_ylim(ymin, ymax)   # 固定y轴范围
            plt.draw()  # 刷新图表

        # 监听缩放事件
        fig.canvas.mpl_connect('button_release_event', on_zoom)

        plt.show()

    except ValueError:
        messagebox.showerror("输入错误", "请确保输入的是数字，并且用空格、逗号或换行分隔。")

# 定义清除输入框的函数
def clear_input():
    text_input.delete("1.0", "end")  # 清空文本框

# 创建一个框架用于按钮
button_frame = tk.Frame(root)
button_frame.pack(pady=10)  # 设置上下间距

button_clear = tk.Button(button_frame, text="清除输入", command=clear_input)
button_clear.pack(side=tk.LEFT, padx=5)  # 将按钮放在左侧，添加左右间距

# 定义按钮
button_generate = tk.Button(button_frame, text="生成波形", command=generate_waveform)
button_generate.pack(side=tk.LEFT, padx=5)  # 将按钮放在左侧，添加左右间距

# 运行主循环
root.mainloop()
