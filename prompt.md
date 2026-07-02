我想在现有 ~/ai_workspace 工程下新增一个 paper_radar 子项目，用来本地自动追踪科研论文和 AI 前沿进展。请帮我设计并实现第一版 MVP。

背景：
- 我已有本地 ai_workspace 工程，里面已有一些 LLM router、Obsidian 输出、Chroma/RAG 相关脚本。
- 生成模型统一走远程 OpenAI-compatible API，例如 DeepSeek / DashScope / SiliconFlow / OpenAI。
- 本地可以做 RSS 抓取、PDF 下载、文本抽取、embedding、Chroma 入库。
- 第一版不要做复杂 Web UI，只做命令行脚本和 Markdown 输出。
- 第一版也不要急着做 PDF 全文精读，先基于标题和摘要进行筛选、LLM 评分、生成日报。
- Obsidian Vault 输出路径需要可配置，默认可以设为：
  /mnt/f/ObsidianVault/AI/PaperRadar

项目目标：
实现一个 paper_radar 模块，每天自动抓取 arXiv 新论文，按我的研究兴趣筛选，并生成 Markdown 日报。后续要方便扩展到 bioRxiv、medRxiv、PubMed、OpenReview、Hugging Face Papers、GitHub Trending 和 PDF 精读。

我的研究兴趣包括：
1. 脑信号和生理信号：
   EEG, electroencephalography, fMRI, functional magnetic resonance imaging, MEG, ECoG, EMG, EOG, BCI, brain-computer interface, biosignal, physiological signal。

2. 脑解码和神经科学：
   neural decoding, brain decoding, visual decoding, auditory decoding, motor imagery, image reconstruction, video reconstruction, stimulus reconstruction, neuroimaging, cognitive neuroscience, computational neuroscience, neural representation。

3. AI 方法：
   CLIP, contrastive learning, diffusion model, flow matching, rectified flow, transformer, self-supervised learning, representation learning, multimodal learning, vision-language model, VLM, foundation model。

4. AI SOTA 和大模型：
   LLM, large language model, agent, reasoning, benchmark, SOTA, state-of-the-art, post-training, test-time scaling, alignment, long context, retrieval augmented generation, RAG, world model, tool use。

第一版数据源：
请先只接 arXiv RSS，分类包括：
- cs.CV
- cs.LG
- cs.AI
- cs.CL
- eess.SP
- eess.IV
- q-bio.NC
- stat.ML

arXiv RSS 链接格式：
https://rss.arxiv.org/rss/cs.CV
https://rss.arxiv.org/rss/cs.LG
https://rss.arxiv.org/rss/cs.AI
https://rss.arxiv.org/rss/cs.CL
https://rss.arxiv.org/rss/eess.SP
https://rss.arxiv.org/rss/eess.IV
https://rss.arxiv.org/rss/q-bio.NC
https://rss.arxiv.org/rss/stat.ML

请实现以下结构：

paper_radar/
├── README.md
├── requirements.txt
├── .env.example
├── config/
│   ├── sources.yaml
│   ├── keywords.yaml
│   ├── scoring.yaml
│   └── output.yaml
├── data/
│   ├── papers.db
│   └── logs/
├── notes/
│   ├── daily/
│   └── papers/
├── paper_radar/
│   ├── __init__.py
│   ├── models.py
│   ├── storage.py
│   ├── scoring.py
│   ├── markdown.py
│   ├── utils.py
│   ├── sources/
│   │   ├── __init__.py
│   │   └── arxiv_rss.py
│   └── llm/
│       ├── __init__.py
│       ├── router.py
│       └── prompts.py
└── scripts/
    ├── fetch_arxiv.py
    ├── filter_papers.py
    ├── score_with_llm.py
    ├── generate_daily_note.py
    └── run_daily.py

具体要求：

1. config/sources.yaml
   - 配置 arXiv RSS 源。
   - 每个源包含 name、url、category、enabled。
   - 后续要方便扩展 bioRxiv、PubMed、OpenReview。

2. config/keywords.yaml
   - 按主题组配置关键词。
   - 至少包含：
     brain_signals
     brain_decoding
     neuroscience
     ai_core
     ai_sota
   - 每组关键词分 high 和 medium 两级。
   - high 关键词权重大，medium 关键词权重小。

3. config/scoring.yaml
   - 配置规则评分：
     title 命中 high 关键词加多少分
     abstract 命中 high 关键词加多少分
     title 命中 medium 关键词加多少分
     abstract 命中 medium 关键词加多少分
   - 配置进入 LLM 评分的最低 rule_score 阈值。
   - 配置最终 read / skim / skip 的分数范围。

4. config/output.yaml
   - 配置 Obsidian 输出路径。
   - 配置 daily note 文件名格式，例如 YYYY-MM-DD-paper-radar.md。
   - 配置是否同时输出到项目本地 notes/daily。

5. paper_radar/models.py
   - 用 dataclass 或 pydantic 定义 Paper 数据结构。
   - 字段至少包括：
     id
     title
     authors
     summary
     source
     source_category
     url
     pdf_url
     published
     fetched_at
     rule_score
     matched_keywords
     llm_score
     llm_category
     llm_decision
     llm_reason
     note_priority
     status

6. paper_radar/storage.py
   - 使用 sqlite3 或 SQLAlchemy 管理 data/papers.db。
   - 支持：
     初始化表
     upsert paper
     根据 url 或 arxiv id 去重
     查询未筛选论文
     查询待 LLM 评分论文
     查询某日期的候选论文
   - 不要重复插入同一篇论文。

7. paper_radar/sources/arxiv_rss.py
   - 使用 feedparser 抓取 arXiv RSS。
   - 解析 title、authors、summary、url、published、category。
   - 尽量生成 pdf_url。
   - 注意处理 RSS 字段缺失的情况。
   - 抓取失败时不要让整个流程崩溃，要记录日志。

8. paper_radar/scoring.py
   - 实现关键词规则筛选。
   - 标题和摘要都要匹配。
   - 匹配时大小写不敏感。
   - 输出 rule_score 和 matched_keywords。
   - matched_keywords 要保留主题组，例如：
     brain_signals: EEG
     ai_core: diffusion model

9. paper_radar/llm/router.py
   - 优先复用现有 ~/ai_workspace/scripts/llm_router.py。
   - 如果复用困难，则实现一个简单 OpenAI-compatible client。
   - API key、base_url、model 从 .env 读取。
   - 要有超时、失败重试、JSON 解析失败处理。
   - LLM 调用失败时，论文状态标记为 llm_failed，不要中断整个 run_daily。

10. paper_radar/llm/prompts.py
    - 实现 LLM 初筛 prompt。
    - 输入：
      title
      abstract
      source
      category
      matched_keywords
    - 让 LLM 输出严格 JSON：
      {
        "relevance_score": 0-10,
        "category": ["brain_signal", "brain_decoding", "neuroscience", "ai_core", "ai_sota", "irrelevant"],
        "decision": "read" | "skim" | "skip",
        "reason": "简短中文说明",
        "keywords": ["关键词"],
        "note_priority": "high" | "medium" | "low"
      }
    - prompt 要说明我的研究兴趣：
      脑信号、EEG、fMRI、MEG、ECoG、EMG、EOG、BCI、神经解码、视觉解码、图像/视频重建、神经科学、多模态学习、CLIP、diffusion、LLM、VLM、agent、reasoning、benchmark、AI SOTA。

11. scripts/fetch_arxiv.py
    - 从 config/sources.yaml 读取 enabled 的 arXiv RSS 源。
    - 抓取并写入 SQLite。
    - 打印抓取数量、新增数量、重复数量。

12. scripts/filter_papers.py
    - 对未筛选论文做关键词规则评分。
    - 更新 rule_score、matched_keywords、status。
    - rule_score 低于阈值可以标记为 rule_skipped。
    - 高于阈值标记为 llm_pending。

13. scripts/score_with_llm.py
    - 对 llm_pending 的论文进行 LLM 评分。
    - 支持参数限制数量，例如：
      python scripts/score_with_llm.py --limit 50
    - 更新 llm_score、llm_category、llm_decision、llm_reason、note_priority、status。
    - read / skim / skip 都要保存。

14. paper_radar/markdown.py
    - 生成 Obsidian 友好的 Markdown。
    - Daily note 结构如下：

      # Paper Radar - YYYY-MM-DD

      ## 今日概览
      - 抓取论文数：
      - 初筛通过：
      - LLM 推荐精读：
      - LLM 推荐略读：

      ## 强相关，建议精读

      ### 1. Paper Title
      - Source:
      - Category:
      - Published:
      - URL:
      - PDF:
      - Relevance:
      - Tags:
      - Matched Keywords:
      - Reason:
      - 一句话判断：

      ## 中等相关，建议略读

      ## AI SOTA / 方法进展

      ## 脑信号 / 神经科学相关

      ## 跳过但可留意

    - 每篇论文要包含 arXiv 链接和 pdf 链接。
    - 适合直接保存到 Obsidian。

15. scripts/generate_daily_note.py
    - 根据当天或指定日期生成日报。
    - 支持参数：
      --date YYYY-MM-DD
    - 同时输出到：
      paper_radar/notes/daily/
      以及 config/output.yaml 中指定的 Obsidian 路径。

16. scripts/run_daily.py
    - 一键执行：
      fetch_arxiv.py
      filter_papers.py
      score_with_llm.py
      generate_daily_note.py
    - 支持参数：
      --limit-llm 50
      --date YYYY-MM-DD
      --no-llm
    - --no-llm 模式只做 RSS 抓取和关键词筛选，然后生成日报。

17. README.md
    - 写清楚：
      安装依赖
      配置 .env
      如何运行
      如何修改关键词
      如何修改 arXiv 源
      如何输出到 Obsidian
      如何设置 Windows 任务计划程序或 Linux cron 每天自动运行

18. requirements.txt
    至少包含：
    feedparser
    pyyaml
    python-dotenv
    requests
    pydantic 或 SQLAlchemy 二选一
    openai 如果使用 OpenAI-compatible client

代码质量要求：
- Python 3.10+
- 函数要模块化，不要把所有逻辑写在一个脚本里。
- 所有路径都从配置读取，避免硬编码。
- 有基础日志。
- 对网络失败、API 失败、JSON 解析失败要有容错。
- 命令行脚本要能从项目根目录直接运行。
- 第一版不要下载 PDF，不做全文解析。
- 后续要方便扩展到 bioRxiv、medRxiv、PubMed、OpenReview、Hugging Face Papers 和 PDF 精读。

请先：
1. 检查当前 ~/ai_workspace 结构，判断已有 LLM router 和 Obsidian 输出逻辑能否复用。
2. 给出你计划新增/修改的文件列表。
3. 再逐步实现第一版 MVP。
4. 实现后给出测试命令，例如：
   python scripts/run_daily.py --no-llm
   python scripts/run_daily.py --limit-llm 20
5. 最后说明生成的 Markdown 日报在哪里。