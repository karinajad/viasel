from fastapi import FastAPI

app = FastAPI(title="Viasel")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# routers registered in plan 04
