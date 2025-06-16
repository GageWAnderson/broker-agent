import asyncio
from typing import Any

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    CrawlResult,
    LLMConfig,
    LLMExtractionStrategy,
)
from pydantic import BaseModel


class ApartmentExtractionSchema(BaseModel):
    address: str
    price: str
    bedrooms: int
    bathrooms: int
    square_feet: int
    description: str
    amenities: list[str]
    # images: list[str] # TODO: Can the LLM handle URLs directly?
    # url: str
    # source: str


def run_crawl4ai() -> None:
    """Entry point for poetry script to run the crawl4ai extraction demo."""
    asyncio.run(_main())


async def _main() -> None:
    llm_config = LLMConfig(
        provider="ollama/deepseek-r1:70b",
        # provider="ollama/llama3.1:latest",
        # base_url="http://localhost:11434",
        base_url="http://gort:11434",
    )
    llm_strat = LLMExtractionStrategy(
        llm_config=llm_config,
        schema=ApartmentExtractionSchema.model_json_schema(),
        extraction_type="schema",
        instruction="Extract entities from the following apartment listing page. Return the entities in a JSON format.",
        chunk_token_threshold=32000,
        apply_chunking=True,
        input_format="html",
    )

    crawl_config = CrawlerRunConfig(
        extraction_strategy=llm_strat,
        cache_mode=CacheMode.BYPASS,
    )

    async with AsyncWebCrawler(config=BrowserConfig(headless=False)) as crawler:
        res: Any = await crawler.arun(
            url="https://www.apartments.com/new-york-ny/",
            config=crawl_config,
        )

        print(f"{res}")

        if isinstance(res, CrawlResult) and res.success:
            with open("res.json", "w", encoding="utf-8") as f:
                f.write(res.extracted_content)
        else:
            raise ValueError(
                "Failed to crawl the page", getattr(res, "error_message", None)
            )
