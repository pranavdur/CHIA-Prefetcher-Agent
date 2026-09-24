#!/bin/bash
set -e

source ~/CHIA-Prefetcher-Agent/venv/bin/activate
cd ~/CHIA-Prefetcher-Agent

echo "=================================================="
echo "1/3: Running Agentic Loop — Config 1 (L1D-Only)"
echo "=================================================="
sed -i 's/"prefetcher": ".*"/"prefetcher": "no"/g' champsim_config.json
sed -i '/"L1D": {/,/}/s/"prefetcher": "no"/"prefetcher": "custom_pref"/' champsim_config.json
./config.sh champsim_config.json && make -j$(nproc)
python3 chia_agent/chia_distributed_loop.py --output_history chia_search_history_config1_full.json || python3 chia_agent/agent.py

echo "=================================================="
echo "2/3: Running Agentic Loop — Config 2 (L2C-Only)"
echo "=================================================="
sed -i 's/"prefetcher": ".*"/"prefetcher": "no"/g' champsim_config.json
sed -i '/"L2C": {/,/}/s/"prefetcher": "no"/"prefetcher": "custom_pref"/' champsim_config.json
./config.sh champsim_config.json && make -j$(nproc)
python3 chia_agent/chia_distributed_loop.py --output_history chia_search_history_config2_full.json || python3 chia_agent/agent.py

echo "=================================================="
echo "3/3: Running Agentic Loop — Config 3 (Joint L1+L2)"
echo "=================================================="
sed -i 's/"prefetcher": ".*"/"prefetcher": "no"/g' champsim_config.json
sed -i 's/"prefetcher": "no"/"prefetcher": "custom_pref"/g' champsim_config.json
sed -i '/"L1I": {/,/}/s/"prefetcher": "custom_pref"/"prefetcher": "no"/' champsim_config.json
./config.sh champsim_config.json && make -j$(nproc)
python3 chia_agent/chia_distributed_loop.py --output_history chia_search_history_config3_full.json || python3 chia_agent/agent.py

echo "=================================================="
echo "All 3 Agentic Loop Optimization Sweeps Complete!"
echo "=================================================="
