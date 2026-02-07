"""Manages the Telegram bot background thread."""
import logging
import threading

from orchestrator.registry import SkillRegistry
from integrations.telegram_bot import start_bot

logger = logging.getLogger(__name__)


class TelegramManager:
    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, registry: SkillRegistry) -> str:
        """Start the Telegram bot in a background thread. Returns status message."""
        with self._lock:
            if self.is_running:
                return "Telegram bot is already running."

            self._stop_event.clear()
            self._thread = threading.Thread(
                target=start_bot,
                args=(registry, self._stop_event),
                name="telegram-bot",
                daemon=True,
            )
            self._thread.start()
            return "Telegram bot started. You can now send messages to your bot on Telegram."

    def stop(self) -> str:
        """Signal the bot to stop and wait for the thread to finish."""
        with self._lock:
            if not self.is_running:
                return "Telegram bot is not running."

            self._stop_event.set()
            self._thread.join(timeout=10)
            self._thread = None
            return "Telegram bot stopped."
