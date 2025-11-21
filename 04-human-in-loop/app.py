import asyncio
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from payment_functions import submit_payment  # Your approval-required tool

agent = ChatAgent(
    chat_client=AzureOpenAIChatClient(
        credential=AzureCliCredential(),
        endpoint="https://warstandalone.openai.azure.com/",
        deployment_name="dep-gpt-5-mini"
    ),
    name="FinanceAgent",
    instructions="You assist users with financial operations and provide clear explanations.",
    tools=[submit_payment],
)

async def main():
    # Request a payment that requires approval
    result = await agent.run(
        "Please submit a payment of $150.50 to TechVendor Inc. for software licenses."
    )
    print(result.text)

if __name__ == "__main__":
    asyncio.run(main())