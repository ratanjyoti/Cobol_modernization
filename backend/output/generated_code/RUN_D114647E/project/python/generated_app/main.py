from fastapi import FastAPI

app = FastAPI(title="Generated Migration API")


@app.get("/health")
def health():
    return {"status": "ok"}
