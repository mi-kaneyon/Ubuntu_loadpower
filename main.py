import tkinter as tk
from tkinter import ttk
import psutil
from cpu_load.cpu_load import apply_cpu_load
from gpu_load.gpu_load import apply_combined_load, apply_gpu_tensor_load
from system_info.system_info import get_cpu_info, get_gpu_info, get_system_power
import threading
import time

class LoadTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System power loading Tester")
        self.root.geometry("1000x800")  # ウィンドウサイズを大きく設定

        self.cpu_load = tk.IntVar()
        self.gpu_load = tk.IntVar()
        self.gpu_load_type = tk.StringVar(value="3D描画")  # GPU負荷タイプの選択

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

        # PSUの電力消費を表示するボックスを追加
        self.psu_power_label = tk.Label(root, text="System Power: N/A", font=("Helvetica", 14), anchor="w", justify="left")
        self.psu_power_label.grid(column=0, row=7, padx=10, pady=10, sticky="w")

        self.stop_event = threading.Event()

        self.display_system_info()
        self.start_update_thread()

    def display_system_info(self):
        cpu_info = get_cpu_info()
        gpu_info = get_gpu_info()
        self.info_area.insert(tk.END, "CPU情報:\n" + cpu_info + "\n")
        self.info_area.insert(tk.END, "GPU情報:\n" + gpu_info + "\n")

    def apply_load(self):
        self.stop_event.clear()
        cpu_load_percentage = self.cpu_load.get()
        gpu_load_percentage = self.gpu_load.get()
        gpu_load_type = self.gpu_load_type.get()

        self.info_area.insert(tk.END, f"\nCPU負荷: {cpu_load_percentage}%\n")
        self.info_area.insert(tk.END, f"GPU負荷: {gpu_load_percentage}% ({gpu_load_type})\n")

        if cpu_load_percentage > 0:
            self.cpu_stop_event = apply_cpu_load(cpu_load_percentage)
        if gpu_load_percentage > 0:
            if gpu_load_type == "3D描画":
                self.gpu_thread = threading.Thread(target=self.run_combined_load, args=(gpu_load_percentage,), daemon=True)
            else:
                self.gpu_thread = threading.Thread(target=self.run_gpu_tensor_load, args=(gpu_load_percentage,), daemon=True)
            self.gpu_thread.start()

    def stop_load(self):
        self.stop_event.set()
        if hasattr(self, 'cpu_stop_event'):
            self.cpu_stop_event.set()
        if hasattr(self, 'gpu_thread') and self.gpu_thread.is_alive():
            self.gpu_thread.join()
        self.info_area.insert(tk.END, "\n負荷テストが停止されました。\n")

        # 初期状態に戻す
        self.cpu_slider.set(0)
        self.gpu_slider.set(0)
        self.gpu_load_type.set("3D描画")

    def run_combined_load(self, gpu_load_percentage):
        if not self.stop_event.is_set():
            apply_combined_load(gpu_load_percentage, self.stop_event)

    def run_gpu_tensor_load(self, gpu_load_percentage):
        if not self.stop_event.is_set():
            apply_gpu_tensor_load(gpu_load_percentage, self.stop_event)

    def update_system_info(self):
        while True:
            try:
                system_power = get_system_power()  # システム全体の電力量を取得
                self.psu_power_label.config(text=system_power)
                self.info_area.insert(tk.END, "\n更新されたシステム情報:\n" + system_power + "\n")
                time.sleep(5)  # 5秒ごとに更新
            except Exception as e:
                self.info_area.insert(tk.END, f"\nエラー: {str(e)}\n")
                time.sleep(5)

    def start_update_thread(self):
        update_thread = threading.Thread(target=self.update_system_info, daemon=True)
        update_thread.start()

    def exit_app(self):
        self.root.quit()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = LoadTestApp(root)
    root.mainloop()
