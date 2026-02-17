/* 全局仪表盘与控制逻辑脚本 */

function formatNumber(num) {
  if (!num) return "0";
  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
  if (num >= 10000) return (num / 10000).toFixed(1) + "万";
  return String(num);
}

async function fetchJson(url, options) {
  const resp = await fetch(url, options);
  if (!resp.ok) {
    throw new Error("请求失败: " + resp.status);
  }
  return await resp.json();
}

async function updateDashboard() {
  try {
    const data = await fetchJson("/api/dashboard");

    document.getElementById("total-novels").innerText = data.total_novels;
    document.getElementById("total-chapters").innerText =
      data.total_chapters;
    document.getElementById("total-words").innerText = formatNumber(
      data.total_words
    );

    updateDailyChart(data.daily_stats || []);
    updateNovelTable(data.novels || []);
  } catch (err) {
    console.error(err);
  }
}

async function updateLogs() {
  try {
    const logs = await fetchJson("/api/logs?limit=200");
    const pre = document.getElementById("log-output");
    pre.textContent = logs
      .map((l) => `[${l.created_at}] [${l.level}] 小说${l.novel_id}：${l.message}`)
      .join("\n");
    pre.scrollTop = pre.scrollHeight;
  } catch (err) {
    console.error(err);
  }
}

async function updateSchedulerState() {
  try {
    const state = await fetchJson("/api/control/state");
    const label = document.getElementById("scheduler-status");
    if (!state.is_running) {
      label.innerText = "未运行";
      label.className = "text-danger fw-bold";
    } else if (state.is_paused) {
      label.innerText = "已暂停";
      label.className = "text-warning fw-bold";
    } else {
      label.innerText = "运行中";
      label.className = "text-success fw-bold";
    }
  } catch (err) {
    console.error(err);
  }
}

let chartDaily = null;

function updateDailyChart(dailyStats) {
  const ctx = document.getElementById("chart-daily").getContext("2d");
  const labels = dailyStats.map((d) => d.date);
  const words = dailyStats.map((d) => d.word_count);

  if (!chartDaily) {
    chartDaily = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "每日字数",
            data: words,
            tension: 0.3,
            borderColor: "#0d6efd",
            backgroundColor: "rgba(13, 110, 253, 0.1)",
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true,
          },
        },
      },
    });
  } else {
    chartDaily.data.labels = labels;
    chartDaily.data.datasets[0].data = words;
    chartDaily.update();
  }
}

function updateNovelTable(novels) {
  const tbody = document.getElementById("novel-table-body");
  tbody.innerHTML = "";

  novels.forEach((n) => {
    const tr = document.createElement("tr");

    const progressPercent = Math.round((n.progress_ratio || 0) * 100);
    const statusMap = {
      PLANNED: "已规划",
      WRITING: "创作中",
      PAUSED: "已暂停",
      COMPLETED: "已完成",
      ERROR: "错误",
    };

    tr.innerHTML = `
      <td>${n.title}</td>
      <td>${n.genre}</td>
      <td>${statusMap[n.status] || n.status}</td>
      <td style="min-width: 140px;">
        <div class="progress progress-small">
          <div class="progress-bar" role="progressbar" style="width: ${progressPercent}%;">
            ${progressPercent}%
          </div>
        </div>
        <div class="small text-muted">
          ${n.chapter_completed}/${n.chapter_total} 章
        </div>
      </td>
      <td>${formatNumber(n.words)}</td>
      <td>
        <button class="btn btn-outline-primary btn-sm btn-generate" data-id="${
          n.novel_id
        }">生成一章</button>
        <button class="btn btn-outline-secondary btn-sm ms-1 btn-view-chapter" data-id="${
          n.novel_id
        }">查看正文</button>
        <button class="btn btn-outline-success btn-sm ms-1 btn-export-docx" data-id="${
          n.novel_id
        }">导出Word</button>
        <button class="btn btn-outline-danger btn-sm ms-1 btn-delete-novel" data-id="${
          n.novel_id
        }">删除</button>
      </td>
    `;

    tbody.appendChild(tr);
  });

  tbody
    .querySelectorAll(".btn-generate")
    .forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const id = e.target.getAttribute("data-id");
        btn.disabled = true;
        btn.innerText = "生成中...";
        try {
          await fetchJson(`/api/novels/${id}/generate`, { method: "POST" });
          await updateDashboard();
          await updateLogs();
        } catch (err) {
          console.error(err);
          alert("生成失败，请查看日志。");
        } finally {
          btn.disabled = false;
          btn.innerText = "生成一章";
        }
      });
    });

  tbody.querySelectorAll(".btn-view-chapter").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const id = e.target.getAttribute("data-id");
      btn.disabled = true;
      btn.innerText = "加载中...";
      try {
        const chapters = await fetchJson(`/api/novels/${id}/chapters`);
        if (!chapters || chapters.length === 0) {
          alert("该小说暂无已生成章节。");
          return;
        }
        showChapterModal(chapters[0], chapters);
      } catch (err) {
        console.error(err);
        alert("加载章节列表失败，请稍后重试。");
      } finally {
        btn.disabled = false;
        btn.innerText = "查看正文";
      }
    });
  });

  tbody.querySelectorAll(".btn-export-docx").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-id");
      if (!id) return;
      window.open(`/api/novels/${id}/export-docx`, "_blank");
    });
  });

  tbody.querySelectorAll(".btn-delete-novel").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-id");
      if (!id) return;
      if (
        !confirm(
          "确定要删除这本小说及其所有章节和日志吗？该操作不可恢复。"
        )
      ) {
        return;
      }
      btn.disabled = true;
      btn.innerText = "删除中...";
      try {
        await fetchJson(`/api/novels/${id}`, { method: "DELETE" });
        await updateDashboard();
        await updateLogs();
      } catch (err) {
        console.error(err);
        alert("删除失败，请检查后端日志。");
      } finally {
        btn.disabled = false;
        btn.innerText = "删除";
      }
    });
  });
}

function showChapterModal(chapter, chapters) {
  const titleEl = document.getElementById("chapter-modal-title");
  const metaEl = document.getElementById("chapter-modal-meta");
  const outlineEl = document.getElementById("chapter-modal-outline");
  const contentEl = document.getElementById("chapter-modal-content");
  const selectEl = document.getElementById("chapter-modal-select");

  if (chapters && Array.isArray(chapters)) {
    selectEl.innerHTML = "";
    chapters.forEach((ch) => {
      const opt = document.createElement("option");
      opt.value = ch.id;
      opt.textContent = `第 ${ch.index} 章：${ch.title}`;
      if (ch.id === chapter.id) {
        opt.selected = true;
      }
      selectEl.appendChild(opt);
    });

    selectEl.onchange = async () => {
      const selectedId = parseInt(selectEl.value, 10);
      let target = chapters.find((c) => c.id === selectedId);
      if (!target) {
        try {
          target = await fetchJson(`/api/chapters/${selectedId}`);
        } catch (err) {
          console.error(err);
          alert("加载章节内容失败。");
          return;
        }
      }
      fillChapterContent(target);
    };
  }

  fillChapterContent(chapter);

  const modalEl = document.getElementById("chapterModal");
  const modal = new bootstrap.Modal(modalEl);
  modal.show();
}

function fillChapterContent(chapter) {
  const titleEl = document.getElementById("chapter-modal-title");
  const metaEl = document.getElementById("chapter-modal-meta");
  const outlineEl = document.getElementById("chapter-modal-outline");
  const contentEl = document.getElementById("chapter-modal-content");

  titleEl.innerText = `第 ${chapter.index} 章：${chapter.title}`;
  metaEl.innerText = `状态：${chapter.status}｜字数：${
    chapter.word_count
  }｜创建时间：${chapter.created_at}`;
  outlineEl.innerText = chapter.outline || "（无小结）";
  contentEl.textContent = chapter.content || "（暂无正文内容）";
}

function setupControlButtons() {
  const actions = [
    { id: "btn-start", action: "start" },
    { id: "btn-pause", action: "pause" },
    { id: "btn-resume", action: "resume" },
    { id: "btn-stop", action: "stop" },
  ];

  actions.forEach(({ id, action }) => {
    const btn = document.getElementById(id);
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        await fetchJson("/api/control", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action }),
        });
        await updateSchedulerState();
      } catch (err) {
        console.error(err);
        alert("控制失败，请查看后台日志。");
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function setupConfigForm() {
  const form = document.getElementById("config-form");
  if (!form) return;
}

async function init() {
  setupControlButtons();
  setupConfigForm();
  setupCreateNovelForm();

  await updateSchedulerState();
  await updateDashboard();
  await updateLogs();

  setInterval(updateSchedulerState, 8000);
  setInterval(updateDashboard, 10000);
  setInterval(updateLogs, 12000);
}

function setupCreateNovelForm() {
  const form = document.getElementById("create-novel-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const titleInput = document.getElementById("novel-title");
    const outlineInput = document.getElementById("novel-outline");
    const genreInput = document.getElementById("novel-genre");
    const chaptersInput = document.getElementById("novel-chapters");

    const title = titleInput.value.trim();
    if (!title) {
      alert("请先填写小说标题。");
      return;
    }

    const payload = {
      title,
      genre: genreInput.value.trim() || "未知",
      description: outlineInput.value.trim() || null,
      target_chapter_count:
        parseInt(chaptersInput.value, 10) || 10,
    };

    try {
      await fetchJson("/api/novels", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      alert("小说计划已创建，后续将根据该设定开始创作。");
      titleInput.value = "";
      outlineInput.value = "";
      genreInput.value = "";
      chaptersInput.value = "10";
      await updateDashboard();
    } catch (err) {
      console.error(err);
      alert("创建小说计划失败，请检查后端日志。");
    }
  });
}

document.addEventListener("DOMContentLoaded", init);
