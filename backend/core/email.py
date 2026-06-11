from fastapi_mail import FastMail , MessageSchema , ConnectionConfig
from backend.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME = settings.MAIL_USERNAME,
    MAIL_PASSWORD = settings.MAIL_PASSWORD,
    MAIL_FROM = settings.MAIL_FROM,
    MAIL_PORT= 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS =False,
    USE_CREDENTIALS = True
)

async def send_async_email(email:str,username:str ):
    message = MessageSchema(
        subject="خوش اومدی ",
        recipients=[email],
        body=f"سلام{username},بت نام موفق بود ",
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)

