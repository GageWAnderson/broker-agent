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
        env_file=ROOT_DIR / ".env", env_file_encoding="utf-8"
    )

    # App
    log_level: str = Field(
        default="INFO",
        description="Logging level for the application"
    )

    websites: list[str] = Field(
        default_factory=list,
        description="List of websites to scrape for rental listings"
    )

    BRAVE_API_KEY: str = Field(
        ...,
        description="API key for Brave Search API"
    )

    @classmethod
    def load_config(cls) -> "BrokerAgentConfig":
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


config = BrokerAgentConfig.load_config()
