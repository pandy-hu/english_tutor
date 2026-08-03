# 部署到 Streamlit Cloud（含数据持久化）

本指南适用于 english_tutor（K12 英语辅导小工具）从本地到公网的完整部署。
本地代码已就绪，推到 GitHub 后按以下步骤在 Streamlit Cloud 上线，并挂持久化卷让学习数据（单词进度 / 错题本）云端不丢。

---

## 一、前置条件

- 代码已推送到 `https://github.com/pandy-hu/english_tutor`（分支 `master`，入口 `app.py`）
- 你已用 `pandy-hu` 这个 GitHub 账号登录过 [app.streamlit.io](https://app.streamlit.io)（首次使用点 "Continue with GitHub" 授权即可，会自动关联该账号下的仓库）

---

## 二、新建 App

1. 打开 [app.streamlit.io](https://app.streamlit.io) → 右上角 **Create app** → **From GitHub repo**。
2. Repository 选 **`pandy-hu/english_tutor`**。
3. Branch 填 **`master`**。
4. Main file path 填 **`app.py`**。
5. 点 **Advanced settings**（关键步骤在下面）。

---

## 三、Advanced settings（持久化 + 可选 AI）

### 1. Python version
选 **3.13**（代码与依赖已验证兼容；若平台无 3.13 选 3.12 也可）。

### 2. 持久化卷（让数据云端不丢）⭐
- 找到 **Mount a directory / Mount** 选项并勾选。
- **Mount path** 填：`/mount_data`（这是 Streamlit Cloud 挂载卷在容器内的路径）。
- 添加环境变量：
  - 名称：`ENGTUTOR_DATA_DIR`
  - 值：`/mount_data`
- 代码已内置读取：`USER_DIR = Path(os.environ.get("ENGTUTOR_DATA_DIR", 本地默认))`。挂上卷后，单词进度、错题本会自动存到 `/mount_data`，**重新部署 / 重启都不丢**。

> 若你的 Streamlit Cloud 套餐没有 "Mount" 选项（部分免费档不开放）：可跳过本步，app 照常运行，只是 `user_data/` 落在临时文件系统、重启会清空。要真持久化可改用腾讯云 CloudBase（本机已连通）或升级套餐。

### 3. AI 模块（可选，写作批改 / 口语陪练）
不配也能跑，只是这两个 Tab 显示"接入后启用"。要启用，添加环境变量（用兼容 OpenAI 的便宜服务，如 DeepSeek / 通义千问）：
- `OPENAI_API_KEY` = 你的 key
- `OPENAI_BASE_URL` = 如 `https://api.deepseek.com/v1`（或通义 `https://dashscope.aliyuncs.com/compatible-mode/v1`）
- `OPENAI_MODEL` = 如 `deepseek-chat`

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
- [ ] 刷新页面后，单词进度 / 错题仍在（验证持久化卷生效）

---

## 七、回滚

代码走 Git 管理，出问题可在 GitHub 仓库切到上一个 commit，或在 Streamlit Cloud 重新 Deploy 旧版本。日常改动流程：本地改 → `git add -A && git commit -m "说明" && git push` → 平台自动重新部署。
