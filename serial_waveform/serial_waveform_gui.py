# -*- coding: utf-8 -*-
import json
import os
import queue
import re
import sys
import threading
import time

import numpy as np
import pyqtgraph as pg
import serial
from PyQt5 import QtCore, QtGui, QtWidgets
from serial.tools import list_ports

from alc.alc_config import ALC_PARAM_CONFIG

# ========== Waveform parameters ==========
DEFAULT_BUFFER_SIZE = 1024
Y_MIN = -32768
Y_MAX = 32767
H_DIVS = 10
V_DIVS = 8
MIN_BUFFER_SAMPLES = 64
MAX_BUFFER_SAMPLES = 200000
DEFAULT_TIMEBASE = 0.01
DEFAULT_SAMPLE_RATE = 1000.0
DEFAULT_VOLTS_PER_COUNT = 1.0
DEFAULT_VOLTS_PER_DIV = (Y_MAX - Y_MIN) / V_DIVS
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "serial_waveform_gui.json")
DEFAULT_CONFIG = {
    "port": "",
    "baud": "115200",
    "auto_connect": False,
    "auto_scale": False,
    "sample_rate": DEFAULT_SAMPLE_RATE,
    "timebase": DEFAULT_TIMEBASE,
    "volts_per_div": DEFAULT_VOLTS_PER_DIV,
    "volts_per_count": DEFAULT_VOLTS_PER_COUNT,
}

pg.setConfigOptions(antialias=False)
pg.setConfigOptions(background="w", foreground="k")


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


TIMEBASE_OPTIONS = [
    1e-6,
    2e-6,
    5e-6,
    10e-6,
    20e-6,
    50e-6,
    100e-6,
    200e-6,
    500e-6,
    1e-3,
    2e-3,
    5e-3,
    10e-3,
    20e-3,
    50e-3,
    100e-3,
    200e-3,
    500e-3,
    1.0,
    2.0,
    5.0,
]

VOLTS_PER_DIV_OPTIONS = [
    0.001,
    0.002,
    0.005,
    0.01,
    0.02,
    0.05,
    0.1,
    0.2,
    0.5,
    1.0,
    2.0,
    5.0,
    10.0,
]


def format_timebase(value):
    if value < 1e-3:
        return f"{value * 1e6:g} us/div"
    if value < 1.0:
        return f"{value * 1e3:g} ms/div"
    return f"{value:g} s/div"


def parse_timebase(text):
    match = re.search(r"([0-9]*\.?[0-9]+)\s*(us|ms|s)", text.strip().lower())
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    if unit == "us":
        return value * 1e-6
    if unit == "ms":
        return value * 1e-3
    return value


def format_volts_per_div(value):
    if value < 1.0:
        return f"{value * 1e3:g} mV/div"
    return f"{value:g} V/div"


def parse_volts_per_div(text):
    match = re.search(r"([0-9]*\.?[0-9]+)\s*(mv|v)", text.strip().lower())
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    if unit == "mv":
        return value * 1e-3
    return value


def format_voltage(value):
    if abs(value) < 1.0:
        return f"{value * 1e3:g} mV"
    return f"{value:g} V"


def safe_float(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


class ALCSettingsDialog(QtWidgets.QDialog):
    def __init__(self, ser, serial_lock, parent=None):
        super().__init__(parent)
        self.ser = ser
        self.serial_lock = serial_lock
        self.entry_vars = []
        self.setWindowTitle("ALC/AGC 参数设置")
        self.resize(600, 800)
        self._build_ui()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QGridLayout(scroll_content)

        param_labels = {
            "enable": "ALC/AGC 使能",
            "pga_control_enable": "PGA 控制使能",
            "mode": "工作模式",
            "hold_time_us": "保持时间(us)",
            "attack_time_us": "攻击时间(us)",
            "decay_time_us": "衰减时间(us)",
            "zero_cross_enable": "零交叉使能",
            "pga_zero_cross_enable": "PGA 零交叉使能",
            "fast_decay_enable": "快速衰减使能",
            "noise_gate_enable": "噪声门使能",
            "noise_gate_threshold_db": "噪声门阈值(dB)",
            "amp_recover_enable": "放大器恢复使能",
            "slow_clock_enable": "慢时钟使能",
            "approx_rate_hz": "近似采样率(Hz)",
            "pga_target_half_db": "PGA 目标增益(0.5dB)",
            "pga_max_half_db": "PGA 最大增益(0.5dB)",
            "pga_min_half_db": "PGA 最小增益(0.5dB)",
            "limit_enable": "原始电平限制使能",
            "limit_max_low": "最大限制低字节",
            "limit_max_high": "最大限制高字节",
            "limit_min_low": "最小限制低字节",
            "limit_min_high": "最小限制高字节",
            "gain_attack_jack": "增益攻击插孔模式",
            "ctrl_gen": "控制生成",
            "group": "ADC 组选择",
        }

        for index, param in enumerate(ALC_PARAM_CONFIG):
            name = param["name"]
            label = param_labels.get(name, name)
            range_text = param["range_text"]
            default = param["default"]

            row = index
            label_widget = QtWidgets.QLabel(f"{index + 1}. {label}:")
            label_widget.setMinimumWidth(220)
            line_edit = QtWidgets.QLineEdit(default)
            range_label = QtWidgets.QLabel(f"({range_text})")
            range_label.setStyleSheet("color: gray;")

            scroll_layout.addWidget(label_widget, row, 0)
            scroll_layout.addWidget(line_edit, row, 1)
            scroll_layout.addWidget(range_label, row, 2)

            self.entry_vars.append(
                {
                    "name": name,
                    "line_edit": line_edit,
                    "range_text": range_text,
                    "default": default,
                }
            )

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        button_layout = QtWidgets.QHBoxLayout()
        get_button = QtWidgets.QPushButton("获取参数")
        restore_button = QtWidgets.QPushButton("恢复默认")
        set_button = QtWidgets.QPushButton("设置参数")
        validate_button = QtWidgets.QPushButton("校验参数")
        cancel_button = QtWidgets.QPushButton("取消")

        get_button.clicked.connect(self.get_alc_params)
        restore_button.clicked.connect(self.restore_defaults)
        set_button.clicked.connect(self.send_alc_command)
        validate_button.clicked.connect(self.show_validation_result)
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(get_button)
        button_layout.addWidget(restore_button)
        button_layout.addWidget(set_button)
        button_layout.addWidget(validate_button)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    def show_validation_result(self):
        errors = self.validate_params()
        if errors:
            QtWidgets.QMessageBox.warning(self, "校验结果", "参数校验失败:\n\n" + "\n".join(errors))
        else:
            QtWidgets.QMessageBox.information(self, "校验结果", "参数校验通过!")

    def restore_defaults(self):
        for entry in self.entry_vars:
            entry["line_edit"].setText(entry["default"])
        QtWidgets.QMessageBox.information(self, "成功", "已恢复所有参数为默认值。")

    def _read_response_locked(self, timeout_s):
        response = ""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            waiting = self.ser.in_waiting
            if waiting:
                response += self.ser.read(waiting).decode(errors="ignore")
                if "OK" in response or "ERROR" in response:
                    break
            QtWidgets.QApplication.processEvents()
            time.sleep(0.05)
        return response

    def send_alc_command(self):
        if not self.ser or not self.ser.is_open:
            QtWidgets.QMessageBox.critical(self, "错误", "串口未连接。")
            return

        errors = self.validate_params()
        if errors:
            QtWidgets.QMessageBox.critical(self, "参数错误", "参数校验失败:\n\n" + "\n".join(errors))
            return

        param_values = [entry["line_edit"].text().strip() for entry in self.entry_vars]
        at_command = f"AT+PARAM=ALC,{','.join(param_values)}\r\n"

        try:
            with self.serial_lock:
                self.ser.write(at_command.encode())
                response = self._read_response_locked(2.0)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "错误", f"发送命令时出错:\n{exc}")
            return

        if "OK" in response:
            QtWidgets.QMessageBox.information(
                self,
                "成功",
                f"ALC 参数设置成功!\n\n命令: {at_command.strip()}\n响应: {response.strip()}",
            )
            self.accept()
        elif "ERROR" in response:
            QtWidgets.QMessageBox.critical(self, "错误", f"设置失败:\n\n{response.strip()}")
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "警告",
                f"未收到有效响应。\n\n{response.strip() if response else '无响应'}",
            )

    def get_alc_params(self):
        if not self.ser or not self.ser.is_open:
            QtWidgets.QMessageBox.critical(self, "错误", "串口未连接。")
            return

        try:
            with self.serial_lock:
                self.ser.write(b"AT+PARAM?\r\n")
                response = self._read_response_locked(3.0)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "错误", f"获取参数时出错:\n{exc}")
            return

        if "ERROR" in response:
            QtWidgets.QMessageBox.critical(self, "错误", f"获取参数失败:\n\n{response.strip()}")
            return

        alc_line = None
        for line in response.split("\n"):
            if line.startswith("+PARAM:ALC,"):
                alc_line = line.strip()
                break

        if not alc_line:
            QtWidgets.QMessageBox.critical(self, "错误", f"未找到 ALC 参数响应:\n\n{response.strip()}")
            return

        param_str = alc_line.replace("+PARAM:ALC,", "").strip()
        param_values = [value.strip() for value in param_str.split(",")]

        if len(param_values) != len(self.entry_vars):
            QtWidgets.QMessageBox.critical(
                self,
                "错误",
                f"参数数量不正确，期望 {len(self.entry_vars)} 个，实际 {len(param_values)} 个。\n\n{param_str}",
            )
            return

        for index, entry in enumerate(self.entry_vars):
            entry["line_edit"].setText(param_values[index])

        QtWidgets.QMessageBox.information(self, "成功", f"已获取当前 ALC 参数:\n\n{alc_line}")

    def validate_params(self):
        errors = []

        mode = None
        try:
            mode_str = self.entry_vars[2]["line_edit"].text().strip()
            if mode_str:
                mode = int(mode_str)
        except ValueError:
            pass

        for index, entry in enumerate(self.entry_vars):
            name = entry["name"]
            value_str = entry["line_edit"].text().strip()
            if not value_str:
                errors.append(f"参数 {index + 1} ({name}): 不能为空")
                continue

            try:
                value = int(value_str)
            except ValueError:
                errors.append(f"参数 {index + 1} ({name}): 必须是整数，当前值 {value_str}")
                continue

            if name in {
                "enable",
                "pga_control_enable",
                "zero_cross_enable",
                "pga_zero_cross_enable",
                "fast_decay_enable",
                "noise_gate_enable",
                "amp_recover_enable",
                "slow_clock_enable",
                "limit_enable",
                "gain_attack_jack",
            }:
                if value not in (0, 1):
                    errors.append(f"参数 {index + 1} ({name}): 必须为 0 或 1，当前值 {value}")
            elif name == "mode":
                if value not in (0, 1):
                    errors.append(f"参数 {index + 1} ({name}): 必须为 0 或 1，当前值 {value}")
                mode = value
            elif name == "hold_time_us":
                if value < 0 or value > 1000000:
                    errors.append(f"参数 {index + 1} ({name}): 必须在 0-1000000 范围内，当前值 {value}")
            elif name == "attack_time_us":
                if mode is None:
                    mode = 1
                if mode == 0 and (value < 125 or value > 128000):
                    errors.append(
                        f"参数 {index + 1} ({name}): normal 模式必须在 125-128000 范围内，当前值 {value}"
                    )
                elif mode == 1 and (value < 32 or value > 32000):
                    errors.append(
                        f"参数 {index + 1} ({name}): limiter 模式必须在 32-32000 范围内，当前值 {value}"
                    )
            elif name == "decay_time_us":
                if mode is None:
                    mode = 1
                if mode == 0 and (value < 0 or value > 512000):
                    errors.append(
                        f"参数 {index + 1} ({name}): normal 模式必须在 0-512000 范围内，当前值 {value}"
                    )
                elif mode == 1 and (value < 125 or value > 128000):
                    errors.append(
                        f"参数 {index + 1} ({name}): limiter 模式必须在 125-128000 范围内，当前值 {value}"
                    )
            elif name == "noise_gate_threshold_db":
                if value < -81 or value > -39:
                    errors.append(
                        f"参数 {index + 1} ({name}): 必须在 -81 到 -39 范围内，当前值 {value}"
                    )
            elif name == "approx_rate_hz":
                if value < 8000 or value > 96000:
                    errors.append(f"参数 {index + 1} ({name}): 必须在 8000-96000 范围内，当前值 {value}")
            elif name == "pga_target_half_db":
                if value < -36 or value > 57:
                    errors.append(f"参数 {index + 1} ({name}): 必须在 -36 到 57 范围内，当前值 {value}")
            elif name == "pga_max_half_db":
                if value < -27 or value > 57:
                    errors.append(f"参数 {index + 1} ({name}): 必须在 -27 到 57 范围内，当前值 {value}")
            elif name == "pga_min_half_db":
                if value < -36 or value > 48:
                    errors.append(f"参数 {index + 1} ({name}): 必须在 -36 到 48 范围内，当前值 {value}")
            elif name in {"limit_max_low", "limit_max_high", "limit_min_low", "limit_min_high"}:
                if value < 0 or value > 255:
                    errors.append(f"参数 {index + 1} ({name}): 必须在 0-255 范围内，当前值 {value}")
            elif name == "ctrl_gen":
                if value < 0 or value > 3:
                    errors.append(f"参数 {index + 1} ({name}): 必须在 0-3 范围内，当前值 {value}")
            elif name == "group":
                if value not in (0, 1, 2, 3, 255):
                    errors.append(f"参数 {index + 1} ({name}): 必须为 0-3 或 255，当前值 {value}")

        return errors


class SerialWaveformWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ser = None
        self.serial_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.reader_thread = None
        self.number_re = re.compile(r"-?\d+")
        self.config = load_config()
        self.sample_rate = safe_float(self.config.get("sample_rate"), DEFAULT_SAMPLE_RATE)
        if self.sample_rate <= 0:
            self.sample_rate = DEFAULT_SAMPLE_RATE
        self.timebase_s_per_div = safe_float(self.config.get("timebase"), DEFAULT_TIMEBASE)
        if self.timebase_s_per_div <= 0:
            self.timebase_s_per_div = DEFAULT_TIMEBASE
        self.volts_per_div = safe_float(self.config.get("volts_per_div"), DEFAULT_VOLTS_PER_DIV)
        if self.volts_per_div <= 0:
            self.volts_per_div = DEFAULT_VOLTS_PER_DIV
        self.volts_per_count = safe_float(self.config.get("volts_per_count"), DEFAULT_VOLTS_PER_COUNT)
        if self.volts_per_count <= 0:
            self.volts_per_count = DEFAULT_VOLTS_PER_COUNT

        self.total_time = self.timebase_s_per_div * H_DIVS
        self.buffer_size = self._compute_buffer_size(self.sample_rate, self.timebase_s_per_div)
        self.data_queue = queue.Queue(maxsize=self._queue_size(self.buffer_size))
        self.data_buffer = np.zeros(self.buffer_size, dtype=np.int32)
        self.x_data = np.linspace(0.0, self.total_time, self.buffer_size)
        self.buffer_pos = 0
        self.sample_count = 0
        self.is_paused = False

        self.setWindowTitle("Serial Real-Time Waveform")
        self._build_ui()
        self.apply_timebase_settings(initial=True)
        self.apply_voltage_scale(initial=True)
        self.on_auto_scale_changed()
        self.refresh_ports()
        self.set_connection_state(False)

        if self.auto_connect_checkbox.isChecked():
            QtCore.QTimer.singleShot(200, self.maybe_auto_connect)

        self.update_timer = QtCore.QTimer(self)
        self.update_timer.timeout.connect(self.update_plot)
        self.update_timer.start(30)

    def _build_ui(self):
        central_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        ctrl_layout = QtWidgets.QHBoxLayout()

        ctrl_layout.addWidget(QtWidgets.QLabel("Port:"))
        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.setMinimumWidth(120)
        ctrl_layout.addWidget(self.port_combo)

        ctrl_layout.addWidget(QtWidgets.QLabel("Baud:"))
        self.baud_combo = QtWidgets.QComboBox()
        self.baud_combo.setEditable(True)
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800"])
        self.baud_combo.setCurrentText(str(self.config.get("baud", "115200")))
        ctrl_layout.addWidget(self.baud_combo)

        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_ports)
        ctrl_layout.addWidget(self.refresh_button)

        self.connect_button = QtWidgets.QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_serial)
        ctrl_layout.addWidget(self.connect_button)

        self.disconnect_button = QtWidgets.QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_serial)
        ctrl_layout.addWidget(self.disconnect_button)

        self.auto_connect_checkbox = QtWidgets.QCheckBox("Auto Connect")
        self.auto_connect_checkbox.setChecked(bool(self.config.get("auto_connect", False)))
        self.auto_connect_checkbox.stateChanged.connect(self.save_current_config)
        ctrl_layout.addWidget(self.auto_connect_checkbox)

        self.pause_button = QtWidgets.QPushButton("Pause")
        self.pause_button.clicked.connect(self.toggle_pause)
        ctrl_layout.addWidget(self.pause_button)

        self.alc_button = QtWidgets.QPushButton("ALC 设置")
        self.alc_button.clicked.connect(self.open_alc_settings)
        ctrl_layout.addWidget(self.alc_button)

        ctrl_layout.addStretch()
        main_layout.addLayout(ctrl_layout)

        status_layout = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("Disconnected")
        self.latest_label = QtWidgets.QLabel("Latest: --")
        self.samples_label = QtWidgets.QLabel("Samples: 0")
        self.min_label = QtWidgets.QLabel("Min: --")
        self.max_label = QtWidgets.QLabel("Max: --")
        self.vpp_label = QtWidgets.QLabel("Vpp: --")
        self.rms_label = QtWidgets.QLabel("RMS: --")
        self.freq_label = QtWidgets.QLabel("Freq: --")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.latest_label)
        status_layout.addWidget(self.min_label)
        status_layout.addWidget(self.max_label)
        status_layout.addWidget(self.vpp_label)
        status_layout.addWidget(self.rms_label)
        status_layout.addWidget(self.freq_label)
        status_layout.addWidget(self.samples_label)
        main_layout.addLayout(status_layout)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel("left", "Voltage", units="V")
        self.plot_widget.setLabel("bottom", "Time", units="s")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setXRange(0, self.total_time, padding=0)
        self.plot_widget.enableAutoRange(x=False, y=False)

        self.curve = self.plot_widget.plot(
            self.x_data,
            self.data_buffer,
            pen=pg.mkPen(color=(0, 140, 255), width=1),
        )
        self.curve.setClipToView(True)
        self.zero_line = pg.InfiniteLine(
            0,
            angle=0,
            pen=pg.mkPen(color=(255, 80, 80), width=1, style=QtCore.Qt.DashLine),
        )
        self.plot_widget.addItem(self.zero_line)
        main_layout.addWidget(self.plot_widget, stretch=1)

        zoom_layout = QtWidgets.QHBoxLayout()
        zoom_layout.addWidget(QtWidgets.QLabel("Zoom:"))

        self.zoom_in_button = QtWidgets.QPushButton("Y+")
        self.zoom_in_button.setFixedWidth(40)
        self.zoom_in_button.clicked.connect(self.zoom_in_y)
        zoom_layout.addWidget(self.zoom_in_button)

        self.zoom_out_button = QtWidgets.QPushButton("Y-")
        self.zoom_out_button.setFixedWidth(40)
        self.zoom_out_button.clicked.connect(self.zoom_out_y)
        zoom_layout.addWidget(self.zoom_out_button)

        self.reset_button = QtWidgets.QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_view)
        zoom_layout.addWidget(self.reset_button)

        self.clear_button = QtWidgets.QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_buffer)
        zoom_layout.addWidget(self.clear_button)

        self.auto_scale_checkbox = QtWidgets.QCheckBox("Auto Y")
        self.auto_scale_checkbox.setChecked(bool(self.config.get("auto_scale", False)))
        self.auto_scale_checkbox.stateChanged.connect(self.on_auto_scale_changed)
        zoom_layout.addWidget(self.auto_scale_checkbox)

        zoom_layout.addStretch()
        main_layout.addLayout(zoom_layout)

        scope_layout = QtWidgets.QHBoxLayout()
        scope_layout.addWidget(QtWidgets.QLabel("Timebase:"))
        self.timebase_combo = QtWidgets.QComboBox()
        self.timebase_combo.setEditable(True)
        self.timebase_combo.addItems([format_timebase(value) for value in TIMEBASE_OPTIONS])
        self.timebase_combo.setCurrentText(format_timebase(self.timebase_s_per_div))
        self.timebase_combo.currentIndexChanged.connect(self.apply_timebase_settings)
        self.timebase_combo.lineEdit().editingFinished.connect(self.apply_timebase_settings)
        scope_layout.addWidget(self.timebase_combo)

        scope_layout.addWidget(QtWidgets.QLabel("Sample Rate (Hz):"))
        self.sample_rate_edit = QtWidgets.QLineEdit(f"{self.sample_rate:g}")
        self.sample_rate_edit.setFixedWidth(90)
        self.sample_rate_edit.setValidator(QtGui.QDoubleValidator(0.1, 1e9, 6))
        self.sample_rate_edit.editingFinished.connect(self.apply_timebase_settings)
        scope_layout.addWidget(self.sample_rate_edit)

        scope_layout.addWidget(QtWidgets.QLabel("V/div:"))
        self.volts_div_combo = QtWidgets.QComboBox()
        self.volts_div_combo.setEditable(True)
        self.volts_div_combo.addItems([format_volts_per_div(value) for value in VOLTS_PER_DIV_OPTIONS])
        self.volts_div_combo.setCurrentText(format_volts_per_div(self.volts_per_div))
        self.volts_div_combo.currentIndexChanged.connect(self.apply_voltage_scale)
        self.volts_div_combo.lineEdit().editingFinished.connect(self.apply_voltage_scale)
        scope_layout.addWidget(self.volts_div_combo)

        scope_layout.addWidget(QtWidgets.QLabel("V/LSB:"))
        self.volts_per_count_edit = QtWidgets.QLineEdit(f"{self.volts_per_count:g}")
        self.volts_per_count_edit.setFixedWidth(80)
        self.volts_per_count_edit.setValidator(QtGui.QDoubleValidator(1e-12, 1e9, 9))
        self.volts_per_count_edit.editingFinished.connect(self.apply_voltage_scale)
        scope_layout.addWidget(self.volts_per_count_edit)

        scope_layout.addStretch()
        main_layout.addLayout(scope_layout)

    def _compute_buffer_size(self, sample_rate, timebase):
        target = int(sample_rate * timebase * H_DIVS)
        if target <= 0:
            target = DEFAULT_BUFFER_SIZE
        return max(MIN_BUFFER_SAMPLES, min(MAX_BUFFER_SAMPLES, target))

    def _queue_size(self, buffer_size):
        return min(buffer_size * 4, MAX_BUFFER_SAMPLES)

    def _time_axis_unit(self):
        if self.timebase_s_per_div >= 1.0:
            return 1.0, "s"
        if self.timebase_s_per_div >= 1e-3:
            return 1e3, "ms"
        return 1e6, "us"

    def _voltage_axis_unit(self, y_min, y_max):
        if max(abs(y_min), abs(y_max)) < 1.0:
            return 1e3, "mV"
        return 1.0, "V"

    def update_axes_ticks(self):
        x_axis = self.plot_widget.getAxis("bottom")
        y_axis = self.plot_widget.getAxis("left")

        x_step = self.timebase_s_per_div
        x_scale, x_unit = self._time_axis_unit()
        x_ticks = [
            (i * x_step, f"{(i * x_step) * x_scale:g}")
            for i in range(H_DIVS + 1)
        ]
        x_axis.setTicks([x_ticks])
        self.plot_widget.setLabel("bottom", "Time", units=x_unit)

        if self.auto_scale_checkbox.isChecked():
            y_min, y_max = self.plot_widget.getViewBox().viewRange()[1]
            step = (y_max - y_min) / V_DIVS if V_DIVS else 1.0
            if step == 0:
                step = 1.0
            y_positions = [y_min + step * i for i in range(V_DIVS + 1)]
        else:
            step = self.volts_per_div
            start = -self.volts_per_div * (V_DIVS / 2)
            y_positions = [start + step * i for i in range(V_DIVS + 1)]
            y_min = y_positions[0]
            y_max = y_positions[-1]

        y_scale, y_unit = self._voltage_axis_unit(y_min, y_max)
        y_ticks = [(pos, f"{pos * y_scale:g}") for pos in y_positions]
        y_axis.setTicks([y_ticks])
        self.plot_widget.setLabel("left", "Voltage", units=y_unit)

    def on_auto_scale_changed(self):
        enabled = not self.auto_scale_checkbox.isChecked()
        self.zoom_in_button.setEnabled(enabled)
        self.zoom_out_button.setEnabled(enabled)
        self.volts_div_combo.setEnabled(enabled)
        self.save_current_config()
        if enabled:
            self.apply_voltage_scale()
        else:
            self.update_axes_ticks()

    def apply_timebase_settings(self, *_, initial=False):
        timebase_text = self.timebase_combo.currentText().strip()
        timebase_value = parse_timebase(timebase_text)
        if timebase_value is None:
            try:
                timebase_value = float(timebase_text)
            except ValueError:
                timebase_value = None

        if not timebase_value or timebase_value <= 0:
            if not initial:
                QtWidgets.QMessageBox.warning(self, "Error", "Invalid timebase setting.")
            self.timebase_combo.setCurrentText(format_timebase(self.timebase_s_per_div))
            return

        sample_rate_value = safe_float(self.sample_rate_edit.text().strip(), self.sample_rate)
        if sample_rate_value <= 0:
            if not initial:
                QtWidgets.QMessageBox.warning(self, "Error", "Invalid sample rate.")
            self.sample_rate_edit.setText(f"{self.sample_rate:g}")
            return

        self.timebase_s_per_div = timebase_value
        self.sample_rate = sample_rate_value
        self.total_time = self.timebase_s_per_div * H_DIVS
        self.timebase_combo.blockSignals(True)
        self.timebase_combo.setCurrentText(format_timebase(self.timebase_s_per_div))
        self.timebase_combo.blockSignals(False)
        self.sample_rate_edit.setText(f"{self.sample_rate:g}")

        new_size = self._compute_buffer_size(self.sample_rate, self.timebase_s_per_div)
        if new_size != self.buffer_size:
            self.buffer_size = new_size
            self.data_buffer = np.zeros(self.buffer_size, dtype=np.int32)
            self.buffer_pos = 0
            self.sample_count = 0
            self.data_queue = queue.Queue(maxsize=self._queue_size(self.buffer_size))

        self.x_data = np.linspace(0.0, self.total_time, self.buffer_size)
        self.plot_widget.setXRange(0, self.total_time, padding=0)
        self.curve.setData(self.x_data, self.data_buffer * self.volts_per_count)
        self.update_axes_ticks()
        self.save_current_config()

    def apply_voltage_scale(self, *_, initial=False):
        volts_div_text = self.volts_div_combo.currentText().strip()
        volts_div_value = parse_volts_per_div(volts_div_text)
        if volts_div_value is None:
            try:
                volts_div_value = float(volts_div_text)
            except ValueError:
                volts_div_value = None

        if not volts_div_value or volts_div_value <= 0:
            if not initial:
                QtWidgets.QMessageBox.warning(self, "Error", "Invalid V/div setting.")
            self.volts_div_combo.setCurrentText(format_volts_per_div(self.volts_per_div))
            return

        volts_per_count_value = safe_float(self.volts_per_count_edit.text().strip(), self.volts_per_count)
        if volts_per_count_value <= 0:
            if not initial:
                QtWidgets.QMessageBox.warning(self, "Error", "Invalid V/LSB setting.")
            self.volts_per_count_edit.setText(f"{self.volts_per_count:g}")
            return

        self.volts_per_div = volts_div_value
        self.volts_per_count = volts_per_count_value
        self.volts_div_combo.blockSignals(True)
        self.volts_div_combo.setCurrentText(format_volts_per_div(self.volts_per_div))
        self.volts_div_combo.blockSignals(False)
        self.volts_per_count_edit.setText(f"{self.volts_per_count:g}")

        if not self.auto_scale_checkbox.isChecked():
            half_range = self.volts_per_div * (V_DIVS / 2)
            self.plot_widget.setYRange(-half_range, half_range, padding=0)

        y_data = self._ordered_buffer() * self.volts_per_count
        self.curve.setData(self.x_data, y_data)
        self.update_axes_ticks()
        self.save_current_config()

    def _step_volts_per_div(self, direction):
        options = sorted(set(VOLTS_PER_DIV_OPTIONS + [self.volts_per_div]))
        current = self.volts_per_div
        index = min(range(len(options)), key=lambda i: abs(options[i] - current))
        next_index = max(0, min(len(options) - 1, index + direction))
        next_value = options[next_index]
        self.volts_div_combo.setCurrentText(format_volts_per_div(next_value))
        self.apply_voltage_scale()

    def _estimate_frequency(self, y_data, vpp):
        if self.sample_rate <= 0:
            return None
        if vpp <= 0:
            return None
        threshold = max(0.05 * vpp, self.volts_per_count * 2)
        if threshold <= 0:
            return None

        mid = (float(np.max(y_data)) + float(np.min(y_data))) / 2.0
        centered = y_data - mid
        crosses = 0
        prev = centered[0]
        for value in centered[1:]:
            if prev < -threshold and value > threshold:
                crosses += 1
            prev = value

        duration = len(y_data) / self.sample_rate
        if duration <= 0 or crosses < 1:
            return None
        return crosses / duration

    def save_current_config(self):
        config_data = {
            "port": self.port_combo.currentText().strip(),
            "baud": self.baud_combo.currentText().strip(),
            "auto_connect": bool(self.auto_connect_checkbox.isChecked()),
            "auto_scale": bool(self.auto_scale_checkbox.isChecked()),
            "sample_rate": self.sample_rate,
            "timebase": self.timebase_s_per_div,
            "volts_per_div": self.volts_per_div,
            "volts_per_count": self.volts_per_count,
        }
        self.config.update(config_data)
        save_config(self.config)

    def refresh_ports(self, keep_selection=True):
        ports = list_serial_ports()
        current = self.port_combo.currentText().strip()

        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        self.port_combo.blockSignals(False)

        selected = None
        if keep_selection and current in ports:
            selected = current
        elif self.config.get("port") in ports:
            selected = self.config.get("port")
        elif ports and (len(ports) == 1 or not current):
            selected = ports[0]

        if selected:
            self.port_combo.setCurrentText(selected)

    def set_connection_state(self, connected):
        state = not connected
        self.port_combo.setEnabled(state)
        self.baud_combo.setEnabled(state)
        self.refresh_button.setEnabled(state)
        self.connect_button.setEnabled(state)

        self.disconnect_button.setEnabled(connected)
        self.pause_button.setEnabled(connected)
        self.alc_button.setEnabled(connected)

    def connect_serial(self):
        if self.ser and self.ser.is_open:
            return

        if self.is_paused:
            self.toggle_pause()

        port = self.port_combo.currentText().strip()
        if not port:
            self.refresh_ports(keep_selection=False)
            port = self.port_combo.currentText().strip()

        baud = self.baud_combo.currentText().strip()
        if not port:
            QtWidgets.QMessageBox.critical(self, "Error", "请选择串口")
            return

        try:
            baud_int = int(baud)
        except ValueError:
            QtWidgets.QMessageBox.critical(self, "Error", f"无效波特率: {baud}")
            return

        try:
            self.ser = serial.Serial(port, baud_int, timeout=0.05)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return

        self.status_label.setText(f"Connected: {port} @ {baud_int}")
        self.clear_buffer()
        self.start_reader()
        self.set_connection_state(True)
        self.save_current_config()

    def disconnect_serial(self):
        self.stop_event.set()
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=0.5)
        self.reader_thread = None

        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

        if self.is_paused:
            self.toggle_pause()

        self.status_label.setText("Disconnected")
        self.set_connection_state(False)
        self.save_current_config()

    def start_reader(self):
        self.stop_event.clear()
        self.reader_thread = threading.Thread(target=self.read_serial_continuously, daemon=True)
        self.reader_thread.start()

    def _enqueue_value(self, value):
        try:
            self.data_queue.put_nowait(value)
        except queue.Full:
            try:
                self.data_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.data_queue.put_nowait(value)
            except queue.Full:
                pass

    def read_serial_continuously(self):
        while not self.stop_event.is_set() and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 0:
                    with self.serial_lock:
                        raw_line = self.ser.readline()
                    if not raw_line:
                        continue
                    line = raw_line.decode(errors="ignore").strip()
                    if line:
                        numbers = self.number_re.findall(line)
                        if numbers:
                            for number in numbers:
                                try:
                                    self._enqueue_value(int(number))
                                except ValueError:
                                    continue
                else:
                    time.sleep(0.01)
            except Exception:
                break

    def update_plot(self):
        if self.is_paused:
            return

        updated = False
        latest_value = None
        count = 0

        while True:
            try:
                value = self.data_queue.get_nowait()
            except queue.Empty:
                break
            self.data_buffer[self.buffer_pos] = value
            self.buffer_pos = (self.buffer_pos + 1) % self.buffer_size
            latest_value = value
            count += 1
            updated = True

        if not updated:
            return

        self.sample_count += count
        y_data = self._ordered_buffer() * self.volts_per_count
        self.curve.setData(self.x_data, y_data)

        y_min = float(np.min(y_data))
        y_max = float(np.max(y_data))
        vpp = y_max - y_min
        rms = float(np.sqrt(np.mean(np.square(y_data))))
        self.min_label.setText(f"Min: {format_voltage(y_min)}")
        self.max_label.setText(f"Max: {format_voltage(y_max)}")
        self.vpp_label.setText(f"Vpp: {format_voltage(vpp)}")
        self.rms_label.setText(f"RMS: {format_voltage(rms)}")
        freq = self._estimate_frequency(y_data, vpp)
        if freq is None:
            self.freq_label.setText("Freq: --")
        else:
            self.freq_label.setText(f"Freq: {freq:g} Hz")

        if self.auto_scale_checkbox.isChecked():
            if y_min == y_max:
                y_min -= 1.0
                y_max += 1.0
            padding = (y_max - y_min) * 0.1
            self.plot_widget.setYRange(y_min - padding, y_max + padding, padding=0)
            self.update_axes_ticks()

        if latest_value is not None:
            latest_voltage = latest_value * self.volts_per_count
            self.latest_label.setText(f"Latest: {format_voltage(latest_voltage)}")
        self.samples_label.setText(f"Samples: {self.sample_count}")

    def _ordered_buffer(self):
        if self.buffer_pos == 0:
            return self.data_buffer
        return np.concatenate((self.data_buffer[self.buffer_pos :], self.data_buffer[: self.buffer_pos]))

    def clear_buffer(self):
        self.data_buffer[:] = 0
        self.buffer_pos = 0
        self.sample_count = 0
        while True:
            try:
                self.data_queue.get_nowait()
            except queue.Empty:
                break
        self.latest_label.setText("Latest: --")
        self.min_label.setText("Min: --")
        self.max_label.setText("Max: --")
        self.vpp_label.setText("Vpp: --")
        self.rms_label.setText("RMS: --")
        self.freq_label.setText("Freq: --")
        self.samples_label.setText("Samples: 0")
        self.curve.setData(self.x_data, self.data_buffer * self.volts_per_count)

    def zoom_in_y(self):
        if self.auto_scale_checkbox.isChecked():
            return
        self._step_volts_per_div(-1)

    def zoom_out_y(self):
        if self.auto_scale_checkbox.isChecked():
            return
        self._step_volts_per_div(1)

    def reset_view(self):
        self.plot_widget.setXRange(0, self.total_time, padding=0)
        if not self.auto_scale_checkbox.isChecked():
            half_range = self.volts_per_div * (V_DIVS / 2)
            self.plot_widget.setYRange(-half_range, half_range, padding=0)
        self.plot_widget.enableAutoRange(x=False, y=False)
        self.update_axes_ticks()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_button.setText("Resume")
            current_status = self.status_label.text()
            if " [Paused]" not in current_status:
                self.status_label.setText(current_status + " [Paused]")
        else:
            self.pause_button.setText("Pause")
            current_status = self.status_label.text()
            if " [Paused]" in current_status:
                self.status_label.setText(current_status.replace(" [Paused]", ""))

    def open_alc_settings(self):
        if not self.ser or not self.ser.is_open:
            QtWidgets.QMessageBox.critical(self, "Error", "请先连接串口")
            return

        dialog = ALCSettingsDialog(self.ser, self.serial_lock, self)
        dialog.exec_()

    def maybe_auto_connect(self):
        if not self.auto_connect_checkbox.isChecked():
            return
        ports = list_serial_ports()
        current = self.port_combo.currentText().strip()
        if current and current in ports:
            self.connect_serial()
        elif len(ports) == 1:
            self.port_combo.setCurrentText(ports[0])
            self.connect_serial()

    def closeEvent(self, event):
        self.disconnect_serial()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = SerialWaveformWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
