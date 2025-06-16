from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).parent.parent.parent


class BrowserSettings(BaseModel):
    """
    Configuration settings for browser automation.

    This class encapsulates all browser-related configuration options
    such as user agent rotation, viewport sizes, timezones,
    and Chrome launch arguments. It provides a convenient method to load
    these settings from a YAML file (typically `browser.yaml`).

    Attributes:
        viewport_sizes (list[dict[str, int]]): List of viewport size dictionaries (e.g., {"width": 1920, "height": 1080}).
        timezones (list[str]): List of timezone strings for randomization (e.g., "America/New_York").
        chrome_args (list[str]): List of additional Chrome launch arguments.
        blocked_url_patterns (list[str]): List of URL patterns to block.
    """

    viewport_sizes: list[dict[str, int]] = Field(
        default=[], description="List of viewport sizes to rotate through"
    )
    timezones: list[str] = Field(
        default=[], description="List of timezones for randomization"
    )
    max_retries: int = Field(
        default=3, description="Maximum number of retries for scraping"
    )
    chrome_args: list[str] = Field(default=[], description="Chrome launch arguments")
    blocked_url_patterns: list[str] = Field(
        default=[], description="List of URL patterns to block"
    )

    @classmethod
    def from_yaml(cls, file_path: Path | None = None) -> "BrowserSettings":
        """
        Load browser settings from a YAML configuration file.

        This method reads browser configuration options from a YAML file
        (by default, `browser.yaml` in the same directory as this settings file)
        and returns a `BrowserSettings` instance populated with those values.

        Args:
            file_path (Optional[Path]): Path to the browser.yaml file. If None, uses the default location.

        Returns:
            BrowserSettings: An instance with values loaded from the YAML file, or default values if the file does not exist.
        """
        if file_path is None:
            file_path = Path(__file__).parent / "browser.yaml"

        if not file_path.exists():
            return cls()

        with open(file_path) as f:
            browser_config = yaml.safe_load(f)

        return cls(**browser_config) if browser_config else cls()


class ImageAnalysisConfig(BaseModel):
    """
    Configuration for apartment image analysis.

    This class encapsulates the prompt template used for analyzing apartment images
    and extracting relevant details like bedrooms, bathrooms, square footage, etc.

    Attributes:
        prompt (str): The prompt template for the image analysis model.
    """

    prompt: str = Field(
        default="", description="The prompt template for apartment image analysis"
    )

    @classmethod
    def from_yaml(cls, file_path: Path | None = None) -> "ImageAnalysisConfig":
        """
        Load image analysis configuration from a YAML file.

        Args:
            file_path (Optional[Path]): Path to the image_analysis.yaml file. If None, uses the default location.

        Returns:
            ImageAnalysisConfig: An instance with values loaded from the YAML file, or default values if the file does not exist.
        """
        if file_path is None:
            file_path = Path(__file__).parent / "image_analysis.yaml"

        if not file_path.exists():
            return cls()

        with open(file_path) as f:
            image_analysis_config = yaml.safe_load(f)

        return cls(**image_analysis_config) if image_analysis_config else cls()


class BrokerAgentConfig(BaseSettings):
    """
    Configuration for the Broker Agent application.

    This class handles loading configuration from:
    1. Environment variables
    2. .env file
    3. default.yaml configuration file

    Configuration values are loaded in the order above, with later sources
    overriding earlier ones.
    """

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    LOGGING_LEVEL: str = Field(
        default="INFO", description="Logging level for the application"
    )

    @field_validator("LOGGING_LEVEL")
    @classmethod
    def validate_logging_level(cls, v):
        allowed_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
        if isinstance(v, str):
            v_upper = v.upper()
            if v_upper in allowed_levels:
                return v_upper
        raise ValueError(
            f"Invalid LOGGING_LEVEL '{v}'. Must be one of: {', '.join(sorted(allowed_levels))}"
        )

    streeteasy_min_price: int = Field(
        default=1000, description="Minimum price for StreetEasy apartment search"
    )
    streeteasy_max_price: int = Field(
        default=2000, description="Maximum price for StreetEasy apartment search"
    )
    streeteasy_apt_type: str = Field(
        default="1 Bedroom",
        description="Apartment type for StreetEasy search (Studio, 1 Bedroom, 2 Bedrooms, etc.)",
    )
    apartments_dot_com_max_retries: int = Field(
        default=3,
        description="Maximum number of retries for Apartments.com pagination navigation",
    )
    apartments_dot_com_base_delay: float = Field(
        default=10.0,
        description="Base delay in seconds before making the first paginated request on Apartments.com",
    )
    apartments_dot_com_max_delay: float = Field(
        default=60.0,
        description="Maximum delay in seconds when applying exponential back-off on Apartments.com paginated requests",
    )
    apartments_dot_com_max_pages: int = Field(
        default=10,
        description="Maximum number of pages to scrape on Apartments.com",
    )
    apartments_dot_com_start_page: int = Field(
        default=0,
        description="Starting page number for Apartments.com pagination navigation",
    )

    minio_bucket: str = Field(default="broker_agent", description="MinIO bucket name")

    websites: list[str] = Field(
        default_factory=list,
        description="List of websites to scrape for rental listings",
    )

    # TODO: Add more LLMs specialized to each part of the app
    llm: str = Field(
        default="deepseek-r1:70b",
        description="LLM model to use for the application",
    )

    vision_llm: str = Field(
        default="gemma3:27b",
        description="LLM model to use for vision tasks",
    )

    script_generation_retries: int = Field(
        default=3,
        description="Number of times to retry script generation",
    )

    # New: StreetEasy scraping configuration
    streeteasy_max_depth: int = Field(
        default=2,
        description="Maximum number of pagination pages to traverse when scraping StreetEasy listings",
    )

    # New: StreetEasy politeness/retry configuration
    streeteasy_base_delay: float = Field(
        default=2.0,
        description="Base delay in seconds before making the first paginated request on StreetEasy",
    )
    streeteasy_max_delay: float = Field(
        default=60.0,
        description="Maximum delay in seconds when applying exponential back-off on StreetEasy paginated requests",
    )
    streeteasy_max_retries: int = Field(
        default=3,
        description="Maximum number of retries when StreetEasy pagination navigation fails",
    )

    parallel_browsers: int = Field(
        default=3,
        description="Number of parallel browser instances to use per website when scraping",
    )

    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434", description="Base URL for the Ollama API"
    )

    BRAVE_API_KEY: str = Field(..., description="API key for Brave Search API")

    # Database configuration
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(
        default="postgres", description="PostgreSQL password"
    )
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_DB: str = Field(default="postgres", description="PostgreSQL database name")

    # MinIO configuration
    MINIO_ENDPOINT: str = Field(
        default="localhost:9000", description="MinIO server endpoint"
    )
    MINIO_ROOT_USER: str = Field(default="minioadmin", description="MinIO user name")
    MINIO_ROOT_PASSWORD: str = Field(default="", description="MinIO secret password")

    # Browser config
    browser_settings: BrowserSettings = Field(
        default_factory=lambda: BrowserSettings.from_yaml(),
        description="Browser-specific configuration",
    )
    HEADLESS_BROWSER: bool = Field(
        default=False, description="Whether to run browsers in headless mode"
    )
    BROWSER_API_ENDPOINT: str = Field(
        default="http://localhost:8000",
        description="Browser API endpoint for remote scraping browser",
    )
    LOCAL_BROWSER: bool = Field(
        default=False,
        description="Whether to use a local browser instance instead of a remote one",
    )
    USE_REMOTE_PROXY_IPS: bool = Field(
        default=False,
        description="Whether to use remote proxy IPs for scraping requests",
    )
    BRD_SERVER: str = Field(
        default="",
        description="BrowserMob Proxy server",
    )
    BRD_PROXY_USERNAME: str = Field(
        default="",
        description="BrowserMob Proxy username",
    )
    BRD_PROXY_PASSWORD: str = Field(
        default="",
        description="BrowserMob Proxy password",
    )

    # Image analysis config
    image_analysis: ImageAnalysisConfig = Field(
        default_factory=lambda: ImageAnalysisConfig.from_yaml(),
        description="Image analysis configuration",
    )

    @classmethod
    def from_yaml_and_env(cls) -> "BrokerAgentConfig":
        """
        Load configuration from environment variables and YAML file.

        Returns:
            BrokerAgentConfig: Fully configured instance
        """
        config = cls()

        config_dir = Path(__file__).parent
        with open(config_dir / "default.yaml") as f:
            yaml_config = yaml.safe_load(f)

        config = cls._load_from_yaml(config, yaml_config)
        return config

    @classmethod
    def _load_from_yaml(cls, config, yaml_config):
        """
        Helper function to load config values from yaml file.

        Args:
            config: The config instance to update
            yaml_config: The loaded yaml configuration

        Returns:
            Updated config instance
        """
        if yaml_config:
            for field_name, _ in config.__dict__.items():
                # Skip private attributes and methods
                if not field_name.startswith("_"):
                    try:
                        if field_name in yaml_config:
                            setattr(config, field_name, yaml_config[field_name])
                    except Exception:
                        # If loading fails, keep the default value
                        pass
        return config


config = BrokerAgentConfig.from_yaml_and_env()
