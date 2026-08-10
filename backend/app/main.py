from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import demand, rom

app = FastAPI(title="Viasel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(rom.router)
app.include_router(demand.router)
