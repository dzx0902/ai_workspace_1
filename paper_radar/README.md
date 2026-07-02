# Paper Radar

Paper Radar 是一个本地科研论文追踪工具。它抓取多个论文来源，以关键词规则初筛，可选调用 OpenAI-compatible 模型评分，并生成适合 Obsidian 的 Markdown 日报。

当前版本已完成多来源抓取、PDF 精读、Chroma/RAG、主题追踪、周期综述、人工反馈和自动化基础设施。

## 当前状态

已实现：

- arXiv RSS 抓取，并保持原有脚本兼容。
- bioRxiv、medRxiv 官方 API 抓取。
- PubMed ESearch + EFetch 检索，无 API key 也可运行。
- OpenReview venue/关键词最小抓取实现。
- Hugging Face Daily Papers RSS 最小抓取实现。
- 统一 `Paper` 结构、SQLite 去重、规则评分、LLM 评分和日报输出。
- 网络 timeout、有限重试、单个来源失败隔离。
- 按评分和来源白名单下载 PDF，失败时可独立重试。
- 使用 PyMuPDF，失败时回退 pypdf，输出结构化全文。
- 区分脑信号论文与 AI 方法论文生成单篇 Markdown 精读笔记。
- 日报、单篇笔记、全文和主题笔记写入 Chroma，并支持带引用问答。
- 8 个研究主题长期追踪，以及周报、月报。
- 从 Markdown 复选框采集人工反馈，并调整后续规则评分。
- cheap/strong model 分流、调用/token/费用记录、dry-run、数据库备份、按日日志。

## 开发路线

- Phase 2：多来源框架、bioRxiv、PubMed、medRxiv、OpenReview、Hugging Face。当前已完成基础版本。
- Phase 3：PDF 下载/抽取、分类精读 prompt 和单篇论文笔记。当前已完成。
- Phase 4：Chroma/RAG 与引用查询。已完成。
- Phase 5：Topic、Weekly、Monthly 综述。已完成。
- Phase 6：反馈学习、成本控制、dry-run、备份和按日日志。已完成基础版本。

## 安装

```bash
cd /home/dzx0902/ai_workspace/paper_radar
../.venv/bin/python -m pip install -r requirements.txt
../.venv/bin/python -m pip install -r requirements-rag.txt
cp .env.example .env
```

第二条仅用于 Chroma/RAG；不使用知识库时可以跳过。

如果工作区根目录 `/home/dzx0902/ai_workspace/.env` 已配置 DeepSeek、DashScope 或 SiliconFlow，可不创建子项目 `.env`。子项目 `.env` 的同名变量优先。

## LLM 配置

选择 provider：

```dotenv
PAPER_RADAR_LLM_PROVIDER=deepseek
```

可选值为 `deepseek`、`dashscope`、`siliconflow`、`openai`。对应配置沿用以下形式：

```dotenv
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

超时和重试：

```dotenv
PAPER_RADAR_LLM_TIMEOUT=60
PAPER_RADAR_LLM_MAX_RETRIES=3
PAPER_RADAR_STRONG_MODEL=
PAPER_RADAR_CHEAP_MODEL=
PAPER_RADAR_INPUT_COST_PER_M=0
PAPER_RADAR_OUTPUT_COST_PER_M=0
PAPER_RADAR_STRONG_INPUT_COST_PER_M=0
PAPER_RADAR_STRONG_OUTPUT_COST_PER_M=0
```

`PAPER_RADAR_STRONG_MODEL` 可选。设置后，标题摘要初筛仍使用 provider 默认模型，全文精读改用该模型。
`PAPER_RADAR_CHEAP_MODEL` 用于标题摘要初筛。费用配置单位为每百万 token，设置后每次运行会输出估算成本。

PubMed 可选配置：

```dotenv
NCBI_API_KEY=
NCBI_EMAIL=your-email@example.com
NCBI_TOOL=paper_radar
```

没有 `NCBI_API_KEY` 时仍可检索。程序会将两次 NCBI 请求间隔至少 0.34 秒；配置 key 后间隔至少 0.11 秒。

OpenReview 长期运行配置：

```dotenv
PAPER_RADAR_OPENREVIEW_USERNAME=your-openreview-email@example.com
PAPER_RADAR_OPENREVIEW_PASSWORD=your-openreview-password
PAPER_RADAR_OPENREVIEW_TOKEN_EXPIRES_IN=604800
```

OpenReview 的 `/notes` API 可能对匿名脚本请求触发 challenge。配置用户名和密码后，Paper Radar 会在运行时自动登录并使用临时 bearer token；`PAPER_RADAR_OPENREVIEW_TOKEN_EXPIRES_IN` 最大建议保持 604800 秒，也就是 7 天。如果你更想手动管理 token，也可以只配置：

```dotenv
PAPER_RADAR_OPENREVIEW_TOKEN=
```

## 运行

从 `paper_radar` 根目录执行：

```bash
../.venv/bin/python scripts/fetch_sources.py --source arxiv
../.venv/bin/python scripts/fetch_sources.py --source biorxiv
../.venv/bin/python scripts/fetch_sources.py --source pubmed
../.venv/bin/python scripts/fetch_sources.py --all --limit 50
```

`--source` 会显式运行该类型的配置，即使配置项的 `enabled` 为 `false`，便于单独测试。`--all` 只运行 `enabled: true` 的来源。`--limit` 是每个配置项的最大返回数量。

原有分步命令继续可用：

```bash
../.venv/bin/python scripts/fetch_arxiv.py
../.venv/bin/python scripts/filter_papers.py
../.venv/bin/python scripts/score_with_llm.py --limit 20
../.venv/bin/python scripts/generate_daily_note.py --date 2026-06-08
```

一键运行，不调用 LLM：

```bash
../.venv/bin/python scripts/run_daily.py --no-llm
```

一键运行并限制 LLM 评分数量：

```bash
../.venv/bin/python scripts/run_daily.py --limit-llm 20
```

预演抓取、筛选和报告统计，但不修改正式数据库、不写日报：

```bash
../.venv/bin/python scripts/run_daily.py --no-llm --dry-run
```

## PDF 下载与精读

配置位于 `config/pdf.yaml`：

```yaml
pdf_download_dir: data/pdfs
extracted_text_dir: data/extracted_texts
paper_notes_dir: notes/papers
obsidian_paper_notes_dir: /mnt/f/ObsidianVault/AI/PaperRadar/Papers
max_pdf_per_run: 10
download_timeout: 60
allowed_sources: [arxiv, biorxiv, medrxiv, openreview]
min_llm_score_for_download: 8
overwrite_existing_pdf: false
max_fulltext_chars_for_llm: 120000
```

批量下载 LLM 判定为 `read` 或 `high priority`、且达到最低分数的论文：

```bash
../.venv/bin/python scripts/download_pdfs.py --limit 10
../.venv/bin/python scripts/download_pdfs.py --date 2026-06-10 --limit 5
```

手动处理单篇论文：

```bash
../.venv/bin/python scripts/download_pdfs.py --paper-id 2606.06915
../.venv/bin/python scripts/extract_pdfs.py --paper-id 2606.06915
../.venv/bin/python scripts/summarize_paper.py --paper-id 2606.06915
```

批量抽取和总结当天高优先级论文：

```bash
../.venv/bin/python scripts/extract_pdfs.py --limit 10
../.venv/bin/python scripts/summarize_paper.py --date 2026-06-10 --limit 5
```

PDF、全文和笔记默认分别写入：

```text
data/pdfs/
data/extracted_texts/
notes/papers/
/mnt/f/ObsidianVault/AI/PaperRadar/Papers/
```

数据库会自动增加 `pdf_path`、下载/抽取状态、全文路径、笔记路径和错误字段。日报流程不会自动触发 PDF 下载，避免意外消耗网络、磁盘和 LLM 配额。

## Chroma / RAG

配置位于 `config/rag.yaml`。默认复用：

```yaml
chroma_host: localhost
chroma_port: 8000
collection: paper_radar
embedding_provider: local
embedding_model: /mnt/f/AIModels/bge-small-zh-v1.5
```

支持 `local`、`ollama`、`openai` 三种 embedding provider。使用 Ollama 时设置：

```dotenv
PAPER_RADAR_EMBED_PROVIDER=ollama
PAPER_RADAR_EMBED_MODEL=nomic-embed-text
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

将日报、单篇笔记、PDF 全文和 Topic note 增量入库：

```bash
../.venv/bin/python scripts/ingest_notes_to_chroma.py
../.venv/bin/python scripts/ingest_notes_to_chroma.py --force
```

不调用 LLM，仅查看语义检索结果和引用：

```bash
../.venv/bin/python scripts/query_papers.py "最近 EEG-to-image 有哪些新工作？"
```

调用配置的生成模型进行 RAG 回答：

```bash
../.venv/bin/python scripts/query_papers.py \
  "有哪些 VLM 方法可能迁移到脑信号解码？" --llm
```

引用包含 paper title、URL、note path 和 chunk index。入库 manifest 位于 `data/rag_manifest.json`，未变化文件默认跳过。

## 主题追踪与综述

主题定义位于 `config/topics.yaml`，可修改关键词、分类、输出路径和 `enabled`。

生成一个或全部 Topic note：

```bash
../.venv/bin/python scripts/generate_topic_note.py --topic "EEG-to-Image"
../.venv/bin/python scripts/generate_topic_note.py --all --days 90
```

生成周报和月报：

```bash
../.venv/bin/python scripts/generate_weekly_review.py --date 2026-06-11
../.venv/bin/python scripts/generate_monthly_review.py --date 2026-06-11
```

输出目录：

```text
notes/topics/
notes/reviews/weekly/
notes/reviews/monthly/
/mnt/f/ObsidianVault/AI/PaperRadar/Topics/
/mnt/f/ObsidianVault/AI/PaperRadar/Reviews/
```

## 人工反馈

新版日报每篇论文带有：

```markdown
- [ ] relevant
- [ ] not relevant
- [ ] read later
- [ ] add to related work
- [ ] summarize full paper
```

在 Obsidian 中勾选后执行：

```bash
../.venv/bin/python scripts/collect_feedback.py
../.venv/bin/python scripts/collect_feedback.py \
  --path /mnt/f/ObsidianVault/AI/PaperRadar
```

反馈会写入数据库。后续规则筛选会提高经常出现在正反馈论文中的关键词和来源权重，降低负反馈来源和关键词权重，调整范围限制在 `-5` 到 `+5`，避免少量反馈完全覆盖基础规则。

## 备份与日志

创建 SQLite 一致性备份：

```bash
../.venv/bin/python scripts/backup_database.py
```

默认输出到 `data/backups/`。日志按日期保存到：

```text
data/logs/paper_radar-YYYY-MM-DD.log
```

## 配置

- `config/sources.yaml`：启用、停用或新增论文源。
- `config/keywords.yaml`：按主题维护 high 和 medium 关键词。
- `config/scoring.yaml`：设置标题、摘要权重和进入 LLM 的最低规则分。
- `config/output.yaml`：设置本地副本和 Obsidian 输出路径。
- `config/pdf.yaml`：PDF 下载、抽取与精读配置。
- `config/rag.yaml`：Chroma、embedding 和分块配置。
- `config/topics.yaml`：长期主题与综述输出配置。

每个 source 配置包含：

```yaml
- name: PubMed EEG and Neural Decoding
  type: pubmed
  query: (EEG OR electroencephalography) AND (deep learning OR decoding)
  category: brain-signals
  enabled: false
  fetch_interval: daily
  description: PubMed search for EEG learning and decoding.
```

支持的 `type`：

- `arxiv_rss`：配置 `url`。
- `biorxiv` / `medrxiv`：配置 API `url`，可设 `recent_days` 和 `subject_filter`。
- `pubmed`：配置 PubMed Boolean `query`。
- `openreview`：配置 API `url` 和 `venue`，或配置 `query`。
- `huggingface`：配置 Daily Papers RSS `url`。

`fetch_interval` 作为 cron/Task Scheduler 配置参考；手动运行不会据此跳过来源。

数据库首次运行时自动创建在 `data/papers.db`。升级旧数据库时会自动新增 `external_id` 并回填已有 arXiv ID。新来源内部 ID 使用 `pubmed:PMID`、`biorxiv:DOI` 等命名空间，重复抓取不会清空已有评分。

## 来源说明

bioRxiv 和 medRxiv 使用官方 API，按最近 N 天分页获取。设置 `subject_filter` 时按 API 返回的 subject category 精确过滤。

PubMed 使用 NCBI E-utilities，先搜索 PMID，再批量获取 XML。请避免高频循环运行；大批量任务建议配置 `NCBI_API_KEY` 和有效联系邮箱。

OpenReview 当前是最小实现。venue ID 会随会议年份变化，例如 `ICLR.cc/2026/Conference`，需要在配置中更新。不同 venue 的字段可能不一致，单个来源解析失败不会影响其他来源。

Hugging Face Papers 页面结构可能变化。其旧 RSS 地址目前返回 HTTP 401，因此该来源默认关闭；公开 feed 恢复后再设置 `enabled: true`。

## 日报位置

默认同时输出：

```text
paper_radar/notes/daily/YYYY-MM-DD-paper-radar.md
/mnt/f/ObsidianVault/AI/PaperRadar/YYYY-MM-DD-paper-radar.md
```

Obsidian 路径不可写时会记录错误，本地日报仍会保留。

## 自动运行

当前部署使用 Docker 常驻调度器 `ai_paper_radar_scheduler`，不依赖 WSL 的 cron 或 systemd。检查状态：

```bash
docker compose ps paper_radar_scheduler
docker logs --since 24h ai_paper_radar_scheduler
```

当前时间表使用 `Asia/Shanghai`：

- 每天 07:30：备份、采集反馈、抓取、最多 LLM 初筛 20 篇、最多精读 3 篇、刷新 Topic 和 RAG。
- 每天 12:30：再次备份、采集 Obsidian 反馈、增量更新 RAG。
- 每周日 18:00：生成周报并入库。
- 每月 1 日 18:30：生成月报并入库。

调度状态保存于 `data/scheduler_state.json`。统一工作流入口为：

```bash
../.venv/bin/python scripts/run_automation.py maintenance
../.venv/bin/python scripts/run_automation.py daily
../.venv/bin/python scripts/run_automation.py weekly
../.venv/bin/python scripts/run_automation.py monthly
```

`config/paper-radar.crontab` 仅作为传统 Linux cron 参考，当前 WSL 没有运行 cron 服务，因此没有安装该 crontab。

Windows 任务计划程序可创建“启动程序”任务：

```text
程序: wsl.exe
参数: bash -lc "cd /home/dzx0902/ai_workspace/paper_radar && ../.venv/bin/python scripts/run_daily.py --limit-llm 50"
```

## AstrBot 接入

Paper Radar 已接入工作区 FastAPI 和 `ai_workspace` AstrBot 插件。重启 FastAPI 与 AstrBot 后，可以在 WebChat 或已连接的 QQ、Telegram、飞书等平台中使用：

```text
/papers
/papers 2026-06-08 10
/paper 2606.06915
/paper_run
/paper_run --llm --limit 20
```

`/papers` 返回筛选后的论文摘要，每篇都包含 arXiv 摘要页和 PDF 原文地址。

在希望接收推送的聊天中订阅：

```text
/paper_subscribe 08:30
/paper_subscribe 08:30 --llm --top 20
/paper_subscription
/paper_unsubscribe
```

推送时间使用 `Asia/Shanghai`，默认推送 Top 20。默认只执行关键词筛选，不消耗 LLM API；显式添加 `--llm` 后每天最多评分 20 篇。订阅绑定当前 AstrBot 会话，因此应在实际希望接收消息的私聊或群聊中执行。

AstrBot 必须先配置至少一个消息平台，主动推送才能送到社交软件。当前平台配置可在 AstrBot WebUI 的“机器人”页面管理。

### 微信个人号故障恢复

当前微信个人号能收到消息，但发送接口返回 `ret=-2`。处理流程：

1. 打开 `http://localhost:6185`。
2. 进入“机器人”。
3. 删除或禁用旧的 `weixin_personal_bcna`。
4. 点击“创建机器人”，选择“个人微信”。
5. 使用手机微信扫描二维码并在手机端确认登录。
6. 保存后，先给机器人发送一句普通文字，刷新会话 `context_token`。
7. 验证机器人能正常回复。
8. 在该微信会话发送 `/paper_subscribe 08:30 --llm --top 20`。

如果重新登录后仍反复出现 `ret=-2`，建议不要继续把个人微信作为主要推送渠道。

### 推荐替代平台

国内网络环境优先推荐飞书：AstrBot 4.25+ 支持扫码一键创建，长连接模式不需要公网 Webhook。

1. 打开 `http://localhost:6185`，进入“机器人”。
2. 点击“创建机器人”，选择“飞书”。
3. 选择“扫码一键创建”和国内版，使用飞书扫码确认。
4. 保存后在飞书中给机器人发送 `/papers`。
5. 能收到回复后发送 `/paper_subscribe 08:30 --llm --top 20`。

Telegram 也很稳定，但通常需要可访问 Telegram 的网络：

1. 在 Telegram 中联系 `@BotFather`，执行 `/newbot` 并保存 Bot Token。
2. AstrBot WebUI -> “机器人” -> “创建机器人” -> `telegram`。
3. 填写 Bot Token；网络受限时在 AstrBot 配置中填写 HTTP 代理。
4. 私聊新机器人发送 `/start` 和 `/papers`。
5. 发送 `/paper_subscribe 08:30 --llm --top 20`。

## 测试

```bash
../.venv/bin/python -m pytest -q
```

仅验证抓取 CLI 参数而不联网：

```bash
../.venv/bin/python scripts/fetch_sources.py --help
../.venv/bin/python -m compileall -q paper_radar scripts
```

## 常见错误

- `failed sources: 1`：查看 `data/logs/paper_radar.log`，其他来源仍会继续。
- PubMed `429`：降低运行频率，确认 `NCBI_API_KEY`，不要并行启动多个抓取任务。
- OpenReview `ChallengeRequiredError`：配置 `PAPER_RADAR_OPENREVIEW_USERNAME` 和 `PAPER_RADAR_OPENREVIEW_PASSWORD`，或提供 `PAPER_RADAR_OPENREVIEW_TOKEN`。
- OpenReview 返回空列表：检查 venue ID、submission invitation 是否匹配当前年份和 API v2，或该会议阶段是否公开。
- Hugging Face RSS 解析失败：页面可能临时变化，可禁用该 source，等待适配器更新。
- `no_pdf_url`：该来源没有提供可直接下载的 PDF，PubMed 常见此情况。
- `extract_failed`：PDF 可能是扫描件、损坏或没有文本层；当前版本不包含 OCR。
- `summary_failed`：检查 LLM 配置和 `data/logs/llm_raw/` 中保存的原始响应。
- SQLite `database is locked`：避免同时运行多个写入任务；程序默认最多等待 30 秒。
- Chroma 连接失败：确认 `docker compose ps chroma`，以及 `CHROMA_HOST`/`CHROMA_PORT`。
- 本地 embedding 模型缺失：修改 `PAPER_RADAR_EMBED_MODEL`，不会自动从 Hugging Face 下载模型。
- Ollama embedding 连接失败：确认 Ollama 已启动，或改回 `embedding_provider: local`。
- RAG 返回旧内容：运行 `ingest_notes_to_chroma.py --force`。
- Obsidian 路径不可写：本地 `notes/daily` 仍会输出，检查 `config/output.yaml`。
