import aiohttp
import asyncio
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any

# Load environment variables from .env file
load_dotenv()

BASE_URL = os.getenv("BASE_URL")

async def fetch(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
    async with session.get(url) as response:
        return await response.json()

async def post(session: aiohttp.ClientSession, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    async with session.post(url, json=data) as response:
        return await response.json()

async def put(session: aiohttp.ClientSession, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    async with session.put(url, json=data) as response:
        return await response.json()

async def delete(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
    async with session.delete(url) as response:
        return await response.json()

async def get_tasks() -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/tasks"
        return await fetch(session, url)

async def get_task(task_id: int) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/tasks/{task_id}"
        return await fetch(session, url)

async def create_task(title: str, description: Optional[str] = None, completed: Optional[bool] = False) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/tasks"
        data = {
            "title": title,
            "description": description,
            "completed": completed
        }
        return await post(session, url, data)

async def update_task(task_id: int, title: Optional[str] = None, description: Optional[str] = None, completed: Optional[bool] = False) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/tasks/{task_id}"
        data = {
            "title": title,
            "description": description,
            "completed": completed
        }
        return await put(session, url, data)

async def delete_task(task_id: int) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/tasks/{task_id}"
        return await delete(session, url)

# Example usage
if __name__ == "__main__":
    import pprint

    async def main():
        # Create a task
        new_task = await create_task("Sample Task", "This is a sample task")
        pprint.pprint(new_task)

        # Get all tasks
        tasks = await get_tasks()
        pprint.pprint(tasks)

        # Get a specific task
        task = await get_task(new_task['id'])
        pprint.pprint(task)

        # Update the task
        updated_task = await update_task(new_task['id'], title="Updated Task", completed=True)
        pprint.pprint(updated_task)

        # Delete the task
        deleted_task = await delete_task(new_task['id'])
        pprint.pprint(deleted_task)

    asyncio.run(main())
