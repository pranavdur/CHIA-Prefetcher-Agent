#!/bin/bash
cd ~/CHIA-Prefetcher-Agent
source venv/bin/activate
export GEMINI_API_KEY="AQ.Ab8RN6JgQ0AVxY8yghA3WUFs0DH10HiZHdTaUcZt9SWlN5DmDw"
python3 chia_agent/agent_loop.py
