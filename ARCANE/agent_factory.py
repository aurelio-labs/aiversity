import yaml
from ARCANE.arcane_system import ArcaneSystem
from llm.LLM import LLM
import logging

class AgentFactory:
    @staticmethod
    def create_agent(agent_config: dict, common_actions: list, llm: LLM, logger: logging.Logger, api_key) -> ArcaneSystem:
        name = agent_config['name']
        port = agent_config['port']
        
        agent = ArcaneSystem(name, llm, llm.model, logger, port, agent_config=agent_config, common_actions=common_actions, api_key=api_key)
        
        print(f'{name} can talk to {agent.allowed_communications}')
        print(f'{name} has the following actions available: {agent.get_available_actions()}')
        
        return agent

    @staticmethod
    def load_agent_config(config_path: str = 'agent_config.yaml') -> dict:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Ensure common_actions are present in the loaded config
        if 'common_actions' not in config:
            raise ValueError("common_actions not found in the configuration file")
        
        return config