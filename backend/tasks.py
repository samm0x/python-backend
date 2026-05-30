from fastapi import BackgroundTasks

def write_log(username: str):
    with open("log.txt", "a") as file:
        file.write(f"{username} logged in\n")