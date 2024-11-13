import os
import subprocess
import tkinter as tk
from tkinter import ttk
from cpu_load.cpu_load import apply_cpu_load  # 修正: apply_cpu_loadを正しくインポート
from gpu_load.gpu_load import apply_gpu_tensor_load, apply_combined_load, apply_gpu_vram_load
from system_info.system_info import get_cpu_info, get_gpu_info, get_psu_power
import threading
import time
import psutil  # 追加: リアルタイムのCPUとメモリ情報を取得するためにpsutilを使用
import torch
from tkinter import messagebox
import random
import string
import hashlib
from concurrent.futures import ThreadPoolExecutor

# Circular import solution - move StorageTestApp import inside the relevant function
class LoadTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Power Loading Tester")
        self.root.geometry("1200x900")  # ウィンドウの幅を拡張して見切れないように調整

        # メインウィンドウ
        self.cpu_load = tk.IntVar()
        self.gpu_load = tk.IntVar()
        self.gpu_vram_load = tk.IntVar()
        self.gpu_load_type = tk.StringVar(value="3D Render")

        # ボタンとスライダーを2列に並べるためのフレーム作成
        controls_frame = tk.Frame(root)
        controls_frame.grid(column=0, row=0, padx=10, pady=10)

        ttk.Label(controls_frame, text="CPU Load (%)").grid(column=0, row=0, padx=10, pady=10)
        self.cpu_slider = ttk.Scale(controls_frame, from_=0, to=100, variable=self.cpu_load)
        self.cpu_slider.grid(column=1, row=0, padx=10, pady=10)

        ttk.Label(controls_frame, text="GPU Load (%)").grid(column=0, row=1, padx=10, pady=10)
        self.gpu_slider = ttk.Scale(controls_frame, from_=0, to=100, variable=self.gpu_load)
        self.gpu_slider.grid(column=1, row=1, padx=10, pady=10)
        
        ttk.Label(controls_frame, text="GPU VRAM Load (%)").grid(column=0, row=2, padx=10, pady=10)
        self.gpu_vram_slider = ttk.Scale(controls_frame, from_=0, to=100, variable=self.gpu_vram_load)
        self.gpu_vram_slider.grid(column=1, row=2, padx=10, pady=10)

        ttk.Label(controls_frame, text="GPU Load Type").grid(column=0, row=3, padx=10, pady=10)
        self.gpu_load_3d = ttk.Radiobutton(controls_frame, text="3D Render", variable=self.gpu_load_type, value="3D Render")
        self.gpu_load_3d.grid(column=1, row=3, padx=10, pady=10)
        self.gpu_load_tensor = ttk.Radiobutton(controls_frame, text="Model Training", variable=self.gpu_load_type, value="Model Training")
        self.gpu_load_tensor.grid(column=2, row=3, padx=10, pady=10)

        self.start_button = ttk.Button(controls_frame, text="Start Load", command=self.apply_load)
        self.start_button.grid(column=0, row=4, padx=10, pady=10)

        self.stop_button = ttk.Button(controls_frame, text="Stop Load", command=self.stop_load)
        self.stop_button.grid(column=1, row=4, padx=10, pady=10)

        # ストレージテストボタンをStop Loadの右、Exitの左に配置
        self.storage_test_button = ttk.Button(controls_frame, text="Storage Test", command=self.open_storage_window)
        self.storage_test_button.grid(column=2, row=4, padx=10, pady=10)

        self.exit_button = ttk.Button(controls_frame, text="Exit", command=self.exit_app)
        self.exit_button.grid(column=3, row=4, padx=10, pady=10)

        # 情報表示エリア
        self.info_area = tk.Text(root, height=10, width=100, font=("Helvetica", 14))  # テキストボックスの幅を拡張
        self.info_area.grid(column=0, row=1, columnspan=2, padx=10, pady=10)

        # PSUの電力消費を表示するボックス
        self.psu_power_label = tk.Label(root, text="PSU Power: N/A", font=("Helvetica", 14))
        self.psu_power_label.grid(column=0, row=2, columnspan=2, pady=10)

        # CPUとメモリの使用率を表示するラベル
        self.cpu_usage_label = tk.Label(root, text="CPU Usage: N/A", font=("Helvetica", 14))
        self.cpu_usage_label.grid(column=0, row=3, columnspan=2, pady=10)

        self.memory_usage_label = tk.Label(root, text="Memory Usage: N/A", font=("Helvetica", 14))
        self.memory_usage_label.grid(column=0, row=4, columnspan=2, pady=10)

        # GPU VRAM使用率を表示するラベル
        self.gpu_vram_label = tk.Label(root, text="VRAM Usage: N/A", font=("Helvetica", 14))
        self.gpu_vram_label.grid(column=0, row=5, columnspan=2, pady=10)

        self.display_system_info()
        self.start_update_thread()

    def display_system_info(self):
        cpu_info = get_cpu_info()
        gpu_info = get_gpu_info()
        self.info_area.insert(tk.END, "CPU Info:\n" + cpu_info + "\n")
        self.info_area.insert(tk.END, "GPU Info:\n" + gpu_info + "\n")

    def apply_load(self):
        self.stop_event = threading.Event()

        cpu_load_percentage = self.cpu_load.get()
        gpu_load_percentage = self.gpu_load.get()
        gpu_vram_percentage = self.gpu_vram_load.get()
        gpu_load_type = self.gpu_load_type.get()

        self.info_area.insert(tk.END, f"\nCPU Load: {cpu_load_percentage}%\n")
        self.info_area.insert(tk.END, f"GPU Load: {gpu_load_percentage}% ({gpu_load_type})\n")
        self.info_area.insert(tk.END, f"GPU VRAM Load: {gpu_vram_percentage}%\n")
        
        if cpu_load_percentage > 0:
            self.cpu_thread = threading.Thread(target=self.run_cpu_load, args=(cpu_load_percentage,), daemon=True)
            self.cpu_thread.start()

        if gpu_load_percentage > 0:
            gpu_ids = list(range(torch.cuda.device_count()))
            if gpu_load_type == "3D Render":
                self.gpu_thread = threading.Thread(target=self.run_gpu_load, args=(gpu_load_percentage, gpu_ids), daemon=True)
            else:
                self.gpu_thread = threading.Thread(target=self.run_gpu_tensor_load, args=(gpu_load_percentage, gpu_ids), daemon=True)
            self.gpu_thread.start()

        if gpu_vram_percentage > 0:
            gpu_ids = list(range(torch.cuda.device_count()))  # ここでgpu_idsを再定義
            self.gpu_vram_thread = threading.Thread(target=self.run_gpu_vram_load, args=(gpu_vram_percentage, gpu_ids), daemon=True)
            self.gpu_vram_thread.start()

    def run_cpu_load(self, cpu_load_percentage):
        apply_cpu_load(cpu_load_percentage, self.stop_event)

    def run_gpu_load(self, gpu_load_percentage, gpu_ids):
        apply_combined_load(gpu_load_percentage, self.stop_event, gpu_ids)

    def run_gpu_tensor_load(self, gpu_load_percentage, gpu_ids):
        apply_gpu_tensor_load(gpu_load_percentage, self.stop_event, gpu_ids)

    def run_gpu_vram_load(self, vram_percentage, gpu_ids):
        apply_gpu_vram_load(vram_percentage, self.stop_event, gpu_ids)

    def update_system_info(self):
        while True:
            gpu_info = get_gpu_info()
            psu_power = get_psu_power()

            # CPUとメモリの使用率を取得して表示
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_usage = psutil.virtual_memory().percent
            vram_usage = torch.cuda.memory_allocated() / torch.cuda.get_device_properties(0).total_memory * 100

            self.info_area.insert(tk.END, "\nUpdated System Info:\n" + gpu_info + "\n")
            self.psu_power_label.config(text=psu_power)
            self.cpu_usage_label.config(text=f"CPU Usage: {cpu_usage}%")
            self.memory_usage_label.config(text=f"Memory Usage: {memory_usage}%")
            self.gpu_vram_label.config(text=f"VRAM Usage: {vram_usage:.2f}%")

            if vram_usage > 90:  # 90%を超えたら警告を表示
                messagebox.showwarning("Warning", "VRAM usage exceeds 90%. Reduce the load.")

            time.sleep(5)  # 5秒ごとに更新

    def start_update_thread(self):
        update_thread = threading.Thread(target=self.update_system_info, daemon=True)
        update_thread.start()

    def stop_load(self):
        if hasattr(self, 'stop_event'):
            self.stop_event.set()

    def exit_app(self):
        self.root.quit()
        self.root.destroy()

    def open_storage_window(self):
        from storage_load.storage_test import StorageTestApp  # 遅延インポートして循環インポートを回避
        storage_window = tk.Toplevel(self.root)
        storage_window.title("Storage Test")
        storage_window.geometry("600x500")
        
        storage_test_app = StorageTestApp(storage_window)  # サブウィンドウでStorageTestAppを初期化

if __name__ == "__main__":
    root = tk.Tk()
    app = LoadTestApp(root)
    root.mainloop()
