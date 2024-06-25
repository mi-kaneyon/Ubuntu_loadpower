import threading
import time
import torch

def cpu_tensor_calculation(load_percentage, stop_event):
    while not stop_event.is_set():
        a = torch.rand((5000, 5000), device='cpu')  # 計算量を増やす
        b = torch.rand((5000, 5000), device='cpu')  # 計算量を増やす
        c = torch.matmul(a, b)
        time.sleep(1 / load_percentage)

def apply_cpu_load(load_percentage):
    stop_event = threading.Event()
    num_threads = torch.get_num_threads()  # 使用可能なスレッド数を取得
    threads = []
    
    for _ in range(num_threads):
        thread = threading.Thread(target=cpu_tensor_calculation, args=(load_percentage, stop_event), daemon=True)
        threads.append(thread)
        thread.start()
    
    return stop_event
