import os
import json
import re

def parse_champsim_output(log_file):
    metrics = {"ipc": 0.0, "chia_accuracy": 0.0}
    if not os.path.exists(log_file):
        return metrics

    with open(log_file, "r") as f:
        content = f.read()

    ipc_match = re.search(r"CPU 0 cumulative IPC:\s+([\d\.]+)", content)
    if ipc_match:
        metrics["ipc"] = float(ipc_match.group(1))

    acc_match = re.search(r"Prefetcher Accuracy:\s+([\d\.]+)", content)
    if acc_match:
        val = float(acc_match.group(1))
        metrics["chia_accuracy"] = val * 100.0 if val <= 1.0 else val

    return metrics

baselines = {
    "No Prefetcher": {
        "pattern_type": "NEXT_LINE", "degree": 0, "distance": 0, 
        "throttle_mode": "NONE", "pattern_params": 0, "throttle_params": 0
    },
    "Standard Next-Line": {
        "pattern_type": "NEXT_LINE", "degree": 1, "distance": 1, 
        "throttle_mode": "NONE", "pattern_params": 0, "throttle_params": 0
    },
    "Basic Stride": {
        "pattern_type": "STRIDE", "degree": 1, "distance": 1, 
        "throttle_mode": "NONE", "pattern_params": 0, "throttle_params": 0
    }
}

trace_path = "traces/600.perlbench_s-210B.champsimtrace.xz"

print("🔍 Running Baseline Prefetcher Comparisons...\n")
results = {}

for name, genome in baselines.items():
    with open("active_genome.json", "w") as f:
        json.dump(genome, f, indent=2)

    log_file = f"sim_baseline_{name.replace(' ', '_')}.log"
    print(f"⚙️ Running {name}...")
    os.system(
        f"./bin/champsim_custom_loop "
        f"--warmup_instructions 1000000 "
        f"--simulation_instructions 5000000 "
        f"{trace_path} > {log_file} 2>&1"
    )

    metrics = parse_champsim_output(log_file)
    results[name] = metrics
    print(f"   -> IPC: {metrics['ipc']:.4f} | Accuracy: {metrics['chia_accuracy']:.2f}%\n")

print("="*50)
print("📊 BASELINE COMPARISON SUMMARY")
print("="*50)
for name, m in results.items():
    print(f"{name:<20} | IPC: {m['ipc']:.4f} | Accuracy: {m['chia_accuracy']:.2f}%")
print("="*50)
