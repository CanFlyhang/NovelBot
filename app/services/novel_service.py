from datetime import date, datetime
from typing import List, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    Chapter,
    ChapterStatus,
    CreationLog,
    GenerationMetric,
    Novel,
    NovelStatus,
    PlotNode,
    Character,
    StoryFact,
    StoryFactImportance,
)
from ..schemas import DashboardSummary, DailyProgress, NovelProgress
from .deepseek_client import client as deepseek_client


def log_creation_event(
    db: Session,
    novel_id: int,
    chapter_id: int | None,
    level: str,
    message: str,
    api_meta: dict | None = None,
) -> None:
    """
    写入一条创作过程日志到数据库。
    """

    latency_ms = None
    request_id = None
    if api_meta:
        latency_ms = api_meta.get("latency_ms")
        request_id = api_meta.get("request_id")

    log = CreationLog(
        novel_id=novel_id,
        chapter_id=chapter_id,
        level=level,
        message=message,
        api_call_id=request_id,
        latency_ms=latency_ms,
        created_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()


def _build_novel_context(
    db: Session,
    novel: Novel,
    target_chapter_index: int,
) -> str:
    """
    构造用于 RAG 的小说上下文字符串，包含最近章节与主要角色信息。
    """

    recent_chapters: List[Chapter] = (
        db.query(Chapter)
        .filter(
            Chapter.novel_id == novel.id,
            Chapter.status == ChapterStatus.COMPLETED,
            Chapter.index < target_chapter_index,
        )
        .order_by(Chapter.index.asc())
        .all()
    )

    characters: List[Character] = (
        db.query(Character)
        .filter(Character.novel_id == novel.id)
        .order_by(Character.id.asc())
        .all()
    )

    plot_nodes: List[PlotNode] = (
        db.query(PlotNode)
        .filter(PlotNode.novel_id == novel.id)
        .order_by(PlotNode.index.asc())
        .all()
    )

    facts: List[StoryFact] = (
        db.query(StoryFact)
        .filter(
            StoryFact.novel_id == novel.id,
            StoryFact.chapter_index < target_chapter_index,
        )
        .order_by(StoryFact.chapter_index.asc(), StoryFact.id.asc())
        .all()
    )

    lines: List[str] = []
    lines.append(f"小说标题：{novel.title}")
    lines.append(f"类型：{novel.genre}")
    if novel.description:
        lines.append(f"整体设定：{novel.description}")

    if characters:
        lines.append("\n主要人物：")
        for c in characters:
            desc = c.description or ""
            lines.append(f"- {c.name}（{c.role or '未知身份'}）：{desc}")

    if plot_nodes:
        lines.append("\n关键情节节点：")
        for node in plot_nodes[-10:]:
            lines.append(f"- 第{node.index}节点：{node.summary}")

    if facts:
        critical = [
            f for f in facts if f.importance == StoryFactImportance.CRITICAL
        ]
        normal = [
            f for f in facts if f.importance == StoryFactImportance.NORMAL
        ]

        critical = critical[-60:]
        normal = normal[-80:]

        if critical:
            lines.append("\n已确立且不能自相矛盾的关键事实：")
            for f in critical:
                lines.append(f"- " + f.content)

        if normal:
            lines.append("\n补充世界观事实：")
            for f in normal:
                lines.append(f"- " + f.content)

    if recent_chapters:
        lines.append("\n前情回顾（按章节顺序）：")
        latest = recent_chapters[-1]
        for ch in recent_chapters:
            content = (ch.content or "").strip()
            outline = (ch.outline or "").strip()
            if not outline and content:
                outline = content[:60]

            if not content:
                snippet = ""
            elif ch.id == latest.id:
                if len(content) > 500:
                    snippet = content[-500:]
                else:
                    snippet = content
            else:
                if len(content) <= 800:
                    snippet = content
                else:
                    snippet = content[:400] + "\n……\n" + content[-300:]

            if outline:
                lines.append(f"第{ch.index}章《{ch.title}》小结：{outline}")
            else:
                lines.append(f"第{ch.index}章《{ch.title}》")
            if snippet:
                lines.append("关键片段：")
                lines.append(snippet)

    return "\n".join(lines)


def _parse_generation_output(text: str) -> Tuple[str, str]:
    """
    从模型输出中解析出章节小结与正文内容。
    """

    if not text:
        return "", ""

    lines = text.split("\n")
    first_line = lines[0].strip()
    if first_line.startswith("本章小结"):
        if ":" in first_line:
            summary = first_line.split(":", 1)[1].strip()
        elif "：" in first_line:
            summary = first_line.split("：", 1)[1].strip()
        else:
            summary = first_line
    else:
        summary = first_line

    body = "\n".join(lines[1:]).strip()
    return summary, body


def _generate_chapter_title(index: int, summary: str) -> str:
    """
    根据章节小结自动生成章节标题。
    """

    clean = summary.strip().replace("\n", "")
    if clean.startswith("本章小结："):
        clean = clean[len("本章小结：") :].strip()
    if not clean:
        return f"第{index}章"
    if len(clean) > 16:
        clean = clean[:16]
    return clean


def _parse_facts_from_text(text: str) -> List[tuple[str, StoryFactImportance]]:
    """
    从模型返回的文本中解析剧情事实列表与重要性标记。
    """

    results: List[tuple[str, StoryFactImportance]] = []
    if not text:
        return results

    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line[0] in "-•*":
            line = line[1:].strip()
        prefix = ""
        if line.startswith("[重要]"):
            prefix = "[重要]"
            line = line[len("[重要]") :].strip()
            importance = StoryFactImportance.CRITICAL
        elif line.startswith("[一般]"):
            prefix = "[一般]"
            line = line[len("[一般]") :].strip()
            importance = StoryFactImportance.NORMAL
        else:
            importance = StoryFactImportance.NORMAL
        if not line:
            continue
        if len(line) > 120:
            line = line[:120]
        results.append((line, importance))

    return results


def _extract_story_facts(
    db: Session,
    novel: Novel,
    chapter: Chapter,
    summary: str,
    body: str,
) -> None:
    """
    调用模型从章节内容中抽取关键剧情事实并写入数据库。
    """

    if not body:
        return

    system_prompt = (
        "你是一名严谨的小说策划编辑，负责维护长篇小说的世界观与设定一致性。"
        "请从给定章节的小结和正文中提取对后续剧情至关重要的“客观事实”。"
    )
    user_prompt = (
        "下面是某一章的小结和正文内容，请提取不超过20条剧情设定事实：\n\n"
        f"【本章小结】\n{summary}\n\n"
        "【本章正文】\n"
        f"{body}\n\n"
        "提取要求：\n"
        "1. 每条事实必须是可以被后文反复引用的客观设定，例如人物的家庭关系、婚姻状态、生死、重大疾病、破产与否等。\n"
        "2. 不要主观感受、比喻和修辞，只要“发生了什么”或“是什么样的人”。\n"
        "3. 对于一旦写出就绝不能自相矛盾的设定（如某人已去世、公司已经破产等），在行首加上“[重要]”。\n"
        "4. 普通事实在行首可加“[一般]”或不加标签。\n"
        "5. 每行一个事实，以“- ”开头，不要编号，不要任何额外解释或总结。\n"
        "仅输出事实列表本身。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        text, _ = deepseek_client.generate_text(
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )
    except Exception:
        return

    parsed = _parse_facts_from_text(text)
    if not parsed:
        return

    for content, importance in parsed:
        fact = StoryFact(
            novel_id=novel.id,
            chapter_id=chapter.id,
            chapter_index=chapter.index,
            category=None,
            content=content,
            importance=importance,
            created_at=datetime.utcnow(),
        )
        db.add(fact)


def _build_fact_block_for_audit(
    db: Session,
    novel: Novel,
    target_chapter_index: int,
) -> str:
    """
    构造用于一致性审核的已知关键事实文本块。
    """

    facts: List[StoryFact] = (
        db.query(StoryFact)
        .filter(
            StoryFact.novel_id == novel.id,
            StoryFact.chapter_index < target_chapter_index,
        )
        .order_by(StoryFact.chapter_index.asc(), StoryFact.id.asc())
        .all()
    )

    if not facts:
        return ""

    critical = [
        f for f in facts if f.importance == StoryFactImportance.CRITICAL
    ]
    normal = [
        f for f in facts if f.importance == StoryFactImportance.NORMAL
    ]

    critical = critical[-50:]
    normal = normal[-50:]

    lines: List[str] = []
    if critical:
        lines.append("【关键事实】以下设定一旦写出，后文不得自相矛盾：")
        for f in critical:
            lines.append(f"- {f.content}")
    if normal:
        lines.append("\n【补充事实】以下为背景与世界观设定：")
        for f in normal:
            lines.append(f"- {f.content}")

    return "\n".join(lines)


def _audit_chapter_consistency(
    db: Session,
    novel: Novel,
    chapter_index: int,
    summary: str,
    body: str,
) -> tuple[bool, List[str]]:
    """
    审核章节内容是否与已记录的关键事实存在明显矛盾。
    """

    fact_block = _build_fact_block_for_audit(db, novel, chapter_index)
    if not fact_block:
        return True, []
    if not body:
        return True, []

    system_prompt = (
        "你是一名严谨的小说审读编辑，负责检查长篇小说是否与既有设定自相矛盾。"
        "你需要基于给定的事实列表，审读当前章节的小结与正文。"
    )
    user_prompt = (
        "下面是这本小说当前已经确立的事实，以及本章的小结和正文。\n\n"
        f"{fact_block}\n\n"
        f"【本章小结】\n{summary}\n\n"
        "【本章正文】\n"
        f"{body}\n\n"
        "请你逐条检查本章内容是否与关键事实存在明显冲突：\n"
        "1. 如果没有任何明显冲突，只输出“OK”。\n"
        "2. 如果存在冲突，请每行输出一个问题点，以“- ”开头，格式为：\n"
        "   “- 冲突描述；相关事实：XXX”。\n"
        "不要输出其他解释或总结。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        text, _ = deepseek_client.generate_text(
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )
    except Exception:
        return True, []

    if not text:
        return True, []

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    issue_lines: List[str] = []
    for line in lines:
        if line.startswith(("- ", "• ", "* ")):
            content = line[1:].strip()
            if content:
                issue_lines.append(content)

    if not issue_lines:
        upper_text = text.strip().upper()
        if upper_text in {"OK", "OK.", "OK。"}:
            return True, []
        if "无明显冲突" in text or "没有明显冲突" in text:
            return True, []
        return True, []

    return False, issue_lines


def _count_words(text: str) -> int:
    """
    粗略统计文本字数，用于字数监控与统计。
    """

    if not text:
        return 0
    normalized = text.replace(" ", "").replace("\n", "")
    return len(normalized)


def generate_next_chapter_for_novel(db: Session, novel_id: int) -> bool:
    """
    为指定小说生成下一章内容，并更新进度和统计信息。
    """

    novel: Novel | None = db.query(Novel).get(novel_id)
    if not novel:
        return False

    next_chapter: Chapter | None = (
        db.query(Chapter)
        .filter(
            Chapter.novel_id == novel.id,
            Chapter.index == novel.current_chapter_index + 1,
        )
        .one_or_none()
    )
    if not next_chapter:
        novel.status = NovelStatus.COMPLETED
        db.commit()
        return False

    try:
        context = _build_novel_context(db, novel, next_chapter.index)
        is_last_chapter = next_chapter.index >= novel.target_chapter_count

        system_prompt = (
            "你是一名专业网络小说作家，擅长用中文创作长篇连载小说。"
            "必须严格保持人物设定和既有情节的连续性，避免与之前内容矛盾或重复编造新的版本，"
            "对于前文已经明确揭示过的设定和真相，只能在此基础上延展或回顾，"
            "语言流畅，情绪饱满，节奏自然推进。"
        )
        if is_last_chapter:
            base_user_prompt = (
                f"下面是这本小说当前已知的信息与上下文：\n\n{context}\n\n"
                f"现在请你在充分承接上一章剧情的基础上，创作本书的最终结局章节（第{next_chapter.index}章），"
                "这是整本小说的收官之章，必须完成主线矛盾的解决与人物命运的交代。\n"
                "创作要求：\n"
                "1. 彻底解决贯穿全书的主要冲突与悬念，不要再引入新的核心矛盾；\n"
                "2. 清晰交代男女主以及关键配角的最终去向和情感走向；\n"
                "3. 对前文重要事件做适度呼应和总结，有情感上的回望与升华；\n"
                "4. 可以保留少量开放式伏笔，但不能留下影响阅读体验的巨大坑。\n"
                "输出格式要求：\n"
                "1. 第一行以“本章小结：”开头，给出不超过120字的结局摘要，明确说明本书已经完结；\n"
                "2. 第二行开始为空一行；\n"
                "3. 之后输出本章正文，分段自然，有人物对话和场景描写，整体有明显的终章收束感；\n"
                "4. 严格使用中文创作，不要输出任何额外解释。"
            )
        else:
            base_user_prompt = (
                f"下面是这本小说当前已知的信息与上下文：\n\n{context}\n\n"
                f"现在请你在充分承接上一章剧情的基础上，创作第{next_chapter.index}章的完整内容，"
                "要求让情节从上一章自然过渡，人物行为与心态前后一致。\n"
                "输出格式要求：\n"
                "1. 第一行以“本章小结：”开头，给出不超过100字的剧情摘要；\n"
                "2. 第二行开始为空一行；\n"
                "3. 之后输出本章正文，分段自然，有人物对话和场景描写；\n"
                "4. 严格使用中文创作，不要输出任何额外解释。"
            )

        def _call_model(user_prompt: str) -> tuple[str, str, int, dict]:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            text, meta = deepseek_client.generate_text(
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
            )
            summary_inner, body_inner = _parse_generation_output(text)
            word_count_inner = _count_words(body_inner)
            return summary_inner, body_inner, word_count_inner, meta

        summary, body, word_count, meta = _call_model(base_user_prompt)

        ok, issues = _audit_chapter_consistency(
            db=db,
            novel=novel,
            chapter_index=next_chapter.index,
            summary=summary,
            body=body,
        )

        if not ok and issues:
            avoid_block = "\n".join(f"- {item}" for item in issues)
            retry_prompt = (
                base_user_prompt
                + "\n\n上一次生成的版本与已有关键事实存在如下冲突，请在重新创作本章时严格避免出现这些问题：\n"
                + avoid_block
                + "\n请重新输出符合要求的本章小结和正文。"
            )
            summary, body, word_count, meta = _call_model(retry_prompt)

        next_chapter.title = _generate_chapter_title(
            next_chapter.index,
            summary,
        )
        next_chapter.outline = summary
        next_chapter.content = body
        next_chapter.word_count = word_count
        next_chapter.status = ChapterStatus.COMPLETED
        next_chapter.updated_at = datetime.utcnow()

        novel.current_chapter_index = next_chapter.index
        novel.status = (
            NovelStatus.COMPLETED
            if novel.current_chapter_index >= novel.target_chapter_count
            else NovelStatus.WRITING
        )

        today = date.today()
        metric: GenerationMetric | None = (
            db.query(GenerationMetric)
            .filter(GenerationMetric.date == today)
            .one_or_none()
        )
        if not metric:
            metric = GenerationMetric(
                date=today,
                novel_count=0,
                chapter_count=0,
                word_count=0,
                created_at=datetime.utcnow(),
            )
            db.add(metric)

        metric.chapter_count += 1
        metric.word_count += word_count
        if novel.current_chapter_index == 1:
            metric.novel_count += 1

        _extract_story_facts(
            db=db,
            novel=novel,
            chapter=next_chapter,
            summary=summary,
            body=body,
        )

        db.commit()

        log_creation_event(
            db=db,
            novel_id=novel.id,
            chapter_id=next_chapter.id,
            level="INFO",
            message=f"成功生成第{next_chapter.index}章，字数约为 {word_count}",
            api_meta=meta,
        )

        return True
    except Exception as exc:
        log_creation_event(
            db=db,
            novel_id=novel.id,
            chapter_id=next_chapter.id if next_chapter else None,
            level="ERROR",
            message=f"生成章节失败：{exc}",
            api_meta=None,
        )
        novel.status = NovelStatus.ERROR
        db.commit()
        return False


def get_dashboard_summary(db: Session) -> DashboardSummary:
    """
    汇总仪表盘所需统计信息，用于前端数据可视化。
    """

    novels: List[Novel] = (
        db.query(Novel)
        .order_by(Novel.created_at.desc())
        .limit(100)
        .all()
    )

    novel_progress: List[NovelProgress] = []

    for novel in novels:
        total_chapters = novel.target_chapter_count
        completed_chapters = (
            db.query(func.count(Chapter.id))
            .filter(
                Chapter.novel_id == novel.id,
                Chapter.status == ChapterStatus.COMPLETED,
            )
            .scalar()
            or 0
        )
        total_words = (
            db.query(func.coalesce(func.sum(Chapter.word_count), 0))
            .filter(Chapter.novel_id == novel.id)
            .scalar()
            or 0
        )

        ratio = (
            completed_chapters / total_chapters
            if total_chapters > 0
            else 0.0
        )

        novel_progress.append(
            NovelProgress(
                novel_id=novel.id,
                title=novel.title,
                genre=novel.genre,
                status=novel.status,
                chapter_completed=completed_chapters,
                chapter_total=total_chapters,
                words=total_words,
                progress_ratio=ratio,
            )
        )

    metrics: List[GenerationMetric] = (
        db.query(GenerationMetric)
        .order_by(GenerationMetric.date.desc())
        .limit(30)
        .all()
    )

    daily_stats: List[DailyProgress] = [
        DailyProgress(
            date=m.date,
            novel_count=m.novel_count,
            chapter_count=m.chapter_count,
            word_count=m.word_count,
        )
        for m in reversed(metrics)
    ]

    aggregate = (
        db.query(
            func.count(Novel.id),
            func.coalesce(func.sum(Chapter.word_count), 0),
            func.count(Chapter.id),
        )
        .select_from(Novel)
        .join(Chapter, Chapter.novel_id == Novel.id, isouter=True)
        .one()
    )
    total_novels = int(aggregate[0] or 0)
    total_words = int(aggregate[1] or 0)
    total_chapters = int(aggregate[2] or 0)

    return DashboardSummary(
        novels=novel_progress,
        daily_stats=daily_stats,
        total_novels=total_novels,
        total_chapters=total_chapters,
        total_words=total_words,
    )
