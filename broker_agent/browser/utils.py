import asyncio
import random
import re

from playwright.async_api import Page

from broker_agent.config.logging import get_logger

logger = get_logger(__name__)


# TODO: May need to filter a11y tree to ensure best model understanding
def format_a11y_tree(tree_data):
    """Format an accessibility tree for better readability."""

    # Handle input that's already a dictionary
    if isinstance(tree_data, dict):
        tree = tree_data
    else:
        raise TypeError("Input must be a dictionary or string")

    # Format the tree recursively
    def format_node(node, depth=0):
        indent = "  " * depth
        result = []

        # Node header with role and name
        header = f"{indent}- {node['role']}: \"{node['name']}\""
        result.append(header)

        # Process children if present
        if "children" in node and node["children"]:
            if len(node["children"]) > 10:
                # Summarize if there are many children
                shown_children = node["children"][:5]
                result.append(f"{indent}  ↳ Children ({len(node['children'])} total):")
                for child in shown_children:
                    result.extend(format_node(child, depth + 2))
                result.append(
                    f"{indent}  ↳ ... {len(node['children']) - 5} more children ..."
                )
            else:
                result.append(f"{indent}  ↳ Children:")
                for child in node["children"]:
                    result.extend(format_node(child, depth + 2))

        return result

    formatted = format_node(tree)
    return "\n".join(["# Accessibility Tree Structure", "```", *formatted, "```"])


async def extract_playwright_script(script_content):
    """
    Extract the playwright script from between the ```playwright and ``` markers

    Args:
        script_content (str): The content containing the playwright script

    Returns:
        str or None: The extracted script if found, None otherwise
    """
    playwright_code = re.search(r"```playwright\n(.*?)```", script_content, re.DOTALL)
    if playwright_code:
        return playwright_code.group(1)
    return None


async def get_text_content_with_timeout(
    page: Page, selector: str, timeout_s: float = 5.0
) -> str | None:
    try:
        locator = page.locator(selector)
        content = await asyncio.wait_for(locator.text_content(), timeout=timeout_s)
        return content.strip() if content else None
    except TimeoutError:
        logger.debug(f"Timeout getting text content for {selector}")
        return None
    except Exception as e:
        logger.debug(f"Error getting text content for {selector}: {e}")
        return None


def generate_random_user_agent():
    """
    Generate a random plausible Chrome-based user agent string.
    """
    # OS options
    os_options = [
        "Windows NT 10.0; Win64; x64",
        "Windows NT 10.0; WOW64",
        "Windows NT 6.1; Win64; x64",
        "Macintosh; Intel Mac OS X 10_15_7",
        "Macintosh; Intel Mac OS X 11_2_3",
        "X11; Linux x86_64",
    ]
    os_str = random.choice(os_options)

    # Chrome version
    chrome_major = random.randint(90, 120)
    chrome_build = random.randint(4400, 5800)
    chrome_patch = random.randint(50, 200)
    chrome_version = f"{chrome_major}.0.{chrome_build}.{chrome_patch}"

    # AppleWebKit version
    webkit_major = 537
    webkit_minor = random.randint(36, 50)
    webkit_version = f"{webkit_major}.{webkit_minor}"

    # Safari version
    safari_major = 537
    safari_minor = random.randint(36, 50)
    safari_version = f"{safari_major}.{safari_minor}"

    user_agent = (
        f"Mozilla/5.0 ({os_str}) "
        f"AppleWebKit/{webkit_version} (KHTML, like Gecko) "
        f"Chrome/{chrome_version} Safari/{safari_version}"
    )
    return user_agent
