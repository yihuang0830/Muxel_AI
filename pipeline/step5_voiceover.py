import asyncio
import re
from pathlib import Path

import edge_tts

VOICE_MAP = {
    "male": "zh-CN-YunyangNeural",
    "female": "zh-CN-XiaoxiaoNeural",
}


def _clean_script(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if re.match(r"^\[MUSIC:", line.strip()):
            continue
        line = re.sub(r"^#+\s*", "", line)
        lines.append(line)
    return "\n".join(lines).strip()


async def _generate_async(text: str, voice: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def generate(ep_dir: Path, host: dict) -> None:
    """把稿本去掉音乐标记后用 edge-tts 合成配音，写入 05_voiceover.mp3。"""
    script = (ep_dir / "03_script_cn.md").read_text()
    clean_text = _clean_script(script)
    voice = VOICE_MAP.get(host.get("gender", "male"), VOICE_MAP["male"])
    output_path = ep_dir / "05_voiceover.mp3"
    asyncio.run(_generate_async(clean_text, voice, output_path))
