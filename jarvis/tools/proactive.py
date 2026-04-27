"""
===========================================================
J.A.R.V.I.S. — Proactive Engine
===========================================================
APScheduler-based scheduled tasks:
  - Morning/evening briefings
  - Water reminders, meeting alerts
  - System health monitoring
  - Auto email checks
===========================================================
"""

import logging
import threading
from datetime import datetime
from jarvis.config import (
    MORNING_BRIEFING_HOUR, EVENING_SUMMARY_HOUR,
    WATER_REMINDER_INTERVAL_HOURS, EMAIL_CHECK_INTERVAL_MINUTES,
    MEETING_REMINDER_MINUTES, USER_TITLE
)

logger = logging.getLogger("jarvis.tools.proactive")


class ProactiveEngine:
    """Scheduled proactive behaviors for JARVIS."""

    def __init__(self, orchestrator=None, memory=None):
        self.orchestrator = orchestrator
        self.memory = memory
        self._scheduler = None
        self._speak_callback = None
        self._running = False

    def set_speak_callback(self, callback):
        """Set the TTS callback for proactive announcements."""
        self._speak_callback = callback

    def start(self):
        """Start the proactive scheduler."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            self._scheduler = BackgroundScheduler()

            # Morning briefing
            self._scheduler.add_job(
                self._morning_briefing, "cron",
                hour=MORNING_BRIEFING_HOUR, minute=0,
                id="morning_briefing"
            )

            # Evening summary
            self._scheduler.add_job(
                self._evening_summary, "cron",
                hour=EVENING_SUMMARY_HOUR, minute=0,
                id="evening_summary"
            )

            # Water reminders
            self._scheduler.add_job(
                self._water_reminder, "interval",
                hours=WATER_REMINDER_INTERVAL_HOURS,
                id="water_reminder"
            )

            # System health check every 10 minutes
            self._scheduler.add_job(
                self._health_check, "interval",
                minutes=10, id="health_check"
            )

            # Email check
            self._scheduler.add_job(
                self._check_emails, "interval",
                minutes=EMAIL_CHECK_INTERVAL_MINUTES,
                id="email_check"
            )

            self._scheduler.start()
            self._running = True
            logger.info("Proactive engine started with scheduled tasks")

        except Exception as e:
            logger.error(f"Proactive engine failed to start: {e}")

    def stop(self):
        """Stop the scheduler."""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Proactive engine stopped")

    def _announce(self, message: str):
        """Speak a proactive message."""
        logger.info(f"Proactive: {message}")
        if self._speak_callback:
            self._speak_callback(message)

    def _morning_briefing(self):
        """Morning briefing: weather + news + calendar."""
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        self._announce(f"{greeting}, {USER_TITLE}. Preparing your morning briefing.")

        # Trigger briefing through orchestrator if available
        if self.orchestrator:
            try:
                self.orchestrator.process_command("Give me my morning briefing with weather, news, and today's schedule")
            except Exception as e:
                logger.error(f"Morning briefing failed: {e}")

    def _evening_summary(self):
        """Evening summary at configured hour."""
        self._announce(
            f"{USER_TITLE}, here's your evening summary. "
            "I'll review today's activities and tomorrow's schedule."
        )
        if self.orchestrator:
            try:
                self.orchestrator.process_command("Give me an evening summary of today and tomorrow's schedule")
            except Exception as e:
                logger.error(f"Evening summary failed: {e}")

    def _water_reminder(self):
        """Remind user to hydrate."""
        hour = datetime.now().hour
        if 8 <= hour <= 22:  # Only during waking hours
            self._announce(f"{USER_TITLE}, a gentle reminder to stay hydrated. Drink some water.")

    def _health_check(self):
        """Monitor system health and alert on issues."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent
            if cpu > 90:
                self._announce(f"Warning, {USER_TITLE}. CPU usage is at {cpu}%. You may want to close some applications.")
            if mem > 90:
                self._announce(f"Warning, {USER_TITLE}. Memory usage is at {mem}%. System may become unstable.")
        except Exception:
            pass

    def _check_emails(self):
        """Check for new emails."""
        if self.orchestrator:
            try:
                # Silently check — only announce if there are new ones
                from tools.email_tool import EmailTool
                email_tool = EmailTool(self.memory)
                if email_tool._available:
                    result = email_tool.execute({"action": "read", "count": 1})
                    if "unread" in result.lower() and "no unread" not in result.lower():
                        self._announce(f"{USER_TITLE}, you have new emails.")
            except Exception:
                pass

    def add_timer(self, seconds: int, label: str = "Timer"):
        """Add a one-shot timer."""
        if self._scheduler:
            from datetime import timedelta
            run_time = datetime.now() + timedelta(seconds=seconds)
            self._scheduler.add_job(
                self._announce,
                "date", run_date=run_time,
                args=[f"{USER_TITLE}, your {label} is up."],
                id=f"timer_{label}_{seconds}"
            )
            return f"Timer set for {seconds} seconds, {USER_TITLE}."
        return "Scheduler not running."

    def get_status(self) -> dict:
        jobs = []
        if self._scheduler:
            for job in self._scheduler.get_jobs():
                jobs.append({"id": job.id, "next_run": str(job.next_run_time)})
        return {"running": self._running, "jobs": jobs}
