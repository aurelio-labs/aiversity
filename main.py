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
    llm = LLM("anthropic", anthropic_api_key)
    weaviate_url = get_environment_variable('WEAVIATE_URL')
    # memory_manager = WeaviateMemoryManager(weaviate_url, anthropic_api_key)
    # serpapi_key = get_environment_variable('SERPAPI_KEY')
    arc = ArcaneSystem(name, llm, model, logger) #, memory_manager)

    # giphy = GiphyFinder(get_environment_variable('GIPHY_API_KEY'))
    # media_generators = [
    #     {"keyword": "IMAGE", "generator_function": llm.create_image},
    #     {"keyword": "GIF", "generator_function": giphy.get_giphy_url}
    # ]

    await arc.start()

    fastapi_backend = FastApiApp(arc, llm, port)
    fastapi_task = asyncio.create_task(fastapi_backend.run())
    logger.info(f"Starting backend for {name}")

    try:
        await fastapi_task
    except asyncio.CancelledError:
        logger.info(f"{name}'s fastapi backend shutting down...")
        await fastapi_backend.shutdown()

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
