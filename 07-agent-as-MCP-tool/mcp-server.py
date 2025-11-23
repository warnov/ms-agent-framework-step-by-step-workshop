"""RestaurantAgent MCP server.

This script shows how to wrap a function-enabled agent from Lab 06 as an MCP
server so that any MCP-compatible host (Claude Desktop, the sample client in
this lab, etc.) can call its tools over stdio.
"""

import os
from typing import Annotated
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential

def get_specials() -> Annotated[str, "Returns the specials from the menu."]:
    """Return a static menu for demo purposes."""
    return """
        Special Soup: Clam Chowder
        Special Salad: Cobb Salad
        Special Drink: Chai Tea
        """

def get_item_price(
    menu_item: Annotated[str, "The name of the menu item."],
) -> Annotated[str, "Returns the price of the menu item."]:
    """Return a placeholder price regardless of the input item."""
    return "$9.99"

# Create an agent with tools using the same Azure OpenAI pattern from Lab 06.
agent = AzureOpenAIChatClient(
    credential=AzureCliCredential(),
    endpoint=os.environ["AOAI_ENDPOINT"],
    deployment_name=os.environ["AOAI_DEPLOYMENT"],
).create_agent(
    name="RestaurantAgent",
    description="Answer questions about the menu.",
    tools=[get_specials, get_item_price],
)

# Expose the agent as an MCP server so stdio clients can call those tools.
server = agent.as_mcp_server()

import anyio
from mcp.server.stdio import stdio_server

async def run():
    """Start the stdio server loop expected by the MCP transport."""

    async def handle_stdin():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    await handle_stdin()

if __name__ == "__main__":
    # anyio abstracts away the event loop policy on each OS.
    anyio.run(run)