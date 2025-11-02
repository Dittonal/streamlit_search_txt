# app.py
# Streamlit 中文文本布尔检索 Dashboard
# 运行：streamlit run app.py

import re
import requests
import pandas as pd
import streamlit as st
import altair as alt
from collections import defaultdict

st.set_page_config(page_title="检索 Dashboard", layout="wide")

# st.title("🔎 中文文本检索 Dashboard")
st.caption("从 GitHub 读取带词性标注的文本，通过布尔逻辑 (AND/OR/NOT) 检索句子。")

# ------------------------
# 在这里内置你的 GitHub RAW 文本地址
# ------------------------
GITHUB_FILES = {
    "路遥《平凡的世界》": "https://raw.githubusercontent.com/Dittonal/streamlit_search_txt/main/路遥《平凡的世界》_pos.txt",
    "老舍《骆驼祥子》": "https://raw.githubusercontent.com/Dittonal/streamlit_search_txt/main/老舍《骆驼祥子》_pos.txt",
    "王安忆《长恨歌》": "https://raw.githubusercontent.com/Dittonal/streamlit_search_txt/main/王安忆《长恨歌》_pos.txt",
    "张爱玲《半生缘》": "https://raw.githubusercontent.com/Dittonal/streamlit_search_txt/main/张爱玲《半生缘》_pos.txt",
}
# ---------------- 工具函数 ----------------
@st.cache_data(show_spinner=False)
def fetch_text(url: str) -> str:
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
    except Exception:
        pass
    return ""

def split_sentences(text: str):
    """简单中文分句"""
    text = re.sub(r"[ \t]+", " ", text.strip())
    return [s.strip() for s in re.split(r"[。！？!?；;]\s*|\n+", text) if s.strip()]

def get_words(sentence: str):
    """提取词（忽略词性）"""
    words = []
    for t in sentence.split():
        if "/" in t:
            w, _ = t.split("/", 1)
            words.append(w)
        else:
            words.append(t)
    return words

def eval_query(query: str, words: list):
    """
    简化布尔逻辑 AND / OR / NOT，从左到右顺序执行。
    """
    q = query.upper().replace("(", " ( ").replace(")", " ) ")
    tokens = [t for t in q.split() if t]
    lw = [w.lower() for w in words]

    def term_match(term):
        return term.lower() in lw

    stack = []
    for t in tokens:
        if t == "NOT":
            if stack and isinstance(stack[-1], bool):
                stack[-1] = not stack[-1]
            else:
                stack.append(True)
        elif t == "AND":
            stack.append("AND")
        elif t == "OR":
            stack.append("OR")
        elif t in ("(", ")"):
            continue
        else:
            stack.append(term_match(t))

    result = None
    op = None
    for item in stack:
        if isinstance(item, bool):
            if result is None:
                result = item
            elif op == "AND":
                result = result and item
            elif op == "OR":
                result = result or item
        else:
            op = item
    return bool(result)

# ---------------- 检索区：同一行布局 ----------------
st.markdown("### 🔍 检索设置")
col1, col2 = st.columns([6, 1])
with col1:
    query = st.text_input("输入检索词（支持 AND / OR / NOT）：", value="女人 AND 爱", label_visibility="collapsed")
with col2:
    search_btn = st.button("🔍 检索")

# Enter 检索（当 query 改变时立即触发）或点击按钮都执行
if search_btn or query:
    # ---------------- 下载文本 ----------------
    corpus, sentences_map = {}, {}
    for name, url in GITHUB_FILES.items():
        raw = fetch_text(url)
        corpus[name] = raw
        sentences_map[name] = split_sentences(raw) if raw else []

    if not any(sentences_map.values()):
        st.warning("未能从内置的 GitHub RAW 链接拉取到文本，请替换为有效的 RAW 地址。")
        st.stop()

    # ---------------- 检索 ----------------
    rows = []
    match_counts = defaultdict(int)
    for fname, sents in sentences_map.items():
        for idx, s in enumerate(sents, start=1):
            words = get_words(s)
            if eval_query(query, words):
                rows.append({"文件": fname, "句号": idx, "句子（含词性）": s})
                match_counts[fname] += 1

    # ---------------- Dashboard ----------------
    total = sum(match_counts.values())
    cols = st.columns(5)
    cols[0].metric("总匹配句子数", total)
    for i, name in enumerate(GITHUB_FILES.keys()):
        cols[i+1].metric(name, match_counts.get(name, 0))

    # ---------------- 柱状图 ----------------
    summary = pd.DataFrame({
        "文件": list(GITHUB_FILES.keys()),
        "匹配句子数": [match_counts.get(n, 0) for n in GITHUB_FILES.keys()]
    })
    
    # ---------------- 表格结果 ----------------
    st.markdown("### 📄 检索结果（含词性）")
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("未检索到匹配结果。")
else:
    st.info("请输入检索词并点击 **🔍 检索** 或按 **Enter** 开始，例如：`女人 AND 爱`。")
