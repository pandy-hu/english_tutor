"""K12 英语辅导小工具 —— 主程序（Streamlit）。

模块：单词卡 / 跟读 / 听力精听 / 阅读高亮 / 语法 / 写作 / 口语 / 错题本 / 关于
运行：streamlit run app.py
"""
import io
import streamlit as st
import core

st.set_page_config(page_title="K12 英语辅导小工具", page_icon="📚", layout="wide")

# ---------------- 顶部导航 ----------------
TOOLS = [
    ("📇 单词卡", "flash"),
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


def play_btn(text, label="🔊 听发音", key=None):
    data = core.speak(text)
    if data:
        st.audio(data, format="audio/mp3")
    else:
        st.caption("（发音引擎未就绪，需在本地/云端安装 edge-tts）")


# ================= 1. 单词卡 =================
if st.session_state.tool == "flash":
    st.header("📇 智能单词卡（间隔重复记忆）")
    st.caption("按记忆曲线复习：答对的词下次出现间隔变长，答错立刻重来。掌握度≥60 的词会进入「已知词」，阅读时不再高亮。")
    due = core.due_words()
    if not due:
        st.success("🎉 今天的复习任务清空啦！去『阅读/跟读』里多接触新词吧。")
    else:
        st.info(f"待复习：{len(due)} 个")
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


# ================= 2. 跟读 =================
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
    mode = st.radio("句子来源", ["内置金句", "自己输入"], horizontal=True)
    if mode == "内置金句":
        target = st.selectbox("选一句", sentences)
    else:
        target = st.text_input("输入要跟读的英文句子", "I want to improve my English.")
    if target:
        play_btn(target, label="🔊 听标准发音")
        st.write("**请跟读上面的句子：**")
        rec = st.audio_input("🎤 点击录音", key="rec_read")
        if rec is not None:
            audio_bytes = rec.getvalue()
            with st.spinner("识别你的发音中…"):
                text = core.transcribe(audio_bytes)
            if text is None:
                st.error("语音识别未就绪（需安装 faster-whisper）。")
            else:
                score, missed = core.compare_text(target, text)
                st.write("**你读的是：**", text)
                st.metric("匹配度", f"{score}%")
                if missed:
                    st.warning("可能读错/漏掉的词：" + ", ".join(missed))
                else:
                    st.success("基本无误，很棒！")
                if score < 70:
                    core.add_mistake("跟读", target, text, "匹配度<70%")
                if st.button("🔁 再听一次标准音"):
                    play_btn(target)


# ================= 3. 听力精听 =================
elif st.session_state.tool == "listen":
    st.header("👂 听力精听（听写填空）")
    st.caption("听一句 → 写下你听到的 → 看匹配度。练『抓词』能力。")
    lib = [
        "The early bird catches the worm.",
        "Honesty is the best policy.",
        "Rome was not built in a day.",
        "Two heads are better than one.",
        "When in Rome, do as the Romans do.",
    ]
    src = st.selectbox("选一句听力材料", lib)
    play_btn(src, label="🔊 播放（可重复听）")
    ans = st.text_input("✍️ 写出你听到的英文")
    if st.button("提交") and ans:
        score, missed = core.compare_text(src, ans)
        st.metric("听写匹配度", f"{score}%")
        if score >= 90:
            st.success("几乎全对！")
        elif score >= 60:
            st.info("不错，注意这些词：" + (", ".join(missed) if missed else "拼写细节"))
        else:
            st.error("差距较大，再看原文多听几遍：\n" + src)
            core.add_mistake("听力", src, ans, src)


# ================= 4. 阅读高亮 =================
elif st.session_state.tool == "read_hl":
    st.header("📖 阅读生词高亮")
    st.caption("粘贴一段英文，生词自动高亮；点『查词』看释义。掌握度≥60 的词不视为生词。")
    txt = st.text_area("粘贴英文段落", "Reading widely is one of the most effective ways to enlarge your vocabulary and improve your writing.", height=180)
    if st.button("高亮生词") and txt:
        html, unknowns = core.highlight_unknown(txt)
        st.markdown(f"<div style='line-height:2;font-size:18px'>{html}</div>", unsafe_allow_html=True)
        if unknowns:
            st.write("**识别出生词：**", ", ".join(unknowns))
            pick = st.selectbox("查哪个词", unknowns)
            if st.button("查词"):
                w = core.lookup(pick)
                if w:
                    st.write(f"**{w['word']}** {w.get('phonetic','')} {w.get('pos','')}")
                    st.write("释义：", w.get("meaning", ""))
                    st.write("例句：", w.get("example", ""))
                    play_btn(w["word"])
                else:
                    st.warning(f"内置词库没有「{pick}」。可到『单词卡』手动添加，或接入词典 API 自动扩充。")
        else:
            st.success("没有生词，水平不错！")


# ================= 5. 语法 =================
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


# ================= 6. 写作 =================
elif st.session_state.tool == "write":
    st.header("✍️ 写作智能批改")
    if not core.ai_available():
        st.warning("⚠️ 此功能需要接入 LLM API（DeepSeek / 通义等，很便宜）。\n\n"
                   "配置方法：在 `.streamlit/secrets.toml` 写入：\n```\n"
                   'api_key = "你的key"\nbase_url = "https://api.deepseek.com/v1"\n'
                   'model = "deepseek-chat"\n```\n\n'
                   "配置后重启应用即可启用 AI 批改。")
    essay = st.text_area("粘贴你的英语作文", "Last weekend, I go to park with my friend. We very happy and take many photo.", height=200)
    if st.button("🤖 AI 批改", disabled=not core.ai_available()):
        with st.spinner("批改中…"):
            res = core.ai_correct_writing(essay)
        if res:
            st.markdown(res)


# ================= 7. 口语 =================
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


# ================= 8. 错题本 =================
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


# ================= 9. 关于 =================
elif st.session_state.tool == "about":
    st.header("💡 关于本工具")
    st.markdown("""
    **K12 英语辅导小工具** —— 一个零成本、可自托管的英语学习助手。

    **已上线（免费、无需任何账号）：**
    - 📇 单词卡：间隔重复记忆，按记忆曲线复习
    - 🎙️ 跟读：edge-tts 免费真人音 + 本地语音识别打分
    - 👂 听力精听：句子听写训练
    - 📖 阅读高亮：生词自动标记 + 查词
    - 📐 语法：高频易错点 + 自测
    - 📋 错题本：自动收集 + 周报 + CSV 导出

    **需接入 LLM API 后启用（很便宜）：**
    - ✍️ 写作 AI 批改 / 💬 口语 AI 陪练

    **部署：** 推到 GitHub 后，用 Streamlit Cloud 一键部署即可公网访问。
    """)
    st.caption("本工具所有学习数据仅存于本地文件，不上传任何服务器。")
