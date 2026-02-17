from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel

from .models import NovelStatus, ChapterStatus


class CharacterBase(BaseModel):
    name: str
    role: Optional[str] = None
    description: Optional[str] = None
    extra_metadata: Optional[dict] = None


class CharacterCreate(CharacterBase):
    pass


class Character(CharacterBase):
    id: int

    class Config:
        orm_mode = True


class PlotNodeBase(BaseModel):
    index: int
    summary: str
    node_type: Optional[str] = None
    extra_metadata: Optional[dict] = None


class PlotNode(PlotNodeBase):
    id: int

    class Config:
        orm_mode = True


class ChapterBase(BaseModel):
    index: int
    title: str
    outline: Optional[str] = None


class ChapterCreate(ChapterBase):
    pass


class Chapter(ChapterBase):
    id: int
    status: ChapterStatus
    word_count: int
    content: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class NovelBase(BaseModel):
    title: str
    genre: str
    description: Optional[str] = None
    target_chapter_count: int


class NovelCreate(NovelBase):
    planned_date: Optional[date] = None


class Novel(NovelBase):
    id: int
    status: NovelStatus
    current_chapter_index: int
    planned_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    chapters: List[Chapter] = []
    characters: List[Character] = []

    class Config:
        orm_mode = True


class CreationLog(BaseModel):
    id: int
    novel_id: int
    chapter_id: Optional[int] = None
    level: str
    message: str
    api_call_id: Optional[str] = None
    latency_ms: Optional[float] = None
    created_at: datetime

    class Config:
        orm_mode = True


class DailyPlan(BaseModel):
    id: int
    date: date
    target_novels: int
    target_words: int
    created_at: datetime

    class Config:
        orm_mode = True


class GenerationMetric(BaseModel):
    id: int
    date: date
    novel_count: int
    chapter_count: int
    word_count: int
    created_at: datetime

    class Config:
        orm_mode = True


class NovelProgress(BaseModel):
    novel_id: int
    title: str
    genre: str
    status: NovelStatus
    chapter_completed: int
    chapter_total: int
    words: int
    progress_ratio: float


class DailyProgress(BaseModel):
    date: date
    novel_count: int
    chapter_count: int
    word_count: int


class DashboardSummary(BaseModel):
    novels: List[NovelProgress]
    daily_stats: List[DailyProgress]
    total_novels: int
    total_chapters: int
    total_words: int


class ControlCommand(BaseModel):
    action: str


class ControlState(BaseModel):
    is_running: bool
    is_paused: bool
    last_heartbeat: Optional[datetime] = None


class ConfigUpdate(BaseModel):
    daily_target_novels: Optional[int] = None
    default_chapters_per_novel: Optional[int] = None
    max_concurrent_api_requests: Optional[int] = None
    max_requests_per_minute: Optional[int] = None
    preferred_genres: Optional[List[str]] = None
