# 像素电台 / Pixel Radio

> 全自动 AI 音乐电台制作流水线 — AI 出力，你掌舵
>
> Fully automated AI music radio pipeline — AI does the work, you make the calls.

B站 + YouTube 双平台 · 中英文双版本 · 每步可审批修改

---

## 是什么

像素电台是一套让你用最少精力运营音乐电台自媒体的工具。

AI 负责：选题 → 策划歌单 → 写主持稿 → 生成封面 → 合成配音 → 剪辑视频 → 写标题简介标签

你负责：在每个节点**看一眼、改一改、按个键继续**。

最终产出：可直接上传的 B 站视频 + YouTube 视频（中英各一条），以及完整的上传元数据。

---

## 八阶段流水线

```
1. 选题  →  2. 歌单  →  3. 稿本  →  4. 视觉  →  5. 配音  →  6. 合成  →  7. 文案  →  8. 发布
  审批✋       审批✋       审批✋       审批✋       自动⚡       自动⚡       审批✋      可选自动
```

**审批机制**：每个 ✋ 节点，AI 输出一个 Markdown/JSON 文件，你直接编辑它，改完后运行一条命令继续。没有额外 UI，文件即界面，Git 天然留存所有修改历史。

---

## 目录结构

```
像素电台/
├── README.md
├── .env.example
├── requirements.txt
│
├── config/
│   ├── host_persona.json        # AI 主持人人设（名字/风格/口癖）
│   ├── show_format.json         # 节目结构（时长/段落数）
│   └── platforms.json           # B站/YouTube 账号配置
│
├── pipeline/
│   ├── step1_topics.py          # 生成 3-5 个选题方案
│   ├── step2_playlist.py        # 根据主题策划歌单
│   ├── step3_script.py          # 撰写中英文主持稿（独立撰写，非翻译）
│   ├── step4_visuals.py         # 生成封面 + 背景素材
│   ├── step5_voice.py           # TTS 配音合成
│   ├── step6_video.py           # FFmpeg 视频合成
│   ├── step7_metadata.py        # 生成标题/简介/标签
│   └── step8_publish.py         # 上传到各平台
│
├── prompts/                     # 所有 Claude 提示词（可自行调优）
│   ├── topics.md
│   ├── playlist.md
│   ├── script_cn.md
│   ├── script_en.md
│   └── metadata.md
│
├── run.py                       # 主入口
└── episodes/
    └── EP001_20240422_indie-folk/
        ├── STATUS.md            # 当前进度追踪
        ├── 01_topics.md         # ★ 待审批：选题方案（直接编辑这个文件）
        ├── 02_playlist.json     # ★ 待审批：歌单
        ├── 03_script_cn.md      # ★ 待审批：中文主持稿
        ├── 03_script_en.md      # ★ 待审批：英文主持稿
        ├── 04_thumbnail.png     # ★ 待审批：封面图
        ├── 04_backgrounds/      # 背景视频素材
        ├── 05_voice_cn.mp3      # 配音（自动生成）
        ├── 05_voice_en.mp3
        ├── 06_video_cn.mp4      # 最终成品
        ├── 06_video_en.mp4
        └── 07_metadata.md       # ★ 待审批：上传标题/简介/标签
```

---

## 节目结构模板

```
[开场曲 30s]
主持人开场白（介绍本期主题）             1-2 min
──────────────────────────────────────────────
  歌曲介绍（背景 / 创作故事 / 为何选它）  30-60s
  [完整歌曲播放]
  简短过渡语
  × 重复 8-10 首
──────────────────────────────────────────────
主持人结语 + 下期预告                    1 min
[结束曲 30s]

总时长：60-90 分钟
```

---

## AI 主持人设定

|  | 中文版（B站） | 英文版（YouTube） |
|--|--------------|------------------|
| **名字** | 像素 | Pixel |
| **风格** | 温柔知性，有点文艺 | 简洁有趣，注重文化背景 |
| **口吻** | 像朋友在推歌 | 像独立播客主持人 |
| **特点** | 擅长情感共鸣 | 擅长讲冷知识和故事 |

英文版**独立撰写**，不是中文稿的翻译，保持各自语言的自然感。

---

## 技术栈

| 功能 | 工具 | 备注 |
|------|------|------|
| 文本生成 | Claude API (Sonnet) | 选题、稿本、文案 |
| AI 配音 | ElevenLabs | 支持克隆自己声音 |
| 封面生成 | DALL-E 3 | 每期独特封面 |
| 背景素材 | Runway Gen-3 / Kling | 循环视频背景（可选） |
| 视频合成 | FFmpeg + MoviePy | 本地处理，免费 |
| B站上传 | biliup-rs | CLI 工具 |
| YouTube 上传 | YouTube Data API v3 | 官方 API |

---

## 音乐版权策略（必读）

直接用有版权的音乐，B站/YouTube 大概率被下架或消音。三条路：

| 方案 | 工具 | 成本 | 风险 |
|------|------|------|------|
| **A — AI 生成音乐**（推荐） | Suno / Udio | 免费 / 低订阅 | 极低，且是差异化卖点 |
| **B — 版权库订阅** | Epidemic Sound / Artlist | ~$15/月 | 无 |
| **C — Creative Commons** | Free Music Archive | 免费 | 极低，需注明来源 |

> 推荐从方案 A 起步：把"AI 时代的音乐电台"作为定位，AI 生成音乐是特色，不是妥协。

---

## 快速开始

```bash
git clone https://github.com/YOUR_USERNAME/pixel-radio
cd pixel-radio
pip install -r requirements.txt
cp .env.example .env      # 填入 API Keys

# 开始新一期节目
python run.py new

# 查看当前进度
python run.py status EP001

# 审批完当前步骤后，继续下一步
python run.py next EP001
```

---

## 环境变量

```env
# 必须
ANTHROPIC_API_KEY=          # Claude API
ELEVENLABS_API_KEY=         # AI 配音
ELEVENLABS_VOICE_ID=        # 选好的音色 ID

# 推荐
OPENAI_API_KEY=             # DALL-E 3 封面生成

# 按需
SUNO_API_KEY=               # AI 音乐生成（方案 A）
YOUTUBE_CLIENT_SECRET=      # YouTube 上传
BILIBILI_SESSDATA=          # B站登录态
BILIBILI_BILI_JCT=          # B站 CSRF token
```

---

## 路线图

- [ ] **v0.1** — 完整 CLI 流水线跑通（本地端到端）
- [ ] **v0.2** — Streamlit 审批 Web UI（手机也能改稿）
- [ ] **v0.3** — 定时触发（每周自动开启新一期）
- [ ] **v0.4** — 数据反哺选题（根据播放量调整内容方向）
- [ ] **v0.5** — Telegram Bot 移动端一键审批

---

## 设计理念

- **文件夹即数据库** — 透明、可 git 追踪、任何编辑器都能改，不依赖数据库
- **中英文独立撰写** — 翻译腔在 YouTube 上效果差，两种语言的观众感受完全不同
- **每步必停** — 自动化的目的是省力，不是抢走你的判断权

---

*Built with Claude API · ElevenLabs · FFmpeg*
