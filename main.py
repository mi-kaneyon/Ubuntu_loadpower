import tkinter as tk
from tkinter import ttk
from cpu_load.cpu_load import apply_cpu_load
from gpu_load.gpu_load import apply_gpu_tensor_load, apply_combined_load
from system_info.system_info import get_cpu_info, get_gpu_info, get_psu_power
import threading
import time
import psutil  # 追加: リアルタイムのCPUとメモリ情報を取得するためにpsutilを使用
import torch

class LoadTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System power loading Tester")
        self.root.geometry("1000x900")  # ウィンドウの縦幅を調整

        self.cpu_load = tk.IntVar()
        self.gpu_load = tk.IntVar()
        self.gpu_load_type = tk.StringVar(value="3D描画")

        ttk.Label(root, text="CPU負荷（%）").grid(column=0, row=0, padx=10, pady=10)
        self.cpu_slider = ttk.Scale(root, from_=0, to=100, variable=self.cpu_load)
        self.cpu_slider.grid(column=1, row=0, padx=10, pady=10)

        ttk.Label(root, text="GPU負荷（%）").grid(column=0, row=1, padx=10, pady=10)
        self.gpu_slider = ttk.Scale(root, from_=0, to=100, variable=self.gpu_load)
        self.gpu_slider.grid(column=1, row=1, padx=10, pady=10)

        ttk.Label(root, text="GPU負荷タイプ").grid(column=0, row=2, padx=10, pady=10)
        self.gpu_load_3d = ttk.Radiobutton(root, text="3D描画", variable=self.gpu_load_type, value="3D描画")
        self.gpu_load_3d.grid(column=1, row=2, padx=10, pady=10)
        self.gpu_load_tensor = ttk.Radiobutton(root, text="モデル学習", variable=self.gpu_load_type, value="モデル学習")
        self.gpu_load_tensor.grid(column=2, row=2, padx=10, pady=10)

        self.start_button = ttk.Button(root, text="負荷をかける", command=self.apply_load)
        self.start_button.grid(column=0, row=3, columnspan=3, pady=20)

        self.stop_button = ttk.Button(root, text="負荷を停止", command=self.stop_load)
        self.stop_button.grid(column=0, row=4, columnspan=3, pady=20)

        self.exit_button = ttk.Button(root, text="終了", command=self.exit_app)
        self.exit_button.grid(column=0, row=5, columnspan=3, pady=20)

        self.info_area = tk.Text(root, height=10, width=80, font=("Helvetica", 14))  # テキストボックスの高さを調整
        self.info_area.grid(column=0, row=6, columnspan=3, padx=10, pady=10)

        # PSUの電力消費を表示するボックス
        self.psu_power_label = tk.Label(root, text="PSU Power: N/A", font=("Helvetica", 14))
        self.psu_power_label.grid(column=0, row=7, columnspan=3, pady=10)

        # CPUとメモリの使用率を表示するラベル
        self.cpu_usage_label = tk.Label(root, text="CPU Usage: N/A", font=("Helvetica", 14))
        self.cpu_usage_label.grid(column=0, row=8, columnspan=3, pady=10)

        self.memory_usage_label = tk.Label(root, text="Memory Usage: N/A", font=("Helvetica", 14))
        self.memory_usage_label.grid(column=0, row=9, columnspan=3, pady=10)

        self.display_system_info()
        self.start_update_thread()

    def display_system_info(self):
        cpu_info = get_cpu_info()
        gpu_info = get_gpu_info()
        self.info_area.insert(tk.END, "CPU情報:\n" + cpu_info + "\n")
        self.info_area.insert(tk.END, "GPU情報:\n" + gpu_info + "\n")

    def apply_load(self):
        self.stop_event = threading.Event()

        cpu_load_percentage = self.cpu_load.get()
        gpu_load_percentage = self.gpu_load.get()
        gpu_load_type = self.gpu_load_type.get()

        self.info_area.insert(tk.END, f"\nCPU負荷: {cpu_load_percentage}%\n")
        self.info_area.insert(tk.END, f"GPU負荷: {gpu_load_percentage}% ({gpu_load_type})\n")
        
        if cpu_load_percentage > 0:
            self.cpu_thread = threading.Thread(target=self.run_cpu_load, args=(cpu_load_percentage,), daemon=True)
            self.cpu_thread.start()

        if gpu_load_percentage > 0:
            gpu_ids = list(range(torch.cuda.device_count()))
            if gpu_load_type == "3D描画":
                self.gpu_thread = threading.Thread(target=self.run_gpu_load, args=(gpu_load_percentage, gpu_ids), daemon=True)
            else:
                self.gpu_thread = threading.Thread(target=self.run_gpu_tensor_load, args=(gpu_load_percentage, gpu_ids), daemon=True)
            self.gpu_thread.start()

    def run_cpu_load(self, cpu_load_percentage):
        apply_cpu_load(cpu_load_percentage, self.stop_event)

    def run_gpu_load(self, gpu_load_percentage, gpu_ids):
        apply_combined_load(gpu_load_percentage, self.stop_event, gpu_ids)

    def run_gpu_tensor_load(self, gpu_load_percentage, gpu_ids):
        apply_gpu_tensor_load(gpu_load_percentage, self.stop_event, gpu_ids)

    def update_system_info(self):
        while True:
            gpu_info = get_gpu_info()
            psu_power = get_psu_power()

            # CPUとメモリの使用率を取得して表示
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_usage = psutil.virtual_memory().percent

            self.info_area.insert(tk.END, "\n更新されたシステム情報:\n" + gpu_info + "\n")
            self.psu_power_label.config(text=psu_power)
            self.cpu_usage_label.config(text=f"CPU Usage: {cpu_usage}%")
            self.memory_usage_label.config(text=f"Memory Usage: {memory_usage}%")

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

if __name__ == "__main__":
    root = tk.Tk()
    app = LoadTestApp(root)
    root.mainloop()
