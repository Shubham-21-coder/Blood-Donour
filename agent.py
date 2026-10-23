"""
LifeLink: Primary Agent Entrypoint (agent.py)
Preserves uagents, Agent Chat Protocol (ACP), Agentverse compatibility, and ASI:One LLM integration.
"""

import os
import sys

# Ensure lifelink directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.coordinator import coordinator_agent, chat_protocol, llm_client, process_user_turn

# Expose 'agent' variable for standard Agentverse & uAgents conventions
agent = coordinator_agent

if __name__ == "__main__":
    print(f"Starting LifeLink Agent: {agent.name} ({agent.address})")
    print(f"ASI:One LLM configured: {llm_client.is_configured} (Model: {llm_client.model})")
    agent.run()
