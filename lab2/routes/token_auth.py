from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from auth import authenticate_user, create_access_token
from fastapi import HTTPException

router = APIRouter()


@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}
