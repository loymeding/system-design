from fastapi import FastAPI
from routes import users, services, token_auth
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

app = FastAPI()

app.include_router(token_auth.router, tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(services.router, prefix="/services", tags=["Services"])


@app.get("/")
def read_root():
    return {"message": "Welcome to the Service Order API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
