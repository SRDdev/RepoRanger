import datetime
import logging
import os
import re
import sys

from colorama import Fore, Style, init
from rich.console import Console

console = Console()


def add_rule_method(logger):
    def rule(text, style=""):
        console.print()  # Add empty line
        console.rule(f" {text} ", style=style)

    logger.rule = rule
    return logger


def setup_logger(name="Base", filename="logs", detail="info"):
    """
    Sets up a logger with the specified name and colored console logging.
    All logs go to a single file with session separation.
    """
    level = getattr(logging, detail.upper(), None)
    if level is None:
        raise ValueError(f"Invalid logging level: {detail}")

    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger(f"{name}")
    logger.setLevel(level)
    logger.propagate = False

    if logger.hasHandlers():
        logger.handlers.clear()

    file_handler = SessionFileHandler(f"logs/{filename}.log")
    file_handler.setFormatter(CustomFormatter(use_color=False))
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CustomFormatter(use_color=True))
    logger.addHandler(console_handler)

    return add_rule_method(logger)  # Add the rule method to logger


# Initialize colorama
init(autoreset=True)


class CustomFormatter(logging.Formatter):
    LEVEL_MAP = {
        "DEBUG": ("DEB", Fore.CYAN),
        "INFO": ("INFO", Fore.GREEN),
        "WARNING": ("WAR", Fore.YELLOW),
        "ERROR": ("ERR", Fore.RED),
        "CRITICAL": ("CRI", Fore.MAGENTA),
    }

    RENAME_MAP = {"uvicorn.error": "API.API", "uvicorn.access": "API.Done", "uvicorn": "API"}

    def __init__(self, use_color=True, width=250):
        super().__init__()
        self.use_color = use_color
        self.width = width

    def format(self, record):
        level_label, color = self.LEVEL_MAP.get(record.levelname, (record.levelname, ""))
        display_name = self.RENAME_MAP.get(record.name, record.name)
        display_name = f"{display_name:<18}"

        message = record.getMessage()
        file_info = f"{record.filename}:{record.lineno}"
        file_info_colored = f"{Style.DIM}{file_info}{Style.RESET_ALL}"

        # Get terminal width dynamically, fallback to default if not available

        import shutil

        terminal_width = shutil.get_terminal_size().columns
        self.width = min(terminal_width, self.width)

        # Reserve space for file info (using actual file info length plus padding)
        file_info_space = len(file_info) + 2

        # Calculate available width for message
        prefix_length = 4 + 3 + len(display_name) + 3  # [LEVEL | display_name | ]
        effective_width = self.width - prefix_length - file_info_space

        # Split message into lines
        lines = []
        for raw_line in message.split("\n"):
            while raw_line:
                if len(raw_line) <= effective_width:
                    lines.append(raw_line)
                    break
                # Find last space within effective width
                split_point = raw_line.rfind(" ", 0, effective_width)
                if split_point == -1:  # No space found, force split
                    split_point = effective_width
                lines.append(raw_line[:split_point])
                raw_line = raw_line[split_point:].lstrip()

        formatted_lines = []
        for i, line in enumerate(lines):
            if self.use_color:
                level = (
                    f"{color}{level_label:<4}{Style.RESET_ALL}" if record.levelno < logging.ERROR else f"{Fore.RED}{level_label:<4}{Style.RESET_ALL}"
                )
            else:
                level = f"{level_label:<4}"

            if i == 0:
                # First line with file info
                base_line = f"{level} | {display_name} | {line}"
                padding = self.width - len(self._strip_ansi(base_line)) - len(file_info) - 1
                formatted_line = base_line + " " * max(padding, 1) + (file_info_colored if self.use_color else file_info)
            else:
                # Continuation lines without file info
                indent_label = " " * 4
                indent_name = " " * len(display_name)
                formatted_line = f"{indent_label} | {indent_name} | {line}"

            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)

    def _strip_ansi(self, text):
        ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        return ansi_escape.sub("", text)


class SessionFileHandler(logging.FileHandler):
    """
    Custom FileHandler that adds a session header if the time gap between logs exceeds 30 minutes.
    """

    TIME_GAP_THRESHOLD = datetime.timedelta(minutes=30)

    def __init__(self, filename, mode="a", encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)
        self._session_needs_header = True
        self._last_log_time = None

        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            self._add_header()
            self._session_needs_header = False

    def _add_header(self):
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.baseFilename, "a", encoding="utf-8") as f:
            f.write("#---------------------------------------------------------------------#\n")
            f.write(f"Run : {current_time}\n")
            f.write("#---------------------------------------------------------------------#\n")

    def emit(self, record):
        current_time = datetime.datetime.now()

        if self._last_log_time and (current_time - self._last_log_time) > self.TIME_GAP_THRESHOLD:
            self._session_needs_header = True

        if self._session_needs_header:
            try:
                if os.path.exists(self.baseFilename) and os.path.getsize(self.baseFilename) > 0:
                    with open(self.baseFilename, "a", encoding="utf-8") as f:
                        f.write("\n\n")
                self._add_header()
                self._session_needs_header = False
            except Exception:
                pass

        self._last_log_time = current_time
        super().emit(record)


class CustomStreamHandler(logging.StreamHandler):
    def __init__(self):
        super().__init__()
        self.setFormatter(CustomFormatter(use_color=True))


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "custom": {
            "()": "Config.logger.CustomFormatter",
            "use_color": False,
        },
        "custom_color": {
            "()": "Config.logger.CustomFormatter",
            "use_color": True,
        },
    },
    "handlers": {
        "console": {
            "class": "Config.logger.CustomStreamHandler",
            "level": "INFO",
        },
        "file": {
            "class": "Config.logger.SessionFileHandler",
            "formatter": "custom",
            "filename": "logs/logs.log",
            "mode": "a",
            "level": "DEBUG",
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG",
    },
}

# Make sure our custom handler is available for the config


sys.modules["Config.logger.SessionFileHandler"] = SessionFileHandler