"""
Technical logging without PII (Personally Identifiable Information).
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


LOG_FILE = Path("vereinseinzug.log")


def setup_logger(log_to_file: bool = True, level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return the application logger.
    Logs technical operations without storing personal data.
    """
    logger = logging.getLogger("vereinseinzug")
    logger.setLevel(level)

    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # keep console quiet, errors/warnings only
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (technical log)
        if log_to_file:
            file_handler = RotatingFileHandler(
                LOG_FILE,
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3,
                encoding="utf-8"
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


def mask_iban(iban: Optional[str]) -> str:
    """Mask IBAN for logging and reports: DE69 **** **** **** **30."""
    if not iban:
        return ""
    clean = str(iban).strip().replace(" ", "")
    if len(clean) < 8:
        return "***"
    return f"{clean[:4]} **** **** **** **{clean[-2:]}"


# Global logger instance
logger = setup_logger()
