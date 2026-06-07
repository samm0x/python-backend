from celery import Celery
import time

celery = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery.task
def send_email(username : str):
    time.sleep(3)
    print(f"email sent to {username}")
    return {"status": "email sent", "to": username}

@celery.task
def generate_report(user_id : str):
    time.sleep(5)
    print(f"report generated for user {user_id}")
    return {"status": "report generated", "to": user_id}