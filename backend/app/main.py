from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import demand, packaging, projects, rom, sourcing

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
app.include_router(sourcing.router)
app.include_router(packaging.router)
app.include_router(projects.router)
