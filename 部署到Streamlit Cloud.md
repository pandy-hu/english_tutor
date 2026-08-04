# 部署到 Streamlit Cloud

本指南适用于 english_tutor（K12 英语辅导小工具）从本地到公网的完整部署。

> ⚠️ 重要变化（2026-08-04 实测）：Streamlit Cloud 新版/旧版后台目前**已没有「Mount a directory / 挂载目录」选项**，免费版实例运行在临时文件系统上。因此，学习进度 / 错题本在**实例重启 / 重新部署后会清空**。要先公网跑起来没问题；要真正云端持久化，需后续接外部数据库（如腾讯云 CloudBase、SQLite on 持久卷、或 PlanetScale/Supabase 等）。

---

## 一、前置条件

- 代码已推送到 `https://github.com/pandy-hu/english_tutor`（分支 `master`，入口 `app.py`）
- 你已用 `pandy-hu` 这个 GitHub 账号登录过 [share.streamlit.io](https://share.streamlit.io)（点 "Continue with GitHub" 授权即可）

> 注：`app.streamlit.io` 主站在国内目前打不开；旧后台 `share.streamlit.io` 仍可进。

---

## 二、新建 App

1. 打开 [share.streamlit.io](https://share.streamlit.io) → 找到 **Create app** / **New app** 按钮。
2. 选择 **Deploy a public app from GitHub**。
3. Repository 选 **`pandy-hu/english_tutor`**。
4. Branch 填 **`master`**。
5. Main file path 填 **`app.py`**。
6. 点 **Advanced settings**（关键步骤在下面）。

---

## 三、Advanced settings

### 1. Python version
选 **3.13**（代码与依赖已验证兼容；若平台无 3.13 选 3.12 也可）。

### 2. Secrets（环境变量）
在 `Secrets` 文本框里按 **TOML 格式**填写，点 **Save** 保存：

```toml
# 数据目录（可选）
# Streamlit Cloud 免费版无持久卷，这个目录在临时文件系统里，
# 实例重启/重新部署后数据会清空；不填就存在默认 user_data/。
ENGTUTOR_DATA_DIR = "/tmp/english_tutor_data"

# AI 模块可选配置（写作批改 / 口语陪练）
# 不配也能跑，只是这两个 Tab 显示"接入后启用"。
# 用兼容 OpenAI 的便宜服务即可，如 DeepSeek：
# OPENAI_API_KEY = "sk-xxx"
# OPENAI_BASE_URL = "https://api.deepseek.com/v1"
# OPENAI_MODEL = "deepseek-chat"
```

**注意 TOML 格式**：
- 字符串值必须用英文双引号 `"..."`
- `#` 开头是注释
- key 和 `=` 之间可加空格

### 3. 没有「Mount a directory」怎么办？
不用找——现在界面里没有这个选项。按上面 Secrets 配即可。

---

## 四、Deploy

确认无误后点 **Deploy**。首次构建会安装依赖（见下方注意事项），约 1–3 分钟，日志实时可见。部署完成后平台给出公网地址，如 `https://englishtutor-xxx.streamlit.app`。

---

## 五、依赖安装注意事项

`requirements.txt` 含 `faster-whisper`（本地语音识别，用于跟读 / 口语）。该包在云端安装体量较大（含 onnxruntime），可能出现：

- **安装较慢**：属正常，等它跑完即可。
- **安装超时失败**：app 仍能启动（代码对 faster-whisper 是**防御式导入**，缺了就降级提示，不影响单词卡 / 阅读 / 语法 / 错题本等核心功能）。若想用跟读 / 口语识别，可改用轻量方案或本地运行。

`edge-tts`（真人发音）需要容器能访问外网，Streamlit Cloud 默认可访问；若发音失败多为网络抖动，重试即可。

---

## 六、上线后验证清单

- [ ] 打开公网地址，首页 Tab 导航正常显示
- [ ] 📇 单词卡：选学段 → 出现待复习词 → 答完"认识/不认识"进度变化
- [ ] 🎙️ 跟读：点播放有真人发音、录音可提交（云端若未装 whisper 会提示降级，属预期）
- [ ] 📖 阅读高亮：粘贴英文 → 生词标黄、点词查释义
- [ ] 📋 错题本：制造一次错误 → 出现在错题本 → 导出 CSV 成功

> 因为免费版无持久卷，刷新或重新部署后进度会清零。要持久化请见下方第七节。

---

## 七、数据持久化后续方案

Streamlit Cloud 免费版无法持久化本地文件。要让学习数据真正不丢，可选：

| 方案 | 复杂度 | 说明 |
|---|---|---|
| **腾讯云 CloudBase** | 中 | 你本地已连通 CloudBase 连接器，可接云数据库或云存储，国内访问快 |
| **SQLite + 持久卷** | 低-中 | 需要付费/升级平台获取持久卷；代码已支持 `ENGTUTOR_DATA_DIR` |
| **第三方免费数据库** | 中 | Supabase / PlanetScale 免费档，需联网和账号 |
| **迁腾讯云 CloudRun** | 中-高 | 自己跑容器，可挂持久化存储；国内稳、家长访问快 |

建议：先公网跑起来验证功能，再按需接入 CloudBase/数据库做持久化。

---

## 八、回滚

代码走 Git 管理，出问题可在 GitHub 仓库切到上一个 commit，或在 Streamlit Cloud 重新 Deploy 旧版本。日常改动流程：本地改 → `git add -A && git commit -m "说明" && git push` → 平台自动重新部署。
