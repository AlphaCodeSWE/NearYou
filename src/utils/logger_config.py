# src/utils/logger_config.py - versione compatibile
import logging
import os

def setup_logging():
    """
    Configura il logging con un formato leggibile e livello configurabile.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )