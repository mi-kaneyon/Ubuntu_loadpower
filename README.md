# Ubuntu_loadpower

## Overview
Ubuntu_loadpower is a tool designed to stress test the system's CPU and GPU on Ubuntu. It provides a graphical interface to apply different levels of load to the CPU and GPU, allowing users to monitor the system's power consumption and performance under stress.

## Features
- CPU load test using matrix multiplication for maximum stress.
- GPU load test with options for 3D rendering and machine learning model training.
- Real-time system information display, including CPU and GPU usage and power consumption.
- Easy-to-use graphical interface with load control sliders.

## System Components
- **main.py**: Main GUI application script.
- **cpu_load/cpu_load.py**: Script for applying load to the CPU.
- **gpu_load/gpu_load.py**: Script for applying load to the GPU.
- **system_info/system_info.py**: Script for retrieving system information.

## Directory Structure

```

Ubuntu_loadpower/
├── cpu_load/
│ └── cpu_load.py
├── gpu_load/
│ └── gpu_load.py
├── system_info/
│ └── system_info.py
├── main.py
├── create_directories.sh
├── lin_beninstall.sh
└── requirements.txt

```

## Setup and Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/Manyan3/Ubuntu_loadpower.git
   cd Ubuntu_loadpower
  ```
2. Install the required Python packages:

```sh
pip install -r requirements.txt
```
3. Create the directory structure:
 
```sh
chmod +x create_directories.sh 
./create_directories.sh
```

4. Place the respective script files in the appropriate directories:

    - Place main.py in the Ubuntu_loadpower directory.
    - Place cpu_load.py in the Ubuntu_loadpower/cpu_load directory.
    - Place gpu_load.py in the Ubuntu_loadpower/gpu_load directory.
    - Place system_info.py in the Ubuntu_loadpower/system_info directory. 


```
python main.py
```








