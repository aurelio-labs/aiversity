import yaml
from ARCANE.arcane_system import ArcaneSystem
from llm.LLM import LLM
import logging
import os

class AgentFactory:
    @staticmethod
    def create_agent(agent_config: dict, llm: LLM, logger: logging.Logger) -> ArcaneSystem:
        name = agent_config['name']
        port = agent_config['port']
        
        agent = ArcaneSystem(name, llm, llm.model, logger, port, agent_config=agent_config)
        
        # Set additional attributes based on the config
        agent.allowed_communications = agent_config['allowed_communications']
        print(f'{name} can talk to {agent.allowed_communications}')
        
        return agent


    @staticmethod
    def load_agent_config(config_path: str = 'agent_config.yaml') -> dict:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

