import os
import json
from pathlib import Path
from openai import OpenAI


def _client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["QWEN_API_KEY"],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )


def _build_context(ep_dir: Path, show: dict) -> str:
    topic = (ep_dir / "01_topics.md").read_text().strip()
    playlist = json.loads((ep_dir / "02_playlist.json").read_text())
    songs_brief = "、".join(f"《{s['title']}》" for s in playlist.get("songs", []))
    theme = playlist.get("theme_summary", "")
    script_file = ep_dir / "03_script_cn.md"
    script_excerpt = script_file.read_text()[:600].strip() if script_file.exists() else ""
    return f"节目：{show['name_cn']}\n主题：{theme}\n选题方向：{topic}\n歌单：{songs_brief}\n开场摘录：{script_excerpt}"


def generate(ep_dir: Path, show: dict) -> None:
    """根据选题、歌单、稿本生成 B站上传文案，写入 07_metadata.md。"""
    context = _build_context(ep_dir, show)

    prompt = f"""你是一个自媒体运营，负责给音乐电台节目写 B站 上传文案。

{context}

要求：
- 标题：吸引眼球，含节目名「{show['name_cn']}」，不超过 80 字，可以用竖线或 | 分隔层次
- 简介：2-3 段，介绍本期氛围/主题/适合谁听，结尾引导关注，口语自然，不要套话
- 标签：12-15 个，用空格分隔，涵盖音乐类型、情绪、艺人名、场景关键词

直接输出以下格式，不要额外说明：

# B站上传文案

**标题**
[标题]

**简介**
[简介]

**标签**
[标签1 标签2 标签3]"""

    response = _client().chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
    )
    (ep_dir / "07_metadata.md").write_text(response.choices[0].message.content)


def chat_reply(messages: list[dict], current_metadata: str, show: dict, ep_dir: Path) -> str:
    """根据导演反馈修改文案，返回完整新版本。"""
    context = _build_context(ep_dir, show)
    system = f"""你是「{show['name_cn']}」的自媒体运营。
{context}

当前文案：
{current_metadata}

导演给了修改意见，请根据意见输出完整修改后的文案（保持原格式），直接输出，不要加前缀说明。"""

    response = _client().chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=1500,
    )
    return response.choices[0].message.content
