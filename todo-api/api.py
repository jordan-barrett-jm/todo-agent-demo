from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
import os

app = FastAPI()

JSON_FILE = "tasks.json"


class Task(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    completed: bool = False


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    completed: Optional[bool] = False

class TaskUpdate(BaseModel):
    title: str
    description: Optional[str] = None
    completed: Optional[bool] = False
    id: Optional[str] = None

def load_tasks():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as file:
            return json.load(file)
    return []


def save_tasks(tasks):
    with open(JSON_FILE, "w") as file:
        json.dump(tasks, file, indent=4)


def generate_id(tasks):
    if not tasks:
        return 1
    max_id = max(task["id"] for task in tasks)
    return max_id + 1


@app.get("/api/tasks", response_model=List[Task])
def get_tasks():
    return load_tasks()


@app.get("/api/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    tasks = load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")


@app.post("/api/tasks", response_model=Task)
def create_task(task: TaskCreate):
    tasks = load_tasks()
    new_task = Task(
        id=generate_id(tasks),
        title=task.title,
        description=task.description,
        completed=task.completed
    )
    tasks.append(new_task.dict())
    save_tasks(tasks)
    return new_task


@app.put("/api/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, updated_task: TaskUpdate):
    tasks = load_tasks()
    for i, task in enumerate(tasks):
        print(task)
        if task["id"] == task_id:
            updated_task.id = task_id  # Ensure the ID remains unchanged
            tasks[i] = updated_task.dict()
            save_tasks(tasks)
            return tasks[i]
    raise HTTPException(status_code=404, detail="Task not found")


@app.delete("/api/tasks/{task_id}", response_model=Task)
def delete_task(task_id: int):
    tasks = load_tasks()
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            deleted_task = tasks.pop(i)
            save_tasks(tasks)
            return deleted_task
    raise HTTPException(status_code=404, detail="Task not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8445)