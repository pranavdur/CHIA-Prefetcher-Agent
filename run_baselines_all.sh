#!/bin/bash
set -e

source ~/CHIA-Prefetcher-Agent/venv/bin/activate
cd ~/CHIA-Prefetcher-Agent

echo "=================================================="
echo "1/3: Running Config 1 Baseline (L1D-Only)"
echo "=================================================="
sed -i 's/"prefetcher": ".*"/"prefetcher": "no"/g' champsim_config.json
sed -i '/"L1D": {/,/}/s/"prefetcher": "no"/"prefetcher": "next_line"/' champsim_config.json
sed -i 's/results_.*\.json/results_config1_L1Only.json/g' chia_agent/run_baselines.py
./config.sh champsim_config.json && make -j$(nproc)
python3 chia_agent/run_baselines.py

echo "=================================================="
echo "2/3: Running Config 2 Baseline (L2C-Only)"
echo "=================================================="
sed -i 's/"prefetcher": ".*"/"prefetcher": "no"/g' champsim_config.json
sed -i '/"L2C": {/,/}/s/"prefetcher": "no"/"prefetcher": "next_line"/' champsim_config.json
sed -i 's/results_.*\.json/results_config2_L2Only.json/g' chia_agent/run_baselines.py
./config.sh champsim_config.json && make -j$(nproc)
python3 chia_agent/run_baselines.py

echo "=================================================="
echo "3/3: Running Config 3 Baseline (Joint L1+L2)"
echo "=================================================="
sed -i 's/"prefetcher": ".*"/"prefetcher": "no"/g' champsim_config.json
sed -i 's/"prefetcher": "no"/"prefetcher": "next_line"/g' champsim_config.json
sed -i '/"L1I": {/,/}/s/"prefetcher": "next_line"/"prefetcher": "no"/' champsim_config.json
sed -i 's/results_.*\.json/results_config3_L1L2Hierarchy.json/g' chia_agent/run_baselines.py
./config.sh champsim_config.json && make -j$(nproc)
python3 chia_agent/run_baselines.py

echo "=================================================="
echo "All 3 Baseline Sweeps Completed Successfully!"
echo "=================================================="
