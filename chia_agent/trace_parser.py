import re
import sys
import json

def parse_champsim_output(log_filepath):
    """
    Parses a ChampSim simulation output file and extracts key performance metrics
    such as IPC, L1D/L2C cache hit/miss rates, prefetch stats, and custom CHIA metrics.
    """
    metrics = {
        "ipc": None,
        "instructions": None,
        "cycles": None,
        "l1d_access": None,
        "l1d_hit": None,
        "l1d_miss": None,
        "l2c_access": None,
        "l2c_hit": None,
        "l2c_miss": None,
        "l2c_pref_requested": None,
        "l2c_pref_issued": None,
        "l2c_pref_useful": None,
        "l2c_pref_useless": None,
        "l2c_miss_latency": None,
        "dram_row_hit": None,
        "dram_row_miss": None,
        "chia_accuracy": None
    }

    try:
        with open(log_filepath, 'r') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: Log file not found at {log_filepath}")
        return None

    # 1. Parse IPC, Instructions, Cycles
    ipc_match = re.search(r"cumulative IPC:\s+([0-9.]+)", content)
    if ipc_match:
        metrics["ipc"] = float(ipc_match.group(1))

    instr_cycle_match = re.search(r"CPU 0 instructions:\s+(\d+)\s+cycles:\s+(\d+)", content)
    if instr_cycle_match:
        metrics["instructions"] = int(instr_cycle_match.group(1))
        metrics["cycles"] = int(instr_cycle_match.group(2))
        if not metrics["ipc"] and metrics["cycles"] > 0:
            metrics["ipc"] = float(metrics["instructions"]) / metrics["cycles"]

    # 2. Parse Cache Stats
    l1d_match = re.search(r"cpu0->cpu0_L1D LOAD\s+ACCESS:\s+(\d+)\s+HIT:\s+(\d+)\s+MISS:\s+(\d+)", content)
    if l1d_match:
        metrics["l1d_access"] = int(l1d_match.group(1))
        metrics["l1d_hit"] = int(l1d_match.group(2))
        metrics["l1d_miss"] = int(l1d_match.group(3))

    l2c_match = re.search(r"cpu0->cpu0_L2C TOTAL\s+ACCESS:\s+(\d+)\s+HIT:\s+(\d+)\s+MISS:\s+(\d+)", content)
    if l2c_match:
        metrics["l2c_access"] = int(l2c_match.group(1))
        metrics["l2c_hit"] = int(l2c_match.group(2))
        metrics["l2c_miss"] = int(l2c_match.group(3))

    # 3. Parse Prefetch Metrics
    pref_match = re.search(r"cpu0->cpu0_L2C PREFETCH REQUESTED:\s+(\d+)\s+ISSUED:\s+(\d+)\s+USEFUL:\s+(\d+)\s+USELESS:\s+(\d+)", content)
    if pref_match:
        metrics["l2c_pref_requested"] = int(pref_match.group(1))
        metrics["l2c_pref_issued"] = int(pref_match.group(2))
        metrics["l2c_pref_useful"] = int(pref_match.group(3))
        metrics["l2c_pref_useless"] = int(pref_match.group(4))

    # Average Miss Latency
    latency_match = re.search(r"cpu0->cpu0_L2C AVERAGE MISS LATENCY:\s+([0-9.]+)\s+cycles", content)
    if latency_match:
        metrics["l2c_miss_latency"] = float(latency_match.group(1))

    # 4. Parse DRAM row buffer stats
    row_hit_match = re.search(r"Channel 0 RQ ROW_BUFFER_HIT:\s+(\d+)", content)
    if row_hit_match:
        metrics["dram_row_hit"] = int(row_hit_match.group(1))

    row_miss_match = re.search(r"ROW_BUFFER_MISS:\s+(\d+)", content)
    if row_miss_match:
        metrics["dram_row_miss"] = int(row_miss_match.group(1))

    # 5. Parse Custom CHIA Stats (Highly robust bracket-free pattern)
    chia_match = re.search(r"Prefetcher Accuracy:\s+([0-9.]+)", content)
    if chia_match:
        metrics["chia_accuracy"] = float(chia_match.group(1))

    return metrics

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 trace_parser.py <path_to_champsim_log>")
        sys.exit(1)

    results = parse_champsim_output(sys.argv[1])
    if results:
        print(json.dumps(results, indent=2))