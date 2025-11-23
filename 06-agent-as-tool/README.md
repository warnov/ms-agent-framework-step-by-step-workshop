# Using an agent as a function tool
This lab shows you how to use an agent as a function tool, so that one agent can call another agent as a tool.

## Create and use an agent as a function tool
You can use a `ChatAgent` as a function tool by calling `.as_tool()` on the agent and providing it as a tool to another agent. This allows you to compose agents and build more advanced workflows.

First, create a function tool that will be used by your agent that's exposed as a function. Place it in [`tools.py`](tools.py) so it can be imported by other modules in this lab.

```python
from typing import Annotated
from pydantic import Field


def get_weather(
    location: Annotated[str, Field(description="The location to get the weather for.")],
) -> str:
    """Get the weather for a given location."""
    return f"The weather in {location} is cloudy with a high of 15°C."
```

## Run the interactive example

[`app.py`](app.py) builds two agents:

- `WeatherAgent`: owns the `get_weather` tool and answers in simple English.
- `main_agent`: answers in French and calls `WeatherAgent.as_tool()` whenever it needs weather data.

When you run the script you can type any city or country and you will see two consecutive responses: the direct WeatherAgent response and the orchestrator agent invoking it as a tool.

```powershell
python 06-agent-as-tool/app.py
```

Example output:

```
=== Agent as Tool Lab ===
Compare WeatherAgent's direct response with MainAgent calling it as a tool (type 'exit' to stop).

City or country: Amsterdam

[WeatherAgent direct]
The weather in Amsterdam is cloudy with a high of 15°C.

[MainAgent using WeatherAgent as a tool]
Le temps à Amsterdam est nuageux avec une température maximale de 15 °C.
```

Type `exit` or `quit` to leave the loop. This demonstrates how a specialized agent can be exposed as a tool while another agent keeps a different tone or language.

## Customize the tool metadata

Sometimes you need the downstream agent to see friendlier tool names, descriptions, or argument hints than the defaults that come from `as_tool()`. The file [`app_custom_tool.py`](app_custom_tool.py) mirrors the interactive sample but emphasizes how to override those metadata fields before wiring the tool into the orchestrator.

The snippet below highlights the change (full context in `app_custom_tool.py`):

```python
weather_tool = weather_agent.as_tool(
    name="WeatherLookup",
    description="Look up weather information for any location",
    arg_name="query",
    arg_description="The weather query or location",
)

main_agent = AzureOpenAIChatClient(
    credential=AzureCliCredential(),
    endpoint=os.environ["AOAI_ENDPOINT"],
    deployment_name=os.environ["AOAI_DEPLOYMENT"]
).create_agent(
    instructions="You are a helpful assistant who responds in French.",
    tools=weather_tool,
)
```

Create or Run `python 06-agent-as-tool/app_custom_tool.py` to see the customized version in action.

------

## 📝 Lab 06 Conclusion: Agent as Tool Composition

In this lab you connected two fully fledged agents: `WeatherAgent`, which owns a domain-specific tool, and `main_agent`, which orchestrates the conversation in another language. The interactive comparison shows exactly what changes when you wrap an agent as a tool—the downstream orchestrator can keep its own tone, safety filters, and instructions while delegating weather-specific logic. The custom metadata variant in `app_custom_tool.py` highlights how to expose friendlier tool docs or rename arguments without touching the backing agent.

------

#### Key Takeaways from Lab 06

- **Agents can become tools:** `weather_agent.as_tool()` lets one agent encapsulate its skills so another agent can invoke it like any other function tool.
- **Orchestrators keep their own persona:** `main_agent` continues responding in French even though the weather data comes from an English agent.
- **Custom tool metadata matters:** The `app_custom_tool.py` sample demonstrates giving product-ready names, descriptions, and argument hints so end users and downstream planners know how to call the tool.
- **Interactive loops aid debugging:** The CLI prints both direct and tool-mediated responses, making it easy to validate that the tool wiring behaves as expected before embedding it elsewhere.

------

### Code Reference

- [`app.py`](app.py) — Interactive comparison between direct WeatherAgent calls and tool-based orchestration.
- [`app_custom_tool.py`](app_custom_tool.py) — Same flow but with custom tool metadata (name, description, argument labels).
- [`tools.py`](tools.py) — Reusable `get_weather` function that the agents import.

------

## 🔗 Navigation

- **[⬅️ Back: Lab 05 — Structured Output](../05-structured-output/README.md)** — Revisit structured response schemas and streaming.
- **[🏠 Back to Workshop Home](../README.md)** — Return to the lab index and prerequisites.
- **[➡️ Next: Lab 07 — Expose an Agent as an MCP Server](../07-agent-as-MCP-tool/README.md)** — Publish domain tools through the Model Context Protocol.

