import asyncio
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential

agent = AzureOpenAIChatClient(
    credential=AzureCliCredential(),
    endpoint="https://warstandalone.openai.azure.com/",
    deployment_name="dep-gpt-5-mini"
).create_agent(
    instructions="You are good at telling jokes.",
    name="Joker"
)

thread = agent.get_new_thread()

async def main():
    thread1 = agent.get_new_thread()
    thread2 = agent.get_new_thread()

    result1 = await agent.run("Tell me a joke about a pirate.", thread=thread1)
    print(result1.text)

    result2 = await agent.run("Tell me a joke about a robot.", thread=thread2)
    print(result2.text)

    result3 = await agent.run("Now add some emojis to the joke and tell it in the voice of a pirate's parrot.", thread=thread1)
    print(result3.text)

    result4 = await agent.run("Now add some emojis to the joke and tell it in the voice of a robot.", thread=thread2)
    print(result4.text)

asyncio.run(main())