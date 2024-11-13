import os
import time
import subprocess
import tkinter as tk
from tkinter import ttk
import threading
import random
import string
import hashlib
from concurrent.futures import ThreadPoolExecutor

# テスト用の小さなテキストファイルを作成（100文字）
def create_test_file(file_path, text="Sample text for USB transfer verification. " * 2):
    with open(file_path, 'w') as f:
        f.write(text[:100])  # 100文字に制限

# ファイルのハッシュを計算（テキストファイル用）
def calculate_hash(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

class StorageTest:
    def __init__(self, gui_callback=None):
        self.stop_event = threading.Event()
        self.gui_callback = gui_callback  # GUIに進行状況を表示するためのコールバック関数
        self.usb_devices = []  # USBデバイスのリストを保持
        self.storage_devices = []  # ストレージデバイスのリスト

    def detect_usb_devices(self):
        # USBデバイスのリストを探す（lsusbコマンドで検出）
        self.usb_devices = []
        self.storage_devices = []
        result = subprocess.run(["lsusb"], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line:
                    self.usb_devices.append(line)
        self.update_gui(f"[INFO] Detected USB devices: {self.usb_devices}")

        # ストレージデバイスのリストを探す（lsblkコマンドで検出）
        try:
            lsblk_output = subprocess.check_output("lsblk -o NAME,MOUNTPOINT,SIZE,TYPE", shell=True).decode('utf-8')
            for line in lsblk_output.splitlines():
                if '/media/' in line and 'part' in line:
                    parts = line.split()
                    mountpoint = parts[1]
                    self.storage_devices.append(mountpoint)
                    self.update_gui(f"[DEBUG] Detected storage device with mountpoint: {mountpoint}")
        except subprocess.CalledProcessError as e:
            self.update_gui(f"[ERROR] Failed to detect storage devices: {e}")

    def run_storage_test(self, progress_callback):
        # ストレージテストを開始する
        self.update_gui("[INFO] Starting storage test...")
        source_file = "/tmp/test_file.txt"
        create_test_file(source_file)
        
        with ThreadPoolExecutor() as executor:
            futures = []
            # ストレージデバイスのテスト
            for idx, mountpoint in enumerate(self.storage_devices):
                futures.append(executor.submit(self.perform_storage_test, idx, mountpoint, source_file, progress_callback))
            # 非ストレージデバイスの応答テスト
            for idx, device_info in enumerate(self.usb_devices):
                is_storage = any(mount in device_info for mount in self.storage_devices)
                if not is_storage:
                    futures.append(executor.submit(self.perform_non_storage_response_test, idx, device_info, progress_callback))

            # 各タスクの完了を待つ
            for future in futures:
                future.result()
        os.remove(source_file)

    def perform_storage_test(self, index, mountpoint, source_file, progress_callback, duration=300):
        # ストレージデバイスに対して読み書きテストを実行
        target_file = os.path.join(mountpoint, "test_copy.txt")
        success_count = 0
        fail_count = 0
        start_time = time.time()

        while time.time() - start_time < duration:
            if self.stop_event.is_set():
                break
            try:
                subprocess.check_call(f"cp {source_file} {target_file}", shell=True)
                if calculate_hash(source_file) == calculate_hash(target_file):
                    success_count += 1
                else:
                    fail_count += 1
                os.remove(target_file)
            except Exception as e:
                fail_count += 1
                self.update_gui(f"[ERROR] Failed to write/read to storage device {index + 1}: {e}")
            progress_callback(index, (time.time() - start_time) / duration * 100)
            time.sleep(1)
        self.update_gui(f"[INFO] Storage test completed on {mountpoint}: {success_count} successes, {fail_count} failures.")

    def perform_non_storage_response_test(self, index, device_info, progress_callback, duration=300):
        # 非ストレージデバイスに対して応答テストを実行
        start_time = time.time()
        success_count = 0
        fail_count = 0

        try:
            # USB規格・スピードを取得
            device_id = device_info.split()[5]  # デバイスID（例: 0930:6544）
            usb_speed_cmd = f"lsusb -v -d {device_id} | grep -i 'bcdUSB\\|bDeviceClass\\|iProduct'"
            usb_speed_info = subprocess.check_output(usb_speed_cmd, shell=True).decode('utf-8')
        except Exception as e:
            usb_speed_info = f"Failed to retrieve info for {device_id}: {e}"

        while time.time() - start_time < duration:
            if self.stop_event.is_set():
                break
            try:
                # 応答テスト（ここでは単純に成功/失敗の確認としてsleepを模擬）
                time.sleep(0.05)  # 50msの遅延を模擬
                success_count += 1
            except Exception as e:
                fail_count += 1
                self.update_gui(f"[ERROR] Non-storage device {index + 1} response test failed: {e}")
            progress_callback(index, (time.time() - start_time) / duration * 100)
            time.sleep(1)
        self.update_gui(f"[INFO] Response test completed for device {index + 1}: {device_info}\nUSB Info:\n{usb_speed_info}")

    def stop_test(self):
        self.stop_event.set()
        self.update_gui("[INFO] Storage test stopped.")

    def update_gui(self, message):
        if self.gui_callback:
            self.gui_callback(message)
        else:
            print(message)

class StorageTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Storage Test")
        self.root.geometry("800x600")

        # ストレージテストのインスタンス作成
        self.storage_test = StorageTest(gui_callback=self.update_status)

        # USBデバイスの詳細を表示する上部領域
        self.device_details_frame = tk.Frame(root)
        self.device_details_frame.pack(padx=10, pady=10)

        # ボタン配置領域を作成し、コントロール要素を整然と配置
        self.controls_frame = tk.Frame(root)
        self.controls_frame.pack(pady=10)

        self.start_button = ttk.Button(self.controls_frame, text="Detect USB Devices", command=self.display_device_status)
        self.start_button.grid(row=0, column=0, padx=10)

        self.test_button = ttk.Button(self.controls_frame, text="Start Storage Test", command=self.start_storage_test)
        self.test_button.grid(row=0, column=1, padx=10)

        self.stop_button = ttk.Button(self.controls_frame, text="Stop Storage Test", command=self.stop_storage_test)
        self.stop_button.grid(row=0, column=2, padx=10)

        # ステータスメッセージ表示エリア
        self.status_area = tk.Text(root, height=10, width=80, font=("Helvetica", 10))
        self.status_area.pack(pady=10)

        self.progress_bars = []

    def update_status(self, message):
        # デバイスステータスの詳細はテキストエリアに表示
        self.status_area.insert(tk.END, message + "\n")
        self.status_area.see(tk.END)

    def display_device_status(self):
        # USBデバイスの検出と表示
        self.storage_test.detect_usb_devices()
        for widget in self.device_details_frame.winfo_children():
            widget.destroy()  # 古いフレーム内のウィジェットを削除

        self.progress_bars = []

        for index, device_info in enumerate(self.storage_test.usb_devices, start=1):
            is_storage = any(mount in device_info for mount in self.storage_test.storage_devices)
            label_text = f"USB Device {index}: {device_info}"
            label_color = "red" if is_storage else "blue"
            label = tk.Label(self.device_details_frame, text=label_text, fg=label_color, font=("Helvetica", 12))
            label.pack(anchor="w")

            # 各デバイスごとに進行状況ゲージを追加
            progress_label = tk.Label(self.device_details_frame, text=f"Progress for USB Device {index}", fg="green", font=("Helvetica", 10))
            progress_label.pack(anchor="w")
            progress_bar = ttk.Progressbar(self.device_details_frame, orient="horizontal", length=300, mode="determinate")
            progress_bar.pack(pady=5)
            progress_bar["value"] = 0  # デフォルト値を設定
            if is_storage:
                style = ttk.Style()
                style_name = f"Red.Horizontal.TProgressbar{index}"
                style.configure(style_name, troughcolor='red', background='red')
                progress_bar.configure(style=style_name)
            self.progress_bars.append(progress_bar)

        # ウィンドウサイズの自動調整
        new_height = 200 + len(self.storage_test.usb_devices) * 70
        self.root.geometry(f"800x{new_height}")

    def start_storage_test(self):
        # ストレージテストをバックグラウンドスレッドで開始する
        threading.Thread(target=self.storage_test.run_storage_test, args=(self.update_progress_bar,), daemon=True).start()

    def stop_storage_test(self):
        # ストレージテストを停止する
        self.storage_test.stop_test()

    def update_progress_bar(self, index, value):
        if index < len(self.progress_bars):
            self.progress_bars[index]["value"] = value

if __name__ == "__main__":
    root = tk.Tk()
    app = StorageTestApp(root)
    root.mainloop()
