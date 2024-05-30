import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv
from openai import AssistantEventHandler
from typing_extensions import override
from helper_functions import *
import json
import asyncio
import time
import tempfile
    
# Load environment variables from .env file
load_dotenv()

assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
client = OpenAI()

async def run_tool(tool_call):
    arguments = json.loads(tool_call.function.arguments)
    function_name = tool_call.function.name
    try:
        if function_name == "get_tasks":
            res = await get_tasks()
        elif function_name == "get_task":
            task_id = arguments["task_id"]
            res = await get_task(task_id)
        elif function_name == "create_task":
            title = arguments["title"]
            description = arguments.get("description")
            completed = arguments.get("completed", False)
            res = await create_task(title, description, completed)
        elif function_name == "update_task":
            task_id = arguments["task_id"]
            title = arguments.get("title")
            description = arguments.get("description")
            completed = arguments.get("completed", False)
            res = await update_task(task_id, title, description, completed)    
        elif function_name == "delete_task":
            task_id = arguments["task_id"]
            res = await delete_task(task_id)
        else:
            raise Exception(f"Unknown function name: {function_name}")
    except Exception as e:
        print(e)
        return str(e), tool_call.id
    sidebar_output.text_area("",str(res))
    return str(res), tool_call.id

async def executeToolCalls(tool_calls):
    tasks = [run_tool(tc) for tc in tool_calls]
    results = await asyncio.gather(*tasks)
    results_arr = []
    for res, tool_call_id in results:
        results_arr.append({
            "tool_call_id": tool_call_id,
            "output": res
        })
    return results_arr

# Create an event handler class to manage streaming events
class MyEventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        st.session_state.run_id = self.current_run.id
      
    @override
    def on_text_delta(self, delta, snapshot):
        st.session_state.run_id = self.current_run.id
        st.session_state.placeholder += delta.value
        message_placeholder.markdown(st.session_state.placeholder + "▌")

    def on_tool_call_done(self, tool_call):
        print("Added tool call to list...")
        st.session_state.tool_calls.append(tool_call)
        st.session_state.run_id = self.current_run.id
        

    def on_tool_call_delta(self, delta, snapshot):
        st.session_state.run_id = self.current_run.id
        if delta.type == 'function':
            if delta.function.arguments:
                print(delta.function.arguments, end="", flush=True)
                st.session_state.placeholder_sidebar += delta.function.arguments
                sidebar_placeholder.text_area("",st.session_state.placeholder_sidebar)
    
    def on_message_done(self, message):
        st.session_state.run_id = self.current_run.id

def get_run_status(run_id, thread_id):
    run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
            )
    run_status = run.status
    return run_status

# Function to create and stream a run
def stream_assistant_response(thread_id, message):
    st.session_state.tool_calls = []
    with client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant_id,
        event_handler=MyEventHandler(),
    ) as stream:
        stream.until_done()
    run_status = get_run_status(st.session_state.run_id, thread_id)
    while run_status in ('queued', 'in_progress', 'requires_action'):
        if run_status == 'requires_action':
            try:
                tool_outputs = asyncio.run(executeToolCalls(st.session_state.tool_calls))
                st.session_state.tool_calls = []
                with client.beta.threads.runs.submit_tool_outputs_stream(
                        thread_id=thread_id,
                        run_id=st.session_state.run_id,
                        tool_outputs=tool_outputs,
                        event_handler=MyEventHandler()
                    ) as stream:
                        stream.until_done()
            except Exception as e:
                print (e)
                #delete tool calls
                st.session_state.tool_calls = []
                #cancel the run
                client.beta.threads.runs.cancel(
                    thread_id=thread_id,
                    run_id=st.session_state.run_id
                )
                break
        else:
            time.sleep(1)
        run_status = get_run_status(st.session_state.run_id, thread_id)
    st.session_state.run_id = None
    messages = client.beta.threads.messages.list(thread_id)
    latest_message = messages.data[0].content[0].text
    return latest_message


st.title("Todo Bot")

if "placeholder" not in st.session_state:
    st.session_state.placeholder = ""

if "run_id" not in st.session_state:
    st.session_state.run_id = None
    st.session_state.tool_calls = []

# Initialize chat history
if "messages" not in st.session_state:
    with st.chat_message("assistant"):
        st.markdown("Hello! How can I help you stay on top of your tasks?")
    st.session_state.messages = []


def update_sidebar():
    st.sidebar.header("Tool Call Arguments")
    st.session_state.placeholder_sidebar = ""

if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

st.session_state.update_sidebar = update_sidebar

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    role = message["role"]
    with st.chat_message(role):
        st.markdown(message['message'])

chat_image = st.file_uploader("Upload an image", type=['png', 'jpg', 'jpeg'])
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
            if chat_image:
                 # Get the file name and extension of the uploaded file
                file_name = chat_image.name
                file_extension = os.path.splitext(file_name)[1]
                
                # Create a temporary file with the same extension
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                    temp_file.write(chat_image.read())
                    temp_file_path = temp_file.name

                image_file = client.files.create(file=open(temp_file_path, "rb"), purpose="vision")
                content = [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_file",
                        "image_file": {
                            "file_id": image_file.id
                        }
                    }
                ]
            else:
                content = prompt
            # Add a message to the thread
            message = client.beta.threads.messages.create(
                thread_id=st.session_state.thread_id,
                role="user",
                content=content
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