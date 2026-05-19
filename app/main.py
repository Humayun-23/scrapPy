from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import billing, health, internal, jobs, keys, proxy, scrape


def create_app() -> FastAPI:
    app = FastAPI(
        title="Scrappy API",
        description="Stealth web scraping powered by CloakBrowser + Hysteria2",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(scrape.router)
    app.include_router(jobs.router)
    app.include_router(proxy.router)
    app.include_router(billing.router)
    app.include_router(keys.router)
    app.include_router(internal.router)

    return app


app = create_app()
