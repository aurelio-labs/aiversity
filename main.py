import asyncio
import signal
from dotenv import load_dotenv
from ARCANE.arcane_system import ArcaneSystem
from llm.LLM import LLM
# from memory.weaviate_memory_manager import WeaviateMemoryManager
from util import get_environment_variable
from channels.web.fastapi_app import FastApiApp
from logging_util import setup_logger

async def arcane_base_main(name, descriptor, model, port):
    load_dotenv()
    logger = setup_logger(name)

    anthropic_api_key = get_environment_variable('ANT_API_KEY')
    llm = LLM(logger)
    arc = ArcaneSystem(name, llm, model, logger, port)

    await arc.start()

    fastapi_backend = FastApiApp(arc, llm, port)
    logger.info(f"Starting backend for {name}")

    try:
        await fastapi_backend.run()
    except asyncio.CancelledError:
        logger.info(f"{name}'s fastapi backend shutting down...")
    finally:
        if fastapi_backend:
            await fastapi_backend.shutdown()
        logger.info(f"{name}'s fastapi backend has been shut down.")

# Example of usage
if __name__ == "__main__":
    asyncio.run(arcane_base_main("ExampleAgent", "An example descriptor", "claude-3-haiku-20240307", 8000))


## TODO: remove DiscordBot and FastApiApp - or leverage the code behind FastApiApp as this is what we will be doing basically
## Then we implement the first triage agent, and see how it talks to the planning agent, once given context such as files, 
# system awareness, capabilities, context of other agents, and the ability to handoff to the planning agent and an understanding 
# of the orchestration of the whole system

# Keep copying over from ACE, but reducing, and converting to Anthropic

# We want the profile pictures in the UI too, and maybe a typing animation?
# We also want the ability to summarise current state of the system so we can show this in the UI for the user//dev initially, use a spinning /-\|/-\|
# And we can use smaller LLMs to respond to queries current action state, or maybe Agents just main a descriptor of what they're currently blocked on/doing
