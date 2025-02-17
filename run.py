import logging
from app import create_app
from app.services.scheduler import initialize_scheduler

app = create_app()
scheduler = initialize_scheduler(app)

if __name__ == "__main__":
    logging.info("Flask app started")
    try:
        app.run(host="0.0.0.0", port=8000)
    finally:
        scheduler.shutdown()
