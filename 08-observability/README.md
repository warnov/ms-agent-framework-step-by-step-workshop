# Lab08 - Enabling observability for Agents
This tutorial shows how to enable OpenTelemetry on an agent so that interactions with the agent are automatically logged and exported. In this tutorial, output is written to the console using the OpenTelemetry console exporter.

## What is OpenTelemetry?
OpenTelemetry is an open-source observability framework that standardizes how metrics, traces, and logs are collected and exported. It provides SDKs that let your agent emit data consistently so you can analyze performance, troubleshoot issues, and correlate distributed calls with any backend that supports the OpenTelemetry protocol.

###### When you install the Agent Framework, it automatically includes all necessary OpenTelemetry dependencies:

```text
opentelemetry-api
opentelemetry-sdk
opentelemetry-exporter-otlp-proto-grpc
opentelemetry-semantic-conventions-ai
```

If you also want to export to Azure Monitor (Application Insights), you also need to install the `azure-monitor-opentelemetry` package:

```bash
pip install azure-monitor-opentelemetry
```

## Enable OpenTelemetry in your app

Agent Framework provides a convenient `setup_observability` function that configures OpenTelemetry with sensible defaults. By default, it exports to the console if no specific exporter is configured.

```python
import asyncio
from agent_framework.observability import setup_observability
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

# Force console-only exporting so no OTLP collector is required
setup_observability(enable_sensitive_data=True, exporters=[ConsoleSpanExporter()])
```

### Understanding `setup_observability` parameters

The `setup_observability` function accepts the following parameters to customize your observability configuration:

- **`enable_otel`** (bool, optional): Enables OpenTelemetry tracing and metrics. Default is `False` when using environment variables only, but is assumed `True` when calling `setup_observability()` programmatically. When using environment variables, set `ENABLE_OTEL=true`.
- **`enable_sensitive_data`** (bool, optional): Controls whether sensitive data like prompts, responses, function call arguments, and results are included in traces. Default is `False`. Set to `True` to see actual prompts and responses in your traces. **Warning**: Be careful with this setting as it might expose sensitive data in your logs. Can also be set via `ENABLE_SENSITIVE_DATA=true` environment variable.
- **`otlp_endpoint`** (str, optional): The OTLP endpoint URL for exporting telemetry data. Default is `None`. Commonly set to `http://localhost:4317`. This creates an OTLPExporter for spans, metrics, and logs. Can be used with any OTLP-compliant endpoint such as [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/), [Aspire Dashboard](https://learn.microsoft.com/en-us/dotnet/aspire/fundamentals/dashboard/overview?tabs=bash), or other OTLP endpoints. Can also be set via `OTLP_ENDPOINT` environment variable.
- **`applicationinsights_connection_string`** (str, optional): Azure Application Insights connection string for exporting to Azure Monitor. Default is `None`. Creates AzureMonitorTraceExporter, AzureMonitorMetricExporter, and AzureMonitorLogExporter. You can find this connection string in the Azure portal under the "Overview" section of your Application Insights resource. Can also be set via `APPLICATIONINSIGHTS_CONNECTION_STRING` environment variable. Requires installation of the `azure-monitor-opentelemetry` package.
- **`vs_code_extension_port`** (int, optional): Port number for the AI Toolkit or Azure AI Foundry VS Code extension. Default is `4317`. Allows integration with VS Code extensions for local development and debugging. Can also be set via `VS_CODE_EXTENSION_PORT` environment variable.
- **`exporters`** (list, optional): Custom list of OpenTelemetry exporters for advanced scenarios. Default is `None`. Allows you to provide your own configured exporters when the standard options don't meet your needs. 

> [!IMPORTANT]
>
> When no exporters (either through parameters, environment variables, or explicit exporters) are provided, Agent Framework adds console exporters automatically for local debugging. Setting `OTLP_ENDPOINT`, `VS_CODE_EXTENSION_PORT`, or `APPLICATIONINSIGHTS_CONNECTION_STRING` will add network exporters, so clear those variables if you want console-only output.

### Setup options

You can configure observability in three ways:

**1. Environment variables** (simplest approach - you can create them using the method you prefer):

```bash
export ENABLE_OTEL=true
export ENABLE_SENSITIVE_DATA=true
export OTLP_ENDPOINT=http://localhost:4317
```

Only set `OTLP_ENDPOINT` (or related variables) when you have a collector listening on that address; otherwise leave them unset so you stay in console-only mode. Remember to restart your console/VS Code for these changes to take effect.

> [!TIP]
> If you do **not** have an OTLP collector listening on `localhost:4317`, unset `OTLP_ENDPOINT`, `VS_CODE_EXTENSION_PORT`, and `APPLICATIONINSIGHTS_CONNECTION_STRING` so Agent Framework falls back to console exporters and you avoid repeated `StatusCode.UNAVAILABLE` warnings.

Then in your code:

```python
from agent_framework.observability import setup_observability

setup_observability()  # Reads from environment variables
```

**2. Programmatic configuration**:

```python
from agent_framework.observability import setup_observability
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

# note that ENABLE_OTEL is implied to be True when calling setup_observability programmatically
setup_observability(
    enable_sensitive_data=True,
    exporters=[ConsoleSpanExporter()],
)
```

**3. Custom exporters** (for advanced scenarios):

```python
from agent_framework.observability import setup_observability
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

custom_exporters = [
    OTLPSpanExporter(endpoint="http://localhost:4317"),
    ConsoleSpanExporter()
]

setup_observability(exporters=custom_exporters, enable_sensitive_data=True)
```

The `setup_observability` function sets the global tracer provider and meter provider, allowing you to create custom spans and metrics:

```python
from agent_framework.observability import get_tracer, get_meter

tracer = get_tracer()
meter = get_meter()

with tracer.start_as_current_span("my_custom_span"):
    # Your code here
    pass

counter = meter.create_counter("my_custom_counter")
counter.add(1, {"key": "value"})
```

## Create and run the agent

Putting all together, create a new `app.py` inside this lab folder (or open the existing [`08-observability/app.py`](app.py)) and paste the following code. The observability will be automatically enabled for the agent once `setup_observability` has been called.

```python
import asyncio
import os
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from agent_framework.observability import setup_observability
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

setup_observability(enable_sensitive_data=True, exporters=[ConsoleSpanExporter()])

# Create the agent - telemetry is automatically enabled
agent = ChatAgent(
    chat_client=AzureOpenAIChatClient(
        credential=AzureCliCredential(),
        endpoint=os.environ["AOAI_ENDPOINT"],
        deployment_name=os.environ["AOAI_DEPLOYMENT"],
    ),
    name="Joker",
    description="You are good at telling jokes."
)

# Run the agent
async def main():
    result = await agent.run("Tell me a joke about a pirate.")
    print(result.text)

asyncio.run(main())
```

If you copied the snippet into a fresh file, compare it against the committed [`app.py`](app.py) to confirm nothing is missing before you run the sample.

The agent responds first:

```text
Why did the pirate go to school?

Because he wanted to improve his "arrr-ticulation"! ⛵
```

Immediately after, the console exporter shows the associated trace data:

```text
{
    "name": "invoke_agent Joker",
    "context": {
        "trace_id": "0xf2258b51421fe9cf4c0bd428c87b1ae4",
        "span_id": "0x2cad6fc139dcf01d",
        "trace_state": "[]"
    },
    "kind": "SpanKind.CLIENT",
    "parent_id": null,
    "start_time": "2025-09-25T11:00:48.663688Z",
    "end_time": "2025-09-25T11:00:57.271389Z",
    "status": {
        "status_code": "UNSET"
    },
    "attributes": {
        "gen_ai.operation.name": "invoke_agent",
        "gen_ai.system": "openai",
        "gen_ai.agent.id": "Joker",
        "gen_ai.agent.name": "Joker",
        "gen_ai.request.instructions": "You are good at telling jokes.",
        "gen_ai.response.id": "chatcmpl-CH6fgKwMRGDtGNO3H88gA3AG2o7c5",
        "gen_ai.usage.input_tokens": 26,
        "gen_ai.usage.output_tokens": 29
    }
}
```

------

## Azure AI Foundry integration

If you're using Azure AI Foundry clients, there's a convenient method for automatic setup:

```python
from agent_framework.azure import AzureAIAgentClient
from azure.identity import AzureCliCredential

agent_client = AzureAIAgentClient(
    credential=AzureCliCredential(),
    # endpoint and model_deployment_name can be taken from environment variables
    # project_endpoint="https://<your-project>.foundry.azure.com"
    # model_deployment_name="<your-deployment-name>"
)

# Automatically configures observability with Application Insights
await agent_client.setup_azure_ai_observability()
```

This method retrieves the Application Insights connection string from your Azure AI Foundry project and calls `setup_observability` automatically. If you want to use Foundry Telemetry with other types of agents, you can do the same thing with:

```python
from agent_framework.observability import setup_observability
from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential

project_client = AIProjectClient(endpoint, credential=AzureCliCredential())
conn_string = project_client.telemetry.get_application_insights_connection_string()
setup_observability(applicationinsights_connection_string=conn_string)
```

Also see the [relevant Foundry documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/trace-agents-sdk).

When using Azure Monitor for your telemetry, you need to install the `azure-monitor-opentelemetry` package explicitly, as it is not included by default with Agent Framework.

## Next steps

For more advanced observability scenarios and examples, see the [Agent Observability user guide](https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-observability) and the [observability samples](https://github.com/microsoft/agent-framework/tree/main/python/samples/getting_started/observability) in the GitHub repository.

## 📝 Lab 08 Conclusion: Observability Bootstrapped

You wired Agent Framework telemetry into a simple Azure OpenAI–backed agent and forced console-only exporters so diagnostics stay local unless you deliberately point them at OTLP or Azure Monitor. With `setup_observability` in place, every agent run now emits structured traces, metrics, and logs you can redirect to collectors whenever you are ready.

------

#### Key Takeaways from Lab 08

- `setup_observability` gives you console exporters by default; add other exporters only when a collector exists.
- Clearing OTLP-related environment variables keeps the sample from retrying `localhost:4317` unnecessarily.
- The same code can ship to production by swapping in OTLP or Azure Monitor exporters without touching the agent logic.

------

## 🔗 Navigation

- **[⬅️ Back: Lab 07 — Agent as MCP Server](../07-agent-as-MCP-tool/README.md)** — Revisit how MCP servers expose agents as tools.
- **[🏠 Back to Workshop Home](../README.md)** — Return to the lab index and prerequisites.
- **[➡️ Next: Upcoming Lab](../README.md)** — Placeholder for the next module in the series.
