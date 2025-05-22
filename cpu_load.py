#!/usr/bin/env python3
"""
cpu_load.py  ―  Burn-in／単独負荷用　CPU ストレステスト
  ・multiprocessing.Event で停止シグナルを安全に共有
  ・優先度を下げて OS 応答性を確保
"""

import os
import subprocess
import time
from multiprocessing import Event, Process, cpu_count

# ────────────────────────────────────────────────────────────
# 1) x86 アセンブラ版 (外部バイナリ mixed_load を呼ぶ)
# ────────────────────────────────────────────────────────────
def apply_cpu_load_x86(load_percentage: int, stop_event: Event, modulate: bool = False):
    binary_path = os.path.join(os.path.dirname(__file__), "mixed_load")
    if not (os.path.exists(binary_path) and os.access(binary_path, os.X_OK)):
        print("[ERROR] mixed_load binary not found or not executable"); return

    def worker(evt: Event):
        # 各プロセス：優先度を下げる
        try: os.nice(10)
        except Exception as e: print(f"[WARN] nice() failed: {e}")

        while not evt.is_set():
            proc = subprocess.Popen(
                [binary_path, str(load_percentage)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            # 0.2 秒ごとに停止判定
            interval = 0.2 * (2 if modulate else 1)
            while not evt.is_set() and proc.poll() is None:
                time.sleep(interval)

            # 終了処理
            if proc.poll() is None:
                proc.terminate(); proc.wait()
            time.sleep(0.5 * (2 if modulate else 1))

    _launch_processes(worker, stop_event)


# ────────────────────────────────────────────────────────────
# 2) 純 Python 計算版
# ────────────────────────────────────────────────────────────
def apply_cpu_load(load_percentage: int, stop_event: Event, modulate: bool = False):
    work_ratio = load_percentage / 100.0
    interval   = 0.1                       # 100 ms スライス
    work_time  = interval * work_ratio
    idle_time  = interval - work_time

    def worker(evt: Event):
        try:
            while not evt.is_set():
                t0 = time.perf_counter()
                # busy loop で work_time だけ回す
                while (time.perf_counter() - t0) < work_time and not evt.is_set():
                    pass
                # 残り時間はスリープ
                time.sleep(max(0, idle_time) * (2 if modulate else 1))
        except KeyboardInterrupt:
            pass

    _launch_processes(worker, stop_event)


# ────────────────────────────────────────────────────────────
# 共通：プロセス起動＆停止監視
# ────────────────────────────────────────────────────────────
def _launch_processes(target, stop_event: Event):
    n_proc = cpu_count() or 1
    print(f"[DEBUG] Launching {n_proc} CPU-load processes")
    procs: list[Process] = [Process(target=target, args=(stop_event,)) for _ in range(n_proc)]
    for p in procs: p.start()

    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop_event.set()

    # 終了待ち
    for p in procs:
        if p.is_alive(): p.terminate()
        p.join()


# ────────────────────────────────────────────────────────────
# テスト実行
# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    evt = Event()
    try:
        apply_cpu_load(70, evt)           # 70 % 負荷を手動テスト
    finally:
        evt.set()
        print("Stopped.")
