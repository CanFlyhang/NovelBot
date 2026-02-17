# NovelBot · 全自动长篇小说创作机器人

> 像最近很火的 Clawbot 一样，这个项目可以**一直帮你写小说**。  
> 在本地持续创作长篇连载，写完直接投稿各大小说平台，争取稿费。

<p align="center">
  <b>NovelBot = AI 代笔作者 × 长篇记忆 × 一键导出投稿稿件</b>
</p>

<p align="center">
  <a href="#快速开始-quick-start">快速开始</a> ·
  <a href="#功能特点详细">功能特点</a> ·
  <a href="#架构概览">架构</a> ·
  <a href="#与-clawbot-的对比与特点">对比 Clawbot</a> ·
  <a href="#参与共创-contributing">参与共创</a>
</p>

NovelBot 是一个基于大语言模型（如 DeepSeek）的本地小说创作机器人，可以在你的电脑或服务器上**长期运行**，自动规划、创作和管理多部长篇小说。

- 📝 面向“想靠网文赚稿费”的个人创作者  
- 🧬 面向想批量孵化 IP / 文库的工作室  
- 🧪 面向研究长文本生成、一致性控制的开发者和研究者

你只需要提供一个大致的故事构想，它就能像“AI 代笔作者”一样，日复一日地帮你把一本本长篇写出来。

---

## 特性总览

- 🚀 **多本小说并行创作**  
  支持同时规划和创作多部作品，每本都有独立的标题、题材、章节数、故事线。

- 📚 **长篇上下文记忆 + RAG**  
  自动回顾前文章节、人物与关键情节，降低“前后剧情断裂”的情况。

- 🧠 **剧情事实记忆 + 一致性审核 + 返工循环**  
  把“母亲是否已去世”“公司是否已经破产”之类的硬设定结构化存进数据库，  
  再用模型做一致性检查，自动对冲突章节进行二次创作，最大程度减少设定打脸。

- 🧩 **终章意识与收官写作**  
  能识别“最后一章”，主动以“完结篇”的方式写结局，解开主线悬念并交代角色命运。

- 📊 **可视化控制台**  
  自带 Web 后台：系统控制、仪表盘、产量统计、日志、查看正文、导出 Word，一目了然。

- 💾 **本地部署，数据自控**  
  所有小说内容、设定、日志都存储在你自己的数据库中，更适合作为“生产力工具”长期使用。

---

## 功能特点（详细）

### 小说创作能力

- **多本小说并行创作**  
  - 为每本小说单独配置标题、题材、章节数、故事发展线  
  - 支持玄幻、科幻、都市、悬疑等任意题材

- **自动章节生成**  
  - 调度器根据你创建的“小说计划”依次生成章节  
  - 也可以在 Web 界面中手动点击“生成一章”

- **终章意识与结局收束**  
  - 当生成到**最后一章**时，模型会被明确要求写成“全书收官章”  
  - 要求：解开主线悬念、交代角色结局、情感升华，而不是继续无止境地“水文”

### 上下文与一致性

- **章节级上下文 RAG**  
  - 每次生成新章节时，系统会回顾前面所有已完成章节  
  - 对最近章节提取关键片段，结合人物设定、情节节点组成上下文

- **剧情事实记忆（Story Facts）**  
  - 每一章生成完成后，系统会再调用一次模型，从本章中抽取“客观事实设定”，例如：  
    - 某人已去世 / 已破产 / 已离婚 / 身份关系  
    - 重大事件发生过的时间 / 地点  
  - 这些事实会写入 MySQL 中的 `story_facts` 表，并按照重要程度分为：  
    - `CRITICAL`：一旦写出就不能自相矛盾（比如“母亲已经去世”、“公司已经破产”）  
    - `NORMAL`：一般设定和背景信息

- **一致性审核 + 返工循环**  
  - 正常生成一章后，再次调用模型，对照“关键事实”做一致性审查：  
    - 如果无冲突：直接采用这一版  
    - 如果发现冲突：  
      - 输出“冲突描述 + 相关事实”  
      - 把这份“冲突黑名单”塞回给模型，请它**在避免这些错误的前提下重新生成本章**  
  - 典型问题比如：  
    - 第 2 章写母亲已死，第 29 章又写从国外接母亲回国  
    - 第 2 章写公司已经破产，后面又在正常运转  
    - 这类设定会被 StoryFacts + 审核环节尽量拦截、纠正

### 控制与监控

- **Web 控制面板**  
  - 一键控制：开始创作 / 暂停 / 恢复 / 停止 调度器  
  - 查看调度器当前状态（运行中 / 暂停 / 停止）

- **仪表盘与统计**  
  - 小说列表与进度：每本小说的完成章节数、目标章节数、总字数、状态  
  - 每日写作产量：按天统计章节数与字数  
  - 全局统计：小说总数、章节总数、累计字数

- **实时创作日志**  
  - 每次生成章节会记录一条日志：小说 ID、章节 ID、字数、耗时等  
  - 出现错误时，可以在日志区域看到具体原因

### 作品管理

- **查看全文**  
  - Web 界面中可以按小说查看任意章节的：章节标题、本章小结、正文  
  - 支持章节下拉选择快速跳转

- **自动章节标题**  
  - 模型生成的“本章小结”会被自动提炼为章节标题，方便列表展示

- **导出 Word**  
  - 整本小说可以一键导出为 `.docx`，适合：  
    - 投稿到各大小说平台  
    - 本地排版与备份  
  - 支持中文标题文件名，已处理浏览器下载时的编码问题

- **删除小说**  
  - 在列表中一键删除某本小说（连同其章节与日志），便于清理实验结果

---

## 适用场景

- 想尝试写网文但时间有限，希望 AI 帮你打底，你再精修润色
- 有一堆故事点子，却很难坚持写完一本长篇
- 想快速做“多本小说实验”，测试哪种题材/人设更受读者欢迎
- 想研究长文本故事生成、记忆机制、一致性控制等课题

---

## 设计理念

很多自动小说项目只是“证明可以生成一段小说”，而 NovelBot 的目标是**真正能“陪你写完一本书”**。

在设计时我们刻意遵循了几个原则：

- 以创作者为中心：  
  UI 和交互围绕“开新书、看进度、导出稿件”设计，而不是围绕“炫技 Demo”。

- 以一致性为底线：  
  用 Story Facts + 审核 + 返工机制，抵抗大模型在长篇中的“健忘症”和“编新设定”的冲动。

- 以长期运行为常态：  
  所有逻辑都假设调度器会长期跑在本机或服务器上，能够持续产出、持续统计。

- 保持可拆分：  
  你可以只用其中一部分能力（比如只用章节生成 + Word 导出），也可以把 NovelBot 嵌入到自己的写作工作流里。

---

## 架构概览

- **后端**
  - Python 3.x
  - FastAPI
  - SQLAlchemy + MySQL

- **前端**
  - Bootstrap 5
  - Chart.js
  - 原生 JavaScript（无重框架依赖）

- **模型接入**
  - DeepSeek 或其他 OpenAI Chat Completions 兼容接口  
  - 自带简单的：限流、重试、超时处理

- **主要模块**
  - `scheduler`：调度器线程，按小说计划生成章节
  - `services/novel_service`：核心业务逻辑（RAG 上下文、事实记忆、一致性审核、章节生成）
  - `services/deepseek_client`：模型调用封装
  - `models`：ORM 模型（Novel / Chapter / StoryFact / CreationLog 等）
  - `web`：管理后台页面与静态资源

---

## 快速开始（Quick Start）

### 环境准备

- Python 3.10+（建议）
- MySQL 5.7+ / 8.x
- 操作系统：Windows / macOS / Linux 均可（作者在 Windows 环境下开发）

### 1. 克隆项目

```bash
git clone https://github.com/CanFlyhang/NovelBot.git
cd NovelBot
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量（.env）

在项目根目录创建 `.env` 文件，例如：

```env
# 应用基础配置
APP_NAME=NovelBot

# 数据库
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=novelbot

# 模型相关
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# 调度参数
MAX_REQUESTS_PER_MINUTE=30
API_REQUEST_TIMEOUT=60
API_MAX_RETRIES=3
SCHEDULER_TICK_SECONDS=10
```

根据自己的 MySQL 和模型服务实际情况修改。

### 4. 初始化数据库

确保你配置的数据库已存在（例如 `novelbot`），然后首次运行时会自动建表：

```bash
uvicorn app.main:app --reload
```

### 5. 打开管理后台

浏览器访问：

```text
http://127.0.0.1:8000/
```

你将看到：

- 左侧：系统控制（开始创作 / 暂停 / 恢复 / 停止）+ 新建小说计划
- 中间：每日产量统计 + 小说列表与进度
- 右侧：实时创作日志

---

## 使用说明（Usage）

### 1. 新建小说计划

在“新建小说计划”卡片中填写：

- 小说标题（必填）
- 故事情节发展线：简要描述世界观、主线、主角目标等
- 类型：玄幻 / 科幻 / 都市 / 悬疑等
- 章节数：计划写多少章（例如 50 章）

点击“创建小说计划”后，对应记录会写入数据库，并出现在下方“小说列表与进度”中。

### 2. 启动自动创作

有两种方式：

1. **后台调度器自动写**  
   - 点击“开始创作”按钮  
   - 调度器会在后台不断挑选计划中的小说生成下一章

2. **手动推进某一本小说**  
   - 在“小说列表与进度”中找到目标小说  
   - 点击“生成一章”按钮

### 3. 查看与导出

- **查看章节正文**：  
  - 点击“查看正文”，弹出章节查看弹窗  
  - 可通过下拉框选择任意已生成章节

- **导出为 Word**：  
  - 点击“导出 Word”  
  - 浏览器将下载整本小说的 `.docx` 文件，可以用于投稿或排版

---

## 与 Clawbot 的对比与特点

目前市面上已有类似 Clawbot 这样的长篇小说自动生成项目。  
NovelBot 在此基础上重点做了以下强化：

- **更偏向“投稿实用”而不是 demo**  
  - 支持导出 Word  
  - 调度与统计围绕“长期写作产出”设计

- **剧情一致性更重视**  
  - 剧情事实记忆 + 一致性审核 + 返工循环  
  - 尽量减少“人死复活、设定自打脸、真相二次编造”等问题

- **终章意识**  
  - 会主动识别“最后一章”，引导模型写出完整结局，而不是无限拖剧情

- **开放共创**  
  - 代码结构清晰，便于二次开发  
  - 欢迎基于 NovelBot 打造你自己的“个人写作工厂”

如果你希望把作品投向各大小说网站（起点、番茄、晋江、QQ 阅读等），NovelBot 目标是成为一个**可以真正辅助你量产稿件**的工具，而不是只能“玩玩看”的实验品。

---

## 演示截图（Screenshots）

> 以下为示意占位，你可以替换为自己实际的截图。

- 管理后台主页：小说列表、进度与每日产量  
  `docs/screenshot-dashboard.png`
- 章节正文查看弹窗  
  `docs/screenshot-chapter-view.png`

建议在 `docs/` 目录下放两三张关键界面截图，并在此处改成：

```markdown
![Dashboard](docs/screenshot-dashboard.png)
![Chapter Viewer](docs/screenshot-chapter-view.png)
```

---

## 路线图（Roadmap）

- [ ] 前端增加“剧情设定视图”：可直接浏览 `StoryFact` 列表  
- [ ] 支持更多模型与自托管 LLM（如本地大模型）  
- [ ] 支持多语言小说（英文 / 日文等）  
- [ ] 支持“一键生成全书大纲 + 分章大纲”模式  
- [ ] 集成简单的投稿导出模板（章节命名、分卷结构等）
- [ ] 提供 Docker 镜像，一行命令即可启动完整环境  
- [ ] 内置更多“写作模版”（爽文向、慢热向、群像向等）

欢迎提交 Issue / PR，一起把它打磨成真正可商用的“AI 网文助手”。

---

## 参与共创（Contributing）

欢迎任何形式的参与，包括但不限于：

- 提交 Issue：  
  - 报告 Bug  
  - 提出新的功能需求  
  - 分享你在真实创作中的使用体验与痛点

- 提交 PR：  
  - 修复问题、优化代码  
  - 增强前端体验或新增视图  
  - 改进剧情一致性算法、终章写作策略等

推荐的协作流程：

1. 在 GitHub 上 Fork 本仓库  
2. 新建分支，如 `feature/story-fact-view`  
3. 完成修改并附带必要的说明 / 截图  
4. 提交 Pull Request，简要描述动机与改动点

如果你是在真实平台上用 NovelBot 投稿并取得了一些成绩（签约、上榜、完结等），也非常欢迎在 Issue 里分享使用心得，这会帮到后来者更好地“用好这台机器”。  

---

## Star & 交流

如果你觉得这个项目对你有帮助，欢迎：

- 在 GitHub 上点一个 ⭐ Star，方便以后继续跟进更新
- 把仓库分享给也在研究 AI 写作 / 网文创作的朋友
- 在 Issue 中留言你希望一起共创的方向（比如：专攻某个题材、做自动投稿脚本等）

越多人参与，这个“AI 网文创作基座”就会越好用。

---

## 免责声明

- 请确保遵守你所接入模型服务的使用条款（包括但不限于 DeepSeek、OpenAI 等）。  
- 使用本项目生成的内容进行商业化投稿时，请自行确认目标平台的规则与政策。  
- 本项目仅提供技术工具，不保证生成内容的质量、收益或版权归属。

---

## License

本项目基于 MIT License 开源，完整条款如下：

```text
MIT License

Copyright (c) 2026 CanFlyhang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---
