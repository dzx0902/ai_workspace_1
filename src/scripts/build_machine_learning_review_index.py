from __future__ import annotations

import re
from pathlib import Path


SOURCE_DIR = Path("/mnt/f/auto_notes/data/notes/机器学习")
OUTPUT_DIR = SOURCE_DIR / "整理输出"
TITLE_OVERRIDES = {
    "机器学习-0306-0855.md": "最大似然估计、损失函数与鲁棒回归",
    "机器学习-0331-1000.md": "过拟合、岭回归、核岭回归与样条函数",
    "机器学习-0403-0855.md": "正则化几何、表示定理与贝叶斯解释",
    "机器学习-0410-0800.md": "正则化、贝叶斯岭回归与表示者定理",
    "机器学习-0417-0800.md": "Mini-batch、Momentum与AdaGrad",
    "机器学习-0417-0855.md": "RMSProp、Adam与卷积神经网络基础",
    "机器学习-0512-1000.md": "GAN、VAE理论与PCA引论",
    "机器学习-0526-1000.md": "EM算法：Q函数构造与化简",
    "机器学习-0609-1000.md": "神经网络可解释性：交互作用理论、机理审计与泛化",
    "机器学习-0609-1055.md": "大模型过拟合机理、泛化交互与表征优化",
    "机器学习-0616-1000.md": "期末复习上：线性模型、分类、SVM与正则化",
    "机器学习-0616-1055.md": "期末复习下：网络设计、反向传播、GAN/VAE、PCA与EM",
}


def first_title(text: str, fallback: str) -> str:
    match = re.search(r"^#{2,3}\s+学习笔记[：:]\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def section(text: str, start: str, ends: tuple[str, ...]) -> str:
    match = re.search(start, text, re.MULTILINE)
    if not match:
        return ""
    tail = text[match.end() :]
    positions = []
    for pattern in ends:
        end_match = re.search(pattern, tail, re.MULTILINE)
        if end_match:
            positions.append(end_match.start())
    return tail[: min(positions)] if positions else tail


def compact(value: str) -> str:
    lines: list[str] = []
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
    for path in sorted(SOURCE_DIR.glob("机器学习-*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        documents.append(
            {
                "path": path,
                "title": TITLE_OVERRIDES.get(path.name, first_title(text, path.stem)),
                "summary": compact(
                    section(
                        text,
                        r"^#{2,4}\s+(?:\d+\.\s*)?核心知识点总结.*$",
                        (
                            r"^#{2,4}\s+(?:\d+\.\s*)?老师原话强调回顾.*$",
                            r"^#\s+4\.",
                            r"^#\s+5\.",
                        ),
                    )
                ),
                "emphasis": compact(
                    section(
                        text,
                        r"^#{2,4}\s+(?:\d+\.\s*)?老师原话强调回顾.*$",
                        (
                            r"^#\s+4\.",
                            r"^#\s+5\.",
                            r"^#{2,3}\s+4\.1\s+知识点层级结构",
                        ),
                    )
                ),
                "exercises": compact(
                    section(
                        text,
                        r"^#{2,4}\s+5\.2\s+自测练习题.*$",
                        (
                            r"^#{2,4}\s+5\.3\s+难点突破指南",
                            r"^#{2,4}\s+5\.4\s+学习建议",
                            r"^#\s+6\.",
                        ),
                    )
                ),
            }
        )

    lines = [
        "# 机器学习逐课重点与原题索引",
        "",
        f"> 自动从 {len(documents)} 份原笔记的结构化章节中抽取。原始文件未被修改。",
        "> 自动转写中的符号、上下标和矩阵转置可能失真，正式推导以课件和教材为准。",
        "",
        f"- 纳入课程：{len(documents)} 份",
        "- 时间范围：2026-03-03 至 2026-06-16",
        "",
        "## 课程目录",
        "",
    ]
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
