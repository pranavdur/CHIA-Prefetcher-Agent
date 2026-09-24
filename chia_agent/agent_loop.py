import os
import sys
import json
import subprocess

# Ensure imports work from current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from trace_parser import parse_champsim_output
from gemini_client import GeminiArchitectClient

# Configuration Constants
NUM_GENERATIONS = 10
CHAMPSIM_BIN = "./bin/champsim_custom_loop"
TRACES = [
    "traces/600.perlbench_s-210B.champsimtrace.xz",
    "traces/bc.web-704B.champsimtrace.xz",
    "traces/bfs.road-140B.champsimtrace.xz",
    "traces/xs.XL100nuclide-296B.champsimtrace.xz"
]
GENOME_FILE = "active_genome.json"
LOG_FILE = "sim_run.log"
HISTORY_FILE = "chia_agent/search_history.json"

def read_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return default
    return default

def write_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def main():
    print(" Starting the Agentic Hardware Optimization Loop (Multi-Trace)...")
    client = GeminiArchitectClient()
    
    history = read_json(HISTORY_FILE, [])
    print(f" Found {len(history)} existing runs in history.")
    
    current_genome = read_json(GENOME_FILE, {
        "pattern_type": "DELTA",
        "degree": 4,
        "distance": 3,
        "throttle_mode": "ACC_AWARE",
        "pattern_params": 0,
        "throttle_params": 0
    })

    for gen in range(1, NUM_GENERATIONS + 1):
        print(f"\n===================  Generation {gen} / {NUM_GENERATIONS} ===================")
        print(f"Active Genome Config: {json.dumps(current_genome)}")
        
        write_json(GENOME_FILE, current_genome)
        
        trace_results = {}
        total_ipc = 0.0
        total_acc = 0.0
        valid_count = 0

        for trace_path in TRACES:
            trace_name = os.path.basename(trace_path)
            print(f"⏳ Running ChampSim simulation on trace: {trace_name}...")
            
            sim_cmd = [
                CHAMPSIM_BIN,
                "--warmup_instructions", "100000",
                "--simulation_instructions", "1000000",
                trace_path
            ]
            
            try:
                with open(LOG_FILE, "w") as log_f:
                    subprocess.run(sim_cmd, stdout=log_f, stderr=subprocess.STDOUT, check=True)
                
                parsed = parse_champsim_output(LOG_FILE)
                
                if isinstance(parsed, dict):
                    ipc = float(parsed.get("ipc") or 0.0)
                    accuracy = parsed.get("chia_accuracy")
                    if accuracy is None:
                        useful = parsed.get("l2c_pref_useful") or 0
                        issued = parsed.get("l2c_pref_issued") or 0
                        accuracy = (useful / issued * 100.0) if issued > 0 else 0.0
                    else:
                        accuracy = float(accuracy)
                elif isinstance(parsed, (tuple, list)):
                    ipc, accuracy = float(parsed[0]), float(parsed[1])
                else:
                    ipc, accuracy = 0.0, 0.0

                trace_results[trace_name] = {"ipc": ipc, "accuracy": accuracy}
                total_ipc += ipc
                total_acc += accuracy
                valid_count += 1
                print(f"    {trace_name}: IPC = {ipc:.4f}, Accuracy = {accuracy:.2f}%")
            except Exception as e:
                print(f"    Failed on {trace_name}: {e}")
                trace_results[trace_name] = {"ipc": 0.0, "accuracy": 0.0}

        avg_ipc = total_ipc / valid_count if valid_count > 0 else 0.0
        avg_acc = total_acc / valid_count if valid_count > 0 else 0.0
        print(f"\n Generation {gen} Aggregate -> Mean IPC: {avg_ipc:.4f}, Mean Accuracy: {avg_acc:.2f}%")

        run_record = {
            "generation": gen,
            "genome": current_genome,
            "avg_ipc": avg_ipc,
            "avg_accuracy": avg_acc,
            "trace_results": trace_results
        }
        history.append(run_record)
        write_json(HISTORY_FILE, history)

        if gen < NUM_GENERATIONS:
            print(" Querying Gemini Architect for mutated genome...")
            try:
                mutated = client.mutate_genome(current_genome, run_record, json.dumps(history))
                if isinstance(mutated, dict) and mutated:
                    current_genome = mutated
                    print(f"    Mutated Genome Received: {json.dumps(current_genome)}")
                else:
                    print("   ️ Received invalid genome, keeping current genome.")
            except Exception as e:
                print(f"    Mutation query failed: {e}")

if __name__ == "__main__":
    main()
