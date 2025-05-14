"""
Configurazione del logger strutturato con output JSON e tracciamento contesto.
Supporta integrazione con Loki e altre piattaforme di aggregazione log.
"""
import os
import json
import logging
import logging.config
import socket
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

# Configurazione base dal file .env
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
SERVICE_NAME = os.getenv("SERVICE_NAME", "nearyou")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Classe per formattare i log in JSON
class JsonFormatter(logging.Formatter):
    """Formatter che converte i log in formato JSON strutturato."""
    
    def __init__(self, service_name: str = SERVICE_NAME):
        self.service_name = service_name
        self.hostname = socket.gethostname()
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatta il record di log in JSON."""
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "service": self.service_name,
            "host": self.hostname,
            "environment": ENVIRONMENT,
            "path": record.pathname,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Aggiungi eventuale contesto extra
        if hasattr(record, "context") and record.context:
            log_data["context"] = record.context
        
        # Aggiungi info eccezione se presente
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data)

# Classe per aggiungere contesto ai logger
class ContextLogger(logging.Logger):
    """Logger esteso che supporta l'aggiunta di contesto ai log."""
    
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
        """Override per supportare il contesto nei record di log."""
        if extra is None:
            extra = {}
        
        if not "context" in extra and hasattr(self, "context"):
            extra["context"] = self.context
            
        return super().makeRecord(name, level, fn, lno, msg, args, exc_info, func, extra, sinfo)
    
    def bind(self, **kwargs) -> 'ContextLogger':
        """Aggiunge contesto al logger."""
        if not hasattr(self, "context"):
            self.context = {}
        
        for key, value in kwargs.items():
            self.context[key] = value
            
        return self

def setup_logging(service_name: Optional[str] = None):
    """
    Configura il logging strutturato in formato JSON.
    
    Args:
        service_name: Nome del servizio, se None usa la variabile d'ambiente SERVICE_NAME
    """
    if service_name:
        global SERVICE_NAME
        SERVICE_NAME = service_name
    
    # Registra la classe logger personalizzata
    logging.setLoggerClass(ContextLogger)
    
    # Configurazione base
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JsonFormatter,
                "service_name": SERVICE_NAME
            },
            "standard": {
                "format": "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json" if ENVIRONMENT != "development" else "standard",
                "level": LOG_LEVEL,
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": LOG_LEVEL,
                "propagate": True
            },
            # Logger specifici per componenti
            "src": {
                "level": LOG_LEVEL,
                "handlers": ["console"],
                "propagate": False
            },
            "services": {
                "level": LOG_LEVEL,
                "handlers": ["console"],
                "propagate": False
            },
            "kafka": {
                "level": os.getenv("KAFKA_LOG_LEVEL", "WARNING"),
                "handlers": ["console"],
                "propagate": False
            },
            # Silenzia alcuni logger troppo verbosi
            "urllib3": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False
            }
        }
    }
    
    # Applica la configurazione
    logging.config.dictConfig(logging_config)
    
    # Log iniziale di configurazione
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configurato per {SERVICE_NAME}",
        extra={"context": {"environment": ENVIRONMENT, "log_level": LOG_LEVEL}}
    )
    
    return logger

def get_logger(name: str) -> ContextLogger:
    """
    Ottiene un logger con contesto.
    
    Args:
        name: Nome del logger
        
    Returns:
        ContextLogger: Logger con supporto per contesto
    """
    return logging.getLogger(name)

# Setup automatico se importato direttamente
if __name__ != "__main__":
    setup_logging()