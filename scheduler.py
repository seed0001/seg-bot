from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config import SCHEDULE_HOUR, SCHEDULE_MINUTE


def _daily_run():
    from modules.github_analyzer import run_github_analysis
    print("[Scheduler] Running daily GitHub analysis...")
    run_github_analysis()
    print("[Scheduler] Done.")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _daily_run,
        CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE),
        id="daily_segment",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
