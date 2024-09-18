from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import TAGS_METADATA
from app.pipeline import DataCollectorPipeline
from app.scripts.google_http import GoogleAccessor

# Import routers
from .routes import (
    affecters, getters
)

# Declaring Server Lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Data Collector
    # Deta Collections
    # deta_collection = DetaCollection(PROJECT_KEY, BASE_NAME, DRIVE_NAME)
    # # making deta_collection available for all routes
    # app.state.deta_collection = deta_collection
    # Google Service
    google_accessor = GoogleAccessor()
    app.state.google_accessor = google_accessor
    # Pipeline
    data_collector = DataCollectorPipeline(
        app, ["BNBUSDT", "LINKUSDT"])
    # data_collector = DataCollectorPipeline(
    #     app, ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT", "DOGEUSDT"])
    # making data_collector available for all routes
    app.state.data_collector = data_collector
    # # Start scraping exchange data
    # asyncio.create_task(data_collector.run())
    # print(">>> Data Collector API Started Successfully")
    yield
    # Tasks to execute when the application shuts down.
    # Disconnect from Database Connection
    # print(">>> Data Collector API ShutDown Successfully")


# Initialize FastAPI app
app = FastAPI(lifespan=lifespan, openapi_tags=TAGS_METADATA)

# Include routers
app.include_router(affecters.router)
app.include_router(getters.router)
