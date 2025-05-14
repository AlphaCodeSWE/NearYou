# src/utils/logger_config.py 
import logging
import logging.handlers
import os
import json
import socket
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Union, List

# Valori possibili: "json", "text"
LOG_FORMAT = os.getenv("LOG_FORMAT", "text").lower()
# Destinazione: "stdout", "file", "both"
LOG_DESTINATION = os.getenv("LOG_DESTINATION", "stdout").lower()
# Percorso dei file di log
LOG_FILE = os.getenv("LOG_FILE", "/var/log/nearyou/app.log")
# Dimensione massima del file di log prima della rotazione
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", 10485760))  # 10MB
# Numero di backup da mantenere
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", 5))

class StructuredLogRecord(logging.LogRecord):
    """Estende LogRecord per supportare campi aggiuntivi e formattazione JSON."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hostname = socket.gethostname()
        self.service = os.getenv("SERVICE_NAME", "nearyou")
        self.environment = os.getenv("ENVIRONMENT", "development")
    
    def get_structured_data(self) -> Dict[str, Any]:
        """Restituisce i dati di log strutturati come dizionario."""
        data = {
            "timestamp": datetime.utcfromtimestamp(self.created).isoformat() + "Z",
            "level": self.levelname,
            "message": self.getMessage(),
            "logger": self.name,
            "path": self.pathname,
            "function": self.funcName,
            "line": self.lineno,
            "process": self.process,
            "thread": self.thread,
            "hostname": self.hostname,
            "service": self.service,
            "environment": self.environment
        }
        
        # Aggiungi informazioni sull'eccezione se presente
        if self.exc_info:
            data["exception"] = {
                "type": self.exc_info[0].__name__,
                "message": str(self.exc_info[1]),
                "traceback": ''.join(traceback.format_exception(*self.exc_info))
            }
            
        # Aggiungi campi extra personalizzati
        for key, value in self.__dict__.items():
            if key.startswith('_') or key in data:
                continue
            try:
                # Assicurati che il valore sia serializzabile in JSON
                json.dumps({key: value})
                data[key] = value
            except (TypeError, OverflowError):
                data[key] = str(value)
        
        return data

class JsonFormatter(logging.Formatter):
    """Formattatore che converte i record di log in JSON."""
    
    def format(self, record: StructuredLogRecord) -> str:
        """Formatta il record come JSON."""
        return json.dumps(record.get_structured_data())

def setup_logging_handlers() -> List[logging.Handler]:
    """Configura e restituisce gli handler di log appropriati."""
    handlers = []
    
    # Handler per stdout
    if LOG_DESTINATION in ["stdout", "both"]:
        stdout_handler = logging.StreamHandler(sys.stdout)
        if LOG_FORMAT == "json":
            stdout_handler.setFormatter(JsonFormatter())
        else:
            fmt = "%(asctime)s [%(levelname)s] %(name)s [%(hostname)s] [%(service)s] - %(message)s"
            stdout_handler.setFormatter(logging.Formatter(fmt))
        handlers.append(stdout_handler)
    
    # Handler per file con rotazione
    if LOG_DESTINATION in ["file", "both"]:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT
        )
        if LOG_FORMAT == "json":
            file_handler.setFormatter(JsonFormatter())
        else:
            fmt = "%(asctime)s [%(levelname)s] %(name)s [%(hostname)s] [%(service)s] - %(message)s"
            file_handler.setFormatter(logging.Formatter(fmt))
        handlers.append(file_handler)
    
    return handlers

def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Configura il logging con formato e livello personalizzabili.
    
    Args:
        log_level: Livello di log opzionale, altrimenti usa LOG_LEVEL dall'ambiente
    """
    # Sovrascrive la factory predefinita per creare record strutturati
    logging.setLogRecordFactory(StructuredLogRecord)
    
    # Configura il livello di log
    level = log_level or os.getenv("LOG_LEVEL", "INFO").upper()
    logging.root.setLevel(level)
    
    # Aggiungi gli handler configurati
    handlers = setup_logging_handlers()
    for handler in handlers:
        logging.root.addHandler(handler)
        
    # Registra un messaggio di informazione sull'inizializzazione
    logging.info(
        "Logging inizializzato",
        extra={
            "format": LOG_FORMAT,
            "destination": LOG_DESTINATION,
            "level": level
        }
    )

def get_logger(name: str) -> logging.Logger:
    """
    Ottieni un logger con il nome specificato.
    
    Args:
        name: Nome del logger, tipicamente __name__
        
    Returns:
        Logger configurato
    """
    return logging.getLogger(name)