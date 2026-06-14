# Python Backend API

A complete backend system built with FastAPI

## Live Demo

https://python-backend-production-ff36.up.railway.app/docs

## Features

- User registration and login
- JWT Authentication
- Multi-device session management
- Task management system
- File upload
- Automatic email sending
- Rate limiting
- Automatic logging

## Technologies

- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Celery
- Docker
- JWT Authentication

## Setup

1. Install dependencies:
pip install -r requirements.txt

2. Configure .env file:
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///./test.db
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15

3. Run:
uvicorn backend.server:app --reload

## API Documentation

After running, full documentation available at:
http://localhost:8000/docs