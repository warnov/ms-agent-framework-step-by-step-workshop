# Lab05 - Producing Structured Output with Agents

This lab shows you how to produce structured output with an agent, where the agent is built on the `Azure OpenAI Chat Completion` service.

> [!IMPORTANT]
>
> Not all agent types support structured output. The `ChatAgent` supports structured output when used with compatible chat clients such as:
>
> - `AzureOpenAIChatClient` (Azure OpenAI Chat Completions)
> - `OpenAIResponsesClient` (OpenAI-compatible Responses API)
> - `GitHubOpenAIChatClient` (GitHub Models chat endpoint)
>
> Any client that implements the structured output contract (tool definitions + JSON modes) can be plugged into `ChatAgent` for this lab.

## Create the agent with structured output

The `ChatAgent` is built on top of any chat client implementation that supports structured output. The `ChatAgent` uses the `response_format` parameter to specify the desired output schema.

When creating or running the agent, you can provide a Pydantic model that defines the structure of the expected output.

Various response formats are supported based on the underlying chat client capabilities.

This example creates an agent that produces structured output in the form of a JSON object that conforms to a Pydantic model schema.

First, define a Pydantic model that represents the structure of the output you want from the agent. Create a file named [`model.py`](model.py) and place the following schema inside it (the finished version is available at that link for reference):

```python
from pydantic import BaseModel

class PersonInfo(BaseModel):
    """Information about a person."""
    name: str | None = None
    age: int | None = None
    occupation: str | None = None
```

Below is how `app.py` is organized. Each logical unit maps directly to a function so you can reuse pieces independently.

### 1. Agent factory (`build_agent`)

This block centralizes every dial that defines how the agent talks to Azure OpenAI. By creating a helper that returns a fully configured `ChatAgent`, you isolate endpoint, deployment, name, and instructions in a single place, making it trivial to reuse or swap environments without touching the rest of the workflow.

```python
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential


def build_agent():
    return AzureOpenAIChatClient(
        credential=AzureCliCredential(),
        endpoint="https://warstandalone.openai.azure.com/",
        deployment_name="dep-gpt-5-mini"
    ).create_agent(
        name="HelpfulAssistant",
        instructions=(
            "You are an assistant that extracts person information from free-form descriptions. "
            "Only fill the fields that are explicitly mentioned."
        )
    )
```

- Keeps the deployment details in one place.
- Returns a fully configured `ChatAgent` ready for structured output runs.

### 2. Formatter (`print_person`)

Before we worry about models and streaming, we want a consistent way to show people data. This helper receives whatever structured output the agent produced and prints it with friendly labels, highlighting when a field was omitted by the model so testers can immediately see what information was captured.

```python
def print_person(info: PersonInfo | None, label: str) -> None:
    print(f"\n=== {label} ===")
    if not info:
        print("No structured data found in response")
        return
    print(
        f"Name: {info.name or 'unknown'}, Age: {info.age or 'unknown'}, "
        f"Occupation: {info.occupation or 'unknown'}"
    )
```

- Centralizes how structured output is presented.
- Shows when a field is missing by printing `unknown`.

### 3. Dual execution path (`describe_person`)

Structured output can arrive in two different modes: a single JSON blob when you call `agent.run(...)`, or as a sequence of deltas when you use streaming. This function demonstrates both paths back-to-back so you can compare the results. 

The streaming branch requires two things: 

1. Invoking `agent.run_stream(...)` to receive incremental updates
2. Passing that generator into `AgentRunResponse.from_agent_response_generator(...)`, which stitches all of the fragments into the same Pydantic model (`PersonInfo`) you expect from the non-streaming path. Without this collector, you would have to manually buffer every update and merge them yourself. 

Showing the two executions together highlights that—you get the same typed object in the end, but streaming gives earlier feedback while the agent is still “thinking,” which is invaluable for UI scenarios.

```python
from agent_framework import AgentRunResponse


async def describe_person(agent, description: str) -> None:
    response = await agent.run(description, response_format=PersonInfo)
    print_person(response.value if hasattr(response, "value") else None, "Non-streaming response")

    final_response = await AgentRunResponse.from_agent_response_generator(
        agent.run_stream(description, response_format=PersonInfo),
        output_format_type=PersonInfo,
    )
    print_person(final_response.value, "Streaming response")
```

- First call uses `agent.run(...)` for the immediate JSON payload.
- Second call uses `run_stream(...)` plus `AgentRunResponse.from_agent_response_generator(...)` to aggregate streaming deltas into the same `PersonInfo` Pydantic model.

### 4. Interactive loop (`main`)

Finally, we wrap the building blocks into a simple CLI. This loop sets user expectations, keeps the agent alive for the entire session, and handles exit conditions. It is intentionally minimal so the focus stays on how the previous components work together.

```python
import asyncio


async def main() -> None:
    agent = build_agent()
    print("=== Structured Output Lab ===")
    print("Describe a person and I will emit structured JSON (type 'exit' to quit).\n")

    while True:
        description = input("Describe a person: ").strip()
        if not description:
            continue
        if description.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        await describe_person(agent, description)


if __name__ == "__main__":
    asyncio.run(main())
```

- Provides clear instructions to the user.
- Keeps the agent alive for the whole session, which avoids re-authenticating every turn.

### Run the interactive lab

```bash
python 05-structured-output/app.py
```

Example session:

```
Describe a person: Carla is a 29-year-old data scientist living in Lima.

=== Non-streaming response ===
Name: Carla, Age: 29, Occupation: data scientist

=== Streaming response ===
Name: Carla, Age: 29, Occupation: data scientist
```

Behind the scenes the app uses `agent.run(...)` for the immediate result and `AgentRunResponse.from_agent_response_generator(...)` to gather the streaming updates into the same `PersonInfo` model. This mirrors the pattern you can reuse in your own applications when you need typed JSON back from either execution mode.

------

## 📝 Lab 05 Conclusion: Structured Output

You now have an agent that emits typed JSON artifacts regardless of whether you call it in blocking or streaming mode. The dual-mode execution you coded demonstrates a practical alternative when the downstream system expects a complete object but you still want the UX advantages of streaming. By piping the streaming generator through `AgentRunResponse.from_agent_response_generator`, the framework aggregates every partial update into the exact same `PersonInfo` instance returned by the blocking call. That means you can render live progress to a user interface, yet still hand over a single, fully populated JSON payload to whatever comes next—whether that is a database write, another agent, or a workflow engine. Without this aggregator you would have to buffer all deltas yourself, handle ordering, and re-run schema validation. Here the framework does all of that heavy lifting, letting you focus on business logic instead of plumbing.

------

#### Key Takeaways from Lab 05

- **Pydantic schemas drive consistency:** Supplying `response_format=PersonInfo` ensures the agent validates output against a strongly typed model before handing it back.
- **Reusable agent factory:** Centralizing credentials and deployment settings in `build_agent` keeps environment changes isolated.
- **Dual-mode execution:** Combining `agent.run` with `run_stream` + `AgentRunResponse.from_agent_response_generator` gives you fast previews while the model streams, then automatically aggregates the deltas into a complete JSON payload that downstream steps can consume as a single object. This pattern is essential when a downstream component (for example, a payment processor or CRM update) requires the entire record at once, yet you still want the responsiveness of streaming updates in the UI.
- **Formatter for observability:** `print_person` makes it obvious when fields are missing so you can refine prompts or post-processing.

------

### Code Reference

- [`model.py`](model.py) — Pydantic schema (`PersonInfo`) that defines the response structure.
- [`app.py`](app.py) — Interactive console app demonstrating non-streaming and streaming structured output.

------

## 🔗 Navigation

- **[⬅️ Back: Lab 04 — Human-in-the-loop Approvals](../04-human-in-loop/README.md)** — Review approval workflows for high-impact tools.
- **[🏠 Back to Workshop Home](../README.md)** — Return to prerequisites and the complete lab index.
- **[➡️ Next: Lab 06 — Advanced Agent Telemetry](../06-advanced-telemetry/README.md)** — Continue with observability patterns (placeholder for upcoming content).

------
