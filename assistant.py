import os
from openai import OpenAI
from dotenv import load_dotenv
from openai import AssistantEventHandler
from typing_extensions import override
from helper_functions import *
import json
import asyncio

# Load environment variables from .env file
load_dotenv()

assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
client = OpenAI()

async def run_tool(tool_call):
    arguments = json.loads(tool_call.function.arguments)
    function_name = tool_call.function.name
    
    if function_name == "get_tasks":
        return await get_tasks()
    
    elif function_name == "get_task":
        task_id = arguments["task_id"]
        res = await get_task(task_id)
        return str(res)
    
    elif function_name == "create_task":
        title = arguments["title"]
        description = arguments.get("description")
        completed = arguments.get("completed", False)
        res = await create_task(title, description, completed)
        return str(res)
    
    elif function_name == "update_task":
        task_id = arguments["task_id"]
        title = arguments.get("title")
        description = arguments.get("description")
        completed = arguments.get("completed", False)
        res = await update_task(task_id, title, description, completed)
        return str(res)
    
    elif function_name == "delete_task":
        task_id = arguments["task_id"]
        res = await delete_task(task_id)
        return str(res)
    
    else:
        raise f"Unknown function name: {function_name}"


# Create an event handler class to manage streaming events
class MyEventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)
      
    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)
      
    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    def on_tool_call_done(self, tool_call):
        tool_call_id = tool_call.id
        tool_output = asyncio.run(run_tool(tool_call))
        thread_id = self.current_run.thread_id
        run_id = self.current_run.id
        print(f"\n\noutput > ", flush=True, end="")
        with client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=[
                {
                "tool_call_id": tool_call_id,
                "output": tool_output
                }
            ],
        ) as stream:
            for text in stream.text_deltas:
                print(text, end="", flush=True)

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == 'function':
            if delta.function.arguments:
                print(delta.function.arguments, end="", flush=True)
    
    def on_message_done(self, message):
        print(message)

# Function to create and stream a run
def stream_assistant_response(thread_id, message):
    with client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant_id,
        event_handler=MyEventHandler(),
    ) as stream:
        stream.until_done()

# Example usage
if __name__ == "__main__":
    # Create a thread
    thread = client.beta.threads.create()
    
    # Add a message to the thread
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="Can you remind me to get eggs from the supermarket later today?"
    )

    # Stream the response
    stream_assistant_response(thread.id, message.content)