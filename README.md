# 📚 K12 英语辅导小工具

一个**零成本、可自托管**的 K12（小一到高三）英语学习助手。面向中国学生与家长的真实痛点：单词记不住、发音没人纠、阅读遇生词卡死、家长辅导不了。

## 功能模块

| 模块 | 解决痛点 | 是否免费 |
|---|---|---|
| 📇 单词卡 | 记了就忘（间隔重复记忆曲线，可按小学/初中/高中选词） | ✅ 免费 |
| 🎙️ 跟读 | 发音不标准没人纠（真人音+本地识别打分） | ✅ 免费 |
| 👂 听力精听 | 听写抓不住词 | ✅ 免费 |
| 📖 阅读高亮 | 遇生词卡死（自动标记+查词） | ✅ 免费 |
| 📐 语法 | 抽象难懂（高频易错点+自测） | ✅ 免费 |
| 📋 错题本 | 家长辅导不了（自动收集+周报+CSV） | ✅ 免费 |
| ✍️ 写作批改 | 中式英语零反馈 | 🔑 需 LLM API |
| 💬 口语陪练 | 没环境不敢开口 | 🔑 需 LLM API |

> 🔑 写作/口语模块需接入一个 OpenAI 兼容的 LLM（DeepSeek / 通义千问等，极便宜）。未配置时显示配置说明，不影响其它功能。

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 启用 AI 批改 / 口语陪练（可选）

在 `.streamlit/secrets.toml` 写入（以 DeepSeek 为例）：

```toml
api_key = "你的key"
base_url = "https://api.deepseek.com/v1"
model = "deepseek-chat"
```

重启应用即生效。

## 一键部署到公网（Streamlit Cloud）

1. 把这个目录推到你的 GitHub 仓库
2. 打开 https://share.streamlit.io → New app → 选该仓库的 `app.py`
3. 点 Deploy，几分钟后得到公网地址

数据全部存在本地 `user_data/` 目录下（学习进度、错题本），**不上传任何服务器**，隐私安全；`user_data/` 已在 `.gitignore` 忽略，不会进版本库。词库 `data/words.json` 含 **652 个 K12 核心词**，按小学/初中/高中标注，可在「单词卡」里按学段筛选，或在页面内手动添加。

> 云端部署持久化：设置环境变量 `ENGTUTOR_DATA_DIR` 指向挂载卷（如 Streamlit Cloud 的 volume 挂载路径），用户数据即可跨重启保留。

## 技术栈

- Streamlit（界面）
- edge-tts（免费真人发音，微软语音）
- faster-whisper（本地语音识别，用于跟读/听写打分）
- 本地 JSON 存储（单词进度、错题本）

## 后续可增强

- 接入免费词典 API，生词一键查详情、批量导入词库
- 对接学校课本单元词汇
- 家长端：微信/邮件推送周报
- 错题打印成 PDF
