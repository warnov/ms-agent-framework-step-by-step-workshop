"""Utility script to exercise the RestaurantAgent MCP server over stdio."""

import asyncio
import json
import sys
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPRestaurantClient:
    def __init__(self, server_script_path: str):
        """MCP client for the RestaurantAgent server with optional verbose logging."""
        self.server_script_path = server_script_path
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
        # Verbose mode prints environment diagnostics and tool schemas
        # before switching to the quieter interactive loop.
        self.verbose = True
        
    async def connect(self):
        """Connect to the MCP server using stdio transport."""
        import os

        if self.verbose:
            print(f"Connecting to server script: {self.server_script_path}")
            print("Environment checks:")
            print(f"- AOAI_ENDPOINT: {os.environ.get('AOAI_ENDPOINT', 'NOT SET')}")
            print(f"- AOAI_DEPLOYMENT: {os.environ.get('AOAI_DEPLOYMENT', 'NOT SET')}")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[self.server_script_path],
            env=os.environ.copy(),
        )
        
        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read_stream, write_stream = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            init_result = await self.session.initialize()
            print(f"Connected to {init_result.serverInfo.name} v{init_result.serverInfo.version}")
        except Exception as e:
            print(f"Failed to connect: {e}")
            raise
        
    async def disconnect(self):
        """Close the MCP session and all underlying resources."""
        await self.exit_stack.aclose()
        print("Disconnected from MCP server")
        
    async def list_tools(self):
        """List the tools exposed by the server."""
        tools_list = await self.session.list_tools()
        print("\n=== Tool catalog ===")
        for tool in tools_list.tools:
            description = tool.description or "No description provided."
            print(f"- {tool.name}: {description}")
            if getattr(tool, "inputSchema", None) and self.verbose:
                print("  Input schema:")
                print(json.dumps(tool.inputSchema, indent=2))
        return tools_list.tools
        
    async def call_tool(self, tool_name: str, arguments: dict | None = None, *, log_call: bool = True):
        """Invoke a tool and display the textual response.

        The ``log_call`` flag lets the interactive loop reuse this helper while
        keeping the console quiet after the initial diagnostics.
        """
        if arguments is None:
            arguments = {}

        if log_call and self.verbose:
            print(f"\nInvoking tool '{tool_name}' with arguments: {json.dumps(arguments)}")
        
        result = await self.session.call_tool(tool_name, arguments)
        for content in result.content:
            if hasattr(content, "text"):
                print(content.text.strip())
            else:
                print(content)
        
        return result
        
    async def get_specials(self, *, log_call: bool = True):
        """Ask the agent for today's specials."""
        return await self.call_tool(
            "RestaurantAgent",
            {"task": "What are today's specials?"},
            log_call=log_call,
        )
        
    async def get_item_price(self, menu_item: str, *, log_call: bool = True):
        """Ask the agent for a menu item's price."""
        return await self.call_tool(
            "RestaurantAgent",
            {"task": f"What is the price of {menu_item}?"},
            log_call=log_call,
        )


async def main():
    """Run the sample client with a basic interactive loop."""
    SERVER_SCRIPT = "mcp-server.py"
    
    client = MCPRestaurantClient(SERVER_SCRIPT)
    
    try:
        await client.connect()
        await client.list_tools()

        print("\nSample calls:")
        await client.get_specials()
        await client.get_item_price("Clam Chowder")

        print("\nInteractive mode (type 4 to exit):")
        while True:
            print("\nSelect an option:")
            print("1. Show specials")
            print("2. Get price for an item")
            print("3. Ask a custom question")
            print("4. Exit")

            choice = input("Choice: ").strip()

            if choice == "1":
                await client.get_specials(log_call=False)
            elif choice == "2":
                item = input("Menu item name: ").strip()
                if item:
                    await client.get_item_price(item, log_call=False)
            elif choice == "3":
                question = input("Enter your question: ").strip()
                if question:
                    await client.call_tool("RestaurantAgent", {"task": question}, log_call=False)
            elif choice == "4":
                break
            else:
                print("Invalid option. Please choose 1-4.")
    except FileNotFoundError:
        print(f"Server script '{SERVER_SCRIPT}' was not found. Make sure it exists next to this client.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    print("=== RestaurantAgent MCP client ===\n")
    asyncio.run(main())