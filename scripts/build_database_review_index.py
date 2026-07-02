from __future__ import annotations

import re
from pathlib import Path


SOURCE_DIR = Path("/mnt/f/auto_notes/data/notes/数据库技术")
OUTPUT_DIR = SOURCE_DIR / "整理输出"
EXCLUDED = {}
TITLE_OVERRIDES = {
    "数据库技术-0303-1400.md": "数据库系统概论：核心概念、DBMS与数据独立性",
    "数据库技术-0303-1455.md": "数据管理演进、数据独立性与E-R模型",
    "数据库技术-0310-1400.md": "三元联系、实体判定与数据模型演进",
    "数据库技术-0331-1400.md": "关系代数高级查询与关系规范化理论入门",
    "数据库技术-0411-1455.md": "范式判断、3NF与BCNF",
    "数据库技术-0616-1400.md": "并发控制收尾、意向锁与全书期末复习",
    "数据库技术-0616-1455.md": "期末答疑、模拟卷说明与课程收尾",
    "数据库技术-0421-1455.md": "SQL表修改、索引与SELECT执行顺序",
    "数据库技术-0428-1400.md": "SQL单表查询、分组、排序与空值",
    "数据库技术-0428-1455.md": "SQL连接查询、子查询与量词",
    "数据库技术-0529-1600.md": "数据库物理存储、记录与文件组织",
    "数据库技术-0609-1455.md": "日志、WAL、检查点与数据库恢复",
}


def first_title(text: str, fallback: str) -> str:
    patterns = (r"^#{2,3}\s+学习笔记[：:]\s*(.+)$",)
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            return match.group(1).strip()
    return fallback


def section(text: str, start: str, ends: tuple[str, ...]) -> str:
    match = re.search(start, text, re.MULTILINE)
    if not match:
        return ""
    tail = text[match.end() :]
    end_positions = []
    for pattern in ends:
        end_match = re.search(pattern, tail, re.MULTILINE)
        if end_match:
            end_positions.append(end_match.start())
    value = tail[: min(end_positions)] if end_positions else tail
    return value.strip()


def compact(value: str) -> str:
    lines = []
    blank = False
    for raw_line in value.replace("\r\n", "\n").splitlines():
        line = raw_line.rstrip()
        if not line:
            if lines and not blank:
                lines.append("")
            blank = True
            continue
        if line.startswith("```mermaid") or line.startswith("graph "):
            break
        heading = re.match(r"^(#{1,6})(\s+.*)$", line)
        if heading:
            level = min(6, len(heading.group(1)) + 2)
            line = f"{'#' * level}{heading.group(2)}"
        lines.append(line)
        blank = False
    return "\n".join(lines).strip()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    documents = []
    for path in sorted(SOURCE_DIR.glob("数据库技术-*.md")):
        if path.name in EXCLUDED:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        summary = section(
            text,
            r"^#{2,4}\s+(?:\d+\.\s*)?核心知识点总结.*$",
            (
                r"^#{2,4}\s+(?:\d+\.\s*)?老师原话强调回顾.*$",
                r"^#\s+4\.",
                r"^#\s+5\.",
            ),
        )
        emphasis = section(
            text,
            r"^#{2,4}\s+(?:\d+\.\s*)?老师原话强调回顾.*$",
            (
                r"^#\s+4\.",
                r"^#\s+5\.",
                r"^#{2,3}\s+4\.1\s+知识点层级结构",
            ),
        )
        exercises = section(
            text,
            r"^#{2,4}\s+5\.2\s+自测练习题.*$",
            (
                r"^#{2,4}\s+5\.3\s+难点突破指南",
                r"^#{2,4}\s+5\.4\s+学习建议",
                r"^#\s+6\.",
            ),
        )
        documents.append(
            {
                "path": path,
                "title": TITLE_OVERRIDES.get(path.name, first_title(text, path.stem)),
                "summary": compact(summary),
                "emphasis": compact(emphasis),
                "exercises": compact(exercises),
            }
        )

    lines = [
        "# 数据库技术逐课重点与原题索引",
        "",
        "> 自动从原笔记的结构化章节中抽取。原始文件未被修改。",
        "",
        f"- 纳入课程：{len(documents)} 份",
        f"- 排除文件：{len(EXCLUDED)} 份",
        "",
        "## 排除记录",
        "",
    ]
    for name, reason in EXCLUDED.items():
        lines.append(f"- `{name}`：{reason}。")

    lines.extend(["", "## 课程目录", ""])
    for index, doc in enumerate(documents, 1):
        anchor = re.sub(r"[^\w\u4e00-\u9fff-]", "", f"{index}-{doc['title']}").lower()
        lines.append(f"{index}. [{doc['title']}](#{anchor}) - `{doc['path'].name}`")

    for index, doc in enumerate(documents, 1):
        lines.extend(
            [
                "",
                "---",
                "",
                f"## {index}. {doc['title']}",
                "",
                f"来源：[{doc['path'].name}](../{doc['path'].name})",
                "",
                "### 核心知识点",
                "",
                doc["summary"] or "_原笔记未提供独立的核心总结章节。_",
                "",
                "### 教师强调与易错点",
                "",
                doc["emphasis"] or "_原笔记未提供独立的教师强调章节。_",
                "",
                "### 原笔记练习",
                "",
                doc["exercises"] or "_原笔记未提供可稳定抽取的练习章节。_",
            ]
        )

    output = OUTPUT_DIR / "01-逐课重点与原题索引.md"
    output.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(output)
    print(f"documents={len(documents)}")


if __name__ == "__main__":
    main()
