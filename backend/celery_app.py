from celery import Celery
from  fastapi_mail import FastMail , MessageSchema
from backend.core.email import conf

celery = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery.task
def send_email(email: str , username : str ):
    import asyncio
    message = MessageSchema(
        subject="خوش اومدی",
        recipients=[email],
        body=f"سلام {username}، ثبت نام موفق بود.",
        subtype="plain"
    )
    fm = FastMail(conf)
    asyncio.run(fm.send_message(message))
    return {"status": "email sent", "to": email}

@celery.task
def generate_report(user_id:str):
    import time
    time.sleep(5)
    print(f"report generated for user {user_id}")
    return {"status": "report generated", "to": user_id}