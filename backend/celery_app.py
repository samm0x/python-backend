from celery import Celery
celery = Celery(
    "tasks",
    broker = "redid://localhost:6379/0"
)
@celery.task
def send_email():
    print("email sent")