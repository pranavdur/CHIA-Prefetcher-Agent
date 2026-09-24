CHIA Prefetcher Agent:

An autonomous **agentic architecture loop** that mutates a CPU prefetcher “genome” (set of parameters) designed to optimize prefetcher strategies in **ChampSim** for the **MICRO 2026 CHIA Hackathon (A³: Agentic Approaches to Architecture)**.

This project pairs **Gemini 2.5** as a reasoning engine with **ChampSim** as a hardware evaluation simulator to mutate a dynamic JSON hardware genome across an iterative optimization cycle, learning and applying human-readable microarchitectural skills along the way.

The goal is to discover adaptive prefetching strategies that maximize **Instruction Per Cycle (IPC)** while mitigating cache pollution and memory bandwidth congestion on complex workloads.

The 5-Phase Agent Loop

1. **Genome Formulation**: Encapsulates prefetcher aggressiveness and patterns (`STRIDE`, `DELTA`, `NEXT_LINE`, `degree`, `distance`, `throttle_mode`) inside a dynamic JSON structure.
2. **ChampSim Simulation**: Evaluates active genomes against microarchitectural memory traces (`600.perlbench_s`, GAP, XSBench) to record IPC and prefetch accuracy.
3. **Phase 3 — Skill Distillation**: Analyzes performance deltas across generations to extract actionable, human-readable microarchitectural principles (saved to `skill_bank.json`).
4. **Phase 4 — Skill-Guided Mutation**: Injects learned skills and search history back into Gemini's prompt context to guide future mutations intelligently.
5. **Pareto Optimization**: Maps the trade-off frontier between execution throughput and memory efficiency.

---

## Quick Start

### 1. Environment Setup
```bash
source venv/bin/activate
export GEMINI_API_KEY="your_api_key_here"

2. Run Control Baselines
python3 chia_agent/run_baselines.py

3. Launch CHIA Agent Optimization Sweep
python3 chia_agent/chia_distributed_loop.py


Framework & Citation
Built for the MICRO 2026 CHIA Hackathon. Powered by ChampSim and the CHIA Framework. EOF
