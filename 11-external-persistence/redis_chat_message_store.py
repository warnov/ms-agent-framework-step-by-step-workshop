from collections.abc import Sequence
import json
from typing import Any
from uuid import uuid4

import redis.asyncio as redis
from agent_framework import ChatMessage
from pydantic import BaseModel


class RedisStoreState(BaseModel):
    """State model for serializing and deserializing Redis chat message store data."""

    thread_id: str
    redis_url: str | None = None
    key_prefix: str = "chat_messages"
    max_messages: int | None = None


class RedisChatMessageStore:
    """Redis-backed implementation of ChatMessageStore using Redis Lists."""

    def __init__(
        self,
        redis_url: str | None = None,
        thread_id: str | None = None,
        key_prefix: str = "chat_messages",
        max_messages: int | None = None,
    ) -> None:
        """Initialize the Redis chat message store.

        Args:
            redis_url: Redis connection URL (for example, "redis://localhost:6379").
            thread_id: Unique identifier for this conversation thread.
                      If not provided, a UUID will be auto-generated.
            key_prefix: Prefix for Redis keys to namespace different applications.
            max_messages: Maximum number of messages to retain in Redis.
                         When exceeded, oldest messages are automatically trimmed.
        """
        if redis_url is None:
            raise ValueError("redis_url is required for Redis connection")

        self.redis_url = redis_url
        self.thread_id = thread_id or f"thread_{uuid4()}"
        self.key_prefix = key_prefix
        self.max_messages = max_messages

        # Initialize Redis client
        self._redis_client = redis.from_url(redis_url, decode_responses=True)

    @property
    def redis_key(self) -> str:
        """Get the Redis key for this thread's messages."""
        return f"{self.key_prefix}:{self.thread_id}"

    async def add_messages(self, messages: Sequence[ChatMessage]) -> None:
        """Add messages to the Redis store.

        Args:
            messages: Sequence of ChatMessage objects to add to the store.
        """
        if not messages:
            return

        # Serialize messages and add to Redis list
        serialized_messages = [self._serialize_message(msg) for msg in messages]
        await self._redis_client.rpush(self.redis_key, *serialized_messages)

        # Apply message limit if configured
        if self.max_messages is not None:
            current_count = await self._redis_client.llen(self.redis_key)
            if current_count > self.max_messages:
                # Keep only the most recent max_messages using LTRIM
                await self._redis_client.ltrim(self.redis_key, -self.max_messages, -1)

    async def list_messages(self) -> list[ChatMessage]:
        """Get all messages from the store in chronological order.

        Returns:
            List of ChatMessage objects in chronological order (oldest first).
        """
        # Retrieve all messages from Redis list (oldest to newest)
        redis_messages = await self._redis_client.lrange(self.redis_key, 0, -1)

        messages = []
        for serialized_message in redis_messages:
            message = self._deserialize_message(serialized_message)
            messages.append(message)

        return messages

    async def serialize_state(self, **kwargs: Any) -> Any:
        """Serialize the current store state for persistence.

        Returns:
            Dictionary containing serialized store configuration.
        """
        state = RedisStoreState(
            thread_id=self.thread_id,
            redis_url=self.redis_url,
            key_prefix=self.key_prefix,
            max_messages=self.max_messages,
        )
        return state.model_dump(**kwargs)

    async def deserialize_state(self, serialized_store_state: Any, **kwargs: Any) -> None:
        """Deserialize state data into this store instance.

        Args:
            serialized_store_state: Previously serialized state data.
            **kwargs: Additional arguments for deserialization.
        """
        if serialized_store_state:
            state = RedisStoreState.model_validate(serialized_store_state, **kwargs)
            self.thread_id = state.thread_id
            self.key_prefix = state.key_prefix
            self.max_messages = state.max_messages

            # Recreate Redis client if the URL changed
            if state.redis_url and state.redis_url != self.redis_url:
                self.redis_url = state.redis_url
                self._redis_client = redis.from_url(self.redis_url, decode_responses=True)

    async def serialize(self, **kwargs: Any) -> dict[str, Any]:
        """Return a lightweight structure compatible with ChatMessageStoreState."""
        # AgentThreadState expects a list of messages, so provide an empty placeholder
        # plus embed our Redis configuration in a sidecar field.
        state = await self.serialize_state(**kwargs)
        return {"messages": [], "store_metadata": state}

    @classmethod
    async def deserialize(cls, serialized_store_state: Any, **kwargs: Any) -> "RedisChatMessageStore":
        """Return a new store instance from serialized state."""
        if not serialized_store_state:
            raise ValueError("serialized_store_state is required to deserialize RedisChatMessageStore")

        redis_state = serialized_store_state.get("store_metadata")
        if redis_state is None:
            raise ValueError("store_metadata missing from serialized_store_state")

        state = RedisStoreState.model_validate(redis_state, **kwargs)
        redis_url = state.redis_url or kwargs.get("redis_url")
        if not isinstance(redis_url, str):
            raise ValueError("redis_url must be provided when deserializing RedisChatMessageStore")

        return cls(
            redis_url=redis_url,
            thread_id=state.thread_id,
            key_prefix=state.key_prefix,
            max_messages=state.max_messages,
        )

    async def update_from_state(self, serialized_store_state: Any, **kwargs: Any) -> None:
        """Update this instance with serialized state (protocol helper)."""
        redis_state = serialized_store_state.get("store_metadata") if serialized_store_state else None
        if not redis_state:
            return
        await self.deserialize_state(redis_state, **kwargs)

    def _serialize_message(self, message: ChatMessage) -> str:
        """Serialize a ChatMessage to JSON string."""
        if hasattr(message, "to_dict"):
            message_dict = message.to_dict()
        elif hasattr(message, "model_dump"):
            message_dict = message.model_dump()
        elif isinstance(message, BaseModel):
            message_dict = message.model_dump()
        else:
            raise TypeError("ChatMessage does not support to_dict/model_dump serialization")
        return json.dumps(message_dict, separators=(",", ":"))

    def _deserialize_message(self, serialized_message: str) -> ChatMessage:
        """Deserialize a JSON string to ChatMessage."""
        message_dict = json.loads(serialized_message)
        if hasattr(ChatMessage, "from_dict"):
            return ChatMessage.from_dict(message_dict)
        if hasattr(ChatMessage, "model_validate"):
            return ChatMessage.model_validate(message_dict)
        raise TypeError("ChatMessage does not support from_dict/model_validate deserialization")

    async def clear(self) -> None:
        """Remove all messages from the store."""
        await self._redis_client.delete(self.redis_key)

    async def aclose(self) -> None:
        """Close the Redis connection."""
        await self._redis_client.aclose()