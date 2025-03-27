#!/usr/bin/env python3
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import multiprocessing
import time
import psutil
import torch

from cpu_load.cpu_load import apply_cpu_load, apply_cpu_load_x86
from gpu_load.gpu_load import apply_gpu_tensor_load, apply_combined_load, apply_gpu_vram_load
from system_info.system_info import get_cpu_info, get_gpu_info, get_psu_power

# StorageTest 関連のインポート
try:
    from storage_load.storage_test import StorageTest, StorageTestApp
except ImportError:
    StorageTest = None
    StorageTestApp = None

# NetworkTest 関連のインポート
try:
    # 今回は連続実行用の関数 run_network_test_loop を使用する
    from network_test.nettest import NetworkTestApp, run_network_test_loop
except ImportError:
    run_network_test_loop = None
    NetworkTestApp = None

# グローバルな同期イベント（Burn‑in テスト用）
global start_event
start_event = threading.Event()


def run_cpu_load_wrapper(cpu_func, cpu_load_percentage, stop_event):
    start_event.wait()
    cpu_func(cpu_load_percentage, stop_event)


def run_gpu_load_wrapper(gpu_func, gpu_load_percentage, gpu_ids, stop_event):
    start_event.wait()
    gpu_func(gpu_load_percentage, stop_event, gpu_ids)


def run_sound_test_wrapper(stop_event, info_area, sound_threshold, delay_time=3, test_duration=120):
    start_event.wait()
    time.sleep(delay_time)
    if test_duration < 120:
        try:
            from sound_test.noisetester import play_and_record_main
        except ImportError:
            if info_area.winfo_exists():
                info_area.insert(tk.END, "[Sound Loop] Sound test module not found. Skipping sound test.\n")
                info_area.see(tk.END)
            return
        try:
            mean_corr = play_and_record_main()
            if info_area.winfo_exists():
                info_area.insert(tk.END, f"[Sound Loop] Single run mean correlation: {mean_corr:.4f}\n")
                if mean_corr < sound_threshold:
                    info_area.insert(tk.END, "[Sound Loop] Warning: Low correlation detected.\n")
                else:
                    info_area.insert(tk.END, "[Sound Loop] Sound test passed.\n")
                info_area.see(tk.END)
        except Exception as e:
            if info_area.winfo_exists():
                info_area.insert(tk.END, f"[Sound Loop] Exception: {e}\n")
        return
    else:
        while not stop_event.is_set():
            try:
                from sound_test.noisetester import play_and_record_main
            except ImportError:
                if info_area.winfo_exists():
                    info_area.insert(tk.END, "[Sound Loop] Sound test module not found. Skipping sound test.\n")
                    info_area.see(tk.END)
                return
            try:
                mean_corr = play_and_record_main()
                if info_area.winfo_exists():
                    info_area.insert(tk.END, f"[Sound Loop] Mean correlation: {mean_corr:.4f}\n")
                    if mean_corr < sound_threshold:
                        info_area.insert(tk.END, "[Sound Loop] Warning: Low correlation detected.\n")
                    else:
                        info_area.insert(tk.END, "[Sound Loop] Sound test passed.\n")
                    info_area.see(tk.END)
            except Exception as e:
                if info_area.winfo_exists():
                    info_area.insert(tk.END, f"[Sound Loop] Exception: {e}\n")
            for _ in range(3):
                if stop_event.is_set():
                    break
                time.sleep(1)


def run_storage_test_wrapper(storage_instance, progress_callback, duration, stop_event):
    start_event.wait()
    storage_instance.run_storage_test(progress_callback, duration)


def run_network_test_wrapper(stop_event, net_area, test_interval=5):
    # ネットワークテストの連続実行用関数を使用する
    if run_network_test_loop is None:
        net_area.insert(tk.END, "[Network Test] Network test module not found. Skipping network test.\n")
        net_area.see(tk.END)
        return
    # ここでは、ターゲット IP をデフォルト（例: "8.8.8.8"）として実行します
    target_ip = "8.8.8.8"
    run_network_test_loop(stop_event, target_ip, test_interval, callback=lambda result: (
        net_area.insert(tk.END, f"[Network Test] Result: {result}\n"),
        net_area.see(tk.END)
    ))


def create_burnin_popup(root):
    popup = tk.Toplevel(root)
    popup.title("Burn‑in Test Progress")
    popup.geometry("600x400")
    progress_area = tk.Text(popup, height=20, width=70, font=("Helvetica", 10))
    progress_area.pack(padx=10, pady=10)
    return popup, progress_area


########################################
# Main GUI クラス
########################################
class LoadTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Power Loading Tester")
        self.root.geometry("1200x900")

        # 単体テスト時は burn_in_mode を False にする
        self.burn_in_mode = False

        # サウンドテストしきい値
        self.sound_threshold = 0.6

        # 負荷テスト制御変数
        self.cpu_load = tk.IntVar(value=0)
        self.gpu_load = tk.IntVar(value=0)
        self.gpu_vram_load = tk.IntVar(value=0)
        self.gpu_load_type = tk.StringVar(value="3D Render")
        self.cpu_load_type = tk.StringVar(value="Standard")

        # Burn‑in テスト関連
        self.burnin_duration = tk.IntVar(value=50)  # テスト時間（秒）
        self.stress_level = tk.StringVar(value="Low")

        # ストップイベント・スレッド管理
        self.stop_event = None
        self.burnin_stop_event = threading.Event()
        self.cpu_threads = []
        self.cpu_processes = []
        self.gpu_threads = []
        self.sound_test_thread = None
        self.storage_test_thread = None
        self.network_test_thread = None

        # UI レイアウト
        controls_frame = tk.Frame(root)
        controls_frame.grid(column=0, row=0, padx=10, pady=10)

        # CPU Load Controls
        ttk.Label(controls_frame, text="CPU Load (%)").grid(column=0, row=0, padx=10, pady=5)
        self.cpu_slider = ttk.Scale(controls_frame, from_=0, to=100, variable=self.cpu_load)
        self.cpu_slider.grid(column=1, row=0, padx=10, pady=5)
        ttk.Label(controls_frame, text="CPU Load Type").grid(column=0, row=1, padx=10, pady=5)
        self.cpu_load_standard = ttk.Radiobutton(controls_frame, text="Standard", variable=self.cpu_load_type, value="Standard")
        self.cpu_load_standard.grid(column=1, row=1, padx=10, pady=5)
        self.cpu_load_x86 = ttk.Radiobutton(controls_frame, text="x86 Instructions", variable=self.cpu_load_type, value="x86")
        self.cpu_load_x86.grid(column=2, row=1, padx=10, pady=5)

        # GPU Load Controls
        ttk.Label(controls_frame, text="GPU Load (%)").grid(column=0, row=2, padx=10, pady=5)
        self.gpu_slider = ttk.Scale(controls_frame, from_=0, to=100, variable=self.gpu_load)
        self.gpu_slider.grid(column=1, row=2, padx=10, pady=5)
        ttk.Label(controls_frame, text="GPU VRAM Load (%)").grid(column=0, row=3, padx=10, pady=5)
        self.gpu_vram_slider = ttk.Scale(controls_frame, from_=0, to=100, variable=self.gpu_vram_load)
        self.gpu_vram_slider.grid(column=1, row=3, padx=10, pady=5)
        ttk.Label(controls_frame, text="GPU Load Type").grid(column=0, row=4, padx=10, pady=5)
        self.gpu_load_3d = ttk.Radiobutton(controls_frame, text="3D Render", variable=self.gpu_load_type, value="3D Render")
        self.gpu_load_3d.grid(column=1, row=4, padx=10, pady=5)
        self.gpu_load_tensor = ttk.Radiobutton(controls_frame, text="Model Training", variable=self.gpu_load_type, value="Model Training")
        self.gpu_load_tensor.grid(column=2, row=4, padx=10, pady=5)

        # テストボタン
        self.start_button = ttk.Button(controls_frame, text="Start Load", command=self.apply_load)
        self.start_button.grid(column=0, row=5, padx=10, pady=10)
        self.stop_button = ttk.Button(controls_frame, text="Stop Load", command=self.stop_all_tests)
        self.stop_button.grid(column=1, row=5, padx=10, pady=10)
        self.storage_test_button = ttk.Button(controls_frame, text="Storage Test", command=self.open_storage_window)
        self.storage_test_button.grid(column=2, row=5, padx=10, pady=10)
        self.sound_test_button = ttk.Button(controls_frame, text="Sound Test", command=self.open_sound_test_window)
        self.sound_test_button.grid(column=3, row=5, padx=10, pady=10)
        self.network_test_button = ttk.Button(controls_frame, text="Network Test", command=self.open_network_test_window)
        self.network_test_button.grid(column=4, row=5, padx=10, pady=10)
        self.exit_button = ttk.Button(controls_frame, text="Exit", command=self.exit_app)
        self.exit_button.grid(column=5, row=5, padx=10, pady=10)

        # Burn‑in Test Controls
        ttk.Separator(controls_frame, orient="horizontal").grid(column=0, row=6, columnspan=6, sticky="ew", pady=10)
        ttk.Label(controls_frame, text="Burn‑in Test Duration (sec):").grid(column=0, row=7, padx=10, pady=5)
        self.burnin_entry = ttk.Entry(controls_frame, textvariable=self.burnin_duration, width=10)
        self.burnin_entry.grid(column=1, row=7, padx=10, pady=5)
        ttk.Label(controls_frame, text="Stress Level:").grid(column=2, row=7, padx=10, pady=5)
        self.stress_combo = ttk.Combobox(controls_frame, textvariable=self.stress_level,
                                         values=["Low", "Mid", "High"], state="readonly", width=10)
        self.stress_combo.grid(column=3, row=7, padx=10, pady=5)
        self.burnin_button = ttk.Button(controls_frame, text="Run Burn‑in Test", command=self.run_burn_in_test)
        self.burnin_button.grid(column=4, row=7, padx=10, pady=5)

        # メイン情報表示エリア
        self.info_area = tk.Text(root, height=10, width=100, font=("Helvetica", 14))
        self.info_area.grid(column=0, row=1, columnspan=6, padx=10, pady=10)
        self.info_area.insert(tk.END, "System Information will appear here.\n")
        self.psu_power_label = tk.Label(root, text="PSU Power: N/A", font=("Helvetica", 14))
        self.psu_power_label.grid(column=0, row=2, columnspan=6, pady=10)
        self.cpu_usage_label = tk.Label(root, text="CPU Usage: N/A", font=("Helvetica", 14))
        self.cpu_usage_label.grid(column=0, row=3, columnspan=6, pady=10)
        self.memory_usage_label = tk.Label(root, text="Memory Usage: N/A", font=("Helvetica", 14))
        self.memory_usage_label.grid(column=0, row=4, columnspan=6, pady=10)
        self.gpu_vram_label = tk.Label(root, text="VRAM Usage: N/A", font=("Helvetica", 14))
        self.gpu_vram_label.grid(column=0, row=5, columnspan=6, pady=10)

        self.display_system_info()
        self.start_update_loop()

    def update_status(self, message):
        self.info_area.insert(tk.END, message + "\n")
        self.info_area.see(tk.END)

    # ============== Sound Test (Individual Execution) ==============
    def open_sound_test_window(self):
        threading.Thread(target=self.run_sound_test_once, daemon=True).start()

    def run_sound_test_once(self):
        self.update_status("\nStarting sound test (pre-test + main test)...\n")
        try:
            from sound_test.noisetester import play_and_record_main
        except ImportError:
            self.root.after(0, lambda: messagebox.showerror("Sound Test",
                "Sound test module not found. Please check that 'sound_test/__init__.py' and 'noisetester.py' exist."))
            return
        try:
            result_corr = play_and_record_main()
            self.update_status(f"Sound test completed. Mean correlation: {result_corr:.4f}\n")
            if result_corr < self.sound_threshold:
                self.root.after(0, lambda: messagebox.showerror("Sound Test", f"Sound test failed (corr={result_corr:.4f})"))
            else:
                self.root.after(0, lambda: messagebox.showinfo("Sound Test", f"Sound test succeeded (corr={result_corr:.4f})"))
        except Exception as e:
            self.update_status(f"[ERROR] Sound Test Exception: {e}\n")
            self.root.after(0, lambda: messagebox.showerror("Sound Test", f"Exception: {e}"))

    # ============== Storage Test (Subwindow) ==============
    def open_storage_window(self):
        try:
            from storage_load.storage_test import StorageTestApp
        except ImportError:
            messagebox.showerror("Storage Test", "StorageTestApp module not found.")
            return
        storage_window = tk.Toplevel(self.root)
        storage_window.title("Storage Test")
        storage_window.geometry("600x500")
        StorageTestApp(storage_window)

    # ============== Network Test (Subwindow) ==============
    def open_network_test_window(self):
        try:
            from network_test.nettest import NetworkTestApp
        except ImportError as e:
            messagebox.showerror("Network Test", f"Network test module not found: {e}")
            return
        net_window = tk.Toplevel(self.root)
        net_window.title("Network Test")
        net_window.geometry("400x350")
        app = NetworkTestApp(net_window)

    # ============== Burn‑in Test (with Popup) ==============
    def run_burn_in_test(self):
        try:
            duration = int(self.burnin_duration.get())
        except Exception:
            messagebox.showerror("Input Error", "Invalid burn‑in duration.")
            return
        stress = self.stress_level.get()
        if stress == "Low":
            cpu_val, gpu_val, vram_val = 30, 30, 30
        elif stress == "Mid":
            cpu_val, gpu_val, vram_val = 60, 60, 60
        elif stress == "High":
            cpu_val, gpu_val, vram_val = 80, 80, 80
        else:
            messagebox.showerror("Input Error", "Invalid stress level.")
            return

        self.burn_in_mode = True
        self.cpu_load.set(cpu_val)
        self.gpu_load.set(gpu_val)
        self.gpu_vram_load.set(vram_val)
        self.update_status(f"\nStarting Burn‑in Test for {duration} sec at {stress} level...\n")

        self.stop_event = multiprocessing.Event()
        self.burnin_stop_event.clear()
        global start_event
        start_event.clear()

        # CPU Load Test
        if self.cpu_load.get() > 0:
            if self.cpu_load_type.get() == "x86":
                p = multiprocessing.Process(target=run_cpu_load_wrapper, args=(apply_cpu_load_x86, self.cpu_load.get(), self.stop_event))
                self.cpu_processes.append(p)
                p.start()
            else:
                t = threading.Thread(target=run_cpu_load_wrapper, args=(apply_cpu_load, self.cpu_load.get(), self.stop_event), daemon=True)
                self.cpu_threads.append(t)
                t.start()
        # GPU Load Test
        if self.gpu_load.get() > 0:
            gpu_ids = list(range(torch.cuda.device_count()))
            if self.gpu_load_type.get() == "3D Render":
                t = threading.Thread(target=run_gpu_load_wrapper, args=(apply_combined_load, self.gpu_load.get(), gpu_ids, self.stop_event), daemon=True)
            else:
                t = threading.Thread(target=run_gpu_load_wrapper, args=(apply_gpu_tensor_load, self.gpu_load.get(), gpu_ids, self.stop_event), daemon=True)
            self.gpu_threads.append(t)
            t.start()
        # GPU VRAM Load Test
        if self.gpu_vram_load.get() > 0:
            gpu_ids = list(range(torch.cuda.device_count()))
            t = threading.Thread(target=run_gpu_load_wrapper, args=(apply_gpu_vram_load, self.gpu_vram_load.get(), gpu_ids, self.stop_event), daemon=True)
            self.gpu_threads.append(t)
            t.start()

        # Storage Test
        if StorageTest is not None:
            self.storage_test_instance = StorageTest(gui_callback=self.update_status)
            self.storage_test_instance.detect_usb_devices()
            self.storage_test_thread = threading.Thread(target=run_storage_test_wrapper,
                                                        args=(self.storage_test_instance, self._update_storage_progress, duration, self.stop_event),
                                                        daemon=True)
            self.storage_test_thread.start()
        else:
            self.update_status("[WARN] StorageTest module not found. Skipping storage test.")

        # Network Test: Continuous execution in burn‑in mode
        if run_network_test_wrapper:
            self.network_test_thread = threading.Thread(target=run_network_test_wrapper,
                                                          args=(self.stop_event, self.info_area, 5),
                                                          daemon=True)
            self.network_test_thread.start()
        else:
            self.update_status("[WARN] Network test module not found. Skipping network test.\n")

        # Create a popup window for burn‑in progress (for sound test progress)
        self.burnin_popup, self.burnin_progress = create_burnin_popup(self.root)
        # Sound Test: run in a dedicated thread for burn‑in mode
        self.sound_test_thread = threading.Thread(target=run_sound_test_wrapper,
                                                    args=(self.stop_event, self.burnin_progress, self.sound_threshold, 3, duration),
                                                    daemon=True)
        self.sound_test_thread.start()

        # Start all tests simultaneously
        start_event.set()
        threading.Thread(target=self._burn_in_timer, args=(duration,), daemon=True).start()

    def _update_storage_progress(self, index, percent):
        self.update_status(f"[Storage] Device {index+1} progress: {percent:.1f}%")

    def _burn_in_timer(self, duration):
        time.sleep(duration)
        self.stop_all_tests()
        self.burn_in_mode = False
        self.update_status("\nBurn‑in Test completed.\n")
        self.root.after(0, lambda: messagebox.showinfo("Burn‑in Test", "Burn‑in Test completed."))
        if hasattr(self, 'burnin_popup') and self.burnin_popup.winfo_exists():
            self.burnin_popup.destroy()
        self.root.after(100, self.reset_system_info)

    def reset_system_info(self):
        self.info_area.delete("1.0", tk.END)
        self.info_area.insert(tk.END, "System Information will appear here.\n")
        self.display_system_info()

    # ============== CPU/GPU Test (Individual Execution) ==============
    def apply_load(self):
        if self.burn_in_mode:
            return
        self.stop_event = multiprocessing.Event()
        cpu_load_percentage = self.cpu_load.get()
        gpu_load_percentage = self.gpu_load.get()
        gpu_vram_percentage = self.gpu_vram_load.get()
        cpu_load_type = self.cpu_load_type.get()
        gpu_load_type = self.gpu_load_type.get()

        self.update_status(f"\nCPU Load: {cpu_load_percentage}% ({cpu_load_type})\n")
        self.update_status(f"GPU Load: {gpu_load_percentage}% ({gpu_load_type})\n")
        self.update_status(f"GPU VRAM Load: {gpu_vram_percentage}%\n")

        if cpu_load_percentage > 0:
            if cpu_load_type == "x86":
                p = multiprocessing.Process(target=apply_cpu_load_x86, args=(cpu_load_percentage, self.stop_event))
                self.cpu_processes.append(p)
                p.start()
            else:
                t = threading.Thread(target=apply_cpu_load, args=(cpu_load_percentage, self.stop_event), daemon=True)
                self.cpu_threads.append(t)
                t.start()
        if gpu_load_percentage > 0:
            gpu_ids = list(range(torch.cuda.device_count()))
            if gpu_load_type == "3D Render":
                t = threading.Thread(target=apply_combined_load, args=(gpu_load_percentage, self.stop_event, gpu_ids), daemon=True)
            else:
                t = threading.Thread(target=apply_gpu_tensor_load, args=(gpu_load_percentage, self.stop_event, gpu_ids), daemon=True)
            self.gpu_threads.append(t)
            t.start()
        if gpu_vram_percentage > 0:
            gpu_ids = list(range(torch.cuda.device_count()))
            t = threading.Thread(target=apply_gpu_vram_load, args=(gpu_vram_percentage, self.stop_event, gpu_ids), daemon=True)
            self.gpu_threads.append(t)
            t.start()

    # ============== System Information Display ==============
    def display_system_info(self):
        cpu_info = get_cpu_info()
        gpu_info = get_gpu_info()
        self.update_status("CPU Info:\n" + cpu_info + "\n")
        self.update_status("GPU Info:\n" + gpu_info + "\n")

    def update_system_info(self):
        psu_power = get_psu_power()
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        if torch.cuda.device_count() > 0:
            vram_usage = (torch.cuda.memory_allocated() / torch.cuda.get_device_properties(0).total_memory) * 100
        else:
            vram_usage = 0
        self.psu_power_label.config(text=psu_power)
        self.cpu_usage_label.config(text=f"CPU Usage: {cpu_usage}%")
        self.memory_usage_label.config(text=f"Memory Usage: {memory_usage}%")
        self.gpu_vram_label.config(text=f"VRAM Usage: {vram_usage:.2f}%")
        self.root.after(5000, self.update_system_info)

    def start_update_loop(self):
        self.update_system_info()

    def stop_all_tests(self):
        if self.stop_event:
            self.stop_event.set()
        self.burnin_stop_event.set()
        self.update_status("\nStop signal sent. Waiting for tests to terminate...\n")
        threading.Thread(target=self._join_all_threads, daemon=True).start()

    def _join_all_threads(self):
        for thread in self.cpu_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        for process in self.cpu_processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        for thread in self.gpu_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        if self.storage_test_thread and self.storage_test_thread.is_alive():
            self.storage_test_instance.stop_test()
            self.storage_test_thread.join(timeout=5)
        if self.sound_test_thread and self.sound_test_thread.is_alive():
            self.sound_test_thread.join(timeout=5)
        if self.network_test_thread and self.network_test_thread.is_alive():
            self.network_test_thread.join(timeout=5)
        self.root.after(0, lambda: self.update_status("\nAll tests have been stopped.\n"))

    def exit_app(self):
        self.stop_all_tests()
        self.root.quit()
        self.root.destroy()
        import sys
        sys.exit(0)


if __name__ == "__main__":
    root = tk.Tk()
    app = LoadTestApp(root)
    app.start_update_loop()
    root.mainloop()
