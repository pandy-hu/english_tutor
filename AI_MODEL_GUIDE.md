# AI 模型选型与配置指南（英语辅导小工具）

> 目标：**尽量少花钱**，把「手写/拍照识别」和「作文批改/口语陪练」跑通。
> 本工具统一用 **OpenAI 兼容接口**调用各家模型，配置只需填 `base_url` + `api_key` + `model`，无需改代码。

---

## 0. 一句话结论（最划算组合）

| 能力 | 推荐模型 | 服务商 | 大约单价 | 一句话理由 |
|---|---|---|---|---|
| **手写/拍照识别**（OCR） | `qwen-vl-ocr` | 阿里云百炼 / DashScope | 输入 ≈ $0.043 / 1M tokens | 专为 OCR 设计，比通用多模态视觉模型便宜一个量级 |
| **作文批改 / 口语陪练**（文本） | `deepseek-v4-flash`（兼容别名 `deepseek-chat`） | DeepSeek | 输入 $0.14 / 1M，输出 $0.28 / 1M | 中英都强、便宜，缓存命中再打 8 折 |

> 省钱账：一张作业照约 500–1500 image tokens、一篇 200 词作文批改约 1–2K tokens。
> 就算 **每天 10 个学生各用 5 次识别 + 5 次批改**（≈ 3000 次/月），月成本也 **< $1**。
> 再加上 CloudBase 持久化只在「复习一次 / 记一次错」各写 1 次（免费额度内），整体几乎零成本。

---

## 1. 手写 / 拍照识别：`qwen-vl-ocr`

### 为什么选它
- 阿里通义千问专门出的 **OCR 视觉模型**，识别印刷体 + 手写英文都很准，输出干净纯文本。
- 走 OpenAI 兼容接口，和本工具代码完全兼容，无需适配。
- 单价极低：输入约 **$0.043 / 1M tokens**、输出约 **$0.072 / 1M tokens**（≈ ¥0.3 / 1M 输入）。
- 通用多模态模型（如 GPT-4o、Qwen-VL 通用版、GLM-4V）也能做 OCR，但单价高 5–20 倍，不划算。

### 端点与模型名
- **base_url（OpenAI 兼容）**：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- **model**：`qwen-vl-ocr`（或 `qwen-vl-ocr-latest`）
- **api_key**：阿里云百炼控制台申请的 `DASHSCOPE_API_KEY`（https://help.aliyun.com/model-studio → 获取 API-Key）

---

## 2. 作文批改 / 口语陪练：`deepseek-v4-flash`

### 为什么选它
- DeepSeek-V3 系列，对**中文讲解 + 英文纠错**都很强，适合 K12 写作批改和口语陪练。
- 单价低：输入 **$0.14 / 1M tokens**（缓存命中 **$0.028 / 1M**），输出 **$0.28 / 1M**。
- 旧名 `deepseek-chat` 仍可用（官方说明它对应 `deepseek-v4-flash` 的非思考模式），未来会逐步迁移到新名，建议直接填 `deepseek-v4-flash`。

### 端点与模型名
- **base_url**：`https://api.deepseek.com`
- **model**：`deepseek-v4-flash`
- **api_key**：https://platform.deepseek.com 申请的密钥

---

## 3. 备选方案

| 场景 | 备选 | 备注 |
|---|---|---|
| 想**只用一家**服务商 | 文本用 `qwen-plus`，视觉用 `qwen-vl-ocr`，都走 DashScope | `qwen-plus` 输入约 ¥0.0008 / 千 tokens（≈ $0.11 / 1M），比 DeepSeek 略贵但省心 |
| 先**零成本 prototyping** | 视觉可用 `GLM-4.5V`（约 $0.01 / 1M） | 精度一般，仅适合验证流程，不建议长期 |
| 追求**最高识别精度** | 视觉用 `qwen3-vl-32b`（约 $0.52 / 1M） | 比 ocr 版贵，但复杂版面更强，非必需 |

---

## 4. 配置步骤（部署到 Streamlit Cloud）

在 Streamlit Cloud 后台：**App → Settings → Secrets**，把下面内容整段粘贴进去（TOML 格式）：

```toml
# ===== CloudBase 持久化（Streamlit 重启后单词进度/错题本不丢）=====
CLOUDBASE_API_KEY = "这里填你的CloudBase publish_key"
CLOUDBASE_ENV     = "shangye-tengxunyun-d6cezf7ba95e3"

# ===== 文本批改 / 口语陪练（DeepSeek，最划算）=====
api_key       = "sk-你的DeepSeek密钥"
base_url      = "https://api.deepseek.com"
model         = "deepseek-v4-flash"

# ===== 手写 / 拍照识别（DashScope qwen-vl-ocr，最划算）=====
vision_model      = "qwen-vl-ocr"
vision_api_key    = "sk-你的DashScope密钥"
vision_base_url   = "https://dashscope.aliyuncs.com/compatible-mode/v1"
```

### 字段说明
- `CLOUDBASE_API_KEY` / `CLOUDBASE_ENV`：让进度和错题本跨重启保留（见 `core.py` 双写容错层）。
- `api_key` / `base_url` / `model`：文本类 AI（作文批改、口语陪练）用。
- `vision_model` / `vision_api_key` / `vision_base_url`：**单独**给视觉模型用。
  - 视觉默认回落到文本密钥（`vision_api_key` 留空时复用 `api_key`），但本推荐组合里视觉是 DashScope、文本是 DeepSeek，**所以两个密钥都要填**。
  - 如果你只用一家（比如全用 DashScope），可把 `vision_api_key` / `vision_base_url` 留空，自动复用文本那套。

### 本地调试
把同样内容存到 `english_tutor/.streamlit/secrets.toml` 即可（`core.py` 会自动读取）。

### 不配置会怎样
所有 AI 功能**优雅降级**：没有 key 时，「拍照识别 / 作文批改 / 口语陪练」按钮会提示未配置，不影响单词复习、跟读、错题本等核心功能；CloudBase 不可用时本地文件兜底，数据也不丢。

---

## 5. 验证清单
1. 配好 Secrets 后重新部署（或本地 `streamlit run app.py`）。
2. 「写作」页上传一张手写英文照片 → 应能识别出文本。
3. 「写作」页粘贴一段作文点批改 → 应返回中文点评。
4. 复习几个单词、记一条错题 → 重启应用（或清掉本地 `user_data/`）→ 进度和错题仍在（来自 CloudBase）。
