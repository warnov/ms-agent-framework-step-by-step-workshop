import asyncio
from agent_framework import AgentRunResponse
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from model import PersonInfo


def build_agent():
    """Instantiate a ChatAgent configured for PersonInfo extraction."""
    return AzureOpenAIChatClient(
        credential=AzureCliCredential(),
        endpoint="https://warstandalone.openai.azure.com/",
        deployment_name="dep-gpt-5-mini"
    ).create_agent(
        name="HelpfulAssistant",
        instructions=(
            "You are a helpful assistant that extracts person information from free-form descriptions. "
            "Only fill the fields that are explicitly mentioned."
        )
    )


def print_person(info: PersonInfo | None, label: str) -> None:
    """Pretty-print normalized structured output, even when values are missing."""
    print(f"\n=== {label} ===")
    if not info:
        print("No structured data found in response")
        return
    print(
        f"Name: {info.name or 'unknown'}, Age: {info.age or 'unknown'}, "
        f"Occupation: {info.occupation or 'unknown'}"
    )


async def describe_person(agent, description: str) -> None:
    """Run both non-streaming and streaming calls so the user can compare outputs."""
    response = await agent.run(description, response_format=PersonInfo)
    print_person(response.value if hasattr(response, "value") else None, "Non-streaming response")

    final_response = await AgentRunResponse.from_agent_response_generator(
        agent.run_stream(description, response_format=PersonInfo),
        output_format_type=PersonInfo,
    )
    print_person(final_response.value, "Streaming response")


async def main() -> None:
    """Interactive CLI loop that keeps the agent alive across user prompts."""
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