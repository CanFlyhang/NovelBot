import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api import router as api_router
from .config import settings
from .db import Base, engine
from .scheduler import scheduler


def _setup_logging() -> None:
    """
    初始化日志系统，输出到控制台与文件。
    """

    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "novelbot.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用实例。
    """

    _setup_logging()

    Base.metadata.create_all(bind=engine)

    app = FastAPI(title=settings.app_name)

    app.mount(
        "/static",
        StaticFiles(directory="app/web/static"),
        name="static",
    )
    templates = Jinja2Templates(directory="app/web/templates")

    app.include_router(api_router)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        """
        返回管理控制面板的主页面。
        """

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "app_name": settings.app_name,
            },
        )

    return app


app = create_app()
