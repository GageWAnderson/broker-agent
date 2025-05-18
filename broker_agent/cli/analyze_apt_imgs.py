import asyncio
import traceback

import click
from ollama import ChatResponse
from sqlalchemy import select

from broker_agent.common.enum import LLMType
from broker_agent.common.utils import get_all_imgs_by_apt_id_as_base64
from broker_agent.config.logging import configure_logging, get_logger
from broker_agent.config.settings import config
from broker_agent.llm.client import get_llm
from database.alembic.models.models import Apartment
from database.connection import async_db_session

configure_logging(log_level=config.log_level)

logger = get_logger(__name__)


async def analyze_img_by_urls(img_urls: list[str]) -> str:
    """
    Analyze a list of apartment images and return a description using
    the configured prompt template from image_analysis.yaml.

    Args:
        img_urls: List of image URLs to analyze

    Returns:
        str: Description of the apartment
    """
    llm = get_llm()

    # Use the prompt from the image analysis config
    prompt = config.image_analysis.prompt

    content = [{"type": "text", "text": prompt}]
    for url in img_urls:
        content.append(
            {
                "type": "image",
                "source_type": "url",
                "url": url,
            }
        )

    message = {
        "role": "user",
        "content": content,
    }

    response = await llm.ainvoke([message])
    return response.content


async def analyze_img_by_base64(img_base64_list: list[dict]) -> str | None:
    """
    Analyze a list of apartment images (as base64) and return a description using
    the configured prompt template from image_analysis.yaml.

    Args:
        img_base64_list: List of dicts, each containing:
            {
                "data": "<base64 data string>",
                "mime_type": "image/jpeg"  # or "image/png", etc.
            }

    Returns:
        str: Description of the apartment
    """
    vision_llm = get_llm(model_name=config.vision_llm, llm_type=LLMType.OLLAMA_VLM)
    images = [img["data"] for img in img_base64_list if "data" in img]

    message = [
        {
            "role": "user",
            "content": config.image_analysis.prompt,
            "images": images,
        }
    ]

    response: ChatResponse = await vision_llm.chat(model=config.vision_llm, messages=message)
    if not response.message.content:
        logger.warning("No response from vision LLM for image")
        return None
    return response.message.content


async def async_run_analyze_apt_imgs() -> None:
    """
    Analyze images for all apartments in the database.
    For each apartment:
    1. Retrieve all image URLs
    2. Analyze the images using the LLM
    3. Print the results
    """
    # Use the async_db_session context manager
    async with async_db_session() as session:
        # Get all apartment IDs
        result = await session.execute(select(Apartment.apartment_id))
        apartment_ids = result.scalars().all()

        for apt_id in apartment_ids:
            try:
                # Get image URLs for this apartment
                imgs = await get_all_imgs_by_apt_id_as_base64(apt_id, session)

                if not imgs:
                    logger.warning(f"No images found for apartment ID: {apt_id}")
                    continue
                logger.info(f"Analyzing {len(imgs)} images for apartment ID: {apt_id}")
                # Analyze images
                analysis = await analyze_img_by_base64(imgs)

                if not analysis:
                    continue

                # Print the results
                logger.info(f"Analysis for apartment ID {apt_id}:")
                logger.info(analysis)
                logger.info("-" * 50)

            except Exception as e:
                logger.error(f"Error analyzing apartment ID {apt_id}: {e}")
                logger.debug(traceback.extract_stack())
                raise e


@click.command()
def run_analyze_apt_imgs() -> None:
    asyncio.run(async_run_analyze_apt_imgs())
