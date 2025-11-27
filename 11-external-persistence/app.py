import asyncio
import os
from textwrap import dedent
from typing import cast

from agent_framework import ChatAgent, ChatMessage
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from redis.exceptions import ConnectionError as RedisConnectionError

from redis_chat_message_store import RedisChatMessageStore

def _message_text(msg: ChatMessage) -> str:
    """Render a ChatMessage's textual content for CLI display."""

    text = getattr(msg, "text", None)
    if isinstance(text, str) and text.strip():
        return text

    contents = getattr(msg, "contents", None)
    if isinstance(contents, list):
        parts: list[str] = []
        for item in contents:
            item_text = getattr(item, "text", None)
            if isinstance(item_text, str) and item_text:
                parts.append(item_text)
                continue
            if isinstance(item, dict):
                dict_text = item.get("text")
                if isinstance(dict_text, str) and dict_text:
                    parts.append(dict_text)
        if parts:
            return " | ".join(parts)

    return "<non-text content>"


def build_agent(redis_url: str) -> ChatAgent:
    """Create the agent configured to hydrate threads with Redis-backed history."""

    def store_factory() -> RedisChatMessageStore:
        # Each new thread receives its own Redis-backed message store instance.
        return RedisChatMessageStore(
            redis_url=redis_url,
            key_prefix="lab11",
            max_messages=200,
        )

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
        chat_message_store_factory=store_factory,
    )


def create_thread(agent: ChatAgent) -> tuple:
    """Build a new thread and return it plus its Redis store."""
    thread = agent.get_new_thread()
    store = thread.message_store
    if not isinstance(store, RedisChatMessageStore):
        raise RuntimeError(
            "Thread is not using the RedisChatMessageStore. Ensure build_agent sets chat_message_store_factory."
        )
    return thread, cast(RedisChatMessageStore, store)


def print_menu(thread_key: str) -> None:
    print(
        dedent(
            f"""
            ==============================================
            Lab 11 — Redis Chat History Playground
            Current Redis key: {thread_key or 'not initialized yet'}
            ----------------------------------------------
            [1] Send a user message (agent response stored in Redis)
            [2] Peek at Redis history for this thread
            [3] Load a saved Redis thread and continue working on it
            [4] Start a fresh thread (new Redis key)
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
        print(f"- {role.upper()}: {_message_text(msg)}")
    print()


def _thread_id_from_key(full_key: str, prefix: str) -> str:
    if full_key.startswith(f"{prefix}:"):
        return full_key[len(prefix) + 1 :]
    return full_key


async def _list_saved_thread_keys(store: RedisChatMessageStore) -> list[str]:
    pattern = f"{store.key_prefix}:*"
    try:
        keys = await store._redis_client.keys(pattern)  # type: ignore[attr-defined]
    except RedisConnectionError as exc:
        print(
            "\nUnable to reach Redis to list keys. Verify your REDIS_URL (TLS/port 6380) and network connectivity."
        )
        print(f"Details: {exc}\n")
        return []

    keys.sort()
    return keys


async def load_existing_thread(
    agent: ChatAgent,
    current_thread,
    current_store: RedisChatMessageStore,
) -> tuple:
    keys = await _list_saved_thread_keys(current_store)
    if not keys:
        print("\nThere are no persisted threads yet. Start a conversation first.\n")
        return current_thread, current_store

    print("\nAvailable Redis threads:")
    for idx, key in enumerate(keys, start=1):
        try:
            count = await current_store._redis_client.llen(key)  # type: ignore[attr-defined]
        except RedisConnectionError:
            count = "?"
        print(f"[{idx}] {key} ({count} messages)")

    selection = input("\nEnter the number to load (or press Enter to cancel): ").strip()
    if not selection:
        print("Cancelled loading an existing thread.\n")
        return current_thread, current_store
    if not selection.isdigit():
        print("Please enter a numeric option.\n")
        return current_thread, current_store

    index = int(selection)
    if index < 1 or index > len(keys):
        print("That index does not exist.\n")
        return current_thread, current_store

    selected_key = keys[index - 1]
    thread_id = _thread_id_from_key(selected_key, current_store.key_prefix)
    new_store = RedisChatMessageStore(
        redis_url=current_store.redis_url,
        thread_id=thread_id,
        key_prefix=current_store.key_prefix,
        max_messages=current_store.max_messages,
    )

    new_thread = agent.get_new_thread()
    placeholder_store = new_thread.message_store
    if isinstance(placeholder_store, RedisChatMessageStore):
        await placeholder_store.aclose()
    new_thread.message_store = new_store

    await current_store.aclose()

    print(f"\nLoaded thread: {selected_key}")
    await show_history(new_store)
    return new_thread, new_store


async def interactive_demo(agent: ChatAgent) -> None:
    thread, store = create_thread(agent)

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
            thread, store = await load_existing_thread(agent, thread, store)
            continue

        if choice == "4":
            confirm = input("This will start a new Redis key. Continue? (y/N): ").strip().lower()
            if confirm not in {"y", "yes"}:
                print("Keeping current thread.\n")
                continue
            await store.aclose()
            thread, store = create_thread(agent)
            print("Started a brand-new thread + Redis list.\n")
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

    agent = build_agent(redis_url)
    print("\nWelcome to Lab 11! We'll persist agent memory in Azure Cache for Redis.\n")
    await interactive_demo(agent)


if __name__ == "__main__":
    asyncio.run(main())
