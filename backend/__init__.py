# from fastapi import FastAPI , HTTPException
# from typing import List
# from models.poroshe import Task , TaskCreate, TaskUpdate
#
# app = FastAPI()
#
# tasks_db = List[Task] = []
# next_task_id = 1
# @app.get("/General")
# def read_root():
#     return {"massege: Welcome to the to do List API!"}
#
# @app.post("/tasks/",response_model=Task ,status_code=201,tags=["Tasks"])
# def create_task(task_create: TaskCreate):
#     global next_task_id
#     new_task = Task(id=next_task_id , title= task_create.title, description=task_create.description, is_completed= False )
#     tasks_db.append(new_task)
#     next_task_id += 1
#     return new_task
#
# @app.get("/tasks/",response_modes=List[Task] , tags=["Tasks"])
# def get_tasks():
#     return tasks_db
#
# @app.get("/tasks/{task_id}", response_model=Task ,tags=["Tasks"] )
# def get_task(task_id: int):
#     for task in tasks_db:
#         if task.id == task_id:
#             return task
#     raise HTTPException(status_code=404, detail="Task not found")
#
# @app.put("/taskd/{task_id}",response_model=Task ,tags=["Tasks"])
# def update_task(task_id: int, task_update: TaskUpdate):
#     for index, task in enumerate(tasks_db):
#         if task.id == task_id:
#             updated_task_data= task.model_dump(exclude_unset=True)
#             task_update_data= task_update.model_dump(exclude_unset=True)
#             updated_task = task(**updated_task_data , **task_update_data)
#             tasks_db[index]= updated_task
#             return updated_task
#     raise HTTPException(status_code= 404, detail="Task not found")
#
# @app.delete("/tasks/{task_id}",response_model=Task ,tags=["Tasks"])
# def desete_task(task_id: int):
#     global tasks_db
#     initial_length = len(tasks_db)
#     tasks_db = [task for task in tasks_db if task.id != task_id]
#     if len(tasks_db) == initial_length:
#         raise HTTPException(status_code=404, detail="Task not found")
#     return task_id
#
#
