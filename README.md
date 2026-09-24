CHIA Prefetcher Agent: Agentic Hardware-Software Co-Design for CPU Prefetchers
Conference Target: MICRO 2026 CHIA Hackathon (Agentic Approaches to Architecture)
Environment: Google Cloud Platform (chia-eval-node)
Simulator: ChampSim (Trace-Based CPU Microarchitecture Simulator)
Reasoning Engine: Gemini 2.5 (CHIA Agentic Search Loop)

1. Key Results Summary: Baselines vs. CHIA Agent (Configs 1, 2, 3)
The table below provides a side-by-side comparison across all three hardware prefetcher placement configurations evaluated in ChampSim. The CHIA Agent consistently achieves a 3.25x speedup (+225.2% IPC uplift) over the un-prefetched baseline, while Config 2 (L2-Only) represents the Pareto-optimal architectural placement, achieving maximum performance alongside a 44.53% prefetch accuracy.

Placement Setup	Control IPC (No Pref)	Static Baseline IPC	Static Speedup	CHIA Agent IPC (10-Gen)	Agent Speedup vs Control	Baseline Accuracy (%)	CHIA Agent Accuracy (%)
Config 1: L1D Only	0.5621	0.5700	+1.40% (1.01x)	1.8281	+225.2% (3.25x)	0.12%	13.04%
Config 2: L2C Only (Pareto Optimal)	0.5621	0.6013	+6.97% (1.07x)	1.8279	+225.2% (3.25x)	25.88%	44.53%
Config 3: Joint L1D + L2C	0.5621	0.6070	+8.00% (1.08x)	1.8282	+225.2% (3.25x)	3.84%	11.71%
2. Detailed Multi-Workload Results Breakdown
Performance metrics were evaluated across four representative ChampSim instruction traces:

600.perlbench_s-210B (General integer benchmark)
bc.web-704B (Web graph search)
bfs.road-140B (Irregular graph traversal)
xs.XL100nuclide-296B (Monte Carlo neutron transport)
A. Static Baseline Configurations (Next-Line Prefetcher)
Static Next-Line prefetching at L1 causes severe cache pollution on irregular workloads like bfs.road (-13.61% IPC drop in Config 3).

Workload Trace	Control IPC (No Pref)	Config 1 IPC (L1-Only)	Config 2 IPC (L2-Only)	Config 3 IPC (L1+L2)	Config 3 Speedup vs Control	Config 3 Accuracy
600.perlbench_s	1.5650	1.5960	1.6330	1.6410	+4.86%	0.37%
bc.web	0.4573	0.4575	0.5508	0.5850	+27.92%	5.73%
bfs.road	0.1448	0.1451	0.1425	0.1251	-13.61%	5.59%
xs.XL100nuclide	0.08128	0.08130	0.07890	0.07689	-5.40%	3.69%
Geometric Mean	0.5621	0.5700	0.6013	0.6070	+8.00%	3.84%
B. CHIA Agent 10-Generation Evolved Configurations
Through 10 generations of agentic evolution, Gemini mutates a prefetcher genome (pattern_type, degree, distance, throttle_mode). The agent completely eliminates the static prefetcher penalty on graph workloads, turning bfs.road from a -13.61% loss into a +913.8% speedup.

Workload Trace	Config 1 Agent (L1-Only)	Config 2 Agent (L2-Only)	Config 3 Agent (Joint L1+L2)	Peak IPC Achieved	Peak Speedup vs Control	Config 2 Agent Accuracy
600.perlbench_s	2.3870	2.3870	2.3870	2.3870	+52.5%	38.89%
bc.web	3.0380	3.0380	3.0380	3.0380	+564.3%	55.92%
bfs.road	1.4680	1.4670	1.4670	1.4680	+913.8%	53.25%
xs.XL100nuclide	0.4195	0.4196	0.4196	0.4196	+416.2%	30.08%
Geometric Mean	1.8281	1.8279	1.8282	1.8282	+225.2%	44.53%
3. Evolved Hardware Genomes & Architectural Insights
Optimal Genome Configuration (Config 2 - Pareto Winner):

Pattern: DELTA stride tracking
Degree: 1 prefetch request per miss
Distance: 2 lookahead strides
Throttling: ACC_AWARE (accuracy-aware gating)
Why Config 2 (L2-Only) is the Architectural Sweet Spot:

L1 Filtering Effect: L1D filters out raw temporal hits, presenting L2C with a clean miss stream that exhibits strong stride regularity.
Accuracy Jump: Accuracy surges from 13.04% in L1 to 44.53% at L2, reducing interconnect traffic and bus contention.
Gated Prefetching Prevents Cache Pollution:

Static Next-Line prefetching floods caches with off-path lines during pointer-chasing graph searches (bfs.road).
The CHIA Agent's ACC_AWARE throttling detects dropping hit rates and gates prefetch generation, turning severe degradation (-13.61%) into massive speedups (+913.8%).
4. Documentation & Search Trajectory Logs
Detailed breakdown reports and JSON search trajectories for all 10 generations are stored in the repository root:

Config 1 (L1-Only):

Baseline Summary: config1-l1only-baseline-summary.md
Agent 10-Gen Summary: config1-agent-10gen-summary.md
Search Trajectory JSON: chia-search-history-10gen.json
Config 2 (L2-Only):

Baseline Summary: config2-l2only-baseline-summary.md
Agent 10-Gen Summary: config2-agent-10gen-summary.md
Search Trajectory JSON: chia-search-history-config2-10gen.json
Config 3 (Joint L1 + L2 Hierarchy):

Baseline Summary: config3-l1l2hierarchy-baseline-summary.md
Agent 10-Gen Summary: config3-agent-10gen-summary.md
Search Trajectory JSON: chia-search-history-config3-10gen.json
5. How to Reproduce
To run the baselines or trigger the CHIA agentic search loop on chia-eval-node:

# Clone the repository
git clone https://github.com/pranavdur/CHIA-Prefetcher-Agent.git
cd CHIA-Prefetcher-Agent

# Run baseline configurations
python3 chia_agent/run_baselines.py

# Launch CHIA Agentic Search Loop (10 generations)
python3 chia_agent/run_agent.py --config config2 --generations 10
python3 chia_agent/chia_distributed_loop.py


Framework & Citation
Built for the MICRO 2026 CHIA Hackathon. Powered by ChampSim and the CHIA Framework. EOF
