"""
CytoLens Inference Service - FastAPI
Professional structure for WSI inference service
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError
from pydantic import ValidationError

from api import exceptions
from api.routes import auth as auth_routes
from api.routes import inference as inference_routes
from api.routes import slides as slides_routes
from api.routes import viewer as viewer_routes
from core import config

# from utils import logging_utils


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle
    """
    # # Setup logging first
    # logging_utils.setup_logging()
    # logger = logging_utils.get_logger(name="cytolens.main")

    # # Startup - Download model files if needed
    # logger.info("Starting CytoLens Inference Service")

    yield

    # Shutdown
    # logger.info("Shutting down CytoLens Inference Service")


# Create FastAPI app
app = FastAPI(
    title=config.settings.app_name,
    version=config.settings.api_version,
    debug=config.settings.debug,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router)
app.include_router(slides_routes.router)
app.include_router(viewer_routes.router)
app.include_router(inference_routes.router)

# Register exception handlers
app.add_exception_handler(ValidationError, exceptions.validation_exception_handler)
app.add_exception_handler(JWTError, exceptions.jwt_exception_handler)
app.add_exception_handler(ValueError, exceptions.value_error_handler)
app.add_exception_handler(Exception, exceptions.general_exception_handler)


if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=5000)
