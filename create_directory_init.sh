#!/bin/bash
# setup.sh
# This script creates the required subdirectories and __init__.py files
# for the GitHub repository after cloning.

# List of subdirectories to create
dirs=(
  "lin_bench/cpu_load"
  "lin_bench/gpu_load"
  "lin_bench/old_version"
  "lin_bench/sound_test"
  "lin_bench/storage_load"
  "lin_bench/system_info"
)

echo "Creating required directories..."

for dir in "${dirs[@]}"; do
  mkdir -p "$dir"
  echo "Directory created or already exists: $dir"
  init_file="$dir/__init__.py"
  if [ ! -f "$init_file" ]; then
    echo "# This file makes this directory a Python package." > "$init_file"
    echo "__init__.py created in $dir"
  else
    echo "__init__.py already exists in $dir"
  fi
done

echo "All subdirectories and __init__.py files have been set up."
