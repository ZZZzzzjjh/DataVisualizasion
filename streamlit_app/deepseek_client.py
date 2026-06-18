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


def get_config(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value

    try:
        import streamlit as st

        secret_value = st.secrets.get(name)
    except Exception:
        secret_value = None

    return str(secret_value) if secret_value else default


def has_api_key() -> bool:
    return bool(get_config("DEEPSEEK_API_KEY"))


def analyze_with_deepseek(question: str, data_context: str) -> str:
    api_key = get_config("DEEPSEEK_API_KEY")
    if not api_key:
        return "未配置 DEEPSEEK_API_KEY。请先在 .env 文件中配置后再使用智能分析。"

    system_prompt = (
        "你是一个面向普通用户的城市就业与生活成本决策助手。"
        "你的重点是帮助用户根据薪资、生活成本、租房压力、就业机会和城市偏好做选择，"
        "而不是写课程报告或论文分析。"
        "请严格基于用户提供的城市数据进行中文回答，不要编造数据。"
        "回答要直接、友好、实用，优先说明对用户个人决策有帮助的结论、风险和取舍；"
        "涉及金额时使用“元/月”。如果数据存在估算或缺失，请用用户能理解的话说明局限。"
    )
    user_prompt = f"""
用户问题：
{question}

可用城市数据：
{data_context}

输出要求：
1. 先直接回答用户的问题，给出可执行建议
2. 说明推荐或不推荐的关键原因，重点放在用户关心的薪资、成本、租房和结余
3. 如果有多个城市，按适合程度排序，并指出各自适合什么类型的人
4. 给出需要注意的风险或前提，例如数据缺失、估算口径、个人偏好差异
5. 不要写成课程报告口吻，不要给报告写作建议，不要使用没有数据支撑的判断
"""

    payload: dict[str, Any] = {
        "model": get_config("DEEPSEEK_MODEL", "deepseek-chat"),
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
        api_url = get_config("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
        response = requests.post(api_url, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        return f"DeepSeek 调用失败：{exc}"
