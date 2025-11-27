# Lab 11 — Persisting Chat History Outside the Agent Runtime

This lab replaces the in-memory message store used by `agent_framework.ChatAgent` with a Redis-backed implementation so that conversations survive process restarts. Two files participate in the solution:

- `11-external-persistence/redis_chat_message_store.py` — the custom `ChatMessageStore` that writes to Azure Cache for Redis.
- `11-external-persistence/app.py` — an interactive CLI that wires the store into a `ChatAgent`, lets you chat, and resume previously saved threads.

> Requirements: set `AOAI_ENDPOINT`, `AOAI_DEPLOYMENT`, and `REDIS_URL` (`rediss://:<PRIMARY_KEY>@<host>.redis.cache.windows.net:6380/0`) before running `python app.py`.

## RedisChatMessageStore implementation (`redis_chat_message_store.py`)

### Connection and key management

- The constructor takes a `redis_url`, optional `thread_id`, `key_prefix`, and `max_messages` guard.
- When no `thread_id` is provided a UUID is generated. Keys look like `lab11:thread_<guid>` so every agent thread is isolated but easy to enumerate.
- The Redis client uses `redis.asyncio.from_url(..., decode_responses=True)` so we work with plain strings.

### Writing and trimming chat history

```python
async def add_messages(self, messages: Sequence[ChatMessage]) -> None:
	serialized = [self._serialize_message(msg) for msg in messages]
	await self._redis_client.rpush(self.redis_key, *serialized)
	if self.max_messages:
		await self._redis_client.ltrim(self.redis_key, -self.max_messages, -1)
```

- Messages are serialized through `ChatMessage.to_dict()` (with fallback logic for other shapes) and appended via `RPUSH` so Redis keeps oldest→newest order.
- If `max_messages` is set the list is trimmed with `LTRIM` to keep only the most recent N entries.

### Reading chat history back

- `list_messages` calls `LRANGE 0 -1`, deserializes each JSON blob back into `ChatMessage` (`ChatMessage.from_dict` when available), and returns them in chronological order.
- The CLI uses this method whenever you choose “Peek at Redis history”.

### Serialization hooks for AgentThread

`ChatMessageStore` implementations must serialize their configuration so an `AgentThread` can be paused/resumed. The Redis store handles that through:

- `serialize_state` / `deserialize_state` — wrap the thread id, key prefix, limit, and connection string inside a `RedisStoreState` (Pydantic model). This state is what we show when you resume a thread.
- `serialize` — the method the framework calls when persisting an `AgentThread`. We return a dict with an empty `messages` list (to satisfy the protocol) plus a `store_metadata` entry containing the data from `serialize_state`.
- `deserialize` and `update_from_state` — rebuild the store (or update the current instance) from the `store_metadata` blob. These guard against missing `redis_url` so we fail fast if the environment is misconfigured.

> Because Redis already contains the full transcript we never ship the raw messages back through `serialize`; only the metadata required to reconnect is stored in the thread snapshot.

## Wiring the store into the agent (`app.py`)

### Agent creation

```python
def build_agent(redis_url: str) -> ChatAgent:
	def store_factory() -> RedisChatMessageStore:
		return RedisChatMessageStore(redis_url=redis_url, key_prefix="lab11", max_messages=200)

	return ChatAgent(..., chat_message_store_factory=store_factory)
```

- Every time `agent.get_new_thread()` is called the factory hands the thread a brand-new `RedisChatMessageStore` instance pointed at Azure Cache for Redis.
- `create_thread` asserts the injected `message_store` is our Redis implementation and returns both the `AgentThread` and its store so the CLI can reuse them.

### CLI flow

Running `python 11-external-persistence/app.py` launches an interactive menu:

1. **Send a user message** — uses `agent.run(prompt, thread=thread)`; once the assistant responds the framework calls `RedisChatMessageStore.add_messages`, which persists both user + assistant messages.
2. **Peek at Redis history** — invokes `show_history`, which calls `store.list_messages()` and prints them using `_message_text` to unwrap `ChatMessage.contents`.
3. **Load a saved Redis thread** — lists every Redis key with the `lab11:` prefix (via `_list_saved_thread_keys`), shows a numbered menu, and loads the chosen key:
   - Creates a new `RedisChatMessageStore` pointed at the selected key.
   - Creates a new `AgentThread`, swaps its `message_store` for the Redis-backed one, closes the previous store, and keeps going with the new context.
   - Immediately calls `show_history` so you can confirm which conversation you resumed.
4. **Start a fresh thread** — closes the active store, calls `create_thread`, and continues with a new Redis key.
0. **Exit** — closes the Redis connection gracefully.

### Why this architecture works

- Only the `ChatMessageStore` knows how to talk to Redis; `ChatAgent` simply asks it to add/list messages, so we keep a clean separation of concerns.
- The menu-driven loader proves that thread state truly lives outside the agent process—after restarting `app.py` you can immediately pick option 3 and continue with any previous Redis key even though the Python `AgentThread` objects were recreated from scratch.

## Try it yourself

1. Export the required environment variables (`AOAI_ENDPOINT`, `AOAI_DEPLOYMENT`, `REDIS_URL`).
2. From the repo root run `python 11-external-persistence/app.py`.
3. Use option 1 a few times so the assistant learns some facts. Exit and rerun the script.
4. Choose option 3, pick the Redis key you just created, and verify the assistant still remembers the earlier conversation. You can continue chatting, switch to another key, or start from scratch at any time.

This lab gives you a blueprint for any external persistence layer: implement the `ChatMessageStore` protocol in a file like `redis_chat_message_store.py`, wire it in with `chat_message_store_factory`, and build whatever UX you need to inspect or resume threads. Once the store speaks the same interface, the agent framework handles the rest.

