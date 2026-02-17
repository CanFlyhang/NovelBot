import enum
from datetime import datetime, date

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Float,
    Boolean,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from .db import Base


class NovelStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    WRITING = "WRITING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class ChapterStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    WRITING = "WRITING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class StoryFactImportance(str, enum.Enum):
    CRITICAL = "CRITICAL"
    NORMAL = "NORMAL"


class Novel(Base):
    __tablename__ = "novels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    genre = Column(String(64), nullable=False, default="未知")
    description = Column(Text, nullable=True)

    target_chapter_count = Column(Integer, nullable=False, default=10)
    current_chapter_index = Column(Integer, nullable=False, default=0)

    status = Column(
        Enum(NovelStatus),
        nullable=False,
        default=NovelStatus.PLANNED,
    )

    planned_date = Column(Date, nullable=True, index=True)

    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    chapters = relationship(
        "Chapter",
        back_populates="novel",
        cascade="all, delete-orphan",
        order_by="Chapter.index",
    )
    characters = relationship(
        "Character",
        back_populates="novel",
        cascade="all, delete-orphan",
    )
    plot_nodes = relationship(
        "PlotNode",
        back_populates="novel",
        cascade="all, delete-orphan",
        order_by="PlotNode.index",
    )
    logs = relationship(
        "CreationLog",
        back_populates="novel",
        cascade="all, delete-orphan",
        order_by="CreationLog.created_at",
    )
    facts = relationship(
        "StoryFact",
        back_populates="novel",
        cascade="all, delete-orphan",
        order_by="StoryFact.chapter_index",
    )


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (
        UniqueConstraint("novel_id", "index", name="uix_novel_chapter_index"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(
        Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False
    )

    index = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    outline = Column(Text, nullable=True)
    content = Column(Text, nullable=True)

    word_count = Column(Integer, nullable=False, default=0)

    status = Column(
        Enum(ChapterStatus),
        nullable=False,
        default=ChapterStatus.PLANNED,
    )

    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    novel = relationship("Novel", back_populates="chapters")
    plot_nodes = relationship(
        "PlotNode",
        back_populates="chapter",
        cascade="all, delete-orphan",
    )
    logs = relationship(
        "CreationLog",
        back_populates="chapter",
        cascade="all, delete-orphan",
    )


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(
        Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False
    )

    name = Column(String(128), nullable=False)
    role = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=True)

    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    novel = relationship("Novel", back_populates="characters")

    __table_args__ = (
        UniqueConstraint("novel_id", "name", name="uix_character_name"),
    )


class PlotNode(Base):
    __tablename__ = "plot_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(
        Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id = Column(
        Integer, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True
    )

    index = Column(Integer, nullable=False)
    summary = Column(Text, nullable=False)
    node_type = Column(String(64), nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=True)

    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    novel = relationship("Novel", back_populates="plot_nodes")
    chapter = relationship("Chapter", back_populates="plot_nodes")

    __table_args__ = (
        Index("idx_plot_nodes_novel_index", "novel_id", "index"),
    )


class CreationLog(Base):
    __tablename__ = "creation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(
        Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id = Column(
        Integer, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True
    )

    level = Column(String(32), nullable=False, default="INFO")
    message = Column(Text, nullable=False)
    api_call_id = Column(String(128), nullable=True)
    latency_ms = Column(Float, nullable=True)

    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    novel = relationship("Novel", back_populates="logs")
    chapter = relationship("Chapter", back_populates="logs")

    __table_args__ = (
        Index("idx_creation_logs_novel_time", "novel_id", "created_at"),
    )


class DailyPlan(Base):
    __tablename__ = "daily_plans"
    __table_args__ = (
        UniqueConstraint("date", name="uix_daily_plan_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)

    target_novels = Column(Integer, nullable=False, default=0)
    target_words = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )


class SystemState(Base):
    __tablename__ = "system_state"
    __table_args__ = (
        UniqueConstraint("key", name="uix_system_state_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), nullable=False)
    value = Column(String(255), nullable=False)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class GenerationMetric(Base):
    __tablename__ = "generation_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    novel_count = Column(Integer, nullable=False, default=0)
    chapter_count = Column(Integer, nullable=False, default=0)
    word_count = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )


class StoryFact(Base):
    __tablename__ = "story_facts"
    __table_args__ = (
        Index("idx_story_facts_novel_chapter", "novel_id", "chapter_index"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(
        Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id = Column(
        Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )

    chapter_index = Column(Integer, nullable=False)
    category = Column(String(64), nullable=True)
    content = Column(Text, nullable=False)
    importance = Column(
        Enum(StoryFactImportance),
        nullable=False,
        default=StoryFactImportance.NORMAL,
    )

    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    novel = relationship("Novel", back_populates="facts")

