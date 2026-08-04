"""K12 英语辅导小工具 —— 核心能力层。

所有外部依赖都做「防御式导入」，缺哪个模块哪个功能优雅降级，
不影响整个站点启动。
"""
import os
import json
import re
import hashlib
import difflib
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
AUDIO = DATA / "audio"
AUDIO.mkdir(parents=True, exist_ok=True)
WORDS_FILE = DATA / "words.json"
# 用户数据独立目录：本地默认存项目内 user_data/（持久化）；
# 云端部署时可设环境变量 ENGTUTOR_DATA_DIR 指向挂载卷，实现重启不丢数据。
USER_DIR = Path(os.environ.get("ENGTUTOR_DATA_DIR", BASE / "user_data"))
USER_DIR.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = USER_DIR / "progress.json"
MISTAKES_FILE = USER_DIR / "mistakes.json"
CONFIG_FILE = BASE / ".streamlit" / "secrets.toml"

# ---------- 防御式导入 ----------
try:
    import edge_tts
    _TTS_AVAILABLE = True
except Exception:
    _TTS_AVAILABLE = False

try:
    from faster_whisper import WhisperModel
    _WHISPER_AVAILABLE = True
except Exception:
    _WHISPER_AVAILABLE = False

try:
    import requests
    _REQ_AVAILABLE = True
except Exception:
    _REQ_AVAILABLE = False

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False

DEFAULT_VOICE = "en-US-AriaNeural"

_whisper_model = None


# ============================================================
# 1. 发音（edge-tts，免费真人音）
# ============================================================
def speak(text, voice=DEFAULT_VOICE, rate="+0%"):
    """返回 mp3 字节；带本地缓存避免重复生成。"""
    if not _TTS_AVAILABLE:
        return None
    if not text or not text.strip():
        return None
    key = hashlib.md5(f"{text}|{voice}|{rate}".encode("utf-8")).hexdigest()
    path = AUDIO / f"{key}.mp3"
    if path.exists():
        return path.read_bytes()
    try:
        import asyncio
        async def _gen():
            comm = edge_tts.Communicate(text, voice, rate=rate)
            buf = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    buf.extend(chunk["data"])
            return bytes(buf)
        data = asyncio.run(_gen())
        path.write_bytes(data)
        return data
    except Exception:
        return None


# ============================================================
# 2. 语音识别（faster-whisper，本地）
# ============================================================
def get_whisper():
    global _whisper_model
    if not _WHISPER_AVAILABLE:
        return None
    if _whisper_model is None:
        _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _whisper_model


def transcribe(audio_bytes):
    """audio_bytes: wav/mp3 原始字节，返回识别文本（英文，转小写）。"""
    model = get_whisper()
    if model is None:
        return None
    tmp = AUDIO / "_tmp_rec.wav"
    tmp.write_bytes(audio_bytes)
    segments, _ = model.transcribe(str(tmp), language="en", beam_size=4)
    text = " ".join(s.text for s in segments).strip().lower()
    try:
        tmp.unlink()
    except Exception:
        pass
    return text


def compare_text(target, user_text):
    """跟读/听写比对，返回 (得分0-100, 差异说明列表)。"""
    def norm(s):
        return re.findall(r"[a-z']+", (s or "").lower())
    t = norm(target)
    u = norm(user_text)
    if not t:
        return (0, ["目标文本为空"])
    if not u:
        return (0, ["没有识别到你说的内容"])
    ratio = difflib.SequenceMatcher(None, t, u).ratio()
    score = int(ratio * 100)
    sm = difflib.SequenceMatcher(None, t, u)
    missed = []
    for op in sm.get_opcodes():
        if op[0] in ("delete", "replace"):
            missed.extend(t[op[1]:op[2]])
    return (score, missed[:8])


# ============================================================
# 3. 间隔重复（单词记忆）
# ============================================================
def load_progress():
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_progress(data):
    PROGRESS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def schedule_next(box, quality):
    """SuperMemo 式简易间隔重复。box: 0-4（掌握度），quality: 0/1（错/对）。"""
    if quality == 0:
        return 0, datetime.now() + timedelta(minutes=5)
    intervals = [timedelta(minutes=5), timedelta(hours=1),
                 timedelta(days=1), timedelta(days=3), timedelta(days=7)]
    box = min(box + 1, 4)
    return box, datetime.now() + intervals[box]


def due_words(level=None):
    """返回今天及之前该复习的词列表（含内置词 + 用户进度）。level 可选：小学/初中/高中/全部。"""
    words = load_words(level=level)
    prog = load_progress()
    out = []
    now = datetime.now()
    for w in words:
        p = prog.get(w["word"], {"box": 0, "due": ""})
        due = p.get("due") or ""
        try:
            due_dt = datetime.fromisoformat(due) if due else datetime.min
        except Exception:
            due_dt = datetime.min
        if due_dt <= now:
            out.append({**w, "box": p.get("box", 0), "mastery": p.get("mastery", 0)})
    return out


def review_word(word, correct):
    prog = load_progress()
    p = prog.get(word, {"box": 0, "due": "", "mastery": 0, "seen": 0})
    box = p.get("box", 0)
    m = p.get("mastery", 0)
    seen = p.get("seen", 0) + 1
    new_box, due = schedule_next(box, 1 if correct else 0)
    if correct:
        m = min(100, m + 8)
    else:
        m = max(0, m - 12)
    prog[word] = {"box": new_box, "due": due.isoformat(),
                  "mastery": m, "seen": seen,
                  "last": datetime.now().isoformat()}
    save_progress(prog)


# ============================================================
# 4. 词库
# ============================================================
def load_words(level=None):
    if WORDS_FILE.exists():
        try:
            ws = json.loads(WORDS_FILE.read_text(encoding="utf-8")).get("words", [])
            if level and level != "全部":
                ws = [w for w in ws if w.get("level", "初中") == level]
            return ws
        except Exception:
            return []
    return []


def get_levels():
    """返回词库中所有学段（去重、稳定排序）。"""
    levels = set()
    for w in load_words():
        levels.add(w.get("level", "初中"))
    order = {"小学": 0, "初中": 1, "高中": 2, "自定义": 3}
    return sorted(levels, key=lambda x: order.get(x, 9))


def add_word(w):
    data = {"meta": {"name": "user"}, "words": load_words()}
    w = dict(w)
    w.setdefault("level", "自定义")
    if any(x["word"].lower() == w["word"].lower() for x in data["words"]):
        return False
    data["words"].append(w)
    WORDS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def load_readings(level=None):
    """返回分级阅读文章（可选按学段过滤）。每条含 title/text/questions。"""
    f = DATA / "readings.json"
    if not f.exists():
        return []
    try:
        rs = json.loads(f.read_text(encoding="utf-8")).get("readings", [])
        if level and level != "全部":
            rs = [r for r in rs if r.get("level") == level]
        return rs
    except Exception:
        return []


def load_listening(level=None):
    """返回听力题库（可选按学段过滤）。每条含 type/title/script/questions。"""
    f = DATA / "listening.json"
    if not f.exists():
        return []
    try:
        ls = json.loads(f.read_text(encoding="utf-8")).get("listening", [])
        if level and level != "全部":
            ls = [l for l in ls if l.get("level") == level]
        return ls
    except Exception:
        return []


def lookup(word):
    wl = word.lower().strip()
    for w in load_words():
        if w["word"].lower() == wl:
            return w
    return None


# 基础功能词（不在词库里，但绝不视为生词）
STOPWORDS = set("""a an the and or but if then else when while of to in on at by for with from into onto over under
again further once here there all any both each few more most other some such no nor not only own same so than too very
i you he she it we they me him her us them my your his its our their this that these those who whom which what whose
is am are was were be been being do does did doing have has had having will would shall should can could may might must
as about up down out off above below between out through during before after above below s t re ve ll m d don doesn
new said one get go come see look make take find use know think want need like just now also very much many little
he's she's it's i'm you're we're they're that's what's there's""".split())


def highlight_unknown(text, known_lowers=None):
    """把 text 中不在 known 集合里的单词包成高亮。返回 (html, 未知词列表)。"""
    known = set(known_lowers or [])
    prog = load_progress()
    for w, p in prog.items():
        if p.get("mastery", 0) >= 60:
            known.add(w.lower())

    tokens = re.findall(r"[\w']+|[^\w\s]", text)
    out = []
    unknowns = []
    for tok in tokens:
        if re.match(r"[\w']+$", tok):
            low = tok.lower().strip("'")
            if low and low not in known and low not in STOPWORDS and not low.isdigit():
                unknowns.append(low)
                out.append(f'<mark title="生词">{tok}</mark>')
            else:
                out.append(tok)
        else:
            out.append(tok)
    html = "".join(out)
    return html, sorted(set(unknowns))


# ============================================================
# 5. 错题本
# ============================================================
def add_mistake(module, question, user_answer, correct_answer):
    data = []
    if MISTAKES_FILE.exists():
        try:
            data = json.loads(MISTAKES_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = []
    data.append({
        "time": datetime.now().isoformat(timespec="seconds"),
        "module": module,
        "question": question,
        "user_answer": user_answer,
        "correct_answer": correct_answer,
    })
    MISTAKES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_mistakes():
    if MISTAKES_FILE.exists():
        try:
            return json.loads(MISTAKES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def get_mistake_words():
    """返回错题本里出现过的『单词』（小写集合），用于错题强化。

    覆盖：默写（correct_answer 即单词）、单词卡（question 形如『背诵 apple』）。
    """
    out = set()
    for m in get_mistakes():
        mod = m.get("module", "")
        if mod == "默写":
            w = (m.get("correct_answer") or "").strip().lower()
            if w:
                out.add(w)
        elif mod == "单词卡":
            q = m.get("question", "")
            if q.startswith("背诵 "):
                w = q[3:].strip().lower()
                if w:
                    out.add(w)
    return out


def get_mistake_sentences(module):
    """返回某模块（跟读/听力）记录过错的句子列表（去重，保留顺序）。"""
    out = []
    for m in get_mistakes():
        if m.get("module") == module and (m.get("question") or "").strip():
            s = m["question"].strip()
            if s not in out:
                out.append(s)
    return out


def weekly_report():
    """返回本周错题统计（按模块分组 + 总数）。"""
    ms = get_mistakes()
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    recent = [m for m in ms if datetime.fromisoformat(m["time"]) >= week_ago]
    by_mod = {}
    for m in recent:
        by_mod[m["module"]] = by_mod.get(m["module"], 0) + 1
    return {"total": len(recent), "by_module": by_mod, "all": len(ms)}


# ============================================================
# 6. 语法讲解 + 小测
# ============================================================
GRAMMAR_TIPS = [
    {"title": "a / an 怎么选", "body": "看后面单词的「发音」而非字母：元音音素开头用 an（an hour, an MBA），辅音音素开头用 a（a university, a one-way）。"},
    {"title": "一般过去时 vs 现在完成时", "body": "过去时只说过去（I ate.）；完成时强调与现在的联系或影响（I have eaten, so I'm full.）。有具体过去时间用过去时。"},
    {"title": "可数 vs 不可数名词", "body": "advice/information/news/furniture 是不可数，不能加 s，也不能说 a advice，要说 a piece of advice。"},
    {"title": "比较级：more 还是 -er", "body": "短词（单/双音节）加 -er/-est（taller, bigger）；长词（三音节+）用 more/most（more beautiful）。"},
    {"title": "there be 就近原则", "body": "There is a book and two pens. 靠近 be 的是单数用 is；There are two pens and a book. 靠近是复数用 are。"},
    {"title": "情态动词后接原形", "body": "can/must/should/will 后面永远跟动词原形，不加 to、不加 s（He can play）。"},
    {"title": "被动语态结构", "body": "be + 过去分词。一般现在时 am/is/are done；一般过去时 was/were done；含情态动词 can be done。"},
    {"title": "宾语从句语序", "body": "从句必须用陈述语序：I don't know where he is.（不是 where is he）。"},
    {"title": "used to / be used to", "body": "used to + 原形=过去常常；be used to + 动名词=习惯于（to 是介词）。"},
    {"title": "冠词 the 的特指", "body": "双方都知道的、上文提过的、世上唯一的用 the（the sun, the book we read）。"},
]

QUIZ = [
    {"q": "选词：She is ___ honest girl.", "a": ["a", "an", "the"], "correct": 1, "tip": "honest 的 h 不发音，开头是元音音素 /ɒ/，用 an。"},
    {"q": "改错：He can plays basketball.", "a": ["can play", "can plays", "can playing"], "correct": 0, "tip": "情态动词 can 后接动词原形。"},
    {"q": "选词：There ___ two apples and a banana.", "a": ["is", "are", "be"], "correct": 1, "tip": "there be 就近，two apples 是复数用 are。"},
    {"q": "选词：I have ___ advice for you.", "a": ["a", "an", "some"], "correct": 2, "tip": "advice 不可数，不用 a/an，用 some。"},
    {"q": "选词：This book is ___ than that one.", "a": ["more interesting", "interestinger", "most interesting"], "correct": 0, "tip": "多音节词比较级用 more + 原级。"},
]


# ============================================================
# 7. AI 批改 / 口语陪练（OpenAI 兼容，需用户配置 key）
# ============================================================
def get_ai_config():
    cfg = {"api_key": "", "base_url": "", "model": "deepseek-chat"}
    if CONFIG_FILE.exists():
        try:
            txt = CONFIG_FILE.read_text(encoding="utf-8")
            for line in txt.splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    k = k.strip().strip('"')
                    v = v.strip().strip('"')
                    if k in cfg:
                        cfg[k] = v
        except Exception:
            pass
    return cfg


def ai_available():
    return _OPENAI_AVAILABLE and bool(get_ai_config().get("api_key"))


def ai_chat(system_prompt, user_prompt, temperature=0.7):
    cfg = get_ai_config()
    if not _OPENAI_AVAILABLE or not cfg.get("api_key"):
        return None
    try:
        client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"] or None)
        resp = client.chat.completions.create(
            model=cfg["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[AI 调用失败] {e}"


def ai_correct_writing(text):
    sys_p = ("你是 K12 英语写作老师。请批改下面这篇学生作文："
             "1) 先给出总体评价（句式/词汇/逻辑）；2) 逐句指出中式英语、语法、拼写错误并给正确写法；"
             "3) 给出 3 条可操作的提升建议。用中文讲解，保留英文原句。")
    return ai_chat(sys_p, text, temperature=0.4)


def ai_speak_partner(level, user_text, history):
    sys_p = (f"你是耐心的英语口语陪练，面向 K12（{level} 水平）学生。"
             "用简单英文回复，纠正 1 处最明显的错误，并自然接一个跟进问题鼓励继续聊。"
             "每次回复不超过 3 句英文。")
    msgs = [{"role": "system", "content": sys_p}]
    for role, txt in history[-6:]:
        msgs.append({"role": role, "content": txt})
    msgs.append({"role": "user", "content": user_text})
    try:
        cfg = get_ai_config()
        client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"] or None)
        resp = client.chat.completions.create(model=cfg["model"], messages=msgs, temperature=0.8)
        return resp.choices[0].message.content
    except Exception as e:
        return f"[AI 调用失败] {e}"


def ai_transcribe_image(image_bytes):
    """用视觉模型识别图片中的手写/印刷英文，返回文本；未配置或失败返回 None/错误串。"""
    cfg = get_ai_config()
    if not _OPENAI_AVAILABLE or not cfg.get("api_key"):
        return None
    import base64
    b64 = base64.b64encode(image_bytes).decode("ascii")
    try:
        client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"] or None)
        resp = client.chat.completions.create(
            model=cfg["model"],
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "请识别这张图片里的英文手写/印刷内容，只输出识别出的英文文本，不要加解释。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            }],
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[识别失败] {e}"

