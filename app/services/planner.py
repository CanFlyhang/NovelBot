from datetime import date, datetime
from random import choice
from typing import List

from sqlalchemy.orm import Session

from ..config import settings
from ..models import DailyPlan, Novel, NovelStatus, Chapter, ChapterStatus


def ensure_daily_plan(db: Session, target_date: date) -> DailyPlan:
    """
    确保指定日期存在日计划记录，如不存在则根据配置创建。
    """

    plan = (
        db.query(DailyPlan)
        .filter(DailyPlan.date == target_date)
        .one_or_none()
    )
    if plan:
        return plan

    plan = DailyPlan(
        date=target_date,
        target_novels=settings.daily_target_novels,
        target_words=settings.daily_target_novels
        * settings.default_chapters_per_novel
        * 2500,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _pick_genre() -> str:
    """
    随机选择一个配置中的默认小说类型。
    """

    genres: List[str] = settings.preferred_genres or ["玄幻"]
    return choice(genres)


def plan_novels_for_day(db: Session, target_date: date) -> List[Novel]:
    """
    为指定日期规划需要创作的多本小说及其章节框架。
    """

    plan = ensure_daily_plan(db, target_date)

    existing_count = (
        db.query(Novel)
        .filter(Novel.planned_date == target_date)
        .count()
    )
    to_create = max(plan.target_novels - existing_count, 0)
    novels: List[Novel] = []

    for i in range(to_create):
        genre = _pick_genre()
        novel = Novel(
            title=f"{target_date.isoformat()} 第{i + 1}本{genre}小说",
            genre=genre,
            description=f"{genre}题材自动规划小说，由系统在 {target_date.isoformat()} 自动创建。",
            target_chapter_count=settings.default_chapters_per_novel,
            status=NovelStatus.PLANNED,
            planned_date=target_date,
        )
        db.add(novel)
        db.flush()

        for idx in range(1, settings.default_chapters_per_novel + 1):
            chapter = Chapter(
                novel_id=novel.id,
                index=idx,
                title=f"第{idx}章",
                status=ChapterStatus.PLANNED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(chapter)

        novels.append(novel)

    if novels:
        db.commit()
        for novel in novels:
            db.refresh(novel)

    return novels
