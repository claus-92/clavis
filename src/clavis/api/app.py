from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from clavis.api.routes import boards, status
from clavis.core.errors import ClavisError
from clavis.core.service import ClavisService


def create_app() -> FastAPI:
    app = FastAPI(title="clavis")
    app.state.service = ClavisService()
    app.include_router(status.router, prefix="/api")
    app.include_router(boards.router, prefix="/api")

    @app.exception_handler(ClavisError)
    async def clavis_error_handler(_: Request, exc: ClavisError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    return app


app = create_app()
