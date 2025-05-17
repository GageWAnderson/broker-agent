from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).parent.parent.parent


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
    log_level: str = Field(
        default="INFO", description="Logging level for the application"
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
