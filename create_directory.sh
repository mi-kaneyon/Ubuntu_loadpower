#!/bin/bash

# Create main directory
mkdir -p lin_bench

# Create subdirectories
mkdir -p lin_bench/cpu_load
mkdir -p lin_bench/gpu_load
mkdir -p lin_bench/system_info

echo "Directory structure has been created. Please manually place the respective script files in the appropriate directories:"
echo "1. Place main.py in the lin_bench directory."
echo "2. Place cpu_load.py in the lin_bench/cpu_load directory."
echo "3. Place gpu_load.py in the lin_bench/gpu_load directory."
echo "4. Place system_info.py in the lin_bench/system_info directory."
