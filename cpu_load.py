import subprocess
import os
import multiprocessing
import time

# x86命令を使ったCPU負荷テスト
def apply_cpu_load_x86(load_percentage, stop_event):
    binary_path = os.path.join(os.path.dirname(__file__), "mixed_load")

    if not os.path.isfile(binary_path):
        print("[ERROR] 'mixed_load' binary not found. Make sure it is compiled and in the correct directory.")
        return

    if not os.access(binary_path, os.X_OK):
        os.chmod(binary_path, 0o755)

    def cpu_load_task(stop_event):
        try:
            while not stop_event.is_set():
                process = subprocess.Popen([binary_path, str(load_percentage)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                while not stop_event.is_set() and process.poll() is None:
                    time.sleep(0.1)  # ストップイベントのチェック

                if process.poll() is None:
                    process.terminate()
                    process.wait()
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to execute '{binary_path}'. Error: {e}")

    num_processes = os.cpu_count()
    print(f"[DEBUG] Launching {num_processes} processes to apply x86 load.")
    processes = []

    for _ in range(num_processes):
        process = multiprocessing.Process(target=cpu_load_task, args=(stop_event,))
        processes.append(process)
        process.start()

    stop_event.wait()

    # 全てのプロセスを終了する
    for process in processes:
        if process.is_alive():
            process.terminate()
        process.join()

# 通常のCPU負荷テスト
def apply_cpu_load(load_percentage, stop_event):
    def cpu_intensive_task(stop_event):
        while not stop_event.is_set():
            # 大量の計算を行うことでCPU負荷をかける
            for _ in range(5000):
                _ = [i ** 2 for i in range(1000)]
            if stop_event.is_set():
                break
            time.sleep(0.01)

    num_processes = os.cpu_count()
    print(f"[DEBUG] Launching {num_processes} processes to apply CPU load.")
    processes = []

    for _ in range(num_processes):
        process = multiprocessing.Process(target=cpu_intensive_task, args=(stop_event,))
        processes.append(process)
        process.start()

    stop_event.wait()

    # 全てのプロセスを終了する
    for process in processes:
        if process.is_alive():
            process.terminate()
        process.join()
