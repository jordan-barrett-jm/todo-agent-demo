import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Load API key from .env file
load_dotenv()

client = OpenAI()

# Load tool schemas and assistant instructions
with open('tool_schemas.json', 'r') as f:
    tool_schemas = json.load(f)

with open('instructions.txt', 'r') as f:
    instructions = f.read()

tools = []
for schema in tool_schemas:
    tools.append(
        {
            "type": "function",
            "function": schema
        }
    )

# Create the assistant
response = client.beta.assistants.create(
    name="ToDo Bot",
    instructions=instructions,
    tools=tools,
    model="gpt-4o"
)

# Get the assistant ID from the response
assistant_id = response.id

# Save the assistant ID to the .env file without erasing existing content
with open('.env', 'a') as f:
    f.write(f"\nOPENAI_ASSISTANT_ID={assistant_id}")

print(f"Assistant created with ID: {assistant_id}")
