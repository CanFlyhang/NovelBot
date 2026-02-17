import threading
import time
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .models import Novel, NovelStatus, SystemState
from .services.novel_service import generate_next_chapter_for_novel


class Scheduler:
    """
    简单的后台调度器，负责每日规划与自动章节生成。
    """

    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()
        self._last_heartbeat: Optional[datetime] = None

    def start(self) -> None:
        """
        启动调度线程，如已启动则忽略。
        """

        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._pause_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop, name="NovelBotScheduler", daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        """
        请求停止调度线程。
        """

        self._stop_event.set()

    def pause(self) -> None:
        """
        暂停调度执行，但不退出线程。
        """

        self._pause_event.set()

    def resume(self) -> None:
        """
        恢复调度执行。
        """

        self._pause_event.clear()

    def is_running(self) -> bool:
        """
        返回调度线程是否处于运行状态。
        """

        return self._thread is not None and self._thread.is_alive()

    def is_paused(self) -> bool:
        """
        返回调度器当前是否处于暂停状态。
        """

        return self._pause_event.is_set()

    def last_heartbeat(self) -> Optional[datetime]:
        """
        获取调度循环上次心跳时间。
        """

        return self._last_heartbeat

    def _run_loop(self) -> None:
        """
        调度主循环，周期性执行规划与创作任务。
        """

        while not self._stop_event.is_set():
            self._last_heartbeat = datetime.utcnow()
            if not self._pause_event.is_set():
                self._run_tick()
            time.sleep(max(settings.scheduler_tick_seconds, 5))

    def _run_tick(self) -> None:
        """
        单次调度执行入口，用于已有小说的章节生成。
        """

        db: Session = SessionLocal()
        try:
            today = date.today()

            novel: Optional[Novel] = (
                db.query(Novel)
                .filter(
                    Novel.status.in_(
                        [NovelStatus.PLANNED, NovelStatus.WRITING]
                    ),
                    Novel.planned_date <= today,
                )
                .order_by(Novel.planned_date.asc(), Novel.id.asc())
                .first()
            )

            if novel:
                generate_next_chapter_for_novel(db, novel.id)

            self._save_state(db)
        finally:
            db.close()

    def _save_state(self, db: Session) -> None:
        """
        将当前调度器运行状态持久化到数据库。
        """

        key = "scheduler_status"
        value = "paused" if self._pause_event.is_set() else "running"
        state: Optional[SystemState] = (
            db.query(SystemState).filter(SystemState.key == key).one_or_none()
        )
        if not state:
            state = SystemState(key=key, value=value)
            db.add(state)
        else:
            state.value = value
        db.commit()


scheduler = Scheduler()
