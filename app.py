# app.py
# 简化版 Streamlit 中文布尔检索 Dashboard
# 运行：streamlit run app.py

import re
import requests
import pandas as pd
import streamlit as st
from collections import defaultdict

st.set_page_config(page_title="中文文本检索 Dashboard", layout="wide", page_icon="🔎")

st.title("🔎 中文文本检索 Dashboard")
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
    """最简版布尔逻辑 AND/OR/NOT"""
    q = query.upper().replace("(", " ( ").replace(")", " ) ")
    tokens = [t for t in q.split() if t]

    def term_match(term):
        return term.lower() in [w.lower() for w in words]

    stack = []
    for t in tokens:
        if t == "NOT":
            if stack:
                stack[-1] = not stack[-1]
        elif t == "AND":
            stack.append("AND")
        elif t == "OR":
            stack.append("OR")
        elif t == "(" or t == ")":
            # 简化：忽略括号
            continue
        else:
            stack.append(term_match(t))
    # 顺序执行：NOT 已处理，剩下 AND/OR 左到右
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
# 输入与下载
# ------------------------
query = st.text_input("输入检索词（支持 AND / OR / NOT）：", value="女人 AND 爱")

corpus = {}
sentences_map = {}
for name, url in GITHUB_FILES.items():
    raw = fetch_text(url)
    corpus[name] = raw
    sentences_map[name] = split_sentences(raw) if raw else []

# ------------------------
# 检索与统计
# ------------------------
rows = []
match_counts = defaultdict(int)

for fname, sents in sentences_map.items():
    for idx, s in enumerate(sents, start=1):
        words = get_words(s)
        if eval_query(query, words):
            rows.append({"文件": fname, "句号": idx, "句子（含词性）": s})
            match_counts[fname] += 1

# ------------------------
# Dashboard 指标
# ------------------------
total = sum(match_counts.values())
cols = st.columns(5)
cols[0].metric("总匹配句子数", total)
for i, name in enumerate(GITHUB_FILES.keys()):
    cols[i+1].metric(name, match_counts.get(name, 0))

# ------------------------
# 图表与表格
# ------------------------
summary = pd.DataFrame({
    "文件": list(GITHUB_FILES.keys()),
    "匹配句子数": [match_counts.get(n, 0) for n in GITHUB_FILES.keys()]
})
# st.bar_chart(summary.set_index("文件"))

st.markdown("### 检索结果（含词性）")
if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("未检索到匹配结果。")

