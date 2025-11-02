# app.py
# 简化版 Streamlit 中文布尔检索 Dashboard
# - 只按“词”检索（忽略词性）
# - 只展示带词性的原句
# - 支持 AND / OR / NOT（从左到右顺序执行，NOT 为一元）
# - 提供“检索”按钮 + Enter 提交
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
    最简版布尔逻辑 AND/OR/NOT：
    - NOT 为一元，作用于其后紧随的一个布尔值（这里直接翻转上一个入栈布尔）
    - AND / OR 按从左到右顺序执行（无括号优先级）
    - 仅按“词”匹配（忽略词性）
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
                # 简单处理：若 NOT 前无布尔值，则将一个占位 False 翻转为 True
                stack.append(True)
        elif t == "AND":
            stack.append("AND")
        elif t == "OR":
            stack.append("OR")
        elif t in ("(", ")"):
            # 简化：忽略括号
            continue
        else:
            stack.append(term_match(t))

    # 顺序计算 AND / OR
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

# ------------------------
# 输入表单：点击按钮或按 Enter 开始检索
# ------------------------
with st.form("search_form", clear_on_submit=False):
    query = st.text_input("输入检索词（支持 AND / OR / NOT）：", value="女人 AND 爱")
    submitted = st.form_submit_button("🔍 检索")

# 只有在点击按钮或按 Enter 提交后才执行检索
if submitted:
    # 下载语料
    corpus = {}
    sentences_map = {}
    for name, url in GITHUB_FILES.items():
        raw = fetch_text(url)
        corpus[name] = raw
        sentences_map[name] = split_sentences(raw) if raw else []

    if not any(sentences_map.values()):
        st.warning("未能从内置的 GitHub RAW 链接拉取到文本。请在代码中替换为有效的 RAW 地址后重试。")
        st.stop()

    # 检索与统计
    rows = []
    match_counts = defaultdict(int)

    for fname, sents in sentences_map.items():
        for idx, s in enumerate(sents, start=1):
            words = get_words(s)  # 只按词匹配
            if eval_query(query, words):
                rows.append({"文件": fname, "句号": idx, "句子（含词性）": s})
                match_counts[fname] += 1

    # Dashboard 指标
    total = sum(match_counts.values())
    cols = st.columns(5)
    cols[0].metric("总匹配句子数", total)
    for i, name in enumerate(GITHUB_FILES.keys()):
        cols[i+1].metric(name, match_counts.get(name, 0))

    # 图表（横坐标文字不旋转）
    summary = pd.DataFrame({
        "文件": list(GITHUB_FILES.keys()),
        "匹配句子数": [match_counts.get(n, 0) for n in GITHUB_FILES.keys()]
    })
    # 结果表格
    st.markdown("### 检索结果（含词性）")
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("未检索到匹配结果。")
else:
    st.info("输入检索词后，点击 **🔍 检索** 或在输入框按 **Enter** 开始。例：`女人 AND 爱`、`女人 OR 爱`、`女人 AND NOT 爱`。")
