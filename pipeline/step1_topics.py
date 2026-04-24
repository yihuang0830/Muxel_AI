import os
from pathlib import Path
from datetime import date
from openai import OpenAI


def _get_season(month: int) -> str:
    if month in (3, 4, 5): return "春天"
    if month in (6, 7, 8): return "夏天"
    if month in (9, 10, 11): return "秋天"
    return "冬天"


def _client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["QWEN_API_KEY"],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )


def _system_prompt(show: dict) -> str:
    today = date.today()
    return f"""你叫小柒，是「{show['name_cn']}」的节目助理，跟了导演好几年了。

你对这档节目的理解：{show['style_description']}
今天：{today.strftime('%Y年%m月%d日')}，{_get_season(today.month)}

你的工作状态：
导演跟你说了这期想做什么之后，你会用自己的话把你听到的方向、情绪、音乐感觉复述给他确认。就像你在脑子里过了一遍，然后告诉他「我理解是这样的，对吗？」

注意：
- 只复述方向和感觉，不帮他想标题、开场白、歌单，那些是后面的事
- 说人话，不要用诗意比喻或文艺修辞，直接说清楚就好
- 用 bullet points 汇报你的理解，每条一句话，简单明了
- 如果导演说偏了或者补充了，你就重新列一遍 bullet points 更新理解"""


def reflect(user_notes: str, show: dict) -> str:
    """收到用户的初始想法，返回 AI 的理解复述。"""
    response = _client().chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": _system_prompt(show)},
            {"role": "user", "content": user_notes},
        ],
        max_tokens=300,
    )
    return response.choices[0].message.content


def chat_reply(messages: list[dict], show: dict) -> str:
    """在对话中继续调整理解，messages 是完整对话历史（不含 system）。"""
    response = _client().chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "system", "content": _system_prompt(show)}] + messages,
        max_tokens=300,
    )
    return response.choices[0].message.content
