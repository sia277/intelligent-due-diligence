"""
智能尽调助手 Web 版 V2.0
Day20 - 优化 UI + 风险标签 + 摘要卡片
"""

import streamlit as st
import os
import requests
import glob

# ===== API Key =====
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", st.secrets.get("DEEPSEEK_API_KEY", "") if hasattr(st, "secrets") else "")


# ===== 文档加载 =====
def load_documents(data_dir="data"):
    files = glob.glob(os.path.join(data_dir, "*.txt"))
    documents = []
    for file_path in files:
        file_name = os.path.basename(file_path)
        if file_name == "rules.txt":
            continue
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        documents.append((file_name, content))
    return documents


def chunk_documents(documents, chunk_size=300):
    all_chunks = []
    chunk_id = 0
    for file_name, content in documents:
        paragraphs = content.strip().split('\n\n')
        current = ""
        for para in paragraphs:
            if len(current) + len(para) < chunk_size:
                current += para + "\n"
            else:
                if current.strip():
                    all_chunks.append((chunk_id, file_name, current.strip()))
                    chunk_id += 1
                current = para + "\n"
        if current.strip():
            all_chunks.append((chunk_id, file_name, current.strip()))
            chunk_id += 1
    return all_chunks


def chunk_text_from_bytes(text, file_name, chunk_size=300):
    chunks = []
    paragraphs = text.strip().split('\n\n')
    current = ""
    chunk_id = 0
    for para in paragraphs:
        if len(current) + len(para) < chunk_size:
            current += para + "\n"
        else:
            if current.strip():
                chunks.append((chunk_id, file_name, current.strip()))
                chunk_id += 1
            current = para + "\n"
    if current.strip():
        chunks.append((chunk_id, file_name, current.strip()))
    return chunks


# ===== 检索 =====
def search_relevant(question, chunks):
    stop_words = {'的', '了', '是', '在', '有', '和', '就', '不', '都', '也',
                  '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看',
                  '自己', '这', '他', '她', '它', '们', '那', '什么', '怎么',
                  '吗', '啊', '呢', '吧', '让', '被', '把', '从', '为', '以',
                  '向', '与', '对', '但', '而', '或', '及', '比', '等'}
    words = [w for w in question if w not in stop_words and w.strip()]
    scores = []
    for chunk_id, file_name, text in chunks:
        score = sum(1 for w in words if w in text)
        if score > 0:
            scores.append((score, chunk_id, file_name, text))
    scores.sort(reverse=True, key=lambda x: x[0])
    return [(file_name, text) for score, chunk_id, file_name, text in scores[:5]]


# ===== 调用 API =====
def call_deepseek(prompt):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一名专业的投资尽调分析师。回答问题时要严谨、基于事实，严格依据提供的资料，不要杜撰信息。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers, json=data, timeout=30
        )
        result = response.json()
        if 'choices' not in result:
            return f"API 异常：{result.get('error', {}).get('message', '未知错误')}"
        return result['choices'][0]['message']['content']
    except Exception as e:
        return f"API 调用失败：{str(e)}"


# ===== RAG 问答 =====
def rag_query(question, chunks):
    results = search_relevant(question, chunks)
    if not results:
        return "资料中未找到相关信息。", []
    context_lines = []
    for file_name, text in results:
        context_lines.append(f"[来源：{file_name}]\n{text}")
    context = "\n\n---\n\n".join(context_lines)
    prompt = f"""
请根据以下尽调资料回答问题。
资料：
{context}
问题：{question}
要求：
1. 严格基于资料回答
2. 不同资料有差异时明确指出
3. 查不到就说"资料中未提及"
"""
    answer = call_deepseek(prompt)
    seen = set()
    sources = []
    for fn, txt in results:
        if fn not in seen:
            sources.append(fn)
            seen.add(fn)
    return answer, sources


# ===== 尽调摘要生成（新增） =====
def generate_summary(chunks):
    """一键生成公司尽调摘要"""
    all_text = "\n\n".join([text for _, _, text in chunks])
    prompt = f"""
根据以下尽调资料，生成一份公司尽调摘要，按这个格式输出：

【公司尽调摘要】

**基本信息**
- 公司名称：
- 所属行业：
- 成立时间：
- 主营业务：

**关键财务指标**
- 营收：
- 净利润：
- 毛利率：
- 资产负债率：
- 净利率：

**主要风险点**（列出 3-5 条，标注风险等级🔴🟡🟢）

**初步判断**
- 一句话结论：
- 建议操作：（推进 / 补充尽调 / 暂缓 / 否决）

资料：
{all_text}

要求：严格基于资料，不要杜撰信息。
"""
    return call_deepseek(prompt)


# ===== 风险标签（新增） =====
def risk_badge(level):
    if level == "高风险":
        return "🔴 高风险"
    elif level == "中风险":
        return "🟡 中风险"
    elif level == "低风险":
        return "🟢 低风险"
    else:
        return "⚪ 未知"


# ===== Streamlit 页面 =====
st.set_page_config(page_title="智能尽调助手 V2.0", layout="wide")

st.title("📋 智能尽调助手 V2.0")
st.markdown("上传尽调材料，AI 帮你提取关键信息、识别风险点。")

# 初始化 session state
if "chunks" not in st.session_state:
    docs = load_documents("data")
    st.session_state.chunks = chunk_documents(docs)
    st.session_state.file_names = [fn for fn, _ in docs]
    st.session_state.messages = []
    st.session_state.summary = None

# ===== 侧边栏 =====
with st.sidebar:
    st.header("📂 文档管理")

    with st.expander("已加载的文档", expanded=True):
        for fn in st.session_state.file_names:
            st.write(f"📄 {fn}")

    uploaded_file = st.file_uploader(
        "上传 .txt 文件",
        type=["txt"],
        accept_multiple_files=False
    )
    if uploaded_file:
        text = uploaded_file.read().decode("utf-8")
        name = uploaded_file.name
        new_chunks = chunk_text_from_bytes(text, name)
        st.session_state.chunks.extend(new_chunks)
        st.session_state.file_names.append(name)
        st.success(f"✅ {name} 已加载")

    st.divider()
    st.markdown(f"📦 **资料片段**：{len(st.session_state.chunks)} 个")

    # 一键摘要按钮
    if st.button("📊 生成尽调摘要", use_container_width=True):
        with st.spinner("正在生成摘要..."):
            st.session_state.summary = generate_summary(st.session_state.chunks)
        st.rerun()

    if st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ===== 显示尽调摘要卡片 =====
if st.session_state.summary:
    with st.container():
        st.subheader("📋 尽调摘要")

        # 提取风险等级来显示标签
        summary_text = st.session_state.summary
        if "高风险" in summary_text:
            badge = risk_badge("高风险")
        elif "中风险" in summary_text:
            badge = risk_badge("中风险")
        elif "低风险" in summary_text:
            badge = risk_badge("低风险")
        else:
            badge = ""

        # 摘要卡片
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(summary_text)
        with col2:
            if badge:
                st.markdown(f"### {badge}")

        st.divider()

# ===== 主区域：问答 =====
st.subheader("💬 尽调问答")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.caption(f"📚 来源：{'、'.join(msg['sources'])}")

question = st.chat_input("输入你的尽调问题...")

if question:
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.status("🔍 正在检索资料...", expanded=False) as status:
            answer, sources = rag_query(question, st.session_state.chunks)
            status.update(label="✅ 回答完成", state="complete")

        st.markdown(answer)
        if sources:
            st.caption(f"📚 参考来源：{'、'.join(sources)}")

    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})

    if len(st.session_state.messages) > 20:
        st.session_state.messages = st.session_state.messages[-20:]

# ===== 底部 =====
with st.expander("💡 使用说明"):
    st.markdown("""
    **新功能：**
    - 点击侧边栏「生成尽调摘要」一键输出公司概览 + 风险等级

    **示例问题：**
    - 这家公司的营收和净利润是多少？
    - 它有哪些风险？
    - 资产负债率是多少？
    """)

# ===== 底部：免责声明（新增） =====
st.caption("⚠️ 本产品生成的内容仅供参考，不构成投资建议。所有结论请结合专业判断确认。")
