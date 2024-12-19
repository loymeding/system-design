from fastapi import APIRouter, HTTPException, Depends, status
from auth import get_current_user
from database import users_db
from models import User

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_user(user: User, current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if user.username in users_db:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    users_db[user.username] = {"username": user.username, "password": user.password, "is_admin": user.is_admin}
    return {"message": "User created successfully"}
