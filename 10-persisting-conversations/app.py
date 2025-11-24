import os
import asyncio
from agent_framework import ChatAgent, ChatMessage, Role
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential


agent = ChatAgent(
    chat_client=AzureOpenAIChatClient(
        credential=AzureCliCredential(),
        endpoint=os.environ["AOAI_ENDPOINT"],
        deployment_name=os.environ["AOAI_DEPLOYMENT"]
    ),
    name="FinanceAgent",
    instructions=(
        "You are an agent from Contoso Bank. You assist users with financial operations "
        "and provide clear explanations. For transfers only amount, recipient name, and reference are needed."
    )
)
