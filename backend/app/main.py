from fastapi import FastAPI

app = FastAPI(title="GenAlpha News Insights API")

@app.get("/health")
def health():
    return {"status": "ok"}