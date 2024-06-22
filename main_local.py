import asyncio
import multiprocessing
import signal
import time
from main import arcane_base_main
from logging_util import setup_logger
import os
from dotenv import load_dotenv

def run_server(name, descriptor, model, port):
    asyncio.run(arcane_base_main(name=name, descriptor=descriptor, model=model, port=port))

def main():
    load_dotenv()
    logger = setup_logger('SYS')
    base_port = 5000
    agents = [
        ("Iris", "Intelligent Routing and Information System"),
        ("STRATOS", "Strategic Task and Resource Allocation Orchestration System")
    ]

    servers = [(name, descriptor, base_port + i) for i, (name, descriptor) in enumerate(agents)]
    processes = []
    model = os.getenv("CLAUDE_DEFAULT_MODEL")

    for name, descriptor, port in servers:
        p = multiprocessing.Process(target=run_server, args=(name, descriptor, model, port))
        p.start()
        processes.append((p, name))  # Store the process and name as a tuple
        logger.info({"event": "server_start", "name": name, "port": port})

    def shutdown(signal, frame):
        logger.info("Shutdown signal received.")
        for p, name in processes:  # Unpack the process and its corresponding name
            p.terminate()
            logger.info({"event": "server_terminate", "name": name})

        for p, name in processes:
            p.join()
            # logger.info({"event": "server_join", "name": name})

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while any(p.is_alive() for p, _ in processes):  # Only check the process part
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)

if __name__ == '__main__':
    main()