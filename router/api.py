from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import usage as usage_log
from .config import load_config
from .errors import ConfigError, MissingPriceError, ProviderError
from .providers import OpenAICompatProvider
from .router import Router


class CompleteRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20000)
    task_type: str
    expected: str | None = None


def create_app(router: Router | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if router is None:
            cfg = load_config(os.getenv("ROUTER_CONFIG_DIR", "config"))
            app.state.router = Router(cfg, OpenAICompatProvider(cfg), os.getenv("ROUTER_DB", "data/router.db"),
                                      strict_costs=os.getenv("STRICT_COSTS") == "1")
        else:
            app.state.router = router
        yield

    app = FastAPI(title="llm-cost-router", lifespan=lifespan)

    @app.post("/complete")
    def complete(body: CompleteRequest):
        try:
            return app.state.router.complete(body.prompt, body.task_type, body.expected).to_dict()
        except ConfigError as exc:
            raise HTTPException(422, str(exc)) from exc
        except MissingPriceError as exc:
            raise HTTPException(500, str(exc)) from exc
        except ProviderError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.get("/usage")
    def usage():
        return usage_log.summary(app.state.router.conn)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


def get_app() -> FastAPI:
    return create_app()
