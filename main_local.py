import asyncio
import multiprocessing
import signal
import time
from logging_util import setup_logger
import os
from dotenv import load_dotenv
from llm.LLM import LLM
from ARCANE.agent_factory import AgentFactory
from channels.web.fastapi_app import FastApiApp
import shutil

def clear_llm_logs():
    log_folder = "llm_logs"
    if os.path.exists(log_folder):
        shutil.rmtree(log_folder)
    os.makedirs(log_folder)
    print(f"Cleared contents of {log_folder}")

def run_server(agent_config, common_actions, llm_config, port):
    from llm.LLM import LLM
    from ARCANE.agent_factory import AgentFactory
    from channels.web.fastapi_app import FastApiApp
    
    logger = setup_logger(agent_config['name'])
    llm = LLM(logger, **llm_config)
    agent = AgentFactory.create_agent(agent_config, common_actions, llm, logger)
    app = FastApiApp(agent, llm, port)
    asyncio.run(app.run())

def main():
    load_dotenv()
    logger = setup_logger('SYS')

    # Clear LLM logs before starting
    clear_llm_logs()
    
    agent_configs = AgentFactory.load_agent_config()
    llm_config = {
        'api_key': os.getenv('ANT_API_KEY'),
        'model': os.getenv('CLAUDE_DEFAULT_MODEL')
    }

    common_actions = agent_configs['common_actions']
    
    processes = []

    for agent_config in agent_configs['agents']:
        p = multiprocessing.Process(
            target=run_server, 
            args=(agent_config, common_actions, llm_config, agent_config['port'])
        )
        p.start()
        processes.append((p, agent_config['name']))
        logger.info({"event": "server_start", "name": agent_config['name'], "port": agent_config['port']})


    def shutdown(signal, frame):
        logger.info("Shutdown signal received.")
        for p, name in processes:
            p.terminate()
            logger.info({"event": "server_terminate", "name": name})

        for p, name in processes:
            p.join()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while any(p.is_alive() for p, _ in processes):
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)

if __name__ == '__main__':
    main()