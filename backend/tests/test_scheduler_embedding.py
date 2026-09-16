"""RUN_SCHEDULER_IN_API lets a single free-tier web service run the scheduler in-process
(no separate paid worker service) - the lifespan must start and cleanly stop it."""
import app.main as main_module
from app.config import settings


async def test_scheduler_not_started_by_default(monkeypatch):
    monkeypatch.setattr(settings, "RUN_SCHEDULER_IN_API", False)
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "BOT_TOKEN", "")

    async with main_module.lifespan(main_module.app):
        pass  # no assertion needed beyond "this doesn't raise or hang"


async def test_scheduler_starts_and_stops_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "RUN_SCHEDULER_IN_API", True)
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "BOT_TOKEN", "")

    from app.workers.scheduler import build_scheduler

    started_schedulers = []
    original_build = build_scheduler

    def spy_build_scheduler():
        scheduler = original_build()
        started_schedulers.append(scheduler)
        return scheduler

    monkeypatch.setattr("app.workers.scheduler.build_scheduler", spy_build_scheduler)

    shutdown_calls = []
    async with main_module.lifespan(main_module.app):
        assert len(started_schedulers) == 1
        scheduler = started_schedulers[0]
        assert scheduler.running
        job_ids = {job.id for job in scheduler.get_jobs()}
        assert job_ids == {
            "digest_tick", "expiry_reminders", "expire_jobs",
            "expire_payment_links", "broadcast_runner", "cleanup_retention",
        }
        original_shutdown = scheduler.shutdown
        monkeypatch.setattr(
            scheduler, "shutdown", lambda *a, **kw: (shutdown_calls.append(1), original_shutdown(*a, **kw))
        )

    assert shutdown_calls == [1]  # lifespan teardown actually called shutdown() on exit
