import json
import os
import yaml

from dotenv import load_dotenv

load_dotenv()


def has_environment_variable(name):
    value = os.getenv(name)
    return value is not None and value.strip() != ""


def get_environment_variable(name):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise EnvironmentError(
            f"{name} environment variable not set! Check your .env file."
        )

    return value


def parse_json(input_string):
    try:
        return json.loads(input_string)
    except json.JSONDecodeError:
        return None


def load_actions(agent_type):
    with open("action_definitions.yaml", "r") as file:
        all_actions = yaml.safe_load(file)
    
    agent_type = agent_type.split("-")[0]

    actions = all_actions["common_actions"]
    if agent_type in all_actions["agent_specific_actions"]:
        actions.extend(all_actions["agent_specific_actions"][agent_type])

    return actions
