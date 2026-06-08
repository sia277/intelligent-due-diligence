"""
智能尽调助手 V1.3
Day18 - 带记忆 + 工具调用

新增功能：
1. 对话记忆：支持连续多轮追问
2. 财务计算工具：自动算资产负债率、净利率、ROE 等指标
"""

import os
import requests
import glob
import re

# ===== API Key =====
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


# ===== 财务计算工具 =====
def calc_debt_ratio(liabilities, assets):
    """资产负债率 = 总负债 / 总资产 × 100%"""
    return f"{liabilities / assets * 100:.1f}%"

def calc_profit_margin(net_profit, revenue):
    """净利率 = 净利润 / 营收 × 100%"""
    return f"{net_profit / revenue * 100:.1f}%"

def calc_gross_margin(gross_profit, revenue):
    """毛利率 = 毛利 / 营收 × 100%"""
    return f"{gross_profit / revenue * 100:.1f}%"

def calc_current_ratio(current_assets, current_liabilities):
    """流动比率 = 流动资产 / 流动负债"""
    return f"{current_assets / current_liabilities:.1f}"

def calc_quick_ratio(current_assets, inventory, current_liabilities):
    """速动比率 = (流动资产 - 存货) / 流动负债"""
    return f"{(current_assets - inventory) / current_liabilities:.1f}"

def calc_roe(net_profit, total_assets, total_liabilities):
    """ROE = 净利润 / 净资产 × 100%（净资产 = 总资产 - 总负债）"""
    equity = total_assets - total_liabilities
    if equity <= 0:
        return "净资产为负，无法计算"
    return f"{net_profit / equity * 100:.1f}%"

def calc_revenue_growth(current_revenue, previous_revenue):
    """营收增长率 = (当期营收 - 上期营收) / 上期营收 × 100%"""
    return f"{(current_revenue - previous_revenue) / previous_revenue * 100:.1f}%"

# 工具注册表：让 AI 知道可以用哪些工具
TOOL_DESCRIPTIONS = """
你可以使用以下财务计算工具。当用户需要计算财务指标时，在回答的最后输出一行：
[TOOL] 工具名(参数1, 参数2, ...)

可用工具：
- calc_debt_ratio(总负债, 总资产) → 资产负债率
- calc_profit_margin(净利润, 营收) → 净利率
- calc_gross_margin(毛利, 营收) → 毛利率
- calc_current_ratio(流动资产, 流动负债) → 流动比率
- calc_quick_ratio(流动资产, 存货, 流动负债) → 速动比率
- calc_roe(净利润, 总资产, 总负债) → 净资产收益率
- calc_revenue_growth(当期营收, 上期营收) → 营收增长率
"""


# ===== 加载文档 =====
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
    return [(chunk_id, file_name, text) for score, chunk_id, file_name, text in scores[:5]]


# ===== 调用 API =====
def call_deepseek(messages, system_prompt=None):
    """支持传入完整消息列表（含历史记录）"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    data = {
        "model": "deepseek-chat",
        "messages": full_messages,
        "temperature": 0.3
    }

    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers, json=data, timeout=30
        )
        result = response.json()
        if 'choices' not in result:
            return f"API 返回异常：{result.get('error', {}).get('message', str(result))}"
        return result['choices'][0]['message']['content']
    except Exception as e:
        return f"调用 API 出错：{str(e)}"


# ===== 执行工具调用 =====
TOOL_FUNCTIONS = {
    "calc_debt_ratio": calc_debt_ratio,
    "calc_profit_margin": calc_profit_margin,
    "calc_gross_margin": calc_gross_margin,
    "calc_current_ratio": calc_current_ratio,
    "calc_quick_ratio": calc_quick_ratio,
    "calc_roe": calc_roe,
    "calc_revenue_growth": calc_revenue_growth,
}

def execute_tools(text, conversation_history):
    """检测模型输出中的 [TOOL] 标记，执行工具并返回结果"""
    match = re.search(r'\[TOOL\]\s*(\w+)\(([^)]*)\)', text)
    if not match:
        return text, False

    tool_name = match.group(1)
    args_str = match.group(2)
    args = [float(a.strip()) for a in args_str.split(',')]

    if tool_name in TOOL_FUNCTIONS:
        result = TOOL_FUNCTIONS[tool_name](*args)

        # 把工具结果作为 assistant 消息追加（DeepSeek 不支持 tool role）
        conversation_history.append({
            "role": "assistant",
            "content": f"计算结果：{tool_name}({args_str}) = {result}"
        })

        return text.replace(match.group(0), f"\n\n📊 计算结果：{result}"), True
    return text, False


# ===== 带记忆的文档问答 =====
def chat_with_memory(question, chunks, conversation_history, system_prompt):
    """带记忆的 RAG 问答"""

    # 1. 检索相关段落
    results = search_relevant(question, chunks)
    context = ""
    if results:
        context_lines = []
        for chunk_id, file_name, text in results:
            context_lines.append(f"[来源：{file_name}]\n{text}")
        context = "\n\n---\n\n".join(context_lines)

    # 2. 构建本次用户消息（含检索到的上下文）
    user_message = f"""
根据以下资料回答问题。

资料：
{context}

问题：{question}

要求：
1. 严格基于资料回答
2. 如果需要计算财务指标，使用 [TOOL] 标记调用工具
3. 查不到就说"资料中未提及"
"""

    # 3. 加入对话历史
    messages = list(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # 4. 调用模型
    answer = call_deepseek(messages, system_prompt)

    # 5. 尝试执行工具调用
    final_answer, tool_used = execute_tools(answer, conversation_history)

    # 6. 更新对话历史
    conversation_history.append({"role": "user", "content": question})
    conversation_history.append({"role": "assistant", "content": final_answer})

    # 7. 限制历史长度（保留最近 6 轮）
    while len(conversation_history) > 12:
        conversation_history.pop(0)
        conversation_history.pop(0)

    return final_answer, [(fn, txt) for _, fn, txt in results]


# ===== 加载规则 =====
def load_rules(rules_path="data/rules.txt"):
    if not os.path.exists(rules_path):
        return None
    with open(rules_path, 'r', encoding='utf-8') as f:
        return f.read()


def risk_assessment(company_data_chunks, rules_text):
    all_data = "\n\n".join([text for _, _, text in company_data_chunks])
    prompt = f"""
你是一名专业的投资风控分析师。请根据以下公司尽调数据和风控规则，完成风控评估。

公司数据：
{all_data}

风控规则：
{rules_text}

请按以下格式输出：

【风控评估报告】

一、触发的规则（逐条列出）
每条包含：规则编号、规则名称、判断依据、风险等级

二、未触发的关键规则

三、综合结论
- 整体风险等级：
- 核心判断：
- 建议：
"""
    return call_deepseek([{"role": "user", "content": prompt}])


# ===== 主程序 =====
def main():
    print("=" * 55)
    print("智能尽调助手 V1.3 — 带记忆版")
    print("=" * 55)

    # 加载文档
    print("\n📚 正在加载文档知识库...")
    documents = load_documents("data")
    chunks = chunk_documents(documents)
    print(f"✅ 文档知识库：{len(documents)} 份文档，{len(chunks)} 个片段")

    # 加载规则
    rules_text = load_rules("data/rules.txt")
    if rules_text:
        rule_count = rules_text.count("规则编号：")
        print(f"✅ 规则知识库：{rule_count} 条风控规则已加载")

    # 系统提示词（含工具说明）
    system_prompt = f"""
你是一名专业的投资尽调分析师。回答问题时要严谨、基于事实，严格依据提供的资料，不要杜撰信息。

{TOOL_DESCRIPTIONS}
"""

    print("\n" + "-" * 55)
    print("选择模式：")
    print("  1. 文档问答（支持连续追问 + 财务计算）")
    print("  2. 风控评估（检查是否符合准入）")
    print("-" * 55)

    while True:
        mode = input("\n请选择模式（1/2，输入 q 退出）：").strip()

        if mode.lower() == 'q':
            print("感谢使用，再见！")
            break

        if mode == '1':
            # 文档问答模式（带记忆）
            conversation_history = []
            print("\n📖 文档问答模式（输入 q 返回模式选择）")
            print("💡 支持连续追问，试试：")
            print('   "这家公司的营收和净利润是多少？"')
            print('   "算一下净利率"')
            print('   "那ROE呢？"')
            print('   "风险有哪些？"')

            while True:
                q = input("\n❓ 问题：").strip()
                if q.lower() == 'q':
                    break
                if not q:
                    continue

                print("\n🔍 正在检索...")
                answer, sources = chat_with_memory(q, chunks, conversation_history, system_prompt)

                print("\n" + "=" * 55)
                print("💡 回答：")
                print(answer)
                if sources:
                    print("\n📚 来源：")
                    seen = set()
                    for fn, _ in sources:
                        if fn not in seen:
                            print(f"   · {fn}")
                            seen.add(fn)
                print("=" * 55)

        elif mode == '2':
            company_chunks = [c for c in chunks if c[1] != "rules.txt"]
            result = risk_assessment(company_chunks, rules_text)
            print("=" * 55)
            print(result)
            print("=" * 55)
        else:
            print("请输入 1 或 2")


if __name__ == "__main__":
    main()
