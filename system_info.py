import subprocess

def get_cpu_info():
    try:
        cpu_info = subprocess.check_output("lscpu", shell=True).decode()
        return cpu_info
    except Exception as e:
        return str(e)

def get_gpu_info():
    try:
        gpu_info = subprocess.check_output("nvidia-smi --format=csv,noheader,nounits --query-gpu=utilization.gpu,utilization.memory,memory.total,memory.free,memory.used", shell=True).decode()
        return gpu_info
    except Exception as e:
        return str(e)

def get_psu_power():
    try:
        # nvidia-smiを使用してGPUの消費電力を取得（他のツールが必要な場合は適宜修正）
        power_info = subprocess.check_output("nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits", shell=True).decode().strip()
        return f"GPU Power Draw: {power_info} W"
    except Exception as e:
        return str(e)
