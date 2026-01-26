"""Scheduler for automated scraping tasks."""

import asyncio
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from .config import settings
from .database import db, ScrapeLog
from .scrapers import SCRAPERS, get_scraper


class ScrapeScheduler:
    """Scheduler for automated university scraping."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        notification_email: Optional[str] = None,
    ):
        """
        Initialize the scheduler.

        Args:
            smtp_host: SMTP server host for email notifications
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            notification_email: Email address to send notifications to
        """
        self.scheduler = AsyncIOScheduler()
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.notification_email = notification_email
        self._running = False

    def start(self) -> None:
        """Start the scheduler."""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown()
            self._running = False
            logger.info("Scheduler stopped")

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    def add_weekly_scrape(
        self,
        university: Optional[str] = None,
        day_of_week: str = "sun",
        hour: int = 2,
        minute: int = 0,
    ) -> str:
        """
        Schedule a weekly scraping job.

        Args:
            university: University code to scrape, or None for all
            day_of_week: Day of week (mon, tue, wed, thu, fri, sat, sun)
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)

        Returns:
            Job ID for the scheduled job
        """
        job_id = f"weekly_scrape_{university or 'all'}"

        trigger = CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
        )

        self.scheduler.add_job(
            self._run_scrape,
            trigger=trigger,
            id=job_id,
            args=[university],
            replace_existing=True,
            name=f"Weekly scrape: {university or 'all universities'}",
        )

        logger.info(f"Added weekly scrape job: {job_id} at {day_of_week} {hour:02d}:{minute:02d}")
        return job_id

    def add_daily_scrape(
        self,
        university: Optional[str] = None,
        hour: int = 3,
        minute: int = 0,
    ) -> str:
        """
        Schedule a daily scraping job.

        Args:
            university: University code to scrape, or None for all
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)

        Returns:
            Job ID for the scheduled job
        """
        job_id = f"daily_scrape_{university or 'all'}"

        trigger = CronTrigger(hour=hour, minute=minute)

        self.scheduler.add_job(
            self._run_scrape,
            trigger=trigger,
            id=job_id,
            args=[university],
            replace_existing=True,
            name=f"Daily scrape: {university or 'all universities'}",
        )

        logger.info(f"Added daily scrape job: {job_id} at {hour:02d}:{minute:02d}")
        return job_id

    def add_interval_scrape(
        self,
        university: Optional[str] = None,
        hours: int = 12,
    ) -> str:
        """
        Schedule scraping at regular intervals.

        Args:
            university: University code to scrape, or None for all
            hours: Interval in hours

        Returns:
            Job ID for the scheduled job
        """
        job_id = f"interval_scrape_{university or 'all'}"

        trigger = IntervalTrigger(hours=hours)

        self.scheduler.add_job(
            self._run_scrape,
            trigger=trigger,
            id=job_id,
            args=[university],
            replace_existing=True,
            name=f"Interval scrape ({hours}h): {university or 'all universities'}",
        )

        logger.info(f"Added interval scrape job: {job_id} every {hours} hours")
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job.

        Args:
            job_id: The job ID to remove

        Returns:
            True if job was removed, False if not found
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
            return True
        except Exception:
            logger.warning(f"Job not found: {job_id}")
            return False

    def list_jobs(self) -> list[dict]:
        """
        List all scheduled jobs.

        Returns:
            List of job information dictionaries
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            # APScheduler 4.x uses different attribute access
            next_run = None
            if hasattr(job, 'next_run_time') and job.next_run_time:
                next_run = job.next_run_time.isoformat()
            elif hasattr(job, 'next_fire_time') and job.next_fire_time:
                next_run = job.next_fire_time.isoformat()

            jobs.append({
                "id": job.id,
                "name": getattr(job, 'name', job.id),
                "next_run": next_run,
                "trigger": str(job.trigger),
            })
        return jobs

    async def _run_scrape(self, university: Optional[str] = None) -> dict:
        """
        Run a scraping job.

        Args:
            university: University code to scrape, or None for all

        Returns:
            Results dictionary with counts and status
        """
        universities = [university] if university else list(SCRAPERS.keys())
        results = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "universities": {},
            "total_new": 0,
            "total_updated": 0,
            "errors": [],
        }

        for uni in universities:
            uni_result = await self._scrape_university(uni)
            results["universities"][uni] = uni_result

            if uni_result.get("error"):
                results["errors"].append(f"{uni}: {uni_result['error']}")
            else:
                results["total_new"] += uni_result.get("new", 0)
                results["total_updated"] += uni_result.get("updated", 0)

        results["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Send notification if there were errors
        if results["errors"] and self.notification_email:
            await self._send_failure_notification(results)

        return results

    async def _scrape_university(self, university: str) -> dict:
        """
        Scrape a single university with logging.

        Args:
            university: University code

        Returns:
            Result dictionary
        """
        log = db.create_scrape_log(university, status="running")
        result = {"university": university}

        try:
            scraper = get_scraper(university)
            technologies = []

            async for tech in scraper.scrape():
                technologies.append(tech)

            new_count, updated_count = db.bulk_insert_technologies(technologies)

            result["new"] = new_count
            result["updated"] = updated_count
            result["total"] = len(technologies)
            result["status"] = "success"

            db.update_scrape_log(
                log.id,
                status="completed",
                technologies_found=len(technologies),
                technologies_new=new_count,
                technologies_updated=updated_count,
            )

            logger.info(f"Scrape completed for {university}: {new_count} new, {updated_count} updated")

        except Exception as e:
            result["error"] = str(e)
            result["status"] = "failed"

            db.update_scrape_log(
                log.id,
                status="failed",
                error_message=str(e),
            )

            logger.error(f"Scrape failed for {university}: {e}")

        return result

    async def _send_failure_notification(self, results: dict) -> None:
        """
        Send email notification about scrape failures.

        Args:
            results: Results dictionary with errors
        """
        if not all([self.smtp_host, self.smtp_user, self.smtp_password, self.notification_email]):
            logger.warning("Email notification not configured, skipping")
            return

        subject = f"[Tech Scraper] Scrape failures - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

        body = f"""Tech Transfer Scraper - Failure Report

Started: {results['started_at']}
Completed: {results['completed_at']}

Errors:
"""
        for error in results["errors"]:
            body += f"  - {error}\n"

        body += f"""
Summary:
  Total new technologies: {results['total_new']}
  Total updated: {results['total_updated']}
"""

        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = self.notification_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, self.notification_email, msg.as_string())

            logger.info(f"Failure notification sent to {self.notification_email}")

        except Exception as e:
            logger.error(f"Failed to send notification email: {e}")

    async def run_now(self, university: Optional[str] = None) -> dict:
        """
        Run a scrape immediately (not scheduled).

        Args:
            university: University code to scrape, or None for all

        Returns:
            Results dictionary
        """
        return await self._run_scrape(university)


def create_scheduler(
    smtp_host: Optional[str] = None,
    smtp_port: int = 587,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
    notification_email: Optional[str] = None,
) -> ScrapeScheduler:
    """
    Factory function to create a configured scheduler.

    Environment variables are used if parameters are not provided:
    - SMTP_HOST
    - SMTP_PORT
    - SMTP_USER
    - SMTP_PASSWORD
    - NOTIFICATION_EMAIL
    """
    import os

    return ScrapeScheduler(
        smtp_host=smtp_host or os.getenv("SMTP_HOST"),
        smtp_port=int(os.getenv("SMTP_PORT", smtp_port)),
        smtp_user=smtp_user or os.getenv("SMTP_USER"),
        smtp_password=smtp_password or os.getenv("SMTP_PASSWORD"),
        notification_email=notification_email or os.getenv("NOTIFICATION_EMAIL"),
    )


# Global scheduler instance
scheduler = create_scheduler()
