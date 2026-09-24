import os
import glob
import json
import subprocess
import re
from concurrent.futures import ProcessPoolExecutor, as_completed

TRACES_DIR = "/home/durbhapranav/CHIA-Prefetcher-Agent/traces"

SELECTED_TRACES = [
    "600.perlbench_s-210B.champsimtrace.xz",
    "bfs.road-140B.champsimtrace.xz",
    "bc.web-704B.champsimtrace.xz",
    "xs.XL100nuclide-296B.champsimtrace.xz",
]

ALL_TRACES = sorted(glob.glob(os.path.join(TRACES_DIR, "*.champsimtrace.xz")))
TRACE_FILES = ALL_TRACES

if not TRACE_FILES:
    TRACE_FILES = ALL_TRACES

NUM_WORKERS = min(os.cpu_count() or 4, len(TRACE_FILES))

print(f" Running fast sweep on {len(TRACE_FILES)} trace(s): {[os.path.basename(t) for t in TRACE_FILES]}")
print(f" Parallel workers: {NUM_WORKERS}\n")

BASELINES = {
    "No Prefetcher": {
        "pattern_type": "NO_PREFETCH",
        "degree": 0,
        "distance": 0,
        "throttle_mode": "off",
        "pattern_params": 0
    },
    "Standard Next-Line": {
        "pattern_type": "NEXT_LINE",
        "degree": 1,
        "distance": 1,
        "throttle_mode": "off",
        "pattern_params": 0
    },
    "Basic Stride": {
        "pattern_type": "STRIDE",
        "degree": 2,
        "distance": 4,
        "throttle_mode": "off",
        "pattern_params": 0
    }
}

def parse_stats(log_file):
    """Extracts IPC and Prefetch Accuracy from ChampSim output log."""
    ipc = 0.0
    accuracy = 0.0
    
    if not os.path.exists(log_file):
        return ipc, accuracy
        
    with open(log_file, "r") as f:
        text = f.read()
        
        ipc_match = re.search(r"CPU 0 cumulative IPC:\s+([\d\.]+)", text)
        if ipc_match:
            ipc = float(ipc_match.group(1))
            
        acc_match = re.search(r"\\[CHIA Stats\\] Prefetcher Accuracy:\s+([\d\.eE\+\-]+)", text)

        if acc_match:
            accuracy = float(acc_match.group(1)) * 100.0
        else:
            matches = re.findall(r"PREFETCH REQUESTED:\s+\d+\s+ISSUED:\s+(\d+)\s+USEFUL:\s+(\d+)", text)
            tot_issued = sum(int(m[0]) for m in matches)
            tot_useful = sum(int(m[1]) for m in matches)
            if tot_issued > 0:
                accuracy = (tot_useful / tot_issued) * 100.0

    return ipc, accuracy

def run_simulation(args):
    """Worker task: runs ChampSim on a single trace file."""
    b_name, trace_path = args
    trace_name = os.path.basename(trace_path)
    log_file = f"sim_baseline_{b_name.replace(' ', '_')}_{trace_name}.log"
    
    cmd = f"./bin/champsim --warmup_instructions 200000 --simulation_instructions 1000000 {trace_path} > {log_file} 2>&1"
    subprocess.run(cmd, shell=True)
    
    ipc, accuracy = parse_stats(log_file)
    return trace_name, ipc, accuracy

results = {name: {} for name in BASELINES}

for b_name, genome in BASELINES.items():
    print("=" * 65)
    print(f"️  Running Baseline Policy: {b_name}")
    print("=" * 65)
    
    with open("active_genome.json", "w") as f:
        json.dump(genome, f, indent=4)
        
    tasks = [(b_name, trace_path) for trace_path in TRACE_FILES]
    
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(run_simulation, task): task for task in tasks}
        
        for future in as_completed(futures):
            trace_name, ipc, accuracy = future.result()
            results[b_name][trace_name] = {"ipc": ipc, "accuracy": accuracy}
            print(f"  [Finished] {trace_name:<35} | IPC: {ipc:.4f} | Accuracy: {accuracy:.2f}%")

print("\n" + "="*70)
print(" MULTI-TRACE BASELINE SWEEP SUMMARY")
print("="*70)

for trace_path in TRACE_FILES:
    t_name = os.path.basename(trace_path)
    print(f"\n Trace: {t_name}")
    print(f"{'Policy':<22} | {'IPC':<10} | {'Prefetch Accuracy':<18}")
    print("-" * 55)
    for b_name in BASELINES:
        stats = results[b_name].get(t_name, {"ipc": 0.0, "accuracy": 0.0})
        print(f"{b_name:<22} | {stats['ipc']:<10.4f} | {stats['accuracy']:<18.2f}%")

print("\n" + "="*70)
print(" AGGREGATE SUMMARY ACROSS ALL TRACES")
print("="*70)
print(f"{'Policy':<22} | {'Mean IPC':<10} | {'Mean Accuracy':<18} | {'IPC Uplift vs No-Pref'}")
print("-" * 75)

no_pref_mean_ipc = sum(results["No Prefetcher"][t]["ipc"] for t in results["No Prefetcher"]) / len(TRACE_FILES) if TRACE_FILES else 0.0

for b_name in BASELINES:
    mean_ipc = sum(results[b_name][t]["ipc"] for t in results[b_name]) / len(TRACE_FILES) if TRACE_FILES else 0.0
    mean_acc = sum(results[b_name][t]["accuracy"] for t in results[b_name]) / len(TRACE_FILES) if TRACE_FILES else 0.0
    uplift = ((mean_ipc - no_pref_mean_ipc) / no_pref_mean_ipc) * 100.0 if no_pref_mean_ipc > 0 else 0.0
    print(f"{b_name:<22} | {mean_ipc:<10.4f} | {mean_acc:<17.2f}% | {uplift:+.2f}%")
print("="*75)

# =================================================================
#  EXPORT RESULTS TO JSON
# =================================================================
import json

output_filename = "results_config3_L1L2Hierarchy.json"
with open(output_filename, "w") as f:
    json.dump(results, f, indent=4)

print(f"\n Summary results successfully exported to {output_filename}")
