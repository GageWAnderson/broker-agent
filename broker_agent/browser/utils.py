import asyncio
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
