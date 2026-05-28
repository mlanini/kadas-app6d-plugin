# -*- coding: utf-8 -*-
"""Logging facility for the KADAS APP-6(D) plugin."""

import logging
import os

_LOG_LEVEL = os.environ.get("KADAS_MILSYMB_LOG_LEVEL", "DEBUG").upper()
_LOG_FILE = os.environ.get(
    "KADAS_MILSYMB_LOG",
    os.path.expanduser("~/.kadas/kadas_milsymb.log"),
)

# Ensure the directory exists
os.makedirs(os.path.dirname(_LOG_FILE), exist_ok=True)

_formatter = logging.Formatter(
    "%(asctime)s  %(name)-30s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(_formatter)

_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(_formatter)


# Configure the root namespace logger once at import time.
_root_logger = logging.getLogger("kadas_milsymb")
_root_logger.setLevel(getattr(logging, _LOG_LEVEL, logging.DEBUG))
_root_logger.addHandler(_file_handler)
_root_logger.addHandler(_stream_handler)
_root_logger.propagate = False


def get_logger(name: str = "kadas_milsymb") -> logging.Logger:
    """Return a named child logger within the *kadas_milsymb* namespace.

    Child loggers propagate messages to the root *kadas_milsymb* logger
    which holds the file and stream handlers.  No handlers are added to
    child loggers so messages are never duplicated.
    """
    return logging.getLogger(name)
