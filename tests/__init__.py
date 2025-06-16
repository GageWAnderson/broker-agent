# __init__.py
import warnings

from .async_configs import (
    BrowserConfig,
    CrawlerRunConfig,
    GeolocationConfig,
    HTTPCrawlerConfig,
    LLMConfig,
    ProxyConfig,
)
from .async_dispatcher import (
    BaseDispatcher,
    MemoryAdaptiveDispatcher,
    RateLimiter,
    SemaphoreDispatcher,
)
from .async_logger import (
    AsyncLogger,
    AsyncLoggerBase,
)
from .async_webcrawler import AsyncWebCrawler, CacheMode
from .browser_profiler import BrowserProfiler
from .chunking_strategy import ChunkingStrategy, RegexChunking
from .components.crawler_monitor import CrawlerMonitor
from .content_filter_strategy import (
    BM25ContentFilter,
    LLMContentFilter,
    PruningContentFilter,
    RelevantContentFilter,
)
from .content_scraping_strategy import (
    ContentScrapingStrategy,
    LXMLWebScrapingStrategy,
    WebScrapingStrategy,
)
from .deep_crawling import (
    BestFirstCrawlingStrategy,
    BFSDeepCrawlStrategy,
    CompositeScorer,
    ContentTypeFilter,
    DeepCrawlDecorator,
    DeepCrawlStrategy,
    DFSDeepCrawlStrategy,
    DomainAuthorityScorer,
    DomainFilter,
    FilterChain,
    FilterStats,
    FreshnessScorer,
    KeywordRelevanceScorer,
    PathDepthScorer,
    SEOFilter,
    URLFilter,
    URLPatternFilter,
    URLScorer,
)
from .docker_client import Crawl4aiDockerClient
from .extraction_strategy import (
    CosineStrategy,
    ExtractionStrategy,
    JsonCssExtractionStrategy,
    JsonLxmlExtractionStrategy,
    JsonXPathExtractionStrategy,
    LLMExtractionStrategy,
    RegexExtractionStrategy,
)
from .hub import CrawlerHub
from .markdown_generation_strategy import DefaultMarkdownGenerator
from .models import CrawlResult, DisplayMode, MarkdownGenerationResult
from .proxy_strategy import (
    ProxyRotationStrategy,
    RoundRobinProxyStrategy,
)

__all__ = [
    "AsyncLoggerBase",
    "AsyncLogger",
    "AsyncWebCrawler",
    "BrowserProfiler",
    "LLMConfig",
    "GeolocationConfig",
    "DeepCrawlStrategy",
    "BFSDeepCrawlStrategy",
    "BestFirstCrawlingStrategy",
    "DFSDeepCrawlStrategy",
    "FilterChain",
    "URLPatternFilter",
    "ContentTypeFilter",
    "DomainFilter",
    "FilterStats",
    "URLFilter",
    "SEOFilter",
    "KeywordRelevanceScorer",
    "URLScorer",
    "CompositeScorer",
    "DomainAuthorityScorer",
    "FreshnessScorer",
    "PathDepthScorer",
    "DeepCrawlDecorator",
    "CrawlResult",
    "CrawlerHub",
    "CacheMode",
    "ContentScrapingStrategy",
    "WebScrapingStrategy",
    "LXMLWebScrapingStrategy",
    "BrowserConfig",
    "CrawlerRunConfig",
    "HTTPCrawlerConfig",
    "ExtractionStrategy",
    "LLMExtractionStrategy",
    "CosineStrategy",
    "JsonCssExtractionStrategy",
    "JsonXPathExtractionStrategy",
    "JsonLxmlExtractionStrategy",
    "RegexExtractionStrategy",
    "ChunkingStrategy",
    "RegexChunking",
    "DefaultMarkdownGenerator",
    "RelevantContentFilter",
    "PruningContentFilter",
    "BM25ContentFilter",
    "LLMContentFilter",
    "BaseDispatcher",
    "MemoryAdaptiveDispatcher",
    "SemaphoreDispatcher",
    "RateLimiter",
    "CrawlerMonitor",
    "DisplayMode",
    "MarkdownGenerationResult",
    "Crawl4aiDockerClient",
    "ProxyRotationStrategy",
    "RoundRobinProxyStrategy",
    "ProxyConfig"
]


# def is_sync_version_installed():
#     try:
#         import selenium # noqa

#         return True
#     except ImportError:
#         return False


# if is_sync_version_installed():
#     try:
#         from .web_crawler import WebCrawler

#         __all__.append("WebCrawler")
#     except ImportError:
#         print(
#             "Warning: Failed to import WebCrawler even though selenium is installed. This might be due to other missing dependencies."
#         )
# else:
#     WebCrawler = None
#     # import warnings
#     # print("Warning: Synchronous WebCrawler is not available. Install crawl4ai[sync] for synchronous support. However, please note that the synchronous version will be deprecated soon.")

# Disable all Pydantic warnings
warnings.filterwarnings("ignore", module="pydantic")
# pydantic_warnings.filter_warnings()
