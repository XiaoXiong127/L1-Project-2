import os
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI,OpenAIEmbeddings

# 加载.env文件中的环境变量
load_dotenv()


# 设置日志模版
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# 模型配置字典
MODEL_CONFIGS = {
    "openai": {
        "base_url": os.getenv("OPENAI_BASE_URL"),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "chat_model": "gpt-4o",
        "embedding_model": "text-embedding-3-small"
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": os.getenv("DASHSCOPE_API_KEY"),
        "chat_model": "qwen-max",
        "embedding_model": "text-embedding-v1"
    },
    "oneapi": {
        "base_url": os.getenv("ONEAPI_BASE_URL"),
        "api_key": os.getenv("DASHSCOPE_API_KEY"),
        "chat_model": "qwen-max",
        "embedding_model": "text-embedding-v1"
    },
    "ollama": {
        "base_url": os.getenv("OLLAMA_BASE_URL"),
        "api_key": os.getenv("OLLAMA_API_KEY"),
        "chat_model": "qwen2.5:32b",
        "embedding_model": "bge-m3:latest"
    },
    "singularity": {
        "base_url": "https://api.singularity-ai.com/v1",
        "api_key": os.getenv("SINGULARITY_API_KEY"),
        "chat_model": "singularity-gpt",
        "embedding_model": "singularity-embedding"
    }
}


# 默认配置
DEFAULT_LLM_TYPE = "qwen"
DEFAULT_TEMPERATURE = 0.5


class LLMInitializationError(Exception):
    """自定义异常类用于LLM初始化错误"""
    pass


def initialize_llm(llm_type: str = DEFAULT_LLM_TYPE) -> tuple[ChatOpenAI, OpenAIEmbeddings]:
    """
    初始化LLM实例

    Args:
        llm_type (str): LLM类型，可选值为 'openai', 'oneapi', 'qwen', 'ollama', 'singularity'

    Returns:
        ChatOpenAI: 初始化后的LLM实例

    Raises:
        LLMInitializationError: 当LLM初始化失败时抛出
    """
    try:
        # 检查llm_type是否有效
        if llm_type not in MODEL_CONFIGS:
            raise ValueError(f"不支持的LLM类型: {llm_type}. 可用的类型: {list(MODEL_CONFIGS.keys())}")

        config = MODEL_CONFIGS[llm_type]

        # 特殊处理 ollama 类型
        if llm_type == "ollama":
            os.environ["OPENAI_API_KEY"] = "NA"

        # 创建LLM实例
        llm_chat = ChatOpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"],
            model=config["chat_model"],
            temperature=DEFAULT_TEMPERATURE,
            timeout=30,  # 添加超时配置（秒）
            max_retries=2  # 添加重试次数
        )

        llm_embedding = OpenAIEmbeddings(
            base_url=config["base_url"],
            api_key=config["api_key"],
            model=config["embedding_model"],
            deployment=config["embedding_model"]
        )

        logger.info(f"成功初始化 {llm_type} LLM")
        return llm_chat, llm_embedding

    except ValueError as ve:
        logger.error(f"LLM配置错误: {str(ve)}")
        raise LLMInitializationError(f"LLM配置错误: {str(ve)}")
    except Exception as e:
        logger.error(f"初始化LLM失败: {str(e)}")
        raise LLMInitializationError(f"初始化LLM失败: {str(e)}")


def get_llm(llm_type: str = DEFAULT_LLM_TYPE) -> ChatOpenAI:
    """
    获取LLM实例的封装函数，提供默认值和错误处理

    Args:
        llm_type (str): LLM类型

    Returns:
        ChatOpenAI: LLM实例
    """
    try:
        return initialize_llm(llm_type)
    except LLMInitializationError as e:
        logger.warning(f"使用默认配置重试: {str(e)}")
        if llm_type != DEFAULT_LLM_TYPE:
            return initialize_llm(DEFAULT_LLM_TYPE)
        raise  # 如果默认配置也失败，则抛出异常


# 示例使用
if __name__ == "__main__":
    try:
        # 测试不同类型的LLM初始化
        # llm_openai = get_llm("openai")
        # llm_qwen = get_llm("qwen")
        llm_singularity = get_llm("singularity")

        # 测试无效类型
        # llm_invalid = get_llm("invalid_type")
    except LLMInitializationError as e:
        logger.error(f"程序终止: {str(e)}")