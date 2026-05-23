"""
llm_client.py - 大模型调用抽象层
支持 API 模式（OpenAI 兼容）和本地 Ollama 模式，提供 chat 与 embed 方法。
"""
import os
import logging
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Generator, Optional
import math
from openai import OpenAI
import httpx

from database import db_session
from models import SystemConfig

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """LLM 客户端抽象基类"""

    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.extra_config = kwargs  # 其他可能的配置（如 base_url, api_key）

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> str | Generator[str, None, None]:
        """
        聊天接口，返回完整回答或流式生成器
        :param messages: 对话历史，[{"role": "user", "content": "..."}]
        :param stream: 是否流式返回
        :param kwargs: 生成参数（temperature, top_p, max_tokens 等）
        :return: 完整字符串或生成器（每次产出一个小块文本）
        """
        pass

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        嵌入接口，返回向量列表
        :param texts: 输入文本列表
        :return: 与输入顺序对应的向量列表
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        测试模型连接是否成功
        :return: True 成功，False 失败
        """
        pass


class APIClient(BaseLLMClient):
    """OpenAI 兼容 API 客户端 (适配 openai >= 1.0.0)"""

    def __init__(self, model_name: str, api_key: str = "", base_url: str = "", **kwargs):
        super().__init__(model_name, **kwargs)

        # 创建一个彻底禁用代理的 httpx 客户端
        transport = httpx.HTTPTransport(proxy=None)
        http_client = httpx.Client(transport=transport)

        self.client = OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY", "dummy"),
            base_url=base_url or None,
            http_client=http_client
        )

    def chat(self, messages, stream=False, **kwargs):
        temperature = kwargs.get("temperature", 0.7)
        top_p = kwargs.get("top_p", 0.9)
        max_tokens = kwargs.get("max_tokens", 1024)
        presence_penalty = kwargs.get("presence_penalty", 0.0)
        frequency_penalty = kwargs.get("frequency_penalty", 0.0)

        logger.info(f"API Chat: model={self.model_name}, stream={stream}, "
                    f"temperature={temperature}, max_tokens={max_tokens}")

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                stream=stream,
            )
            if stream:
                def generate():
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                return generate()
            else:
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"API Chat 错误: {e}")
            raise

    def embed(self, texts: List[str]) -> List[List[float]]:
        logger.info(f"API Embed: model={self.model_name}, batch_size={len(texts)}")
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
            embeddings = [None] * len(texts)
            for item in response.data:
                embeddings[item.index] = item.embedding
            return embeddings
        except Exception as e:
            logger.error(f"API Embed 错误: {e}")
            raise

    def test_connection(self) -> bool:
        """测试连接：先尝试列出模型，不行就做一次简单嵌入"""
        try:
            models = self.client.models.list()
            logger.info(f"API 连接测试成功，可用模型数: {len(models.data)}")
            return True
        except Exception as e:
            logger.warning(f"模型列表获取失败，尝试嵌入测试: {e}")
            try:
                self.embed(["test"])
                logger.info("API 连接测试通过（嵌入请求）")
                return True
            except Exception as e2:
                logger.error(f"API 连接测试失败: {e2}")
                return False


class OllamaClient(BaseLLMClient):
    """Ollama 本地客户端"""

    def __init__(self, model_name: str, base_url: str = "http://localhost:11434", **kwargs):
        super().__init__(model_name, **kwargs)
        self.base_url = base_url.rstrip("/")

    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ):
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "max_tokens": kwargs.get("max_tokens", 1024),
                "presence_penalty": kwargs.get("presence_penalty", 0.0),
                "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
            }
        }
        logger.info(f"Ollama Chat: model={self.model_name}, stream={stream}")

        try:
            response = requests.post(url, json=payload, stream=stream)
            response.raise_for_status()
            if stream:
                def generate():
                    for line in response.iter_lines():
                        if line:
                            import json
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                return generate()
            else:
                data = response.json()
                return data["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama Chat 错误: {e}")
            raise

    def embed(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.base_url}/api/embeddings"
        embeddings = []
        for text in texts:
            payload = {
                "model": self.model_name,
                "prompt": text
            }
            resp = requests.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            emb = data.get("embedding") or data.get("vector")
            if emb is None:
                raise ValueError(f"Ollama 嵌入返回未知格式: {data}")
            # 强制归一化
            norm = math.sqrt(sum(x * x for x in emb))
            if norm > 0:
                emb = [x / norm for x in emb]
            embeddings.append(emb)
        return embeddings

    def test_connection(self) -> bool:
        """尝试获取模型列表或直接进行一次嵌入测试"""
        try:
            # 尝试获取模型列表
            resp = requests.get(f"{self.base_url}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m["name"] for m in models]
                if self.model_name in model_names:
                    logger.info(f"Ollama 连接测试成功，模型 {self.model_name} 已安装")
                    return True
                else:
                    # 模型不存在，但连接没问题，也返回 True？可能模型需要拉取
                    # 为了严格，可以尝试拉取或嵌入测试，这里返回 True 并警告
                    logger.warning(f"Ollama 连接成功，但模型 {self.model_name} 未找到")
                    # 尝试一个简单的 embed（可能失败）
                    self.embed(["test"])
                    return True
            else:
                return False
        except Exception as e:
            logger.error(f"Ollama 连接测试失败: {e}")
            return False


def get_llm_client() -> BaseLLMClient:
    """
    工厂方法：根据数据库配置创建 LLM 客户端实例
    :return: 配置好的客户端实例
    """
    # 从数据库读取配置
    mode = SystemConfig.get_value(db_session, 'llm_mode', 'api')
    chat_model = SystemConfig.get_value(db_session, 'chat_model', 'gpt-3.5-turbo')
    embedding_model = SystemConfig.get_value(db_session, 'embedding_model', 'text-embedding-ada-002')

    logger.info(f"初始化 LLM 客户端，模式={mode}, chat模型={chat_model}, embed模型={embedding_model}")

    if mode == 'ollama':
        base_url = SystemConfig.get_value(db_session, 'ollama_base_url', 'http://localhost:11434')
        # Ollama 使用同一个模型名？通常 chat 和 embed 用不同模型，但我们可以分别传
        # 为简化，这里返回的客户端 chat 方法使用 chat_model，embed 使用 embedding_model
        # 但当前客户端只绑定一个模型名，我们需要根据调用分别创建？更好的设计是拆分为 chat_client 和 embed_client
        # 暂时先返回 chat 模型客户端，embed 时需要切换。或在 rag_engine 中独立创建
        # 为满足现有设计，我们在这里分别提供两个客户端
        pass

    # 返回单一客户端的实现需要改进。考虑到 rag_engine 分别需要 chat 和 embed，
    # 我们可以让这个工厂返回一个包含两个子客户端的 wrapper，或者直接在 rag_engine 中分别获取。
    # 这里先保持简单：返回一个能同时处理 chat 和 embed 的统一客户端。
    # 我们将创建一个统一客户端类，内部包含两个实际的客户端。
    return UnifiedLLMClient()


class UnifiedLLMClient(BaseLLMClient):
    """
    统一客户端，内部根据配置动态选择 chat 和 embed 的执行实例。
    该类不是为了继承，而是组合两个不同模式/模型的客户端。
    """

    def __init__(self):
        self.mode = SystemConfig.get_value(db_session, 'llm_mode', 'api')
        if self.mode == 'api':
            self.chat_model_name = SystemConfig.get_value(db_session, 'api_chat_model', 'gpt-3.5-turbo')
            self.embed_model_name = SystemConfig.get_value(db_session, 'api_embedding_model',
                                                               'text-embedding-ada-002')
            api_key = SystemConfig.get_value(db_session, 'api_key', '')
            base_url = SystemConfig.get_value(db_session, 'api_base_url', '')
            self.chat_client = APIClient(self.chat_model_name, api_key=api_key, base_url=base_url)
            self.embed_client = APIClient(self.embed_model_name, api_key=api_key, base_url=base_url)
        elif self.mode == 'ollama':
            self.chat_model_name = SystemConfig.get_value(db_session, 'local_chat_model', 'qwen3.5:9b')
            self.embed_model_name = SystemConfig.get_value(db_session, 'local_embedding_model',
                                                               'qwen3-embedding:8b')
            base_url = SystemConfig.get_value(db_session, 'ollama_base_url', 'http://localhost:11434')
            self.chat_client = OllamaClient(self.chat_model_name, base_url=base_url)
            self.embed_client = OllamaClient(self.embed_model_name, base_url=base_url)
        else:
            raise ValueError(f"未知 LLM 模式: {self.mode}")

        super().__init__("unified")

    def chat(self, messages, stream=False, **kwargs):
        return self.chat_client.chat(messages, stream=stream, **kwargs)

    def embed(self, texts):
        return self.embed_client.embed(texts)

    def test_connection(self):
        """测试 chat 和 embed 两个连接"""
        chat_ok = self.chat_client.test_connection()
        embed_ok = self.embed_client.test_connection()
        return chat_ok and embed_ok


def test_connection() -> dict:
    """
    测试当前配置的 LLM 连接
    :return: dict with 'success' (bool) and 'message' (str)
    """
    try:
        client = get_llm_client()
        result = client.test_connection()
        return {"success": result, "message": "连接成功" if result else "连接失败"}
    except Exception as e:
        logger.error(f"连接测试异常: {e}")
        return {"success": False, "message": str(e)}