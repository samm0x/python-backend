from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend.models import Task


def create_task(db: Session, user_id: int, title: str, description: str = None):
    task = Task(title=title, description=description, user_id=user_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_tasks(db: Session, user_id: int, is_done: bool = None):
    query = db.query(Task).filter(Task.user_id == user_id)
    if is_done is not None:
        query = query.filter(Task.is_done == is_done)
    return query.all()

def update_task(db: Session, task_id: int, user_id: int, is_done: bool):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="وظیفه پیدا نشد")
    task.is_done = is_done
    db.commit()
    db.refresh(task)
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "is_done": task.is_done,
        "user_id": task.user_id
    }

def delete_task(db: Session, task_id: int, user_id: int):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="وظیفه پیدا نشد")
    db.delete(task)
    db.commit()
    return {"message": "وظیفه حذف شد"}