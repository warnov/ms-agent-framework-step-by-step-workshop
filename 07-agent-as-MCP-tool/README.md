# Lab 07 — Expose an Agent as an MCP Server
This lab walks through building a brand-new **RestaurantAgent** that publishes its capabilities through the [Model Context Protocol](https://modelcontextprotocol.io). The use case is straightforward: a menu concierge that answers two kinds of questions—daily specials and item prices—but the emphasis is on how to wrap those Python tools, host them over stdio, and make the server discoverable by MCP-compatible clients. A lightweight CLI client is bundled solely for local smoke testing.

## 1. Scenario and agent construction
[`mcp-server.py`](mcp-server.py) defines two function tools representing the restaurant concierge’s knowledge:

- `get_specials()` emits a curated board with soup, salad, and drink names plus short descriptions. The hard-coded text lets you focus on the MCP plumbing while still returning realistic menu copy.
- `get_item_price(menu_item)` accepts a string argument (annotated with `typing.Annotated` so MCP clients see a helpful prompt) and responds with a placeholder price. You can later swap the body for a database lookup without touching the MCP wrapper.

Both functions use `Annotated` metadata so hosts display meaningful field descriptions when rendering parameter forms. They are registered on a `RestaurantAgent` built via `AzureOpenAIChatClient`. The agent authenticates through `AzureCliCredential` and reads `AOAI_ENDPOINT`/`AOAI_DEPLOYMENT`, giving it the same production-ready configuration style as earlier labs while keeping the code unique to this restaurant scenario.

```python
agent = AzureOpenAIChatClient(...).create_agent(
	name="RestaurantAgent",
	description="Answer questions about the menu.",
	tools=[get_specials, get_item_price],
)
```

The `typing.Annotated` hints on the tool signatures feed into the MCP JSON schema so clients see rich descriptions when prompting users.

## 2. Wrapping the agent in an MCP server
Calling `agent.as_mcp_server()` returns an object that understands MCP requests. The remaining code focuses on the **transport**—how clients exchange JSON-RPC messages with the server. This lab chooses stdio because desktop hosts (Claude Desktop, Cursor) already support launching MCP servers via stdin/stdout pipes.

```python
server = agent.as_mcp_server()

async def run():
	async def handle_stdin():
		async with stdio_server() as (read_stream, write_stream):
			await server.run(read_stream, write_stream, server.create_initialization_options())

	await handle_stdin()

if __name__ == "__main__":
	anyio.run(run)
```

- `stdio_server()` provides the bidirectional streams bound to stdin/stdout.
- `server.run(...)` blocks while processing JSON-RPC requests from the client, converting tool invocations into the underlying Python callables.
- `anyio.run` makes the script portable across Windows, macOS, and Linux event loops with no extra ceremony.

## 3. Lifecycle: clients launch the server on demand
In typical MCP workflows the **client** starts the server process, uses it, and terminates it. You usually do **not** run `mcp-server.py` manually. Instead:

1. Configure your MCP host (Claude Desktop, Cursor, etc.) with the command `python 07-agent-as-MCP-tool/mcp-server.py`. The host spawns the process when a conversation requires the tool, then shuts it down afterward.
2. During local development you can run `python 07-agent-as-MCP-tool/mcp-client.py`. This helper launches the server subprocess via stdio, issues a few sample calls, and exits—mirroring the exact lifecycle a GUI host would follow.

Manual execution of `mcp-server.py` remains possible for debugging, but the contract you should optimize for is “host controls the process lifetime.”

## 4. Sample client for local testing
[`mcp-client.py`](mcp-client.py) is not the focus of the lab, but it demonstrates how a client would connect: spawn the server subprocess, initialize `ClientSession`, list tools, and call them. It prints verbose diagnostics before entering a quiet interactive loop, so you can validate tool schemas and responses without leaving the terminal.

```powershell
python 07-agent-as-MCP-tool/mcp-client.py
```

Use options 1–3 in the interactive menu to call the MCP server without needing an external host.

------

## 📝 Lab 07 Conclusion: Agent-as-Server via MCP

You built a dedicated RestaurantAgent MCP server from scratch: local Python functions were annotated as tools, an Azure OpenAI–backed agent orchestrated responses, and the stdio transport exposed everything through the Model Context Protocol. The sample client mirrors an MCP host so you can iterate quickly before handing the server binary to design partners or other teams. Thanks to the Microsoft Agent Framework, this entire flow is a handful of lines—`agent.as_mcp_server()` plus the provided stdio helper—whereas previously you had to handcraft JSON-RPC plumbing, argument schemas, and process management yourself.

------

#### Key Takeaways from Lab 07

- **Server creation is additive:** your existing agent code stays intact; MCP wrapping simply layers a protocol boundary on top.
- **Stdio keeps things simple:** a single `stdio_server()` context manager is enough to integrate with Claude Desktop and other hosts.
- **Annotated tools become MCP schemas:** the `typing.Annotated` metadata flows directly into the JSON schema surfaced to clients.
- **Local clients accelerate validation:** the bundled `mcp-client.py` lets you smoke-test the server before wiring it into GUI hosts.

------

### Code Reference

- [`mcp-server.py`](mcp-server.py) — RestaurantAgent tools plus the stdio MCP host loop.
- [`mcp-client.py`](mcp-client.py) — CLI helper that behaves like an MCP host for local testing.

------

## 🔗 Navigation

- **[⬅️ Back: Lab 06 — Agent as Tool Composition](../06-agent-as-tool/README.md)** — Review how agents become reusable tools.
- **[🏠 Back to Workshop Home](../README.md)** — Return to the lab index and prerequisites.
- **[➡️ Next: Upcoming Lab](../README.md)** — Placeholder for the next module in the series.

