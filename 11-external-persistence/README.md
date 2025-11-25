# Lab11 - Storing Chat History in 3rd Party Storage [Work in Progress]

This lab shows how to store agent chat history in external storage by implementing a custom `ChatMessageStore` and using it with a `ChatAgent`.

By default, when using `ChatAgent`, chat history is stored either in memory in the `AgentThread` object or the underlying inference service, if the service supports it.

Where services do not require or are not capable of the chat history to be stored in the service, it is possible to provide a custom store for persisting chat history instead of relying on the default in-memory behavior.

In addition to the usual packages we have been using so far, , we will use the in-memory vector store to store chat messages and a utility package for async LINQ operations. 

## Create a custom ChatMessage Store

To create a custom `ChatMessageStore`, you need to implement the `ChatMessageStore` protocol and provide implementations for the required methods.

### Message storage and retrieval methods

The most important methods to implement are: 

- `add_messages ` - called to add new messages to the store. 
- `list_messages ` - called to retrieve the messages from the store. 

`list_messages ` should return the messages in ascending chronological order. All messages returned by it will be used by the  `ChatClient` when making calls to the underlying chat client. It's therefore important that this method considers the limits of the underlying model, and only returns as many messages as can be handled by the model. 

Any chat history reduction logic, such as summarization or trimming, should be done before returning messages from  `list_messages`.

### Serialization

`ChatMessageStore` instances are created and attached to an  `AgentThread` when the thread is created, and when a thread is resumed from a serialized state. 

While the actual messages making up the chat history are stored externally, the `ChatMessageStore` instance may need to store keys or other state to identify the chat history in the external store. 

To allow persisting threads, you need to implement the `serialize_state` and `deserialize_state` methods of the `ChatMessageStore` protocol. These methods allow the store's state to be persisted and restored when resuming a thread.

## Sample ChatMessageStore implementation

The following sample implementation stores chat messages in Redis using the Redis Lists data structure.

In `add_messages`, it stores messages in Redis using RPUSH to append them to the end of the list in chronological order.

`list_messages` retrieves the messages for the current thread from Redis using LRANGE, and returns them in ascending chronological order.

When the first message is received, the store generates a unique key for the thread, which is then used to identify the chat history in Redis for subsequent calls.

The unique key and other configuration are stored and can be serialized and deserialized using the `serialize_state` and `deserialize_state` methods. This state will therefore be persisted as part of the `AgentThread` state, allowing the thread to be resumed later and continue using the same chat history.

CODE

