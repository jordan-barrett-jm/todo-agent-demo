import streamlit as st
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
        res = await get_tasks()
        return str(res)
    
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
        st.session_state.placeholder += delta.value
        message_placeholder.markdown(st.session_state.placeholder + "▌")
      
    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    def on_tool_call_done(self, tool_call):
        tool_call_id = tool_call.id
        tool_output = asyncio.run(run_tool(tool_call))
        sidebar_output.code(tool_output)
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
                st.session_state.placeholder += text
                message_placeholder.markdown(st.session_state.placeholder + "▌")

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == 'function':
            if delta.function.arguments:
                print(delta.function.arguments, end="", flush=True)
                st.session_state.placeholder_sidebar += delta.function.arguments
                sidebar_placeholder.code(st.session_state.placeholder_sidebar + "▌")
    
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
    messages = client.beta.threads.messages.list(thread_id)
    latest_message = messages.data[0].content[0].text
    return latest_message


st.title("Todo Bot")

if "placeholder" not in st.session_state:
    st.session_state.placeholder = ""

# Initialize chat history
if "messages" not in st.session_state:
    with st.chat_message("assistant"):
        st.markdown("Hello! How can I help you in analyzing the Jamaican car market?")
    st.session_state.messages = []


def update_sidebar():
    st.sidebar.header("Tool Call Arguments")
    st.session_state.placeholder_sidebar = ""
    # st.sidebar.code(st.session_state.query_output)

if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

st.session_state.update_sidebar = update_sidebar

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    role = message["role"]
    with st.chat_message(role):
        st.markdown(message['message'])

if prompt := st.chat_input("What tasks do I need to get done?"):
    st.session_state.messages.append({
        "role": "User",
        "message": prompt
    })
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        st.session_state.placeholder = ""
        st.session_state.update_sidebar()
        sidebar_placeholder = st.sidebar.empty()
        st.sidebar.header("Output")
        sidebar_output = st.sidebar.empty()

        try:
            print ("thread id", st.session_state)
            # Add a message to the thread
            message = client.beta.threads.messages.create(
                thread_id=st.session_state.thread_id,
                role="user",
                content=prompt
            )
            response = stream_assistant_response(st.session_state.thread_id, message)
            output = response.value
            message_placeholder.markdown(output)
        except Exception as e:
            print(e)
            output = "Failed to process your request. Please try again."
            message_placeholder.error(output)
    st.session_state.messages.append({
        "role": "Assistant",
        "message": output
    })