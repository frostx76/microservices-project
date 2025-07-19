from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "FastAPI added to project!"}