from apscheduler.schedulers.background import BackgroundScheduler
from .email_service import EmailMonitor
import os
from dotenv import load_dotenv

load_dotenv()


def initialize_scheduler(app):
    with app.app_context():
        scheduler = BackgroundScheduler()
        email_monitor = EmailMonitor(
            email_address=os.getenv("EMAIL_ADDRESS"),
            password=os.getenv("EMAIL_PASSWORD"),
        )

        # Add job to check emails periodically
        scheduler.add_job(
            email_monitor.process_emails,
            "interval",
            seconds=int(os.getenv("EMAIL_CHECK_INTERVAL", 300)),
            id="email_monitor",
        )

        scheduler.start()
        return scheduler
