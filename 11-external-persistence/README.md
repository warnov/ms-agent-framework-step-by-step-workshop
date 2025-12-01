# Lab11 - Storing Chat History in 3rd Party Storage

This lab shows how to store agent chat history in external storage by implementing a custom `ChatMessageStore` and using it with a `ChatAgent`.

By default, when using `ChatAgent`, chat history is stored either in memory in the `AgentThread` object or the underlying inference service, if the service supports it.

Where services do not require or are not capable of the chat history to be stored in the service, it is possible to provide a custom store for persisting chat history instead of relying on the default in-memory behavior.

## Preserve chat history beyond the process

This lab needs every `AgentThread` to survive editor restarts, multiple shells, and even different machines, yet the default message store disappears as soon as the process stops. The answer is to provide an out-of-process `ChatMessageStore` so the agent can hydrate itself from durable storage regardless of where it runs. Here we implement `RedisChatMessageStore` (see [`redis_chat_message_store.py`](./redis_chat_message_store.py)), a concrete store that serializes each `ChatMessage` and appends it to a Redis list hosted in Azure Cache for Redis. The agent is instantiated with `chat_message_store_factory=RedisChatMessageStore`, so every new thread automatically receives a store that already knows the Redis URL, key prefix, and message limits. When the application restarts, we only need to create another `RedisChatMessageStore` with the same connection info and `thread_id`; the agent thread can then reload history from the Redis list and continue the conversation seamlessly. Because the state now lives outside the process, multiple shells or machines can share the exact same conversation history without any additional synchronization logic.

### Understanding the RedisChatMessageStore implementation

`redis_chat_message_store.py` is a practical walkthrough of everything the `ChatMessageStore` protocol expects from a persistence provider. The implementation is intentionally verbose so you can see how each concern—key management, message serialization, deserialization, and resource cleanup—is handled.

#### Bootstrapping the store

```python
class RedisChatMessageStore:
	def __init__(
		self,
		redis_url: str | None = None,
		thread_id: str | None = None,
		key_prefix: str = "chat_messages",
		max_messages: int | None = None,
	) -> None:
		if redis_url is None:
			raise ValueError("redis_url is required for Redis connection")

		self.redis_url = redis_url
		self.thread_id = thread_id or f"thread_{uuid4()}"
		self.key_prefix = key_prefix
		self.max_messages = max_messages
		self._redis_client = redis.from_url(redis_url, decode_responses=True)
```

The constructor validates that a connection string exists, picks or generates a `thread_id`, records the logical prefix, and creates a single Redis client that remains connected for the life of the store. The `redis_key` property simply concatenates `key_prefix` and `thread_id` so each thread is isolated inside Redis.

#### Writing and trimming messages

```python
async def add_messages(self, messages: Sequence[ChatMessage]) -> None:
	if not messages:
		return

	serialized_messages = [self._serialize_message(msg) for msg in messages]
	await self._redis_client.rpush(self.redis_key, *serialized_messages)

	if self.max_messages is not None:
		current_count = await self._redis_client.llen(self.redis_key)
		if current_count > self.max_messages:
			await self._redis_client.ltrim(self.redis_key, -self.max_messages, -1)
```

`add_messages` is called by the framework whenever the agent produces new content. Each `ChatMessage` is converted to JSON via `_serialize_message`, pushed to a Redis list, and optionally truncated with `LTRIM` so long-lived threads never exceed the configured retention window.

#### Reading conversations back

```python
async def list_messages(self) -> list[ChatMessage]:
	redis_messages = await self._redis_client.lrange(self.redis_key, 0, -1)
	messages = []
	for serialized_message in redis_messages:
		message = self._deserialize_message(serialized_message)
		messages.append(message)
	return messages
```

`list_messages` replays the Redis list in chronological order and reconstructs `ChatMessage` objects (`ChatMessage.from_dict` when available, otherwise `model_validate`). This output feeds directly into the `ChatAgent`, so you always get the same context back that you originally stored.

#### Persisting store metadata

```python
async def serialize_state(self, **kwargs: Any) -> Any:
	state = RedisStoreState(
		thread_id=self.thread_id,
		redis_url=self.redis_url,
		key_prefix=self.key_prefix,
		max_messages=self.max_messages,
	)
	return state.model_dump(**kwargs)

async def serialize(self, **kwargs: Any) -> dict[str, Any]:
	state = await self.serialize_state(**kwargs)
	return {"messages": [], "store_metadata": state}
```

The lab needs `AgentThread.serialize()` to succeed even though the real history lives in Redis. `serialize_state` and `serialize` therefore capture only the configuration needed to reconnect (thread id, key prefix, URL, limits). The message list is left empty because the canonical copy is in Redis; when a thread is restored the code constructs a new `RedisChatMessageStore` with the saved metadata.

#### Rehydrating and cleaning up

```python
@classmethod
async def deserialize(cls, serialized_store_state: Any, **kwargs: Any) -> "RedisChatMessageStore":
	redis_state = serialized_store_state.get("store_metadata")
	state = RedisStoreState.model_validate(redis_state, **kwargs)
	redis_url = state.redis_url or kwargs.get("redis_url")
	return cls(
		redis_url=redis_url,
		thread_id=state.thread_id,
		key_prefix=state.key_prefix,
		max_messages=state.max_messages,
	)

async def aclose(self) -> None:
	await self._redis_client.aclose()
```

`deserialize` rebuilds the store with the exact same identifiers so a new process can attach to an existing Redis list. `aclose` shuts down the Redis connection when the CLI switches threads or exits. Together with `update_from_state` and `clear`, these APIs make the store plug-and-play with the framework’s lifecycle hooks.

Taken as a whole, the file demonstrates how to transform the abstract `ChatMessageStore` contract into a concrete, production-ready persistence layer backed by Azure Cache for Redis. You can lift this pattern to implement other durable stores (SQL, blobs, vector DBs) by swapping out the `_redis_client` calls for the appropriate client library while keeping the same method signatures.

### Walking through the interactive client (`app.py`)

The CLI in [`app.py`](./app.py) stitches everything together: it instantiates the agent, wires the Redis store, and provides menu-driven flows for sending prompts, inspecting history, and loading prior threads. Understanding each section helps adapt the sample to your own agents.

#### Agent and store factory

```python
def build_agent(redis_url: str) -> ChatAgent:
	def store_factory() -> RedisChatMessageStore:
		return RedisChatMessageStore(
			redis_url=redis_url,
			key_prefix="lab11",
			max_messages=200,
		)

	return ChatAgent(
		chat_client=AzureOpenAIChatClient(...),
		name="TravelPlanner",
		instructions="...",
		chat_message_store_factory=store_factory,
	)
```

`build_agent` captures the Redis connection string and exposes a `store_factory`. Every time the framework creates a new `AgentThread`, it calls this factory, guaranteeing that threads automatically inherit the Redis-backed persistence with the right prefix and retention. No manual plumbing is needed later in the code.

#### Thread bootstrapper

```python
def create_thread(agent: ChatAgent) -> tuple:
	thread = agent.get_new_thread()
	store = thread.message_store
	if not isinstance(store, RedisChatMessageStore):
		raise RuntimeError("Thread is not using the RedisChatMessageStore...")
	return thread, cast(RedisChatMessageStore, store)
```

`create_thread` is a small guardrail: after the agent yields a thread, it verifies the message store is indeed the Redis implementation, then returns both so the rest of the CLI can poke at Redis-specific helpers.

#### Rendering stored conversations

```python
async def show_history(store: RedisChatMessageStore) -> None:
	messages = await store.list_messages()
	if not messages:
		print("Redis list is empty...")
		return
	for msg in messages:
		role = msg.role.value if hasattr(msg.role, "value") else msg.role
		print(f"- {role.upper()}: {_message_text(msg)}")
```

`show_history` reuses the store’s `list_messages()` method and `_message_text` helper (which flattens `ChatMessage.contents` into a readable string) to display the persisted conversation. This keeps the CLI agnostic of how messages are encoded internally.

#### Enumerating and loading saved threads

```python
async def load_existing_thread(agent, current_thread, current_store):
	keys = await _list_saved_thread_keys(current_store)
	...
	selected_key = keys[index - 1]
	thread_id = _thread_id_from_key(selected_key, current_store.key_prefix)
	new_store = RedisChatMessageStore(..., thread_id=thread_id, ...)

	new_thread = agent.get_new_thread()
	...
	new_thread.message_store = new_store
	await current_store.aclose()
	print(f"Loaded thread: {selected_key}")
	await show_history(new_store)
	return new_thread, new_store
```

Option 3 in the menu calls `load_existing_thread`. It lists every Redis key under the `lab11` prefix, asks the user to pick one by number, constructs a store preloaded with that `thread_id`, and attaches it to a fresh `AgentThread`. Closing the old store before returning prevents lingering connections.

#### Interactive loop

```python
async def interactive_demo(agent: ChatAgent) -> None:
	thread, store = create_thread(agent)
	while True:
		print_menu(store.redis_key)
		choice = input("Choose an option: ").strip()
		if choice == "1":
			prompt = input("...")
			result = await agent.run(prompt, thread=thread)
			...
		if choice == "2":
			await show_history(store)
			continue
		if choice == "3":
			thread, store = await load_existing_thread(agent, thread, store)
			continue
		if choice == "4":
			...  # start a fresh thread and Redis list
		if choice == "0":
			await store.aclose()
			break
```

The loop is intentionally simple but demonstrates the full lifecycle: send prompts with `agent.run`, inspect Redis history, swap threads mid-session, and start over. Each branch either consumes the shared `store` or replaces it with a newly loaded one, keeping the thread/store pair in sync at all times.

By studying `app.py` alongside `redis_chat_message_store.py`, you can see both halves of the persistence story: the store satisfies the protocol, and the client exercises it in realistic workflows (new conversations, inspections, resumptions). This structure is a solid starting point for any agent that needs durable conversational state.

## Lab recap & next steps

1. **Implement durable storage** – `RedisChatMessageStore` shows how to fulfill the `ChatMessageStore` protocol, serialize messages, cap history, and rehydrate threads across processes.
2. **Wire the agent** – `build_agent` registers the store factory so every `AgentThread` automatically points to Azure Cache for Redis without extra boilerplate.
3. **Exercise persistence interactively** – the CLI in `app.py` lets you send prompts, inspect the Redis-backed history, and reload existing keys to prove that conversations survive restarts.
4. **Extend as needed** – reuse this pattern to plug in other storage engines (SQL, Cosmos DB, blob storage) or to add tooling such as automated cleanup scripts, summaries, and multi-tenant key prefixes.

When you’re ready, run `python 11-external-persistence/app.py`, experiment with creating multiple threads, then advance to the next lab with confidence that you can persist chat history outside the agent process.

## 🔗 Navigation

- **[⬅️ Back: Lab 10 — Persisting Conversations](../10-persisting-conversations/README.md)** — Review how to serialize threads to disk with hotkey-driven workflows.
- **[🏠 Back to Workshop Home](../README.md)** — Return to the full lab index and prerequisites.
- **[➡️ Next: Lab 12 — Agent Memory (WIP)](../12-agent-memory/README.md)** — Preview the upcoming memory patterns lab.




