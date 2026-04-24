#!/usr/bin/env python3
import sys
import json
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

load_dotenv()

EPISODES_DIR = Path("episodes")

STEPS = {
    1: "选题",
    2: "歌单",
    3: "稿本",
    4: "视觉素材",
    5: "配音",
    6: "视频合成",
    7: "上传文案",
    8: "发布",
}

APPROVAL_STEPS = {1, 2, 3, 4, 7}  # 需要人工审批的步骤


def _load_config() -> dict:
    host = json.loads((Path("config") / "host_persona.json").read_text())
    show = json.loads((Path("config") / "show_format.json").read_text())
    return {"host": host, "show": show}


def _next_ep_number() -> int:
    if not EPISODES_DIR.exists():
        return 1
    dirs = [d for d in EPISODES_DIR.iterdir() if d.is_dir() and d.name.startswith("EP")]
    if not dirs:
        return 1
    return max(int(d.name[2:5]) for d in dirs) + 1


def _find_ep_dir(ep_id: str) -> Path:
    EPISODES_DIR.mkdir(exist_ok=True)
    matches = [d for d in EPISODES_DIR.iterdir() if d.name.startswith(ep_id)]
    if not matches:
        print(f"❌ 找不到节目：{ep_id}")
        sys.exit(1)
    return matches[0]


def cmd_new() -> None:
    ep_num = _next_ep_number()
    today = date.today().strftime("%Y%m%d")
    ep_id = f"EP{ep_num:03d}_{today}"

    ep_dir = EPISODES_DIR / ep_id
    ep_dir.mkdir(parents=True, exist_ok=True)

    status = {"current_step": 1, "ep_id": ep_id}
    (ep_dir / "STATUS.json").write_text(json.dumps(status, ensure_ascii=False, indent=2))

    print(f"✅ 已创建：episodes/{ep_id}")
    print(f"   打开 http://localhost:8501 开始聊选题")


def cmd_next(ep_id: str) -> None:
    ep_dir = _find_ep_dir(ep_id)
    status_file = ep_dir / "STATUS.json"

    if not status_file.exists():
        print("❌ 状态文件不存在，请先运行 python run.py new")
        sys.exit(1)

    status = json.loads(status_file.read_text())
    current = status["current_step"]
    next_step = current + 1

    if next_step > max(STEPS):
        print("🎉 所有步骤已完成！")
        return

    if next_step not in STEPS:
        print(f"⚠️  Step {next_step} 尚未实现，敬请期待")
        return

    print(f"▶️  当前进度：Step {current}（{STEPS[current]}）已审批，进入 Step {next_step}（{STEPS[next_step]}）")

    # 更新 current_step
    status["current_step"] = next_step
    status_file.write_text(json.dumps(status, ensure_ascii=False, indent=2))

    # 调用对应 step
    config = _load_config()
    if next_step == 2:
        print("⚠️  Step 2（歌单）尚未实现，敬请期待")
    else:
        print(f"⚠️  Step {next_step}（{STEPS[next_step]}）尚未实现，敬请期待")


def cmd_status(ep_id: str) -> None:
    ep_dir = _find_ep_dir(ep_id)
    status_file = ep_dir / "STATUS.json"

    if not status_file.exists():
        print("❌ 状态文件不存在")
        sys.exit(1)

    status = json.loads(status_file.read_text())
    current = status["current_step"]

    print(f"\n📻 {status['ep_id']}")
    print("─" * 40)
    for step_num, step_name in STEPS.items():
        if step_num < current:
            mark = "✅"
        elif step_num == current:
            mark = "⏳" if step_num in APPROVAL_STEPS else "🔄"
        else:
            mark = "⬜"
        note = " ← 待审批" if step_num == current and step_num in APPROVAL_STEPS else ""
        print(f"  {mark} Step {step_num}：{step_name}{note}")
    print()


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] == "help":
        print("用法：")
        print("  python run.py new                 # 开始新一期节目")
        print("  python run.py next <EP_ID>        # 审批完当前步骤后继续")
        print("  python run.py status <EP_ID>      # 查看进度")
        return

    cmd = args[0]

    if cmd == "new":
        cmd_new()
    elif cmd == "next":
        if len(args) < 2:
            print("❌ 请提供节目 ID，例如：python run.py next EP001_20260423")
            sys.exit(1)
        cmd_next(args[1])
    elif cmd == "status":
        if len(args) < 2:
            print("❌ 请提供节目 ID，例如：python run.py status EP001_20260423")
            sys.exit(1)
        cmd_status(args[1])
    else:
        print(f"❌ 未知命令：{cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
