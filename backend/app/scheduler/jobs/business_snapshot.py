import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.business_snapshot import generate_snapshot
from app.db.tools.snapshot import get_active_business_ids
from app.scheduler.worker import BaseWorker
from app.ws.socketio_server import sio

logger = logging.getLogger(__name__)

WORKER_NAME = "business_snapshot_worker"


class BusinessSnapshotWorker(BaseWorker):
    
    def __init__(self):
        super().__init__(name=WORKER_NAME)

    async def process(self, context: dict) -> None:
        business_ids = get_active_business_ids()

        logger.info(f"Snapshot job started: businesses={len(business_ids)}")

        for business_id in business_ids:
            try:
                await generate_snapshot(business_id)
                await sio.emit("snapshot_updated", {"business_id": business_id}, room=business_id)
            except Exception as e:
                logger.error(f"Snapshot failed for {business_id}: {e}", exc_info=True)

        logger.info(f"Snapshot job completed")

_worker = BusinessSnapshotWorker()


async def _daily_snapshot() -> None:
    await _worker.run(context={})


def register_snapshot_jobs(scheduler: AsyncIOScheduler) -> None:
    """Register snapshot job — runs every 3 minutes."""
    scheduler.add_job(
        _daily_snapshot, "interval", minutes=3,
        #  hours=7,
        id="snapshot_refresh", max_instances=1, replace_existing=True,
    )
