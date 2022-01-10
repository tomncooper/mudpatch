"""This module contains methods for logging program output to standard out."""
import logging


def setup_logger(debug: bool = False) -> logging.Logger:
    """Creates a pre-configured Logger instance.

    Parameters
    ----------
    debug : bool
        If True, the returned logger will be set to DEBUG level and formatted
        to include additional information in the logging output.

    Returns
    -------
    logging.Logger
        A configured Logger instance.
    """

    top_log: logging.Logger = logging.getLogger("mudpatch")

    if debug:
        level = logging.DEBUG
        fmt = (
            "{levelname} | {name} | "
            "function: {funcName} "
            "| line: {lineno} | {message}"
        )
        style = "{"
    else:
        level = logging.INFO
        fmt = "{asctime} | {levelname} | {message}"
        style = "{"

    formatter: logging.Formatter = logging.Formatter(fmt, style=style)

    handler: logging.StreamHandler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)
    top_log.setLevel(level)
    top_log.addHandler(handler)

    return top_log
