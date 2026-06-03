import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

def login_user(username: str):
    logger.info(
        f"User {username} is trying to login"
    )

    try :
        logger.info(
            f"User {username} logged in successfully"
        )
        return {"message" : "success" }


    except Exception as e :
        logger.error(
            f"login failed {e}"
        )
        return {"message": "failed"}

