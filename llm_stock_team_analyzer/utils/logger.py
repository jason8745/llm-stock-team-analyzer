import logging
import sys
import typing as t
from types import FrameType

from loguru import logger

_LOGGERS_MOVE_TO_LOGURU = [
    "uvicorn.asgi",
    "uvicorn.access",
    "uvicorn",
    "langfuse",
    "langchain",
]


class EndpointFilter(logging.Filter):
    def __init__(self, path: str, *args: t.Any, **kwargs: t.Any):
        super().__init__(*args, **kwargs)
        self._path = path

    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find(self._path) == -1


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = t.cast(FrameType, frame.f_back)
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


class Logger:
    def __init__(self):
        self.logger = logger
        self.logger.remove()

    def init_config(self, log_level="INFO", log_path="app.log"):
        logging.getLogger("uvicorn.access").addFilter(EndpointFilter(path="/health"))
        logging.getLogger().handlers = [InterceptHandler()]
        for logger_name in _LOGGERS_MOVE_TO_LOGURU:
            logging.getLogger(logger_name).handlers = [InterceptHandler()]
        logger.configure(
            handlers=[
                {
                    "sink": sys.stdout,
                    "level": log_level,
                    "serialize": False,  # Enable JSON lines
                },
                {
                    "sink": log_path,
                    "level": log_level,
                    "serialize": False,  # Enable JSON lines
                },
            ]
        )

    def get_logger(self):
        return self.logger


Loggers = Logger()
log = Loggers.get_logger()
