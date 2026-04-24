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
    4: "视觉素材", 5: "配音", 6: "视频合成",
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

def load_config():
    host = json.loads((ROOT / "config" / "host_persona.json").read_text())
    show = json.loads((ROOT / "config" / "show_format.json").read_text())
    return {"host": host, "show": show}

def load_chat(ep_dir):
    f = ep_dir / "chat_step1.json"
    return json.loads(f.read_text()) if f.exists() else []

def save_chat(ep_dir, messages):
    (ep_dir / "chat_step1.json").write_text(json.dumps(messages, ensure_ascii=False, indent=2))

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
            st.markdown(f"✅ **{name}**")
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

        # 显示对话
        for msg in chat_history:
            role_label = "你" if msg["role"] == "user" else "助理"
            with st.chat_message(msg["role"] if msg["role"] == "assistant" else "user"):
                st.markdown(msg["content"])

        # 继续对话
        user_input = st.chat_input("哪里不对？补充一下……")
        if user_input:
            config = load_config()
            from pipeline.step1_topics import chat_reply
            chat_history.append({"role": "user", "content": user_input})
            with st.spinner(""):
                reply = chat_reply(chat_history, config["show"])
            chat_history.append({"role": "assistant", "content": reply})
            save_chat(ep_dir, chat_history)
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
