from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value not in (None, '') else default


def _path_env(name: str, default: str) -> Path:
    return Path(_env(name, default)).expanduser().resolve()


APP_ENV = _env('APP_ENV', 'local')
WORKSPACE_ROOT = _path_env('WORKSPACE_ROOT', '/mnt/f/AIWorkspace')

INPUT_ROOT = _path_env('INPUT_ROOT', str(WORKSPACE_ROOT / 'input'))
UPLOADS_ROOT = _path_env('UPLOADS_ROOT', str(WORKSPACE_ROOT / 'uploads'))
PROCESSED_ROOT = _path_env('PROCESSED_ROOT', _env('PROCESSED_DIR', str(WORKSPACE_ROOT / 'processed')))
PROCESSED_MD = _path_env('PROCESSED_MD', str(PROCESSED_ROOT / 'markdown'))
PROCESSED_TRANSCRIPTS = _path_env('PROCESSED_TRANSCRIPTS', str(PROCESSED_ROOT / 'transcripts'))
PROCESSED_JSON = _path_env('PROCESSED_JSON', str(PROCESSED_ROOT / 'json'))
NOTES_ROOT = _path_env('NOTES_ROOT', str(WORKSPACE_ROOT / 'notes'))
REPOS_ROOT = _path_env('REPOS_ROOT', str(WORKSPACE_ROOT / 'repos' / 'allowed'))
READ_REPOS_ROOT = _path_env('READ_REPOS_ROOT', str(REPOS_ROOT))
WRITE_REPOS_ROOT = _path_env('WRITE_REPOS_ROOT', str(WORKSPACE_ROOT / 'repos' / 'allowed'))
TASKS_ROOT = _path_env('TASKS_ROOT', str(WORKSPACE_ROOT / 'tasks'))
KB_DIR = _path_env('KB_DIR', str(WORKSPACE_ROOT / 'kb'))
LOG_DIR = _path_env('LOG_DIR', str(WORKSPACE_ROOT / 'logs'))

OBSIDIAN_VAULT = _path_env('OBSIDIAN_VAULT', '/mnt/f/ObsidianVault')
OBSIDIAN_AI_ROOT = _path_env('OBSIDIAN_AI_ROOT', str(OBSIDIAN_VAULT / 'AI'))
OBSIDIAN_OUT = _path_env('OBSIDIAN_OUT', str(OBSIDIAN_AI_ROOT))

# Backward-compatible aliases used by older scripts.
INBOX_DIR = INPUT_ROOT

GEN_PROVIDER = _env('GEN_PROVIDER', _env('LLM_PROVIDER', 'deepseek'))
LLM_TEMPERATURE = float(_env('LLM_TEMPERATURE', '0.2'))
LLM_MAX_TOKENS = int(_env('LLM_MAX_TOKENS', '4096'))

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = _env('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
DEEPSEEK_MODEL = _env('DEEPSEEK_MODEL', 'deepseek-chat')

DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', '')
DASHSCOPE_BASE_URL = _env('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
DASHSCOPE_MODEL = _env('DASHSCOPE_MODEL', 'qwen-plus')

SILICONFLOW_API_KEY = os.getenv('SILICONFLOW_API_KEY', '')
SILICONFLOW_BASE_URL = _env('SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1')
SILICONFLOW_MODEL = _env('SILICONFLOW_MODEL', 'Qwen/Qwen2.5-7B-Instruct')

EMBED_PROVIDER = _env('EMBED_PROVIDER', 'local')
EMBED_MODEL = _env('EMBED_MODEL', '/mnt/f/AIModels/bge-small-zh-v1.5')
EMBED_DEVICE = _env('EMBED_DEVICE', 'cpu')

CHROMA_HOST = _env('CHROMA_HOST', 'localhost')
CHROMA_PORT = int(_env('CHROMA_PORT', '8000'))
CHROMA_COLLECTION = _env('CHROMA_COLLECTION', 'learning_docs')


@dataclass(frozen=True)
class EmbedConfig:
    provider: str
    model: str
    device: str


def get_embed_config() -> EmbedConfig:
    return EmbedConfig(provider=EMBED_PROVIDER, model=EMBED_MODEL, device=EMBED_DEVICE)


def ensure_dirs() -> None:
    for path in [
        INPUT_ROOT / 'pdf',
        INPUT_ROOT / 'web',
        INPUT_ROOT / 'video',
        INPUT_ROOT / 'text',
        INPUT_ROOT / 'projects',
        UPLOADS_ROOT,
        PROCESSED_MD,
        PROCESSED_TRANSCRIPTS,
        PROCESSED_JSON,
        NOTES_ROOT,
        READ_REPOS_ROOT,
        REPOS_ROOT,
        WRITE_REPOS_ROOT,
        TASKS_ROOT / 'pending',
        TASKS_ROOT / 'running',
        TASKS_ROOT / 'finished',
        KB_DIR,
        LOG_DIR,
        OBSIDIAN_AI_ROOT / 'pdf',
        OBSIDIAN_AI_ROOT / 'web',
        OBSIDIAN_AI_ROOT / 'video',
        OBSIDIAN_AI_ROOT / 'text',
        OBSIDIAN_AI_ROOT / 'projects',
        OBSIDIAN_AI_ROOT / 'review',
    ]:
        path.mkdir(parents=True, exist_ok=True)
