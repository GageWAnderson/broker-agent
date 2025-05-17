from langchain.schema.language_model import BaseLanguageModel
from langchain_ollama import ChatOllama
from ollama import AsyncClient

from broker_agent.common.enum import LLMType
from broker_agent.config.settings import config


def get_llm(
    model_name: str | None = None, llm_type: LLMType | str | None = None
) -> BaseLanguageModel | AsyncClient:
    """
    Get the language model client based on configuration or specified model.

    Args:
        model_name: Optional model name to override the default from config
        llm_type: Optional LLM type to use, defaults to config.llm_type

    Returns:
        A language model instance
    """
    model = model_name or config.llm

    # Convert string to enum if needed
    if isinstance(llm_type, str):
        llm_type = LLMType(llm_type)

    # Use config default if not specified
    llm_type = llm_type or getattr(config, "llm_type", LLMType.OLLAMA)

    # Create the appropriate LLM client based on type
    if llm_type == LLMType.OLLAMA:
        return ChatOllama(base_url=config.OLLAMA_BASE_URL, model=model)
    elif llm_type == LLMType.OLLAMA_VLM:
        return AsyncClient(host=config.OLLAMA_BASE_URL)

    # TODO: Implement other LLM types
    # elif llm_type == LLMType.OPENAI:
    #     return ChatOpenAI(model=model)
    # elif llm_type == LLMType.ANTHROPIC:
    #     return ChatAnthropic(model=model)
    # elif llm_type == LLMType.HUGGINGFACE:
    #     return HuggingFaceEndpoint(endpoint_url=config.HF_ENDPOINT_URL, model=model)
    else:
        raise ValueError(f"Unsupported LLM type: {llm_type}")


# Default LLM instance for backward compatibility
ollama = get_llm()
