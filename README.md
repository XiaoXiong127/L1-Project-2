# RAG Agent 项目

这是一个基于大型语言模型的RAG（检索增强生成）Agent项目，支持多种LLM模型接入。

## 环境配置

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置API密钥

项目使用.env文件管理API密钥和配置信息。请按照以下步骤配置：

1. 在项目根目录下找到`.env`文件
2. 编辑该文件，填入您的API密钥：

```
# API密钥配置文件

# OpenAI配置
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your_openai_api_key_here

# 通义千问配置
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# 硅基流动配置
SINGULARITY_API_KEY=your_singularity_api_key_here

# OneAPI配置
ONEAPI_BASE_URL=http://139.224.72.218:3000/v1

# Ollama配置
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=ollama
```

将上述配置中的`your_xxx_api_key_here`替换为您的实际API密钥。

## 支持的模型

项目当前支持以下LLM模型：

- OpenAI (GPT-4o)
- 通义千问 (Qwen-Max)
- OneAPI
- Ollama (本地部署)
- 硅基流动 (Singularity)

## 运行项目

```bash
python main.py
```

## Web界面

启动Web界面：

```bash
python webUI.py
```

然后在浏览器中访问：http://localhost:8000