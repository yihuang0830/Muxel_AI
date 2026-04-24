import os
import json
from pathlib import Path
from openai import OpenAI


def _client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["QWEN_API_KEY"],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )


def _format_candidates(tracks: list[dict]) -> str:
    lines = [f"- {t['title']} / {t['artist']}" for t in tracks]
    return "\n".join(lines)


def generate(ep_dir: Path, show: dict, song_count: int = 10) -> None:
    """小张根据 01_topics.md 的方向生成歌单，写入 02_playlist.json。"""
    from pipeline.music_db import extract_tags_from_direction, search_by_tags

    topic_file = ep_dir / "01_topics.md"
    if not topic_file.exists():
        raise FileNotFoundError("找不到 01_topics.md，请先完成 Step 1")

    topic_direction = topic_file.read_text().strip()

    # 1. 从方向提取 Last.fm tags，查询真实候选曲库
    candidates_section = ""
    try:
        tags = extract_tags_from_direction(topic_direction, show["style_description"])
        candidates = search_by_tags(tags, limit=50)
        if candidates:
            candidates_section = f"\n\n以下是根据风格标签（{', '.join(tags)}）从音乐数据库找到的真实曲目，请优先从中挑选：\n{_format_candidates(candidates)}\n\n如果候选里没有合适的，可以补充你认为适合的歌曲。"
    except Exception:
        pass  # Last.fm 不可用时降级为纯 LLM 模式

    # 2. 让小张从候选池里策划歌单
    prompt_template = (Path(__file__).parent.parent / "prompts" / "playlist.md").read_text()
    prompt = prompt_template.format(
        show_name=show["name_cn"],
        show_style=show["style_description"],
        topic_direction=topic_direction + candidates_section,
        song_count=song_count,
    )

    response = _client().chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3000,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    playlist = json.loads(raw)
    (ep_dir / "02_playlist.json").write_text(
        json.dumps(playlist, ensure_ascii=False, indent=2)
    )


def chat_reply(messages: list[dict], playlist: dict, show: dict) -> tuple[str, list[dict]]:
    """小张在对话中回应，返回 (回复文本, 要新增的歌曲列表)。"""
    existing_titles = [s["title"] for s in playlist.get("songs", [])]
    system = f"""你叫小张，是「{show['name_cn']}」的资深乐评人顾问，写了多年乐评，什么风格都听过。

这期节目方向：{playlist.get('theme_summary', '')}

你全权负责维护这份歌单，导演只管提需求，你来决定怎么改。
- 导演说加什么，你加，说明理由
- 导演说去掉什么，你去掉
- 导演说感觉缺点什么风格，你自己判断加什么
- 说话直接，不废话

每次回复必须返回以下 JSON 格式，不要有任何其他文字：
{{
  "reply": "你对导演说的话",
  "add_songs": [
    {{
      "title": "歌名",
      "artist": "艺人",
      "album": "",
      "reason": "为什么加这首",
      "mood_tags": ["标签"]
    }}
  ],
  "remove_titles": ["要删掉的歌名"],
  "reorder_titles": ["按新顺序列出所有歌名"]
}}

- 不需要加歌时 add_songs 为 []
- 不需要删歌时 remove_titles 为 []
- 不需要改顺序时 reorder_titles 为 []，需要改顺序时列出全部歌名的新排列"""

    response = _client().chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=1200,
    )
    raw = response.choices[0].message.content.strip()

    # 去掉 markdown 代码块
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break

    # 提取第一个完整 JSON 对象（防止模型在 JSON 后面多说了话）
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        raw = raw[start:end]
        result = json.loads(raw)
        add_songs = result.get("add_songs", [])

        # 用 Last.fm 验证并补全新增歌曲的专辑信息
        if add_songs:
            try:
                from pipeline.music_db import verify_track
                verified = []
                for s in add_songs:
                    info = verify_track(s["title"], s["artist"])
                    if info:
                        verified.append({**s, "artist": info["artist"], "album": info["album"]})
                    else:
                        verified.append(s)  # 验证失败就保留原样
                add_songs = verified
            except Exception:
                pass

        return result["reply"], add_songs, result.get("remove_titles", []), result.get("reorder_titles", [])
    except (ValueError, json.JSONDecodeError):
        return raw or "（小张没有回应，请再试一次）", [], [], []


def append(ep_dir: Path, show: dict, extra_count: int = 3) -> list[dict]:
    """让小张再追加几首，返回新增歌曲列表（调用方负责合并和保存）。"""
    topic_direction = (ep_dir / "01_topics.md").read_text().strip()
    existing = json.loads((ep_dir / "02_playlist.json").read_text())
    existing_titles = [s["title"] for s in existing["songs"]]

    prompt = f"""你叫小张，给「{show['name_cn']}」做歌单顾问。

这期方向：{existing['theme_summary']}

已经有这些歌了：{', '.join(existing_titles)}

再推 {extra_count} 首，不要和已有的重复，同样的 JSON 格式，只输出 songs 数组：

[
  {{
    "title": "歌名",
    "artist": "艺人",
    "album": "",
    "reason": "推荐理由",
    "mood_tags": ["标签"]
  }}
]"""

    response = _client().chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(raw)
