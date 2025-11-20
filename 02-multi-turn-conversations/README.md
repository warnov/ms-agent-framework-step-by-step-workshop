# Lab02 - Multi Turn Conversations

This lab step shows you how to have a multi-turn conversation with an agent, where the agent is built on the Azure OpenAI Chat Completion service. Agent Framework supports many different types of agents. Here, we are going to use an agent based on a Chat Completion service, but all other agent types are run in the same way. For more information on other agent types and how to construct them, see the [Agent Framework user guide](https://learn.microsoft.com/en-us/agent-framework/user-guide/overview).

## **Understanding How Conversation History Is Stored in Multi-Turn Agents**

When building multi-turn conversational agents, it’s important to understand where the conversation history lives, because the storage model changes depending on the type of service powering the `AIAgent`.

### **1. ChatCompletion-based Agents (local or SDK-driven)**

 In this model, conversation history is fully managed by the client application. The `AgentThread` object stores every message exchanged with the user, and the entire history must be sent back to the model on each request. The agent has no backend persistence, so your application is responsible for maintaining context, managing message growth, and handling state across turns.

### **2. Azure AI Agent Service (within Azure AI Foundry)**

 When using the Azure AI Agent Service, the conversation is persisted directly inside the Azure platform. Instead of sending all past messages with every call, the client only provides a conversation reference (such as a conversation ID). Azure handles retrieving the history, maintaining continuity, and storing new messages automatically. This reduces payload size, improves performance, and centralizes state management in a secure, scalable service.

In conclusion, the key distinction is simple: `ChatCompletion` agents store their own memory on the client, while Azure AI Agent Service stores and manages the memory for you. Understanding this difference helps you architect multi-turn agents that scale cleanly and take advantage of Azure’s built-in conversation management.

## Running the agent with a multi-turn conversation

Agents are stateless and do not maintain any state internally between calls. To have a multi-turn conversation with an agent, you need to create an object to hold the conversation state and pass this object to the agent when running it.

For this lab, you can keep the code required to create the agent as in [Lab01](..\01-first-agent\README.md). 
Then, to create the conversation state object, call the `get_new_thread()` method on the agent instance.

```python
thread = agent.get_new_thread()
```

You can then pass this thread object to the `run` and `run_stream` methods on the agent instance, along with the user input.

```python
async def main():
    result1 = await agent.run("Tell me a joke about a pirate.", thread=thread)
    print(result1.text)

    result2 = await agent.run("Now add some emojis to the joke and tell it in the voice of a pirate's parrot.", thread=thread)
    print(result2.text)

asyncio.run(main())
```

This will maintain the conversation state between the calls, and the agent will be able to refer to previous input and response messages in the conversation when responding to new input.

## Single agent with multiple conversations

It is possible to have multiple, independent conversations with the same agent instance, by creating multiple `AgentThread` objects. These threads can then be used to maintain separate conversation states for each conversation. The conversations will be fully independent of each other, since the agent does not maintain any state internally. Replace the previous `main` with this one to learn how this work:

```python
async def main():
    thread1 = agent.get_new_thread()b
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
```

## 📝 Lab 02 Conclusion: Multi-Turn Conversations

You have successfully completed the second lab of the Microsoft Agent Framework workshop, learning how to manage stateful conversations with agents.

------

#### Key Takeaways from Lab 02

- **Conversation State Management:** You learned that agents are stateless and require an `AgentThread` object to maintain conversation history across multiple turns.
- **Multi-Turn Conversations:** You implemented conversations where the agent can reference previous messages, enabling contextual responses using the `thread` parameter in `.run()` and `.run_stream()` methods.
- **Multiple Independent Conversations:** You explored how a single agent instance can handle multiple, independent conversations simultaneously by creating separate `AgentThread` objects for each conversation.
- **Storage Models:** You understood the key difference between ChatCompletion-based agents (client-side history management) and Azure AI Agent Service (server-side history persistence), which is crucial for architecting scalable multi-turn solutions.

This knowledge of conversation management prepares you for more advanced agent patterns involving tools and function calling in the next lab.

------

### Code Reference

The complete code implementation for this lab can be found in the repository:

- **[`app.py`](app.py):** Contains examples of multi-turn conversations with a single thread and multiple independent threads.

------

## 🔗 Navigation

- **[⬅️ Back: Lab 01 — Create and Run Your First Agent](../01-first-agent/README.md)** — Return to the previous lab
- **[🏠 Back to Workshop Home](../README.md)** — Return to the main workshop page and prerequisites
- **[➡️ Next: Lab 03 — Agent Tools and Function Calling](../03-agent-tools/README.md)** — Continue to the next lab on integrating tools with agents

------