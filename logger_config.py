import logging
import os
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

class Colors:
    RESET = '\033[0m'
    DEBUG = '\033[36m'      
    INFO = '\033[32m'       
    WARNING = '\033[33m'   
    ERROR = '\033[31m'     
    CRITICAL = '\033[35m'
    
    BOLD = '\033[1m'
    DIM = '\033[2m'

class ColoredConsoleFormatter(logging.Formatter):
    
    def __init__(self, fmt=None, datefmt=None, style='%', fixed_color=None):
        super().__init__(fmt, datefmt, style)
        self.fixed_color = fixed_color
    
    def format(self, record):
        levelname = record.levelname
        name = record.name
        
        if self.fixed_color:
            formatted_message = super().format(record)
            return f"{self.fixed_color}{formatted_message}{Colors.RESET}"
        
        if record.levelno == logging.DEBUG:
            record.levelname = f"{Colors.DEBUG}{levelname}{Colors.RESET}"
        elif record.levelno == logging.INFO:
            record.levelname = f"{Colors.INFO}{levelname}{Colors.RESET}"
        elif record.levelno == logging.WARNING:
            record.levelname = f"{Colors.WARNING}{levelname}{Colors.RESET}"
        elif record.levelno == logging.ERROR:
            record.levelname = f"{Colors.ERROR}{levelname}{Colors.RESET}"
        elif record.levelno == logging.CRITICAL:
            record.levelname = f"{Colors.CRITICAL}{levelname}{Colors.RESET}"
        
        record.name = f"{Colors.DIM}{name}{Colors.RESET}"
        
        result = super().format(record)
        
        record.levelname = levelname
        record.name = name
        
        return result

def setup_logger():
    logger = logging.getLogger("Calendator")
    logger.setLevel(logging.DEBUG)

    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )

    console_formatter = ColoredConsoleFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )

    file_handler = logging.FileHandler(
        os.path.join(LOG_DIR, f"bot_{datetime.now().strftime('%Y%m%d')}.log"),
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    error_handler = logging.FileHandler(
        os.path.join(LOG_DIR, f"error_{datetime.now().strftime('%Y%m%d')}.log"),
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)

    return logger

def setup_debug_logger():
    debug_logger = logging.getLogger("DEBUG_TEMP")
    debug_logger.setLevel(logging.DEBUG)
    debug_logger.propagate = False

    console_formatter = ColoredConsoleFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        fixed_color=Colors.CRITICAL  
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)  
    debug_logger.addHandler(console_handler)

    return debug_logger

logger = setup_logger()
debug_logger = setup_debug_logger()