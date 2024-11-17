#!/bin/bash

# Create main directory
mkdir -p lin_bench

# Create subdirectories
mkdir -p lin_bench/cpu_load
mkdir -p lin_bench/gpu_load
mkdir -p lin_bench/system_info
mkdir -p lin_bench/storage_load

# Move files to respective directories
mv main.py lin_bench/
mv cpu_load.py lin_bench/cpu_load/
mv gpu_load.py lin_bench/gpu_load/
mv system_info.py lin_bench/system_info/
mv storage_test.py lin_bench/storage_load/

# Output status
echo "Directory structure has been created and files have been moved to their respective directories:"
echo "1. main.py has been moved to lin_bench directory."
echo "2. cpu_load.py has been moved to lin_bench/cpu_load directory."
echo "3. gpu_load.py has been moved to lin_bench/gpu_load directory."
echo "4. system_info.py has been moved to lin_bench/system_info directory."
echo "5. storage_test.py has been moved to lin_bench/storage_load directory."
