import os
import json
from pathlib import Path
from openai import OpenAI


def _client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["QWEN_API_KEY"],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )


def generate(ep_dir: Path, host: dict, show: dict) -> None:
    """像素根据选题方向和歌单写中文主持稿，写入 03_script_cn.md。"""
    topic = (ep_dir / "01_topics.md").read_text().strip()
    playlist = json.loads((ep_dir / "02_playlist.json").read_text())

    songs_text = "\n".join(
        f"{i+1}. 《{s['title']}》— {s['artist']}\n   小张的理由：{s.get('reason', '（无）')}"
        for i, s in enumerate(playlist.get("songs", []))
    )

    prompt = f"""你是「{show['name_cn']}」的电台主持人，名叫{host['name_cn']}。
{host['description_cn']}。说话风格：{host['style_cn']}。

这期节目的选题方向：
{topic}

确认的歌单（按播出顺序）：
{songs_text}

请写这期节目的完整中文主持稿。格式要求：
- 开场白：介绍本期主题，带入情绪，1-2分钟的量
- 每首歌之前：写歌曲介绍（背景、创作故事、为什么在这里放这首），30-60秒的量。结合小张给的理由，但用你自己的语气重新说，不要照搬
- 每首歌之后：一两句过渡语，自然引向下一首
- 结语：收尾本期主题，1分钟的量

格式用 Markdown，每首歌的位置用 `[MUSIC: 歌名 - 艺人]` 标注。
直接输出稿子，不要有额外说明。"""

    response = _client().chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=5000,
    )

    (ep_dir / "03_script_cn.md").write_text(response.choices[0].message.content)
