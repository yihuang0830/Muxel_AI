import json
import subprocess
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
EPISODES_DIR = ROOT / "episodes"

STEPS = {
    1: "选题", 2: "歌单", 3: "稿本",
    4: "视觉素材", 5: "配音", 6: "去 PR 合成",
    7: "上传文案", 8: "发布",
}
APPROVAL_FILES = {
    2: "02_playlist.json",
    3: "03_script_cn.md",
    7: "07_metadata.md",
}


def load_status(ep_dir):
    f = ep_dir / "STATUS.json"
    return json.loads(f.read_text()) if f.exists() else {}

def save_status(ep_dir, status):
    (ep_dir / "STATUS.json").write_text(json.dumps(status, ensure_ascii=False, indent=2))

def load_config(host_id: str = None) -> dict:
    show = json.loads((ROOT / "config" / "show_format.json").read_text())
    hosts_data = json.loads((ROOT / "config" / "hosts.json").read_text())
    hosts = hosts_data["hosts"]
    if host_id:
        host = next((h for h in hosts if h["id"] == host_id), hosts[0])
    else:
        host = next((h for h in hosts if h["available"]), hosts[0])
    return {"host": host, "show": show, "all_hosts": hosts}

def load_chat(ep_dir, filename="chat_step1.json"):
    f = ep_dir / filename
    return json.loads(f.read_text()) if f.exists() else []

def save_chat(ep_dir, messages, filename="chat_step1.json"):
    (ep_dir / filename).write_text(json.dumps(messages, ensure_ascii=False, indent=2))

def list_episodes():
    if not EPISODES_DIR.exists():
        return []
    return sorted([d for d in EPISODES_DIR.iterdir() if d.is_dir()], reverse=True)

def run_cmd(*args):
    r = subprocess.run([sys.executable, "run.py", *args], cwd=ROOT, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


# ── 页面配置 ──────────────────────────────────────────────────────
st.set_page_config(page_title="像素电台", page_icon="📻", layout="wide")

# ── 侧边栏 ────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📻 像素电台")
    if st.button("＋ 新建一期", use_container_width=True, type="primary"):
        code, out = run_cmd("new")
        if code == 0:
            st.rerun()
        else:
            st.error(out)
    st.divider()
    episodes = list_episodes()
    if not episodes:
        st.caption("还没有节目，点上方按钮开始")
        st.stop()
    selected = st.radio("节目列表", [ep.name for ep in episodes], label_visibility="collapsed")

ep_dir = EPISODES_DIR / selected
status = load_status(ep_dir)
current_step = status.get("current_step", 1)

# ── 进度条 ────────────────────────────────────────────────────────
st.markdown(f"## {selected}")
cols = st.columns(len(STEPS))
for i, (num, name) in enumerate(STEPS.items()):
    with cols[i]:
        if num < current_step:
            if st.button(f"✅ {name}", key=f"nav_{num}", help=f"回到{name}"):
                status["current_step"] = num
                save_status(ep_dir, status)
                st.rerun()
        elif num == current_step:
            st.markdown(f"⏳ **{name}**")
        else:
            st.markdown(f"<span style='color:#888'>{name}</span>", unsafe_allow_html=True)
st.divider()

# ── Step 1：选题方向 ──────────────────────────────────────────────
if current_step == 1:
    chat_history = load_chat(ep_dir)

    # 还没提交过想法：显示输入框
    if not chat_history:
        st.markdown("### 这期你想做什么？")
        st.caption("随便写，不用格式。情绪、场景、风格、歌手名字……任何想法都行。")

        notes = st.text_area(
            "想法", height=200, label_visibility="collapsed",
            placeholder="比如：想做一期 R&B，最近在听 Frank Ocean，感觉有点夜晚城市的气息……",
        )
        if st.button("提交给 AI →", type="primary"):
            if not notes.strip():
                st.warning("先写点什么吧")
            else:
                config = load_config()
                from pipeline.step1_topics import reflect
                with st.spinner("理解中…"):
                    reply = reflect(notes, config["show"])
                history = [
                    {"role": "user", "content": notes},
                    {"role": "assistant", "content": reply},
                ]
                save_chat(ep_dir, history)
                st.rerun()

    # 已有对话历史：显示聊天 + 确认按钮
    else:
        # 确认按钮放最上面，方便快速确认
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("✅ 对，就这样", type="primary", use_container_width=True):
                # 把最后一条 AI 的理解保存为选题方向
                last_ai = next(m["content"] for m in reversed(chat_history) if m["role"] == "assistant")
                (ep_dir / "01_topics.md").write_text(last_ai)
                status["current_step"] = 2
                save_status(ep_dir, status)
                st.rerun()
        with col2:
            st.caption("AI 的理解和你想的一样就继续，不对就在下面告诉它哪里偏了")

        st.divider()

        # 显示历史对话
        for msg in chat_history:
            with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
                st.markdown(msg["content"])

        # 继续对话：用户消息立刻渲染，再等 LLM
        user_input = st.chat_input("哪里不对？补充一下……")
        if user_input:
            with st.chat_message("user"):
                st.markdown(user_input)
            chat_history.append({"role": "user", "content": user_input})

            config = load_config()
            from pipeline.step1_topics import chat_reply
            with st.chat_message("assistant"):
                with st.spinner(""):
                    reply = chat_reply(chat_history, config["show"])
                st.markdown(reply)
            chat_history.append({"role": "assistant", "content": reply})
            save_chat(ep_dir, chat_history)
            st.rerun()

# ── Step 2：小张的歌单 ────────────────────────────────────────────
elif current_step == 2:
    import pandas as pd
    playlist_file = ep_dir / "02_playlist.json"
    config = load_config()

    st.markdown("### 小张的歌单")

    # 还没生成 → 先让小张出手
    if not playlist_file.exists():
        st.caption("小张会根据你确认的方向推荐 10 首歌")
        if st.button("让小张来推 →", type="primary"):
            from pipeline.step2_playlist import generate
            with st.spinner("小张选歌中…"):
                generate(ep_dir, config["show"])
            st.rerun()

    else:
        playlist = json.loads(playlist_file.read_text())
        songs = playlist.get("songs", [])

        col_table, col_chat = st.columns([3, 2])

        # ── 左：只读歌单表格 ──────────────────────────────────
        with col_table:
            lastfm = playlist.get("_lastfm", {})
            if lastfm.get("candidate_count"):
                tags_str = "、".join(lastfm["tags"])
                lastfm_note = f"　·　Last.fm ✅ {lastfm['candidate_count']} 首候选（{tags_str}）"
            else:
                lastfm_note = "　·　Last.fm 未启用"
            st.caption(f"主题：{playlist.get('theme_summary', '')}　·　共 {len(songs)} 首{lastfm_note}")

            df = pd.DataFrame([{
                "#": i + 1,
                "歌名": s.get("title", ""),
                "艺人": s.get("artist", ""),
                "小张的理由": s.get("reason", ""),
            } for i, s in enumerate(songs)])

            st.dataframe(df, use_container_width=True, hide_index=True)

            if st.button("✅ 歌单确认，进入稿本", type="primary", use_container_width=True):
                status["current_step"] = 3
                save_status(ep_dir, status)
                st.rerun()

        # ── 右：和小张对话 ────────────────────────────────────
        with col_chat:
            st.caption("告诉小张要加什么、删什么，他会直接更新左边的歌单")

            chat2 = load_chat(ep_dir, "chat_step2.json")
            chat_box = st.container(height=480)
            with chat_box:
                for msg in chat2:
                    with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
                        st.markdown(msg["content"])

            user_input = st.chat_input("跟小张说……")
            if user_input:
                from pipeline.step2_playlist import chat_reply
                current_playlist = json.loads(playlist_file.read_text())

                with chat_box:
                    with st.chat_message("user"):
                        st.markdown(user_input)
                chat2.append({"role": "user", "content": user_input})

                with chat_box:
                    with st.chat_message("assistant"):
                        with st.spinner("小张想了想…"):
                            reply, add_songs, remove_titles, reorder_titles = chat_reply(chat2, current_playlist, config["show"])
                        st.markdown(reply)
                chat2.append({"role": "assistant", "content": reply})
                save_chat(ep_dir, chat2, "chat_step2.json")

                # 应用小张的修改
                updated = current_playlist["songs"]
                if remove_titles:
                    updated = [s for s in updated if s["title"] not in remove_titles]
                if add_songs:
                    updated = updated + add_songs
                if reorder_titles:
                    song_map = {s["title"]: s for s in updated}
                    updated = [song_map[t] for t in reorder_titles if t in song_map]
                    # 把 reorder 里没提到的歌追加到末尾（防止漏掉）
                    mentioned = set(reorder_titles)
                    updated += [s for s in current_playlist["songs"] if s["title"] not in mentioned]
                current_playlist["songs"] = updated
                playlist_file.write_text(json.dumps(current_playlist, ensure_ascii=False, indent=2))
                st.rerun()

# ── Step 3：主持稿 ────────────────────────────────────────────────
elif current_step == 3:
    script_file = ep_dir / "03_script_cn.md"
    host_id = status.get("host_id")
    config = load_config(host_id)

    st.markdown("### 主持稿")

    # ── 选主持人 ──────────────────────────────────────────────────
    if not host_id:
        st.markdown("#### 先选一位主持人")
        cols = st.columns(len(config["all_hosts"]))
        for i, h in enumerate(config["all_hosts"]):
            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"**{h['name_cn']}**　{'♂' if h['gender']=='male' else '♀'}")
                    if h["available"]:
                        st.caption(h["description_cn"])
                        if st.button(f"选{h['name_cn']}", key=f"pick_{h['id']}", type="primary", use_container_width=True):
                            status["host_id"] = h["id"]
                            save_status(ep_dir, status)
                            st.rerun()
                    else:
                        st.caption(f"🔒 {h['description_cn']}")

    # ── 已选主持人：写稿 / 双栏 ──────────────────────────────────
    else:
        host = config["host"]

        if not script_file.exists():
            st.caption(f"主持人：{host['name_cn']}　·　将根据选题方向和歌单生成完整主持稿")
            if st.button(f"让{host['name_cn']}来写 →", type="primary"):
                from pipeline.step3_script import generate
                with st.spinner(f"{host['name_cn']}写稿中…"):
                    generate(ep_dir, host, config["show"])
                st.rerun()
        else:
            col_script, col_chat = st.columns([3, 2])

            with col_script:
                st.caption(f"主持人：{host['name_cn']}　·　可直接编辑，或在右边跟{host['name_cn']}说修改意见")
                script = script_file.read_text()
                edited = st.text_area("稿本", value=script, height=560, label_visibility="collapsed")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ 稿本确认，继续", type="primary", use_container_width=True):
                        script_file.write_text(edited)
                        status["current_step"] = 4
                        save_status(ep_dir, status)
                        st.rerun()
                with c2:
                    if st.button("重新生成", use_container_width=True):
                        script_file.unlink()
                        st.rerun()

            with col_chat:
                st.caption(f"告诉{host['name_cn']}哪里需要改，他会输出完整修改版")
                chat3 = load_chat(ep_dir, "chat_step3.json")
                chat_box = st.container(height=500)
                with chat_box:
                    for msg in chat3:
                        with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
                            st.markdown(msg["content"])

                user_input = st.chat_input(f"跟{host['name_cn']}说…")
                if user_input:
                    from pipeline.step3_script import chat_reply
                    current_script = script_file.read_text()

                    with chat_box:
                        with st.chat_message("user"):
                            st.markdown(user_input)
                    chat3.append({"role": "user", "content": user_input})

                    with chat_box:
                        with st.chat_message("assistant"):
                            with st.spinner(f"{host['name_cn']}改稿中…"):
                                new_script = chat_reply(chat3, current_script, host, config["show"])
                            st.markdown("✏️ 稿子已更新，请查看左侧。")
                    chat3.append({"role": "assistant", "content": "✏️ 稿子已更新，请查看左侧。"})
                    save_chat(ep_dir, chat3, "chat_step3.json")
                    script_file.write_text(new_script)
                    st.rerun()

# ── Step 5：配音 ─────────────────────────────────────────────────
elif current_step == 5:
    config = load_config(status.get("host_id"))
    host = config["host"]
    voice_file = ep_dir / "05_voiceover.mp3"

    st.markdown("### 配音生成")

    from pipeline.step5_voiceover import VOICE_MAP
    voice_name = VOICE_MAP.get(host.get("gender", "male"), VOICE_MAP["male"])
    st.caption(f"主持人：{host['name_cn']}　｜　声音：`{voice_name}`")

    if not voice_file.exists():
        script_file = ep_dir / "03_script_cn.md"
        if not script_file.exists():
            st.error("找不到稿本，请先完成 Step 3。")
        else:
            st.info("将根据稿本（去掉音乐标记）生成主持人配音。")
            if st.button("生成配音 →", type="primary"):
                from pipeline.step5_voiceover import generate
                with st.spinner("合成中，稿子较长可能需要 1-2 分钟…"):
                    generate(ep_dir, host)
                st.rerun()
    else:
        st.audio(str(voice_file), format="audio/mp3")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ 配音确认，继续", type="primary", use_container_width=True):
                status["current_step"] = 6
                save_status(ep_dir, status)
                st.rerun()
        with c2:
            if st.button("重新生成", use_container_width=True):
                voice_file.unlink()
                st.rerun()

# ── Step 6：去 PR 合成 ────────────────────────────────────────────
elif current_step == 6:
    st.markdown("### 去 Premiere Pro 合成视频")
    st.caption("把下面的素材导入 PR，合成完成后点继续。")

    assets = [
        ("🎙️ 主持稿（配音用）", "03_script_cn.md"),
        ("🎵 歌单", "02_playlist.json"),
        ("🖼️ 封面图", "04_thumbnail.png"),
    ]
    for label, fname in assets:
        fpath = ep_dir / fname
        if fpath.exists():
            st.markdown(f"- {label}　`episodes/{selected}/{fname}` ✅")
        else:
            st.markdown(f"- {label}　`episodes/{selected}/{fname}` _(未生成)_")

    st.divider()
    if st.button("✅ 视频已合成，继续上传文案", type="primary"):
        status["current_step"] = 7
        save_status(ep_dir, status)
        st.rerun()

# ── Step 7：上传文案 ──────────────────────────────────────────────
elif current_step == 7:
    metadata_file = ep_dir / "07_metadata.md"
    config = load_config(status.get("host_id"))

    st.markdown("### B站 上传文案")

    if not metadata_file.exists():
        st.caption("将根据选题、歌单、稿本自动生成标题、简介、标签")
        if st.button("生成文案 →", type="primary"):
            from pipeline.step7_metadata import generate
            with st.spinner("生成中…"):
                generate(ep_dir, config["show"])
            st.rerun()
    else:
        col_text, col_chat = st.columns([3, 2])

        with col_text:
            st.caption("可直接编辑，或在右边告诉 AI 哪里要改")
            edited = st.text_area(
                "文案", value=metadata_file.read_text(),
                height=520, label_visibility="collapsed"
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 文案确认，完成", type="primary", use_container_width=True):
                    metadata_file.write_text(edited)
                    status["current_step"] = 8
                    save_status(ep_dir, status)
                    st.rerun()
            with c2:
                if st.button("重新生成", use_container_width=True):
                    metadata_file.unlink()
                    st.rerun()

        with col_chat:
            st.caption("告诉 AI 哪里要改，它会重写完整文案")
            chat7 = load_chat(ep_dir, "chat_step7.json")
            chat_box = st.container(height=460)
            with chat_box:
                for msg in chat7:
                    with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
                        st.markdown(msg["content"])

            user_input = st.chat_input("说说哪里要改…")
            if user_input:
                from pipeline.step7_metadata import chat_reply
                current_meta = metadata_file.read_text()

                with chat_box:
                    with st.chat_message("user"):
                        st.markdown(user_input)
                chat7.append({"role": "user", "content": user_input})

                with chat_box:
                    with st.chat_message("assistant"):
                        with st.spinner("改中…"):
                            new_meta = chat_reply(chat7, current_meta, config["show"], ep_dir)
                        st.markdown("✏️ 文案已更新，请查看左侧。")
                chat7.append({"role": "assistant", "content": "✏️ 文案已更新，请查看左侧。"})
                save_chat(ep_dir, chat7, "chat_step7.json")
                metadata_file.write_text(new_meta)
                st.rerun()

# ── 其他审批步骤 ──────────────────────────────────────────────────
elif current_step in APPROVAL_FILES:
    approval_file = ep_dir / APPROVAL_FILES[current_step]
    st.markdown(f"### Step {current_step}：{STEPS[current_step]} — 待审批")
    if approval_file.exists():
        edited = st.text_area(approval_file.name, value=approval_file.read_text(),
                               height=480, label_visibility="collapsed")
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button(f"审批通过 → Step {current_step + 1}", type="primary", use_container_width=True):
                approval_file.write_text(edited)
                run_cmd("next", selected)
                st.rerun()
        with col2:
            st.caption("直接在上方修改，点按钮保存并继续")
    else:
        st.warning(f"找不到文件：{APPROVAL_FILES[current_step]}")

elif current_step <= max(STEPS):
    st.markdown(f"### Step {current_step}：{STEPS[current_step]} — 自动处理中")
    st.info("这一步不需要审批，流水线将自动执行。（开发中）")
else:
    st.success("🎉 本期节目所有步骤已完成！")
