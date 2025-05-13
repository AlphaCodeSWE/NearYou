# src/logger_config.py
import logging
import os

def setup_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()  # Usa il value di LOG_LEVEL se presente
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
