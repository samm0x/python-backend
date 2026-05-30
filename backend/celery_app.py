from celery import Celery
celery = Celery(
    "tasks",
    broker = "redid://localhost:6379/0"
)