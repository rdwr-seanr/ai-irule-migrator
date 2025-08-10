"""Structured logging setup."""
import logging, sys, json, time
from typing import Any, Mapping

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'time': int(time.time()*1000)
        }
        if record.exc_info:
            base['exc_info'] = self.formatException(record.exc_info)
        if hasattr(record, 'extra_data') and isinstance(record.extra_data, Mapping):
            base.update(record.extra_data)  # type: ignore
        return json.dumps(base)

def configure_logging():
    root = logging.getLogger()
    if not root.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(JsonFormatter())
        root.addHandler(h)
    root.setLevel(logging.INFO)
