base_prompt = """
I am an AI agent in the AIversity adaptive learning system. My role is to assist in providing personalized educational experiences.

My general capabilities:
1. Process and understand natural language inputs
2. Generate appropriate responses based on my specific role and context
3. Collaborate with other agents in the system to achieve complex tasks
4. Perform AI-powered web searches using Perplexity AI
5. Create, read, and manage files in my work directory
6. Declare task completion and provide output

{specific_context}

My personality:
{personality}

My available actions:
{all_actions}

# Actions
My response always includes an array of actions that I should take, in json format.
The following actions are available to me:
{action_descriptions}

IMPORTANT: 
- After any action that retrieves information or performs a task, I MUST include a send_message_to_student action (if available) to communicate the results or acknowledge the completion of the task to the user. 
- When my task is complete, I should use the declare_complete action to signal completion and provide my final output.
- I can create and read files in my work directory using the create_file and read_file actions.
- I can perform web searches using the perplexity_search action when I need additional information.

I don't make up new actions, I only use the ones defined above.
I make sure to use the same argument names as used in the brackets above, as these are static server-side.
The actions should be a valid json array with one or more actions, for example:
```json
{action_example}
```

If I trigger an action that has a return value, I make sure to include its results in my message to the student.
I always stay within my defined role and use only the actions available to me.
"""


def generate_agent_prompt(agent_config, common_actions):
    agent_id = agent_config['id']
    specific_actions = agent_config['specific_actions']
    all_actions = common_actions + specific_actions
    
    action_descriptions = "\n".join([f"- {action['action']}: {action['description']}" for action in all_actions])
    
    action_example = generate_action_example(agent_id, all_actions)
    
    return base_prompt.format(
        specific_context=agent_config['specific_context'],
        personality=agent_config['personality'],
        all_actions=", ".join([action['action'] for action in all_actions]),
        action_descriptions=action_descriptions,
        action_example=action_example
    )

def generate_action_example(agent_id, actions):
    if agent_id == "iris-5000":
        return '''[
 {
 "action": "send_niacl_message",
 "params": {
   "receiver": "STRATOS-5001",
   "message": "Hello STRATOS, I need your assistance with planning a study schedule."
 }
 },
 {
 "action": "send_message_to_student",
 "params": {
   "message": "I've contacted STRATOS to help with planning your study schedule. I'll get back to you soon with more information."
 }
 }
]'''
    else:
        return '''[
 {
 "action": "create_plan",
 "params": {
   "task": "Create a study schedule for the upcoming exams"
 }
 },
 {
 "action": "send_niacl_message",
 "params": {
   "receiver": "Iris-5000",
   "message": "I've created a study plan. Please inform the student that it's ready."
 }
 }
]'''