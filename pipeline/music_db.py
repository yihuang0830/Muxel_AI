import os
import requests

LASTFM_BASE = "https://ws.audioscrobbler.com/2.0/"


def _get(method: str, **params) -> dict:
    resp = requests.get(LASTFM_BASE, params={
        "method": method,
        "api_key": os.environ["LASTFM_API_KEY"],
        "format": "json",
        **params,
    }, timeout=10)
    resp.raise_for_status()
    return resp.json()


def search_by_tags(tags: list[str], limit: int = 40) -> list[dict]:
    """按风格/情绪 tag 搜索真实歌曲，返回多个 tag 的合并去重结果。"""
    seen = set()
    tracks = []
    for tag in tags[:3]:  # 最多取前三个 tag
        try:
            data = _get("tag.gettoptracks", tag=tag, limit=limit // len(tags[:3]))
            for t in data.get("tracks", {}).get("track", []):
                key = (t["name"].lower(), t["artist"]["name"].lower())
                if key not in seen:
                    seen.add(key)
                    tracks.append({
                        "title": t["name"],
                        "artist": t["artist"]["name"],
                        "album": "",
                        "listeners": int(t.get("listeners", 0) or 0),
                    })
        except Exception:
            continue
    return tracks


def get_artist_top_tracks(artist: str, limit: int = 10) -> list[dict]:
    """获取某艺人的代表曲目。"""
    try:
        data = _get("artist.gettoptracks", artist=artist, limit=limit)
        return [
            {
                "title": t["name"],
                "artist": artist,
                "album": "",
                "listeners": int(t.get("listeners", 0) or 0),
            }
            for t in data.get("toptracks", {}).get("track", [])
        ]
    except Exception:
        return []


def verify_track(title: str, artist: str) -> dict | None:
    """验证歌曲是否存在，返回补全后的信息（专辑、正确艺人名），找不到返回 None。"""
    try:
        data = _get("track.getInfo", track=title, artist=artist)
        track = data.get("track")
        if not track:
            return None
        return {
            "title": track["name"],
            "artist": track["artist"]["name"],
            "album": track.get("album", {}).get("title", "") if isinstance(track.get("album"), dict) else "",
            "listeners": int(track.get("listeners", 0) or 0),
        }
    except Exception:
        return None


def extract_tags_from_direction(direction: str, show_style: str) -> list[str]:
    """从选题方向文本里提取适合 Last.fm 的 tag，用 LLM 做。"""
    import os
    from openai import OpenAI
    client = OpenAI(
        api_key=os.environ["QWEN_API_KEY"],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    prompt = f"""根据以下节目方向，提取 3-5 个适合在 Last.fm 上搜索的音乐风格/情绪标签。
只输出英文标签，用逗号分隔，不要其他文字。
标签要具体，比如 "indie folk"、"bedroom pop"、"neo soul"，不要太宽泛如 "pop" 或 "music"。

节目方向：{direction}
节目风格：{show_style}"""

    response = client.chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
    )
    raw = response.choices[0].message.content.strip()
    return [t.strip() for t in raw.split(",") if t.strip()]
