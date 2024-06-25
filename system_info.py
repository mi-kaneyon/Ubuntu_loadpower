import subprocess
import psutil

def get_cpu_info():
    try:
        cpu_info = subprocess.check_output("lscpu", shell=True).decode()
        return cpu_info
    except Exception as e:
        return str(e)

def get_gpu_info():
    try:
        gpu_info = subprocess.check_output("nvidia-smi --format=csv,noheader,nounits --query-gpu=utilization.gpu,utilization.memory,memory.total,memory.free,memory.used,power.draw", shell=True).decode()
        return gpu_info
    except Exception as e:
        return str(e)

def get_system_power():
    try:
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        gpu_info = subprocess.check_output("nvidia-smi --format=csv,noheader,nounits --query-gpu=power.draw", shell=True).decode().strip()
        power_info = f"CPU Usage: {cpu_usage}%\nMemory Usage: {memory_usage}%\nGPU Power Draw: {gpu_info} W"
        return power_info
    except Exception as e:
        return str(e)
