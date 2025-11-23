import asyncio
import os
from agent_framework.observability import setup_observability
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

# Enable Agent Framework telemetry but force console exporter to avoid OTLP retries.
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
async def main() -> None:
    result = await agent.run("Tell me a joke about a pirate.")
    print(result.text)


if __name__ == "__main__":
    asyncio.run(main())