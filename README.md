# 智能尽调助手

一款基于 RAG（检索增强生成）的智能尽调工具，帮助投资经理和并购团队快速检索尽调材料、提取关键信息、识别风险点。
在线体验：https://intelligent-due-diligence-fd76xsyjo8n3duzvklxp4z.streamlit.app/
## 背景

在 PE/VC 和并购场景中，尽调工作需要分析师同时处理多份分散材料（年报、招股书、审计报告、行业研究等）。传统做法需要人工逐份阅读和摘录，耗时且容易遗漏关键风险。

本产品通过 RAG 技术，让用户上传材料后直接提问即可获得基于资料的答案，并自动进行风控规则评估。

## 目标用户

- 投资经理
- 分析师
- 并购团队

## 核心功能

- **多文档问答**：上传多份尽调材料，基于文档内容回答问题，附引用来源
- **风控规则评估**：内置 10 条风控规则，自动检查公司是否符合准入条件
- **对话记忆**：支持连续多轮追问，无需重复上下文
- **财务计算工具**：自动计算净利率、毛利率、ROE、资产负债率等指标
- **尽调摘要**：一键生成公司概览、关键财务指标和风险等级标签
- **风险标签**：🔴🟡🟢 三色风险等级标识

## 技术栈

- **语言**：Python 3.10+
- **Web 框架**：Streamlit
- **模型**：DeepSeek API
- **检索方式**：关键词匹配（TF-IDF）
- **部署**：本地运行

## 快速开始

### 环境要求
- Python 3.10+
- pip

### 安装依赖

```bash
pip install streamlit requests
```

### 配置 API Key

**不要把真实密钥写入 Python 源码、README、Git 提交、截图或聊天。**

本地运行时，在启动应用的进程环境中设置 `DEEPSEEK_API_KEY`。例如在 macOS 的 zsh 中交互输入，避免把值直接写入命令历史：

```zsh
read -s 'DEEPSEEK_API_KEY?请输入 DeepSeek API Key: '; echo
export DEEPSEEK_API_KEY
streamlit run streamlit_app.py
# 结束后从当前终端环境移除
unset DEEPSEEK_API_KEY
```

命令行版本 `python app.py` 也读取此环境变量。项目不会自动加载 `.env` 文件。

在 Streamlit Community Cloud 中，通过应用设置中的 Secrets 配置顶层字段 `DEEPSEEK_API_KEY`，不要在仓库中保存真实值。Web 版优先读取非空环境变量，否则读取 Streamlit Secrets。本地若使用 `.streamlit/secrets.toml`，该文件已列入 `.gitignore`；已被 Git 跟踪的文件不会因忽略规则自动移除。

### 密钥安全与部署提醒

- 曾公开的真实密钥应立即在服务商控制台撤销或轮换，并检查用量、账单及依赖服务；仅修改代码或删除文件不能使旧密钥失效。
- 本次配置方式不清除历史提交，也不表示旧密钥已撤销。历史清理需单独评估分支、标签、克隆与部署影响。
- 不要把真实尽调材料上传到公开演示；请求会将相关内容发送给模型服务。使用前确认授权和数据处理要求。
- 当前示例不包含访问控制或调用限额。公开部署时，服务器密钥可能被任何访客触发消耗，应先配置访问限制和预算告警。
- 错误提示不直接回显服务商响应或异常详情，避免意外暴露凭据或文档。

### 离线配置检查

```bash
python -m unittest discover -s tests -v
```

测试使用模拟请求，不验证真实密钥、不访问模型接口。

### 运行

```bash
cd 智能尽调助手
streamlit run streamlit_app.py
```

### 使用示例

1. 启动后浏览器自动打开 http://localhost:8501
2. 侧边栏可查看已加载的默认文档或上传新的 .txt 文件
3. 输入问题开始问答，例如：
   - "这家公司的营收和净利润是多少？"
   - "它有哪些风险？"
   - "资产负债率是多少？"
4. 点击「生成尽调摘要」一键输出公司概况

## 项目结构

```
智能尽调助手/
  streamlit_app.py      # Web 主程序
  app.py                # 命令行版（含记忆 + 工具调用）
  requirements.txt      # 依赖清单
  data/
    sample_company.txt          # 公司介绍
    audit_report.txt            # 审计报告
    industry_report.txt         # 行业研究报告
    earnings_call.txt           # 电话会议纪要
    rules.txt                   # 风控规则（10 条）
```

## 免责声明

本产品生成的内容仅供参考，不构成投资建议。所有结论请结合专业判断确认。
