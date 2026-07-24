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

打开 `streamlit_app.py`，将 `DEEPSEEK_API_KEY` 替换为你的 DeepSeek API Key。

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
