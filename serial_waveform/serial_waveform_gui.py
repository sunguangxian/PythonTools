import serial
from serial.tools import list_ports
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.animation as animation
from collections import deque
import threading
import time
import re
from alc.alc_config import ALC_PARAM_CONFIG
import json
import os

# ========== 波形参数 ==========
BUFFER_SIZE = 1024
Y_MIN = -32768
Y_MAX = 32767
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "serial_waveform_gui.json")
DEFAULT_CONFIG = {
    "port": "",
    "baud": "115200",
    "auto_connect": False,
    "auto_scale": False,
}

# 全局串口对象
ser = None
data_buffer = deque([0]*BUFFER_SIZE, maxlen=BUFFER_SIZE)
read_thread = None
stop_reading = False
data_updated = False  # 标记是否有新数据
is_paused = False  # 暂停标志
sample_count = 0

# ========== 获取串口列表 ==========
def list_serial_ports():
    ports = list_ports.comports()
    return [p.device for p in ports]

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return DEFAULT_CONFIG.copy()
        config = DEFAULT_CONFIG.copy()
        for key in config:
            if key in data:
                config[key] = data[key]
        return config
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
            json.dump(config, handle, ensure_ascii=True, indent=2)
    except Exception:
        pass

config = load_config()

def save_current_config():
    config_data = {
        "port": port_var.get().strip(),
        "baud": baud_var.get().strip(),
        "auto_connect": bool(auto_connect_var.get()),
        "auto_scale": bool(auto_scale_var.get()),
    }
    config.update(config_data)
    save_config(config)

# ========== 持续读取串口数据（后台线程） ==========
def read_serial_continuously():
    """在后台线程中持续读取串口数据"""
    global ser, data_buffer, stop_reading, data_updated, sample_count
    while not stop_reading and ser and ser.is_open:
        try:
            if ser.in_waiting > 0:
                # 读取所有可用数据
                while ser.in_waiting > 0:
                    try:
                        line = ser.readline().decode(errors="ignore").strip()
                        if line:
                            # Extract all numbers (including negatives) from the line.
                            numbers = re.findall(r'-?\d+', line)
                            if numbers:
                                for number in numbers:
                                    data_buffer.append(int(number))
                                sample_count += len(numbers)
                                data_updated = True  # 标记有新数据
                    except (ValueError, UnicodeDecodeError):
                        pass
                    except Exception:
                        break
            else:
                # 没有数据时短暂休眠，避免CPU占用过高
                time.sleep(0.01)
        except Exception:
            # 如果串口出错，退出循环
            break

# ========== 连接串口 ==========
def connect_serial():
    global ser, read_thread, stop_reading
    if ser and ser.is_open:
        return

    if is_paused:
        toggle_pause()

    port = port_var.get().strip()
    if not port:
        refresh_ports(keep_selection=False)
        port = port_var.get().strip()
    baud = baud_var.get().strip()

    if not port:
        messagebox.showerror("Error", "请选择串口")
        return

    try:
        baud_int = int(baud)
    except ValueError:
        messagebox.showerror("Error", f"Invalid baud rate: {baud}")
        return

    try:
        ser = serial.Serial(port, baud_int, timeout=0.05)
        status_var.set(f"Connected: {port} @ {baud_int}")

        # 启动后台读取线程
        stop_reading = False
        read_thread = threading.Thread(target=read_serial_continuously, daemon=True)
        read_thread.start()
        set_connection_state(True)
        clear_buffer()
        save_current_config()
    except Exception as e:
        messagebox.showerror("Error", str(e))

# ========== 断开串口 ==========
def disconnect_serial():
    global ser, read_thread, stop_reading
    # 停止读取线程
    stop_reading = True
    if read_thread and read_thread.is_alive():
        read_thread.join(timeout=0.5)  # 等待线程结束，最多等待0.5秒

    if ser:
        try:
            ser.close()
        except Exception:
            pass
        ser = None
        read_thread = None

    if is_paused:
        toggle_pause()

    status_var.set("Disconnected")
    set_connection_state(False)
    save_current_config()

# ========== 波形更新 ==========
def update(frame):
    global data_updated, is_paused
    # 如果暂停，不更新显示
    if is_paused:
        return line_plot,
    # 如果有新数据，立即更新波形显示
    if data_updated:
        y_data = list(data_buffer)
        line_plot.set_ydata(y_data)
        if auto_scale_var.get():
            y_min = min(y_data)
            y_max = max(y_data)
            if y_min == y_max:
                y_min -= 1
                y_max += 1
            padding = (y_max - y_min) * 0.1
            ax.set_ylim(y_min - padding, y_max + padding)
        latest_value_var.set(f"Latest: {y_data[-1]}")
        samples_var.set(f"Samples: {sample_count}")
        data_updated = False  # 重置标志
    # 即使没有新数据，也保持显示（确保图形连续）
    return line_plot,

# ========== Tkinter GUI ==========
root = tk.Tk()
root.title("Serial Real-Time Waveform")

# 顶部控制区
ctrl = ttk.Frame(root)
ctrl.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

ttk.Label(ctrl, text="Port:").pack(side=tk.LEFT)
port_var = tk.StringVar(value=config.get("port", ""))
port_combo = ttk.Combobox(ctrl, textvariable=port_var, width=12)
port_combo["values"] = []
port_combo.pack(side=tk.LEFT, padx=5)

ttk.Label(ctrl, text="Baud:").pack(side=tk.LEFT)
baud_var = tk.StringVar(value=str(config.get("baud", "115200")))
baud_combo = ttk.Combobox(
    ctrl,
    textvariable=baud_var,
    values=["9600", "19200", "38400", "57600", "115200", "230400", "460800"],
    width=10
)
baud_combo.pack(side=tk.LEFT, padx=5)

def refresh_ports(keep_selection=True):
    ports = list_serial_ports()
    current = port_var.get().strip()
    port_combo["values"] = ports
    selected = None
    if keep_selection and current in ports:
        selected = current
    elif config.get("port") in ports:
        selected = config.get("port")
    elif ports and (len(ports) == 1 or not current):
        selected = ports[0]
    if selected:
        port_var.set(selected)

refresh_button = ttk.Button(ctrl, text="Refresh", command=refresh_ports)
refresh_button.pack(side=tk.LEFT, padx=5)

connect_button = ttk.Button(ctrl, text="Connect", command=connect_serial)
connect_button.pack(side=tk.LEFT, padx=5)
disconnect_button = ttk.Button(ctrl, text="Disconnect", command=disconnect_serial)
disconnect_button.pack(side=tk.LEFT, padx=5)

auto_connect_var = tk.BooleanVar(value=bool(config.get("auto_connect", False)))
auto_connect_check = ttk.Checkbutton(
    ctrl,
    text="Auto Connect",
    variable=auto_connect_var,
    command=save_current_config,
)
auto_connect_check.pack(side=tk.LEFT, padx=5)
port_combo.bind("<Button-1>", lambda event: refresh_ports())
refresh_ports()

# 暂停/继续功能
def toggle_pause():
    """切换暂停/继续状态"""
    global is_paused
    is_paused = not is_paused
    if is_paused:
        pause_button.config(text="Resume")
        current_status = status_var.get()
        if " [Paused]" not in current_status:
            status_var.set(current_status + " [Paused]")
    else:
        pause_button.config(text="Pause")
        # 移除暂停标记
        current_status = status_var.get()
        if " [Paused]" in current_status:
            status_var.set(current_status.replace(" [Paused]", ""))

pause_button = ttk.Button(ctrl, text="Pause", command=toggle_pause)
pause_button.pack(side=tk.LEFT, padx=5)

# ALC参数设置功能
def open_alc_settings():
    """打开ALC参数设置对话框"""
    if not ser or not ser.is_open:
        messagebox.showerror("Error", "请先连接串口")
        return
    
    # 创建对话框窗口
    dialog = tk.Toplevel(root)
    dialog.title("ALC/AGC 参数设置")
    dialog.geometry("600x800")
    dialog.transient(root)
    
    # 创建滚动框架
    canvas_frame = tk.Canvas(dialog)
    scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas_frame.yview)
    scrollable_frame = ttk.Frame(canvas_frame)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas_frame.configure(scrollregion=canvas_frame.bbox("all"))
    )
    
    canvas_frame.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas_frame.configure(yscrollcommand=scrollbar.set)
    
    # 参数定义和默认值
    param_labels = {
        "enable": "ALC/AGC 使能",
        "pga_control_enable": "PGA 控制使能",
        "mode": "工作模式",
        "hold_time_us": "保持时间(us)",
        "attack_time_us": "攻击时间(us)",
        "decay_time_us": "衰减时间(us)",
        "zero_cross_enable": "零交叉使能",
        "pga_zero_cross_enable": "PGA零交叉使能",
        "fast_decay_enable": "快速衰减使能",
        "noise_gate_enable": "噪声门使能",
        "noise_gate_threshold_db": "噪声门阈值(dB)",
        "amp_recover_enable": "放大器恢复使能",
        "slow_clock_enable": "慢时钟使能",
        "approx_rate_hz": "近似采样率(Hz)",
        "pga_target_half_db": "PGA目标增益(0.5dB)",
        "pga_max_half_db": "PGA最大增益(0.5dB)",
        "pga_min_half_db": "PGA最小增益(0.5dB)",
        "limit_enable": "原始电平限制使能",
        "limit_max_low": "最大限制低字节",
        "limit_max_high": "最大限制高字节",
        "limit_min_low": "最小限制低字节",
        "limit_min_high": "最小限制高字节",
        "gain_attack_jack": "增益攻击插孔模式",
        "ctrl_gen": "控制生成",
        "group": "ADC组选择",
    }
    param_help = {
        "enable": "0=禁用, 1=启用",
        "pga_control_enable": "0=保持PGA固定, 1=允许ALC改变PGA",
        "mode": "0=normal, 1=limiter",
        "hold_time_us": "支持: 0,2000,4000,8000,16000,32000,64000,128000,256000,512000,1000000",
        "attack_time_us": "normal:125-128000, limiter:32-32000",
        "decay_time_us": "normal:0-512000, limiter:125-128000",
        "zero_cross_enable": "0=禁用, 1=启用",
        "pga_zero_cross_enable": "0=禁用, 1=启用",
        "fast_decay_enable": "0=禁用, 1=启用",
        "noise_gate_enable": "0=禁用, 1=启用",
        "noise_gate_threshold_db": "支持: -39,-45,-51,-57,-63,-69,-75,-81",
        "amp_recover_enable": "0=固定行为, 1=根据测量电平恢复",
        "slow_clock_enable": "0=禁用, 1=启用",
        "approx_rate_hz": "支持: 8000,12000,16000,24000,32000,44100,48000,96000",
        "pga_target_half_db": "例如: 0=0dB, 33=16.5dB",
        "pga_max_half_db": "支持: -27,-15,-3,9,21,33,45,57",
        "pga_min_half_db": "支持: -36,-24,-12,0,12,24,36,48",
        "limit_enable": "0=禁用, 1=启用",
        "limit_max_low": "AGC最大值低字节",
        "limit_max_high": "AGC最大值高字节",
        "limit_min_low": "AGC最小值低字节",
        "limit_min_high": "AGC最小值高字节",
        "gain_attack_jack": "0=正常模式, 1=插孔攻击模式",
        "ctrl_gen": "0=normal, 1=jack1, 2=jack2, 3=jack3",
        "group": "0-3=指定组, 255=所有组",
    }
    param_defs = [
        (
            param["name"],
            param_labels.get(param["name"], param["name"]),
            param["range_text"],
            param["default"],
            param_help.get(param["name"], ""),
        )
        for param in ALC_PARAM_CONFIG
    ]
    
    # 存储输入框变量
    entry_vars = []
    
    # 创建参数输入框
    for i, (name, label, range_text, default, help_text) in enumerate(param_defs):
        frame = ttk.Frame(scrollable_frame)
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(frame, text=f"{i+1}. {label}:", width=25, anchor="w").pack(side=tk.LEFT)
        
        var = tk.StringVar(value=default)
        entry = ttk.Entry(frame, textvariable=var, width=15)
        entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(frame, text=f"({range_text})", font=("Arial", 8), foreground="gray").pack(side=tk.LEFT, padx=2)
        
        entry_vars.append((name, var, range_text, default, help_text))
    
    canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # 参数校验函数
    def validate_params():
        """校验所有参数"""
        errors = []
        
        # 先获取mode值（第3个参数，索引2）
        mode = None
        try:
            mode_str = entry_vars[2][1].get().strip()
            if mode_str:
                mode = int(mode_str)
        except:
            pass
        
        for i, (name, var, range_text, default, help_text) in enumerate(entry_vars):
            value_str = var.get().strip()
            if not value_str:
                errors.append(f"参数 {i+1} ({name}): 不能为空")
                continue
            
            try:
                value = int(value_str)
            except ValueError:
                errors.append(f"参数 {i+1} ({name}): 必须是整数，当前值: {value_str}")
                continue
            
            # 根据参数名进行校验
            if name == "enable" or name == "pga_control_enable" or \
               name == "zero_cross_enable" or name == "pga_zero_cross_enable" or \
               name == "fast_decay_enable" or name == "noise_gate_enable" or \
               name == "amp_recover_enable" or name == "slow_clock_enable" or \
               name == "limit_enable" or name == "gain_attack_jack":
                if value not in [0, 1]:
                    errors.append(f"参数 {i+1} ({name}): 必须是0或1，当前值: {value}")
            
            elif name == "mode":
                if value not in [0, 1]:
                    errors.append(f"参数 {i+1} ({name}): 必须是0或1，当前值: {value}")
                mode = value  # 更新mode值
            
            elif name == "hold_time_us":
                valid_values = [0, 2000, 4000, 8000, 16000, 32000, 64000, 128000, 256000, 512000, 1000000]
                if value < 0 or value > 1000000:
                    errors.append(f"参数 {i+1} ({name}): 必须在0-1000000范围内，当前值: {value}")
            
            elif name == "attack_time_us":
                if mode is None:
                    # 如果mode还未设置，使用默认值1（limiter）进行校验
                    mode = 1
                if mode == 0:  # normal
                    if value < 125 or value > 128000:
                        errors.append(f"参数 {i+1} ({name}): normal模式必须在125-128000范围内，当前值: {value}")
                elif mode == 1:  # limiter
                    if value < 32 or value > 32000:
                        errors.append(f"参数 {i+1} ({name}): limiter模式必须在32-32000范围内，当前值: {value}")
            
            elif name == "decay_time_us":
                if mode is None:
                    # 如果mode还未设置，使用默认值1（limiter）进行校验
                    mode = 1
                if mode == 0:  # normal
                    if value < 0 or value > 512000:
                        errors.append(f"参数 {i+1} ({name}): normal模式必须在0-512000范围内，当前值: {value}")
                elif mode == 1:  # limiter
                    if value < 125 or value > 128000:
                        errors.append(f"参数 {i+1} ({name}): limiter模式必须在125-128000范围内，当前值: {value}")
            
            elif name == "noise_gate_threshold_db":
                valid_values = [-81, -75, -69, -63, -57, -51, -45, -39]
                if value < -81 or value > -39:
                    errors.append(f"参数 {i+1} ({name}): 必须在-81到-39范围内，当前值: {value}")
            
            elif name == "approx_rate_hz":
                valid_values = [8000, 12000, 16000, 24000, 32000, 44100, 48000, 96000]
                if value < 8000 or value > 96000:
                    errors.append(f"参数 {i+1} ({name}): 必须在8000-96000范围内，当前值: {value}")
            
            elif name == "pga_target_half_db":
                if value < -36 or value > 57:
                    errors.append(f"参数 {i+1} ({name}): 必须在-36到57范围内，当前值: {value}")
            
            elif name == "pga_max_half_db":
                valid_values = [-27, -15, -3, 9, 21, 33, 45, 57]
                if value < -27 or value > 57:
                    errors.append(f"参数 {i+1} ({name}): 必须在-27到57范围内，当前值: {value}")
            
            elif name == "pga_min_half_db":
                valid_values = [-36, -24, -12, 0, 12, 24, 36, 48]
                if value < -36 or value > 48:
                    errors.append(f"参数 {i+1} ({name}): 必须在-36到48范围内，当前值: {value}")
            
            elif name in ["limit_max_low", "limit_max_high", "limit_min_low", "limit_min_high"]:
                if value < 0 or value > 255:
                    errors.append(f"参数 {i+1} ({name}): 必须在0-255范围内，当前值: {value}")
            
            elif name == "ctrl_gen":
                if value < 0 or value > 3:
                    errors.append(f"参数 {i+1} ({name}): 必须在0-3范围内，当前值: {value}")
            
            elif name == "group":
                if value not in [0, 1, 2, 3, 255]:
                    errors.append(f"参数 {i+1} ({name}): 必须是0-3或255，当前值: {value}")
        
        return errors
    
    # 发送AT命令函数
    def send_alc_command():
        """发送ALC参数设置命令"""
        # 先获取mode值用于校验attack和decay
        mode_var = entry_vars[2][1]  # mode是第3个参数（索引2）
        try:
            mode = int(mode_var.get().strip())
        except:
            mode = 1  # 默认limiter
        
        # 重新校验（需要mode值）
        errors = validate_params()
        if errors:
            error_msg = "参数校验失败:\n\n" + "\n".join(errors)
            messagebox.showerror("参数错误", error_msg)
            return
        
        # 构建AT命令
        param_values = [var.get().strip() for _, var, _, _, _ in entry_vars]
        at_command = f"AT+PARAM=ALC,{','.join(param_values)}\r\n"
        
        try:
            # 发送命令
            ser.write(at_command.encode())
            time.sleep(0.1)  # 等待响应
            
            # 读取响应
            response = ""
            timeout = time.time() + 2  # 2秒超时
            while time.time() < timeout:
                if ser.in_waiting > 0:
                    response += ser.read(ser.in_waiting).decode(errors="ignore")
                    if "OK" in response or "ERROR" in response:
                        break
                time.sleep(0.05)
            
            if "OK" in response:
                messagebox.showinfo("成功", f"ALC参数设置成功!\n\n命令: {at_command.strip()}\n响应: {response.strip()}")
                dialog.destroy()
            elif "ERROR" in response:
                messagebox.showerror("错误", f"设置失败:\n\n{response.strip()}")
            else:
                messagebox.showwarning("警告", f"未收到有效响应:\n\n{response.strip() if response else '无响应'}")
        
        except Exception as e:
            messagebox.showerror("错误", f"发送命令时出错:\n{str(e)}")
    
    # 恢复默认值函数
    def restore_defaults():
        """恢复所有参数为默认值"""
        for i, (name, var, range_text, default, help_text) in enumerate(entry_vars):
            var.set(default)
        messagebox.showinfo("成功", "已恢复所有参数为默认值")
    
    # 获取参数函数
    def get_alc_params():
        """从设备获取当前ALC参数"""
        try:
            # 发送查询命令
            ser.write(b"AT+PARAM?\r\n")
            time.sleep(0.2)  # 等待响应
            
            # 读取响应
            response = ""
            timeout = time.time() + 3  # 3秒超时
            while time.time() < timeout:
                if ser.in_waiting > 0:
                    response += ser.read(ser.in_waiting).decode(errors="ignore")
                    if "OK" in response or "ERROR" in response:
                        break
                time.sleep(0.05)
            
            if "ERROR" in response:
                messagebox.showerror("错误", f"获取参数失败:\n\n{response.strip()}")
                return
            
            # 解析 +PARAM:ALC,... 行
            alc_line = None
            for line in response.split('\n'):
                if line.startswith("+PARAM:ALC,"):
                    alc_line = line.strip()
                    break
            
            if not alc_line:
                messagebox.showerror("错误", f"未找到ALC参数响应:\n\n{response.strip()}")
                return
            
            # 提取参数值（去掉 +PARAM:ALC, 前缀）
            param_str = alc_line.replace("+PARAM:ALC,", "").strip()
            param_values = [v.strip() for v in param_str.split(',')]
            
            if len(param_values) != 25:
                messagebox.showerror("错误", f"参数数量不正确，期望25个，实际{len(param_values)}个:\n\n{param_str}")
                return
            
            # 填充到输入框
            for i, (name, var, range_text, default, help_text) in enumerate(entry_vars):
                if i < len(param_values):
                    var.set(param_values[i])
            
            messagebox.showinfo("成功", f"已获取当前ALC参数:\n\n{alc_line}")
        
        except Exception as e:
            messagebox.showerror("错误", f"获取参数时出错:\n{str(e)}")
    
    # 按钮框架
    button_frame = ttk.Frame(dialog)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
    
    ttk.Button(button_frame, text="获取参数", command=get_alc_params).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="恢复默认", command=restore_defaults).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="设置参数", command=send_alc_command).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="校验参数", command=lambda: messagebox.showinfo("校验结果", 
        "参数校验通过!" if not validate_params() else "参数校验失败:\n\n" + "\n".join(validate_params()))).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

# 添加ALC设置按钮
alc_button = ttk.Button(ctrl, text="ALC设置", command=open_alc_settings)
alc_button.pack(side=tk.LEFT, padx=5)

def set_connection_state(connected):
    state = "disabled" if connected else "normal"
    for widget in (port_combo, baud_combo, refresh_button, connect_button):
        widget.config(state=state)
    disconnect_button.config(state="normal" if connected else "disabled")
    pause_button.config(state="normal" if connected else "disabled")
    alc_button.config(state="normal" if connected else "disabled")

status_frame = ttk.Frame(root)
status_frame.pack(side=tk.TOP, fill=tk.X)

status_var = tk.StringVar(value="Disconnected")
ttk.Label(status_frame, textvariable=status_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

latest_value_var = tk.StringVar(value="Latest: --")
samples_var = tk.StringVar(value="Samples: 0")
ttk.Label(status_frame, textvariable=latest_value_var).pack(side=tk.RIGHT, padx=5)
ttk.Label(status_frame, textvariable=samples_var).pack(side=tk.RIGHT, padx=5)

set_connection_state(False)

# ========== Matplotlib in Tk ==========
fig, ax = plt.subplots(figsize=(8, 4))
line_plot, = ax.plot(range(BUFFER_SIZE), list(data_buffer))
ax.set_ylim(Y_MIN, Y_MAX)
ax.set_title("Waveform")
ax.set_xlabel("Sample")
ax.set_ylabel("Value")
ax.grid(True)

canvas = FigureCanvasTkAgg(fig, root)
canvas.draw()
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

# 缩放控制按钮
zoom_frame = ttk.Frame(root)
zoom_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

auto_scale_var = tk.BooleanVar(value=bool(config.get("auto_scale", False)))

def clear_buffer():
    global data_buffer, data_updated, sample_count
    data_buffer = deque([0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
    data_updated = False
    sample_count = 0
    line_plot.set_ydata(list(data_buffer))
    latest_value_var.set("Latest: --")
    samples_var.set("Samples: 0")
    canvas.draw()


def zoom_in_y():
    """Y轴放大"""
    ylim = ax.get_ylim()
    center = (ylim[0] + ylim[1]) / 2
    span = (ylim[1] - ylim[0]) * 0.7
    ax.set_ylim(center - span/2, center + span/2)
    canvas.draw()

def zoom_out_y():
    """Y轴缩小"""
    ylim = ax.get_ylim()
    center = (ylim[0] + ylim[1]) / 2
    span = (ylim[1] - ylim[0]) / 0.7
    ax.set_ylim(center - span/2, center + span/2)
    canvas.draw()

def reset_view():
    """重置视图"""
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_xlim(0, BUFFER_SIZE)
    canvas.draw()

ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT, padx=2)
ttk.Button(zoom_frame, text="Y+", command=zoom_in_y, width=4).pack(side=tk.LEFT, padx=2)
ttk.Button(zoom_frame, text="Y-", command=zoom_out_y, width=4).pack(side=tk.LEFT, padx=2)
ttk.Button(zoom_frame, text="Reset", command=reset_view, width=6).pack(side=tk.LEFT, padx=2)
ttk.Button(zoom_frame, text="Clear", command=clear_buffer, width=6).pack(side=tk.LEFT, padx=2)
ttk.Checkbutton(
    zoom_frame,
    text="Auto Y",
    variable=auto_scale_var,
    command=save_current_config,
).pack(side=tk.LEFT, padx=5)

# 添加导航工具栏（包含缩放、平移等功能）
toolbar = NavigationToolbar2Tk(canvas, root)
toolbar.update()
toolbar.pack(side=tk.BOTTOM, fill=tk.X)

def maybe_auto_connect():
    if not auto_connect_var.get():
        return
    ports = list_serial_ports()
    current = port_var.get().strip()
    if current and current in ports:
        connect_serial()
    elif len(ports) == 1:
        port_var.set(ports[0])
        connect_serial()

if auto_connect_var.get():
    root.after(200, maybe_auto_connect)

# 连续更新动画，每30ms刷新一次，确保流畅显示
ani = animation.FuncAnimation(fig, update, interval=30, blit=False, cache_frame_data=False, repeat=True)

# ========== 关闭处理 ==========
def on_close():
    disconnect_serial()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
