import os
import json
import re
from google import genai
from google.genai import types

client = genai.Client()

def parse_champsim_output(log_file):
    """Extracts IPC and Prefetch Accuracy from ChampSim log."""
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

def distill_skill(history, skill_bank, current_gen):
    """Phase 3: Discover Skills from metric deltas and history."""
    prompt = f"""
You are an expert computer architect analyzing CPU prefetcher experiment results in ChampSim.
Current Skill Bank: {json.dumps(skill_bank, indent=2)}
Recent Execution History: {json.dumps(history[-3:], indent=2)}

Analyze the performance deltas in recent generations. 
Distill 1 concise, human-readable microarchitectural "skill" or principle learned from these results 
(e.g., "Throttling degree to 1 preserves prefetch accuracy on pointer-heavy workloads").

Return ONLY a valid JSON object matching this schema:
{{
    "skill_title": "Short descriptive title of the principle",
    "rule": "Actionable architectural rule discovered from the metrics"
}}
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text)

def ask_gemini_mutation(current_genome, history, best_genome, skill_bank, current_gen, total_gens):
    """Phase 4: Apply Skills to guide genome mutation."""
    prompt = f"""
You are an expert computer architect optimizing a CPU prefetcher for ChampSim in CHIA.
We are on Generation {current_gen} of {total_gens}.

Learned Skill Bank (Architectural Principles): {json.dumps(skill_bank, indent=2)}
Best Genome So Far: {json.dumps(best_genome, indent=2)}
Execution History: {json.dumps(history, indent=2)}

Use your learned skills from the Skill Bank and search history to propose the next mutated genome.
Do NOT repeat ineffective configurations.
First, explain your reasoning in 'reasoning'.

Return ONLY a valid JSON object matching this schema:
{{
    "reasoning": "How learned skills from the Skill Bank guided this mutation...",
    "pattern_type": "STRIDE" | "DELTA" | "NEXT_LINE",
    "degree": integer (1-4),
    "distance": integer (1-4),
    "throttle_mode": "ACC_AWARE" | "BW_AWARE" | "HYBRID",
    "pattern_params": 0,
    "throttle_params": 0
}}
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text)

if __name__ == "__main__":
    TOTAL_GENERATIONS = 10
    trace_path = "traces/600.perlbench_s-210B.champsimtrace.xz"
    
    print(f"🌐 Starting CHIA Loop with Phase 3/4 Skill Distillation ({TOTAL_GENERATIONS} Gens)...")

    active_genome = {
        "pattern_type": "DELTA",
        "degree": 2,
        "distance": 1,
        "throttle_mode": "ACC_AWARE",
        "pattern_params": 0,
        "throttle_params": 0
    }

    best_genome = dict(active_genome)
    best_accuracy = 0.0
    best_ipc = 0.0
    history = []
    skill_bank = []

    for gen in range(1, TOTAL_GENERATIONS + 1):
        print(f"\n==========================================")
        print(f"🧬 Generation {gen}/{TOTAL_GENERATIONS}")
        print(f"Active Genome: {json.dumps(active_genome)}")
        print(f"==========================================")

        with open("active_genome.json", "w") as f:
            json.dump(active_genome, f, indent=2)

        log_file = f"sim_gen_{gen}.log"
        print("⚙️ Running ChampSim simulation...")
        os.system(
            f"./bin/champsim_custom_loop "
            f"--warmup_instructions 1000000 "
            f"--simulation_instructions 5000000 "
            f"{trace_path} > {log_file} 2>&1"
        )

        metrics = parse_champsim_output(log_file)
        print(f"📊 Results -> IPC: {metrics['ipc']:.4f} | Accuracy: {metrics['chia_accuracy']:.2f}%")

        history.append({
            "generation": gen, 
            "genome": active_genome, 
            "metrics": metrics
        })

        if metrics["chia_accuracy"] > best_accuracy:
            best_accuracy = metrics["chia_accuracy"]
            best_ipc = metrics["ipc"]
            best_genome = dict(active_genome)
            print(f"⭐ NEW PEAK ACCURACY: {best_accuracy:.2f}% (IPC: {best_ipc:.4f})")
            
            with open("best_genome.json", "w") as f:
                json.dump({"accuracy": best_accuracy, "ipc": best_ipc, "genome": best_genome}, f, indent=2)

        # Phase 3: Distill new architectural skill after generation 1
        print("💡 Phase 3: Distilling architectural skill from performance delta...")
        try:
            new_skill = distill_skill(history, skill_bank, gen)
            skill_bank.append(new_skill)
            print(f"   🎓 New Skill Distilled: [{new_skill.get('skill_title')}] -> {new_skill.get('rule')}")
            
            with open("skill_bank.json", "w") as f:
                json.dump(skill_bank, f, indent=2)
        except Exception as e:
            print(f"   ⚠️ Skill distillation skipped ({e}).")

        # Phase 4: Propose next mutation using Skill Bank
        if gen < TOTAL_GENERATIONS:
            print("🤖 Phase 4: Querying Gemini for skill-guided mutation...")
            try:
                response_data = ask_gemini_mutation(active_genome, history, best_genome, skill_bank, gen, TOTAL_GENERATIONS)
                reasoning = response_data.pop("reasoning", "No reasoning provided.")
                print(f"   🧠 Reasoning: {reasoning}")
                
                history[-1]["gemini_reasoning"] = reasoning
                active_genome = response_data
            except Exception as e:
                print(f"   ⚠️ Mutation query failed ({e}). Reverting to best known genome.")
                active_genome = dict(best_genome)

        with open("history_log.json", "w") as f:
            json.dump(history, f, indent=2)

    print("\n" + "="*50)
    print(f"🎉 Step 6 Training Run Complete!")
    print(f"🏆 Best Accuracy: {best_accuracy:.2f}% (IPC: {best_ipc:.4f})")
    print(f"📚 Total Distilled Architectural Skills: {len(skill_bank)}")
    print("Winning Genome Architecture:")
    print(json.dumps(best_genome, indent=2))
    print("="*50)
