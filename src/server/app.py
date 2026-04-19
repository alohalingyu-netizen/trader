"""FastAPI application — market data API server."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.server.routes import market

app = FastAPI(title="Trader Data API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router)
