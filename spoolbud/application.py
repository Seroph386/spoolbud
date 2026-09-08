"""FastAPI application assembly."""

from fastapi import FastAPI

from spoolbud.routes import api, bins, health, home, scan, spools


def create_app() -> FastAPI:
    application = FastAPI(title="SpoolBud Helper")
    for router in (home.router, health.router, scan.router, bins.router, api.router, spools.router):
        application.include_router(router)
    return application
