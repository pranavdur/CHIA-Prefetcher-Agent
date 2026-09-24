import os
import json
import sys
import time
from google import genai
from google.genai import types

class GeminiArchitectClient:
    def __init__(self):
        """
        Initializes the Gemini Client.
        Expects your GEMINI_API_KEY environment variable to be set.
        """
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("\n❌ Error: GEMINI_API_KEY environment variable not found.")
            print("Please export it by running: export GEMINI_API_KEY='your_api_key_here'")
            sys.exit(1)

        # Initialize the modern Google GenAI Client
        self.client = genai.Client(api_key=api_key)
        # Using the active 2026 flagship model
        self.model_name = "gemini-3.6-flash"

    def mutate_genome(self, current_genome, parsed_metrics, history_summary=""):
        """
        Sends current hardware statistics to Gemini and requests a mutated genome configuration.
        Includes automatic retry logic with exponential backoff for transient cloud errors (like 503).
        """
        prompt = f"""
You are a highly experienced Hardware Architect specializing in high-performance cache subsystems.
Your goal is to optimize a CPU prefetcher's behavior (its "genome") to maximize Instructions Per Cycle (IPC).

We are currently optimizing a custom ChampSim L2 Cache prefetcher running speculative algorithms.

### 🧬 Current Hardware Genome (Active Config)
{json.dumps(current_genome, indent=2)}

### 📊 Simulation Performance Metrics
{json.dumps(parsed_metrics, indent=2)}

### 📜 Search History and Observations
{history_summary if history_summary else "This is the initial baseline run."}

### Microarchitectural Bottlenecks to Address:
1. Look at 'ipc' (higher is better).
2. Look at L2C prefetch metrics:
   - High useful prefetches with low misses mean high accuracy.
   - High misses with low useful prefetches suggest cache pollution or incorrect patterns.
3. Look at 'l2c_miss_latency' and DRAM row misses. If latency is high, we are saturating the memory bus. We must throttle the prefetcher degree or distance.

### 🧠 Your Task:
Analyze these results and output a MUTATED genome config. You can change:
- 'pattern_type': ("NEXT_LINE", "STRIDE", or "DELTA")
- 'degree': Aggressiveness level (integer 1 to 8)
- 'distance': Prefetch distance (integer 1 to 4)
- 'throttle_mode': Throttling behavior ("NONE", "ACC_AWARE", "BW_AWARE", "HYBRID")

Provide a brief, 2-3 sentence architectural explanation of why you chose this mutation, and then output the new JSON block.

Respond strictly in this JSON format:
{{
  "explanation": "Your brief architect reasoning here.",
  "new_genome": {{
    "pattern_type": "STRIDE",
    "degree": 4,
    "distance": 2,
    "throttle_mode": "ACC_AWARE",
    "pattern_params": 0,
    "throttle_params": 0
  }}
}}
"""

        max_retries = 5
        backoff_factor = 2  # Double the wait time on each failure

        for attempt in range(max_retries):
            try:
                # We enforce Structured JSON Outputs to guarantee our client parses the response cleanly
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2, # Low temperature for more deterministic, focused reasoning
                    ),
                )

                # Parse the structured JSON response
                mutated_data = json.loads(response.text)
                return mutated_data

            except Exception as e:
                # Check if it looks like a transient cloud error (503, 429, etc.)
                if "503" in str(e) or "502" in str(e) or "429" in str(e):
                    sleep_time = backoff_factor ** attempt
                    print(f"⚠️ API busy (Attempt {attempt + 1}/{max_retries}). Retrying in {sleep_time}s... Error: {e}")
                    time.sleep(sleep_time)
                else:
                    # Critical error, do not retry
                    print(f"❌ Critical error communicating with Gemini API: {e}")
                    return None

        print("❌ Exceeded maximum retries due to API unavailability.")
        return None

if __name__ == "__main__":
    print("🤖 Initializing Gemini Architect Client...")
    client = GeminiArchitectClient()
    print("✅ Gemini Architect Client initialized successfully!")

    # Mock data to run a live test of your API connection
    mock_genome = {
        "pattern_type": "STRIDE",
        "degree": 4,
        "distance": 2,
        "throttle_mode": "ACC_AWARE",
        "pattern_params": 0,
        "throttle_params": 0
    }

    mock_metrics = {
        "ipc": 1.26,
        "instructions": 100000,
        "cycles": 79349,
        "l1d_access": 151134,
        "l1d_hit": 149997,
        "l1d_miss": 1137,
        "l2c_access": 1494,
        "l2c_hit": 536,
        "l2c_miss": 958,
        "l2c_pref_requested": 394,
        "l2c_pref_issued": 394,
        "l2c_pref_useful": 84,
        "l2c_pref_useless": 0,
        "l2c_miss_latency": 190.9,
        "dram_row_hit": 4,
        "dram_row_miss": 886,
        "chia_accuracy": 0.213
    }

    print("\n📡 Sending mock stats to Gemini API to test a mutation request...")
    result = client.mutate_genome(mock_genome, mock_metrics)

    if result:
        print("\n🎉 Connection Successful! Received response from Gemini:")
        print(json.dumps(result, indent=2))
    else:
        print("\n❌ Connection Failed.")