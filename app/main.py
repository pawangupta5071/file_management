from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise

from app.api.files import router as files_router
from app.database import TORTOISE_ORM

app = FastAPI(
    title="File Management",
    version="1.0.0",
)

app.include_router(files_router)

register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=False,
    add_exception_handlers=True,
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}