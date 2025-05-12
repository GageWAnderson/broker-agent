from enum import Enum


class ApartmentType(Enum):
    STUDIO = "Studio"
    ONE_BEDROOM = "1 Bedroom"
    TWO_BEDROOM = "2 Bedrooms"
    THREE_BEDROOM = "3 Bedrooms"
    FOUR_PLUS_BEDROOM = "4+ Bedrooms"


class LLMType(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"


class WebsiteType(Enum):
    STREETEASY = "https://streeteasy.com/for-rent/nyc"
    APARTMENTS_DOT_COM = "https://www.apartments.com/new-york-ny/"
    RENTHOP = "https://renthop.com"
