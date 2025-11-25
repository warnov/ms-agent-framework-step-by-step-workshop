import asyncio
import os
from textwrap import dedent

from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from redis.exceptions import ConnectionError as RedisConnectionError

from redis_chat_message_store import RedisChatMessageStore


def build_agent() -> ChatAgent:
    """Create the agent that will rely on Redis for history."""
    return ChatAgent(
        chat_client=AzureOpenAIChatClient(
            credential=AzureCliCredential(),
            endpoint=os.environ["AOAI_ENDPOINT"],
            deployment_name=os.environ["AOAI_DEPLOYMENT"],
        ),
        name="TravelPlanner",
        instructions=(
            "You are a concise travel assistant. Always remember prior user facts already stored in "
            "the conversation history. Reference those facts when answering."
        ),
    )


async def create_thread(agent: ChatAgent, redis_url: str) -> tuple:
    """Build a new thread + store pair so each session has its own Redis key."""
    store = RedisChatMessageStore(
        redis_url=redis_url,
        key_prefix="lab11",
        max_messages=200,
    )
    thread = agent.get_new_thread(message_store=store)
    return thread, store


def print_menu(thread_key: str) -> None:
    print(
        dedent(
            f"""
            ==============================================
            Lab 11 — Redis Chat History Playground
            Current Redis key: {thread_key or 'not initialized yet'}
            ----------------------------------------------
            [1] Send a user message (agent response stored in Redis)
            [2] Peek at Redis history for the active thread
            [3] Inspect serialized AgentThread metadata
            [4] Start a fresh thread (new Redis key)
            [5] List every Redis key for this lab prefix
            [6] Inspect a specific Redis key (read-only)
            [0] Exit workshop demo
            ==============================================
            """
        ).strip()
    )


async def show_history(store: RedisChatMessageStore) -> None:
    messages = await store.list_messages()
    if not messages:
        print("\nRedis list is empty for this thread. Send a message first!\n")
        return

    print("\nRedis has the following messages (oldest → newest):")
    for msg in messages:
        role = msg.role.value if hasattr(msg.role, "value") else msg.role
        print(f"- {role.upper()}: {msg.content}")
    print()


async def show_serialized_thread(thread) -> None:
    serialized = await thread.serialize()
    print("\nSerialized thread state (notice this contains the Redis key & config, not the chat text):")
    print(serialized)
    print()


async def list_all_keys(store: RedisChatMessageStore) -> None:
    pattern = f"{store.key_prefix}:*"
    try:
        keys = await store._redis_client.keys(pattern)  # type: ignore[attr-defined]
    except RedisConnectionError as exc:
        print(
            "\nUnable to reach Redis to list keys. Verify your REDIS_URL (TLS/port 6380) and network connectivity."
        )
        print(f"Details: {exc}\n")
        return
    if not keys:
        print("\nNo Redis keys found for this prefix yet.\n")
        return
    print("\nRedis keys using this prefix:")
    for key in keys:
        print(f"- {key}")
    print()


async def inspect_specific_key(store: RedisChatMessageStore) -> None:
    key = input("Enter the full Redis key to inspect: ").strip()
    if not key:
        print("Key cannot be empty.\n")
        return
    try:
        exists = await store._redis_client.exists(key)  # type: ignore[attr-defined]
    except RedisConnectionError as exc:
        print(
            "\nUnable to reach Redis to inspect that key. Confirm connectivity and try again."
        )
        print(f"Details: {exc}\n")
        return
    if not exists:
        print("That key does not exist.\n")
        return
    try:
        values = await store._redis_client.lrange(key, 0, -1)  # type: ignore[attr-defined]
    except RedisConnectionError as exc:
        print("Encountered a network error while reading that key.\n")
        print(f"Details: {exc}\n")
        return
    if not values:
        print("The key exists but contains no messages.\n")
        return
    print("\nMessages inside that Redis list:")
    for raw in values:
        print(f"- {raw}")
    print()


async def interactive_demo(agent: ChatAgent, redis_url: str) -> None:
    thread, store = await create_thread(agent, redis_url)

    while True:
        print_menu(store.redis_key)
        choice = input("Choose an option: ").strip()

        if choice == "1":
            prompt = input("\nWhat would you like to tell the agent? ").strip()
            if not prompt:
                print("Please enter a non-empty prompt.\n")
                continue
            result = await agent.run(prompt, thread=thread)
            print(f"\nAssistant replied: {result.text}\n")
            continue

        if choice == "2":
            await show_history(store)
            continue

        if choice == "3":
            await show_serialized_thread(thread)
            continue

        if choice == "4":
            confirm = input("This will start a new Redis key. Continue? (y/N): ").strip().lower()
            if confirm not in {"y", "yes"}:
                print("Keeping current thread.\n")
                continue
            await store.aclose()
            thread, store = await create_thread(agent, redis_url)
            print("Started a brand-new thread + Redis list.\n")
            continue

        if choice == "5":
            await list_all_keys(store)
            continue

        if choice == "6":
            await inspect_specific_key(store)
            continue

        if choice == "0":
            print("Goodbye! Closing Redis connection...")
            await store.aclose()
            break

        print("Unknown option. Please try again.\n")


async def main() -> None:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise RuntimeError(
            "Set the REDIS_URL environment variable (e.g., redis://:<primary_key>@<host>:6380/0)."
        )

    agent = build_agent()
    print("\nWelcome to Lab 11! We'll persist agent memory in Azure Cache for Redis.\n")
    await interactive_demo(agent, redis_url)


if __name__ == "__main__":
    asyncio.run(main())
