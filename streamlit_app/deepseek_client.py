from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]


def load_env_file() -> None:
    for path in [ROOT / ".env", Path(__file__).resolve().parent / ".env"]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


def has_api_key() -> bool:
    return bool(os.getenv("DEEPSEEK_API_KEY"))


def analyze_with_deepseek(question: str, data_context: str) -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return "未配置 DEEPSEEK_API_KEY。请先在 .env 文件中配置后再使用智能分析。"

    system_prompt = (
        "你是一个数据可视化课程项目的智能分析助手。"
        "请严格基于用户提供的城市数据进行中文分析，不要编造数据。"
        "回答要清晰、具体、适合写进课程报告；涉及金额时使用“元/月”。"
        "如果数据存在估算或缺失，请说明局限。"
    )
    user_prompt = f"""
用户问题：
{question}

可用城市数据：
{data_context}

输出要求：
1. 先给出明确结论
2. 再用数据解释原因
3. 给出可视化或报告写作建议
4. 不要使用没有数据支撑的判断
"""

    payload: dict[str, Any] = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.35,
        "max_tokens": 1400,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        api_url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
        response = requests.post(api_url, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        return f"DeepSeek 调用失败：{exc}"
