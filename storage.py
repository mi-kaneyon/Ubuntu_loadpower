import os
import time
import subprocess
from tqdm import tqdm
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

# USBデバイスを検出
def find_usb_devices():
    lsusb_output = subprocess.check_output("lsusb", shell=True).decode('utf-8')
    devices = [line.strip() for line in lsusb_output.splitlines()]

    # lsblkコマンドでストレージデバイスを特定
    lsblk_output = subprocess.check_output("lsblk -o NAME,MOUNTPOINT,SIZE,TYPE", shell=True).decode('utf-8')
    storage_devices = []
    for line in lsblk_output.splitlines():
        if '/media/' in line and 'part' in line:
            parts = line.split()
            mountpoint = parts[1]
            storage_devices.append(mountpoint)
    return devices, storage_devices

# ストレージデバイスの転送テスト
def transfer_test(source_file, target_dir, position, duration=300):  # デフォルト5分
    start_time = time.time()
    success_count = 0
    fail_count = 0
    target_file = os.path.join(target_dir, "test_copy.txt")

    with tqdm(total=duration, desc=f"Storage Test on {target_dir}", unit="s", position=position, leave=False) as pbar:
        while time.time() - start_time < duration:
            try:
                subprocess.check_call(f"cp {source_file} {target_file}", shell=True)
                if calculate_hash(source_file) == calculate_hash(target_file):
                    success_count += 1
                else:
                    fail_count += 1
                os.remove(target_file)
            except Exception as e:
                fail_count += 1
                print(f"Error on {target_dir}: {e}")
            pbar.update(1)
            time.sleep(1)

    print(f"\nSummary for {target_dir}: {success_count} successes, {fail_count} failures")

# 非ストレージデバイスの応答テスト
def non_storage_test(device_info, position, duration=300):  # デフォルト5分
    device_id = device_info.split()[5]  # デバイスID（例: 0930:6544）
    start_time = time.time()
    success_count = 0
    fail_count = 0

    try:
        # USB規格・スピードを取得
        usb_speed_cmd = f"lsusb -v -d {device_id} | grep -i 'bcdUSB\\|bDeviceClass\\|iProduct'"
        usb_speed_info = subprocess.check_output(usb_speed_cmd, shell=True).decode('utf-8')
    except Exception as e:
        usb_speed_info = f"Failed to retrieve info for {device_id}: {e}"

    # 応答性テストの進捗バー
    with tqdm(total=duration, desc=f"Non-Storage Test on {device_id}", unit="s", position=position, leave=False) as pbar:
        while time.time() - start_time < duration:
            try:
                # 応答テスト（ここでは単純に成功/失敗の確認としてsleepを模擬）
                time.sleep(0.05)  # 50msの遅延を模擬
                success_count += 1
            except Exception as e:
                fail_count += 1
                print(f"Error on {device_id}: {e}")
            pbar.update(1)
            time.sleep(1)

    print(f"\nSummary for {device_id}: {success_count} successes, {fail_count} failures\nUSB Info:\n{usb_speed_info}")

# メインプロセス
if __name__ == "__main__":
    source_file = "/tmp/test_file.txt"
    create_test_file(source_file)

    # USBデバイスの検出
    usb_devices, storage_devices = find_usb_devices()

    if not usb_devices:
        print("No USB devices found.")
    else:
        with ThreadPoolExecutor() as executor:
            futures = []
            # ストレージデバイスに対して並行して読み書きテストを実行
            for idx, device in enumerate(storage_devices):
                print(f"Testing storage device mounted at: {device}")
                future = executor.submit(transfer_test, source_file, device, idx)
                futures.append(future)

            # ストレージ以外のデバイスに対して応答テストを実行
            for idx, device_info in enumerate(usb_devices, start=len(storage_devices)):
                is_storage = any(mount in device_info for mount in storage_devices)
                if not is_storage:
                    print(f"Testing non-storage device: {device_info}")
                    future = executor.submit(non_storage_test, device_info, idx)
                    futures.append(future)

            for future in futures:
                future.result()  # 各タスクの完了を待つ

    os.remove(source_file)
