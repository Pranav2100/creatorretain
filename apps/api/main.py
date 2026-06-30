from fastapi import FastAPI

app = FastAPI(
    title="CreatorRetain API",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "CreatorRetain API",
        "version": "0.1.0",
    }