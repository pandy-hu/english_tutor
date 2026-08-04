"""K12 英语辅导小工具 —— 主程序（Streamlit）。

模块：单词卡 / 默写 / 跟读 / 听力 / 阅读 / 语法 / 写作 / 口语 / 错题本 / 关于
运行：streamlit run app.py
"""
import io
import random
import hashlib
import concurrent.futures
import streamlit as st
import core

st.set_page_config(page_title="K12 英语辅导小工具", page_icon="📚", layout="wide")

# ---------------- 顶部导航 ----------------
TOOLS = [
    ("📇 单词卡", "flash"),
    ("✏️ 默写", "dict"),
    ("🎙️ 跟读", "read"),
    ("👂 听力", "listen"),
    ("📖 阅读", "read_hl"),
    ("📐 语法", "grammar"),
    ("✍️ 写作", "write"),
    ("💬 口语", "speak"),
    ("📋 错题本", "mistakes"),
    ("💡 关于", "about"),
]

if "tool" not in st.session_state:
    st.session_state.tool = "flash"

cols = st.columns(len(TOOLS))
for i, (label, key) in enumerate(TOOLS):
    with cols[i]:
        if st.button(label, use_container_width=True,
                     type="primary" if st.session_state.tool == key else "secondary"):
            st.session_state.tool = key

st.divider()


def play_btn(text, label="🔊 听发音", state_key=None):
    """播放发音。state_key 不为空时，渲染一个『再听』按钮，点一次就重新渲染播放器
    （避免把播放器写在按钮 if 块里、重跑后丢失的问题）。"""
    if state_key:
        if state_key not in st.session_state:
            st.session_state[state_key] = 0
        if st.button(label, key=state_key + "_btn"):
            st.session_state[state_key] += 1
        if st.session_state[state_key] > 0:
            data = core.speak(text)
            if data:
                st.audio(data, format="audio/mp3")
            else:
                st.caption("（发音引擎未就绪，需在本地/云端安装 edge-tts）")
    else:
        data = core.speak(text)
        if data:
            st.audio(data, format="audio/mp3")
        else:
            st.caption("（发音引擎未就绪，需在本地/云端安装 edge-tts）")


# ================= 1. 单词卡 =================
if st.session_state.tool == "flash":
    st.header("📇 智能单词卡（间隔重复记忆）")
    st.caption("按记忆曲线复习：答对的词下次出现间隔变长，答错立刻重来。掌握度≥60 的词会进入「已知词」。")
    levels = ["全部"] + core.get_levels()
    if "flash_level" not in st.session_state:
        st.session_state.flash_level = "全部"
    sel_level = st.selectbox("🎯 选择学段（按教材选词）", levels,
                             index=levels.index(st.session_state.flash_level), key="flash_level_sel")
    st.session_state.flash_level = sel_level
    total = len(core.load_words())
    cnt_by_lv = {lv: len(core.load_words(lv)) for lv in core.get_levels()}
    st.caption("📚 词库总量：" + str(total) + " 词　" + "　".join(f"{k} {v}" for k, v in cnt_by_lv.items()))

    only_wrong = st.checkbox("📌 优先练我错过的词", value=False, key="flash_only_wrong")
    wrong_set = core.get_mistake_words() if only_wrong else set()

    due = core.due_words(level=sel_level if sel_level != "全部" else None)
    if only_wrong and wrong_set:
        due.sort(key=lambda w: 0 if w["word"].lower() in wrong_set else 1)
    if not due:
        st.success("🎉 今天的复习任务清空啦！去『阅读/跟读』里多接触新词吧。")
    else:
        st.info(f"待复习：{len(due)} 个" + ("（已把错题词排到最前）" if only_wrong and wrong_set else ""))
        w = due[0]
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader(w["word"])
            st.write(w.get("phonetic", ""), w.get("pos", ""))
            play_btn(w["word"])
        with c2:
            if st.toggle("显示释义", key="show_mean"):
                st.write("**释义：**", w.get("meaning", ""))
                st.write("**例句：**", w.get("example", ""))
                st.write("**翻译：**", w.get("example_cn", ""))
        col_y, col_n = st.columns(2)
        with col_y:
            if st.button("✅ 我记住了", use_container_width=True):
                core.review_word(w["word"], True)
                st.rerun()
        with col_n:
            if st.button("❌ 还不会", use_container_width=True):
                core.review_word(w["word"], False)
                core.add_mistake("单词卡", f"背诵 {w['word']}", "未记住", w.get("meaning", ""))
                st.rerun()

    with st.expander("➕ 手动添加单词到词库"):
        ww = st.text_input("单词")
        ph = st.text_input("音标（可空）")
        pos = st.text_input("词性（如 n./v.）")
        mean = st.text_input("中文释义")
        ex = st.text_input("英文例句")
        exc = st.text_input("例句中文")
        if st.button("添加"):
            if ww and mean:
                ok = core.add_word({"word": ww, "phonetic": ph, "pos": pos,
                                    "meaning": mean, "example": ex, "example_cn": exc})
                st.success("已添加" if ok else "词库里已存在该词")
            else:
                st.warning("单词和释义必填")


# ================= 2. 默写 =================
elif st.session_state.tool == "dict":
    st.header("✏️ 单词默写（看中文写英文）")
    st.caption("根据中文释义拼写英文单词，写错自动进错题本，下次可『只练错题词』强化。")
    levels = ["全部"] + core.get_levels()
    if "dict_level" not in st.session_state:
        st.session_state.dict_level = "全部"
    sel_level = st.selectbox("🎯 选择学段", levels,
                             index=levels.index(st.session_state.dict_level), key="dict_level_sel")
    st.session_state.dict_level = sel_level

    only_wrong = st.checkbox("📌 只练我错过的词",
                             value=st.session_state.get("dict_only_wrong", False), key="dict_only_wrong_cb")
    st.session_state.dict_only_wrong = only_wrong

    pool = core.load_words(level=sel_level if sel_level != "全部" else None)
    if only_wrong:
        wrong_set = core.get_mistake_words()
        pool = [w for w in pool if w["word"].lower() in wrong_set]
    if not pool:
        st.info("这个范围内还没有可练的词" + ("（先去单词卡或错题本积累一些吧）" if only_wrong else ""))
    else:
        if "dict_word" not in st.session_state or st.session_state.dict_word not in pool:
            st.session_state.dict_word = random.choice(pool)
        w = st.session_state.dict_word
        st.subheader(f"中文：{w.get('meaning', '')}")
        if w.get("example_cn"):
            st.caption("例句提示：" + w["example_cn"])
        if "dict_show" not in st.session_state:
            st.session_state.dict_show = False
        ans = st.text_input("✍️ 写出对应的英文单词", key="dict_ans")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("✔️ 提交", use_container_width=True) and ans:
                if ans.strip().lower() == w["word"].lower():
                    st.success(f"✅ 正确！{w['word']}")
                    core.review_word(w["word"], True)
                    st.session_state.dict_show = False
                    st.session_state.dict_word = random.choice(pool)
                    st.rerun()
                else:
                    st.error(f"❌ 正确答案：{w['word']}")
                    core.review_word(w["word"], False)
                    core.add_mistake("默写", w.get("meaning", ""), ans, w["word"])
                    st.session_state.dict_show = True
        with c2:
            if st.button("🔁 换一个", use_container_width=True):
                st.session_state.dict_word = random.choice(pool)
                st.session_state.dict_show = False
                st.rerun()
        with c3:
            if st.button("💡 看答案", use_container_width=True):
                st.session_state.dict_show = True
        if st.session_state.dict_show:
            st.info(f"单词：**{w['word']}**　音标：{w.get('phonetic','')}　词性：{w.get('pos','')}")
            play_btn(w["word"])


# ================= 3. 跟读 =================
elif st.session_state.tool == "read":
    st.header("🎙️ 跟读训练（听标准音 → 录自己的 → 打分）")
    sentences = [
        "Practice makes perfect.",
        "Where there is a will, there is a way.",
        "Actions speak louder than words.",
        "Better late than never.",
        "Knowledge is power.",
        "A good beginning is half the battle.",
    ]
    wrong = core.get_mistake_sentences("跟读")
    if wrong:
        with st.expander("📌 我的错题句（点选重练）"):
            wp = st.selectbox("选一句重练", wrong, key="read_wrong_sel")
            if st.button("用这句重练", key="read_wrong_btn"):
                st.session_state.read_target = wp
    if "read_target" not in st.session_state:
        st.session_state.read_target = ""
    target = st.session_state.read_target or st.selectbox("选一句 / 自己输入", sentences, key="read_sel")
    if st.session_state.read_target:
        if st.button("↩️ 换回内置句", key="read_clear"):
            st.session_state.read_target = ""
            st.rerun()
    target = st.text_input("跟读内容（可修改）", target, key="read_target_box")

    # 标准音：常驻播放器 + 再听按钮（修复『再听没声』）
    play_btn(target, label="🔊 听标准发音")
    play_btn(target, label="🔁 再听一次", state_key="read_replay")

    st.write("**请跟读上面的句子：**")
    rec = st.audio_input("🎤 点击录音", key="rec_read")
    if "read_result" not in st.session_state:
        st.session_state.read_result = None
    if rec is not None:
        cur_hash = hashlib.md5(rec.getvalue()).hexdigest()
        if st.session_state.get("read_hash") != cur_hash:
            st.session_state.read_result = None
            st.session_state.read_hash = cur_hash
        if st.button("🎯 开始打分", key="read_score"):
            audio_bytes = rec.getvalue()
            text = None
            with st.spinner("识别你的发音中…（最多 40 秒）"):
                try:
                    with concurrent.futures.ThreadPoolExecutor() as ex:
                        fut = ex.submit(core.transcribe, audio_bytes)
                        text = fut.result(timeout=40)
                except Exception:
                    text = None
            if text is None:
                st.error("语音识别未就绪（需在本地/云端安装 faster-whisper），或识别超时。")
            else:
                score, missed = core.compare_text(target, text)
                st.session_state.read_result = (text, score, missed)
                if score < 70:
                    core.add_mistake("跟读", target, text, "匹配度<70%")
        if st.session_state.read_result:
            text, score, missed = st.session_state.read_result
            st.write("**你读的是：**", text)
            st.metric("匹配度", f"{score}%")
            if missed:
                st.warning("可能读错/漏掉的词：" + ", ".join(missed))
            else:
                st.success("基本无误，很棒！")


# ================= 4. 听力 =================
elif st.session_state.tool == "listen":
    st.header("👂 听力练习（对话 / 故事 + 选择题）")
    st.caption("听一段日常对话或故事，做题检验理解。可重复听，做完再看原文。")
    levels = ["全部"] + core.get_levels()
    if "listen_level" not in st.session_state:
        st.session_state.listen_level = "全部"
    sel_level = st.selectbox("🎯 选择学段", levels,
                             index=levels.index(st.session_state.listen_level), key="listen_level_sel")
    st.session_state.listen_level = sel_level

    wrong = core.get_mistake_sentences("听力")
    if wrong:
        with st.expander("📌 我的错题句（点选重练）"):
            wp = st.selectbox("选一句重练", wrong, key="listen_wrong_sel")
            if st.button("用这句重练", key="listen_wrong_btn"):
                st.session_state.listen_override = wp

    items = core.load_listening(level=sel_level if sel_level != "全部" else None)
    if not items and "listen_override" not in st.session_state:
        st.info("该学段暂无听力题，去别的学段看看～")
    else:
        if "listen_idx" not in st.session_state:
            st.session_state.listen_idx = 0
        if st.session_state.get("listen_override"):
            ex = {"type": "错题", "title": "错题句重练", "script": st.session_state.listen_override,
                  "questions": []}
        else:
            ex = items[st.session_state.listen_idx % len(items)]
        st.subheader(f"【{ex.get('type','')}】{ex.get('title','')}")
        play_btn(ex["script"], label="🔊 播放（可重复听）", state_key="listen_play")
        if st.button("显示原文", key="listen_show"):
            st.text(ex["script"])
        for qi, q in enumerate(ex.get("questions", [])):
            st.write(f"**{qi+1}. {q['q']}**")
            choice = st.radio("你的答案", q["options"], key=f"lq{ex['title']}{qi}", horizontal=True)
            if st.button("提交", key=f"lqa{ex['title']}{qi}"):
                if q["options"].index(choice) == q["answer"]:
                    st.success("✅ 答对了！")
                else:
                    st.error("❌ 答错了。解析：" + q["explain"])
                    core.add_mistake("听力", ex["script"], choice, q["options"][q["answer"]])
        if not st.session_state.get("listen_override") and items:
            if st.button("下一题", key="listen_next"):
                st.session_state.listen_idx += 1
                st.rerun()
        if st.session_state.get("listen_override"):
            if st.button("↩️ 返回正常题库", key="listen_clear"):
                del st.session_state.listen_override
                st.rerun()


# ================= 5. 阅读 =================
elif st.session_state.tool == "read_hl":
    st.header("📖 分级阅读（选难度 → 读文章 → 练理解）")
    st.caption("按学段选一篇难度匹配的文章，生词自动高亮，读后做选择题检验理解。")
    levels = ["全部"] + core.get_levels()
    if "read_level" not in st.session_state:
        st.session_state.read_level = "全部"
    sel_level = st.selectbox("🎯 选择学段", levels,
                             index=levels.index(st.session_state.read_level), key="read_level_sel")
    st.session_state.read_level = sel_level
    readings = core.load_readings(level=sel_level if sel_level != "全部" else None)
    if not readings:
        st.info("该学段暂无文章，去别的学段看看～")
    else:
        if "read_idx" not in st.session_state:
            st.session_state.read_idx = 0
        titles = [r["title"] for r in readings]
        idx = st.selectbox("选一篇", range(len(readings)),
                           format_func=lambda i: f"{readings[i]['level']} · {readings[i]['title']}",
                           index=st.session_state.read_idx % len(readings), key="read_pick")
        st.session_state.read_idx = idx
        r = readings[idx]
        hl = st.checkbox("🔍 高亮生词", value=True, key="read_hl_chk")
        if hl:
            html, unknowns = core.highlight_unknown(r["text"])
            st.markdown(f"<div style='line-height:2;font-size:18px'>{html}</div>", unsafe_allow_html=True)
            if unknowns:
                st.caption("生词：" + ", ".join(unknowns) + "（掌握度≥60 的不标）")
        else:
            st.markdown(f"<div style='line-height:2;font-size:18px'>{r['text']}</div>", unsafe_allow_html=True)
        st.divider()
        st.subheader("🧪 读后理解（选择题）")
        for qi, q in enumerate(r.get("questions", [])):
            st.write(f"**{qi+1}. {q['q']}**")
            choice = st.radio("你的答案", q["options"], key=f"rq{r['title']}{qi}", horizontal=True)
            if st.button("提交", key=f"rqa{r['title']}{qi}"):
                if q["options"].index(choice) == q["answer"]:
                    st.success("✅ 答对了！")
                else:
                    st.error("❌ 答错了。解析：" + q["explain"])
                    core.add_mistake("阅读", r["title"], choice, q["options"][q["answer"]])


# ================= 6. 语法 =================
elif st.session_state.tool == "grammar":
    st.header("📐 语法高频易错点")
    for i, t in enumerate(core.GRAMMAR_TIPS):
        with st.expander(f"{i+1}. {t['title']}"):
            st.write(t["body"])
    st.divider()
    st.subheader("🧪 小测（选自测薄弱点）")
    if "q_idx" not in st.session_state:
        st.session_state.q_idx = 0
    qi = st.session_state.q_idx % len(core.QUIZ)
    q = core.QUIZ[qi]
    st.write(q["q"])
    choice = st.radio("你的答案", q["a"], key=f"q{qi}", horizontal=True)
    if st.button("交卷"):
        if q["a"].index(choice) == q["correct"]:
            st.success("✅ 答对了！")
        else:
            st.error("❌ 答错了。解析：" + q["tip"])
            core.add_mistake("语法", q["q"], choice, q["a"][q["correct"]])
    if st.button("下一题"):
        st.session_state.q_idx += 1
        st.rerun()


# ================= 7. 写作 =================
elif st.session_state.tool == "write":
    st.header("✍️ 写作智能批改")
    if not core.ai_available():
        st.warning("⚠️ AI 批改 / 拍照识别需要接入 LLM API（DeepSeek / 通义等，很便宜）。\n\n"
                   "配置方法：在 `.streamlit/secrets.toml` 写入：\n```\n"
                   'api_key = "你的key"\nbase_url = "https://api.deepseek.com/v1"\n'
                   'model = "deepseek-chat"\n```\n\n'
                   "（拍照手写识别需要模型支持『视觉/看图』能力，配置时把 model 设为支持视觉的模型即可。）\n\n"
                   "配置后重启应用即可启用。")
    essay = st.text_area("粘贴你的英语作文", "Last weekend, I go to park with my friend. We very happy and take many photo.", height=200)

    st.subheader("📷 拍照 / 上传手写稿（识别后填入上方）")
    img = st.file_uploader("上传图片（手写或印刷的英文作文）", type=["png", "jpg", "jpeg"], key="write_img")
    if img is not None:
        st.image(img, width=320)
        if st.button("🔍 识别图片中的英文", disabled=not core.ai_available(), key="write_ocr"):
            with st.spinner("识别中…"):
                txt = core.ai_transcribe_image(img.getvalue())
            if txt is None:
                st.error("未配置支持视觉的模型，无法识别。请先在 secrets.toml 配置带视觉能力的 model。")
            elif txt.startswith("[识别失败]"):
                st.error(txt)
            else:
                st.session_state.write_ocr_text = txt
                essay = txt
                st.success("识别完成，已填入上方文本框，可编辑后批改。")
                st.text_area("识别结果（可修改）", txt, height=120, key="write_ocr_view")

    if st.button("🤖 AI 批改", disabled=not core.ai_available(), key="write_correct"):
        with st.spinner("批改中…"):
            res = core.ai_correct_writing(essay)
        if res:
            st.markdown(res)


# ================= 8. 口语 =================
elif st.session_state.tool == "speak":
    st.header("💬 AI 口语陪练")
    if not core.ai_available():
        st.warning("⚠️ 此功能需要接入 LLM API（同写作模块配置）。配置后这里就能跟 AI 用英语对话练口语。")
    else:
        level = st.selectbox("学生水平", ["小学", "初中", "高中"])
        if "chat" not in st.session_state:
            st.session_state.chat = []
        for role, msg in st.session_state.chat:
            st.chat_message(role).write(msg)
        user_in = st.chat_input("用英语说点什么…")
        if user_in:
            st.session_state.chat.append(("user", user_in))
            with st.spinner("AI 思考中…"):
                reply = core.ai_speak_partner(level, user_in, st.session_state.chat)
            st.session_state.chat.append(("assistant", reply))
            st.rerun()


# ================= 9. 错题本 =================
elif st.session_state.tool == "mistakes":
    st.header("📋 错题本 & 周报")
    rep = core.weekly_report()
    c1, c2, c3 = st.columns(3)
    c1.metric("本周错题", rep["total"])
    c2.metric("累计错题", rep["all"])
    c3.metric("涉及模块", len(rep["by_module"]))
    if rep["by_module"]:
        st.bar_chart(rep["by_module"])
    ms = core.get_mistakes()
    # 错题强化入口
    wrong_words = core.get_mistake_words()
    if wrong_words:
        if st.button(f"✏️ 去默写强化这 {len(wrong_words)} 个错题词", use_container_width=True, key="mw_go"):
            st.session_state.dict_only_wrong = True
            st.session_state.tool = "dict"
            st.rerun()
    if ms:
        with st.expander("查看全部错题", expanded=True):
            for m in reversed(ms[-50:]):
                st.write(f"**{m['time']} · {m['module']}** — {m['question']}")
                st.caption(f"你的作答：{m['user_answer']} ｜ 正确：{m['correct_answer']}")
        import csv
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["时间", "模块", "题目", "你的作答", "正确答案"])
        for m in ms:
            w.writerow([m["time"], m["module"], m["question"], m["user_answer"], m["correct_answer"]])
        st.download_button("⬇️ 导出错题 CSV（可打印/发给家长）", buf.getvalue().encode("utf-8-sig"), "mistakes.csv", "text/csv")
    else:
        st.info("还没有错题，去做几道题吧！")


# ================= 10. 关于 =================
elif st.session_state.tool == "about":
    st.header("💡 关于本工具")
    st.markdown("""
    **K12 英语辅导小工具** —— 一个零成本、可自托管的英语学习助手。

    **已上线（免费、无需任何账号）：**
    - 📇 单词卡：间隔重复记忆，可优先练错过的词
    - ✏️ 默写：看中文写英文，错词自动进错题本
    - 🎙️ 跟读：edge-tts 免费真人音 + 本地语音识别打分
    - 👂 听力：日常对话 / 故事 + 选择题
    - 📖 阅读：分级文章 + 生词高亮 + 读后理解题
    - 📐 语法：高频易错点 + 自测
    - 📋 错题本：自动收集 + 周报 + CSV 导出 + 一键强化

    **需接入 LLM API 后启用（很便宜）：**
    - ✍️ 写作 AI 批改 / 拍照手写识别
    - 💬 口语 AI 陪练

    **部署：** 推到 GitHub 后，用 Streamlit Cloud 一键部署即可公网访问。
    """)
    st.caption("本工具所有学习数据仅存于本地文件，不上传任何服务器。")
