import uvicorn

from src.appConfig import create_application
from src.core.appEnvironment import get_app_environment

app = create_application()


def run_server() -> None:
    settings = get_app_environment()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run_server()
