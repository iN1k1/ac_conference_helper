"""Logging configuration for the conference helper application."""

import structlog
import logging
import sys


def configure_logger(log_level: str = "INFO"):
    """Configure structlog with proper formatting and processors.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Configure standard logging to suppress verbose HTTP logs
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )
    
    # Suppress verbose HTTP client logs
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    structlog.stdlib.recreate_defaults()

    # Default ConsoleRenderer with columns: timestamp, level, event, logger, logger_name
    default_cr = structlog.stdlib._config._BUILTIN_DEFAULT_PROCESSORS[-1]
    event_col = default_cr._columns[2]
    default_cr._columns[2] = default_cr._columns[3]
    default_cr._columns[3] = event_col

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
            structlog.stdlib.filter_by_level,
            default_cr,
        ],
        context_class=dict,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set the minimum log level for all loggers
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)
