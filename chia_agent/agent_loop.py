import os
import json
import subprocess
import sys
import time

# Ensure we can import our parser and client
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from trace_parser import parse_champsim_output
from gemini_client import GeminiArchitectClient

# Configuration Constants
NUM_GENERATIONS = 5  # Start with a 5-generation run to verify the loop works
CHAMPSIM_BIN = "./bin/champsim_custom_loop"
TRACE_PATH = "traces/600.perlbench_s-210B.champsimtrace.xz"
GENOME_FILE = "active_genome.json"
LOG_FILE = "sim_run.log"
HISTORY_FILE = "chia_agent/search_history.json"

def write_genome(genome, filepath):
    """Writes a genome dictionary to active_genome.json for ChampSim to read."""
    with open(filepath, 'w') as f:
        json.dump(genome, f, indent=2)

def load_search_history(filepath):
    """Loads previous search history if it exists, otherwise starts fresh."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_search_history(history, filepath):
    """Saves the search history database to disk."""
    with open(filepath, 'w') as f:
        json.dump(history, f, indent=2)

def generate_history_summary(history):
    """Summarizes past attempts to help Gemini make better decisions."""
    if not history:
        return "This is the initial baseline run."

    summary = "Summary of previous attempts:\n"
    for idx, record in enumerate(history[-5:]):  # Share only the last 5 runs to keep prompt compact
        g = record["genome"]
        m = record["metrics"]
        summary += (
            f"- Run {idx+1}: Pattern={g['pattern_type']}, "
            f"Degree={g['degree']}, Distance={g['distance']}, "
            f"Throttling={g['throttle_mode']} -> "
            f"IPC={m.get('ipc', 'N/A')}, Accuracy={m.get('chia_accuracy', 'N/A')}\n"
        )
    return summary

def main():
    print("🚀 Starting the Agentic Hardware Optimization Loop...")

    # 1. Initialize Gemini Client
    client = GeminiArchitectClient()

    # 2. Setup Baseline Genome (Step 1 baseline settings)
    current_genome = {
        "pattern_type": "STRIDE",
        "degree": 4,
        "distance": 2,
        "throttle_mode": "ACC_AWARE",
        "pattern_params": 0,
        "throttle_params": 0
    }

    # Load past search progress if resuming
    search_history = load_search_history(HISTORY_FILE)
    if search_history:
        print(f"📜 Found {len(search_history)} existing runs in history. Resuming from latest...")
        current_genome = search_history[-1]["genome"]
    else:
        print("🌱 No history found. Launching baseline configuration...")

    # 3. Core Evolution Loop
    for gen in range(1, NUM_GENERATIONS + 1):
        print(f"\n=================== 🧬 Generation {gen} / {NUM_GENERATIONS} ===================")
        print(f"Active Genome Config: {json.dumps(current_genome)}")

        # Write active configuration to the hardware's interface file
        write_genome(current_genome, GENOME_FILE)

        # Run ChampSim Simulation
        print(f"⏳ Running ChampSim simulation on trace: {os.path.basename(TRACE_PATH)}...")
        sim_cmd = [
            CHAMPSIM_BIN,
            "--warmup_instructions", "100000",
            "--simulation_instructions", "1000000",
            TRACE_PATH
        ]

        try:
            # Execute simulation silently and capture output in sim_run.log
            with open(LOG_FILE, 'w') as log_file:
                subprocess.run(sim_cmd, stdout=log_file, stderr=subprocess.PIPE, check=True)
            print("✅ Simulation complete!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error during ChampSim execution: {e.stderr.decode()}")
            sys.exit(1)

        # Parse metrics
        print("📊 Analyzing simulation metrics...")
        parsed_metrics = parse_champsim_output(LOG_FILE)
        if not parsed_metrics or parsed_metrics.get("ipc") is None:
            print("❌ Failure: Could not extract valid metrics from log.")
            sys.exit(1)

        print(f"📈 Performance achieved: IPC = {parsed_metrics['ipc']:.5f} | Accuracy = {parsed_metrics['chia_accuracy']:.5f}")

        # Record run data
        run_record = {
            "generation": gen,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "genome": current_genome,
            "metrics": parsed_metrics
        }
        search_history.append(run_record)
        save_search_history(search_history, HISTORY_FILE)

        if gen == NUM_GENERATIONS:
            print(f"\n🏁 Finished {NUM_GENERATIONS} generations! Evolution session complete.")
            break

        # Generate past context and request next mutation from Gemini 3.6 Flash
        history_summary = generate_history_summary(search_history)
        print("📡 Consulting Gemini Architect for the next optimization mutation...")

        mutation_result = client.mutate_genome(current_genome, parsed_metrics, history_summary)

        if mutation_result and "new_genome" in mutation_result:
            print(f"🧠 Gemini Reasoning: \"{mutation_result['explanation']}\"")
            current_genome = mutation_result["new_genome"]
        else:
            print("⚠️ Gemini failed to provide a valid mutation. Continuing with current config...")

if __name__ == "__main__":
    main()