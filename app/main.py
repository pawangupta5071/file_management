from fastapi import FastAPI

app = FastAPI(
    title="file_management",
    version="1.0.0",
)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
