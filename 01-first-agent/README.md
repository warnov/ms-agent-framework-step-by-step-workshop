# Lab01 - Create and run your first agent

In this opening exercise you’ll learn how to build and run a basic conversational agent using the Microsoft Agent Framework. We’ll guide you through setting up your environment, installing dependencies, and writing a minimal agent that interacts with a Chat Completion LLM to generate responses. The tutorial uses Azure OpenAI as the inference backend, but any LLM compatible with the framework’s chat client protocol can be used in its place, including providers such as OpenAI, Google Gemini, Anthropic Claude, Mistral, Cohere, DeepSeek, Amazon Bedrock (which exposes models like Claude, Llama, and Mistral), and open-source models served locally through Ollama. Each provider comes with its own considerations—such as Bedrock requiring AWS credentials or Ollama needing to run locally—but all of them work seamlessly as long as they implement an `IChatClient`-compatible interface.

Step by step, you’ll define the agent’s behavior, run it locally, and interact with it through a simple command-line interface. This initial agent will form the foundation for more complex scenarios later in the workshop, giving you a practical starting point for exploring the full capabilities of the Agent Framework.

## 1. Create the folder for the lab and open VS Code

Let's create the folder and then open the workshop folder with VS Code for ease of use:

```
mkdir 01-first-agent
code .
```

Now, within the 01-first-agent create the file app.py.

## 2. Create the agent

- First, create a chat client for communicating with Azure OpenAI and use the same login as you used when authenticating with the Azure CLI in the [Prerequisites](https://learn.microsoft.com/en-us/agent-framework/tutorials/agents/run-agent?pivots=programming-language-python#prerequisites) step.
- Then, create the agent, providing instructions and a name for the agent.

```python
import asyncio
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential

agent = AzureOpenAIChatClient(
    credential=AzureCliCredential(),
    endpoint="[YOUR_ENDPOINT_NAME]",
    deployment_name="[YOUR_DEPLOYMENT_NAME]"
).create_agent(
    instructions="You are good at telling jokes.",
    name="Joker"
)
```

## 3. Running the agent

To run the agent, call the `run` method on the agent instance, providing the user input. The agent will return a response object, and accessing the `.text` property provides the text result from the agent.

```python
async def main():
    result = await agent.run("Tell me a joke about a pirate.")
    print(result.text)

asyncio.run(main())
```

## 4. Running the agent with streaming

Observe how easy is to run the agent with streaming with the agent framework: call the `run_stream` method on the agent instance, providing the user input. The agent will stream a list of update objects, and accessing the `.text` property on each update object provides the part of the text result contained in that update. 

For you to notice the streaming, change the `instructions` to: `"You are good at telling tales."` and the prompt to `"Tell me a tale about a pirate"`

```python
async def main():
    async for update in agent.run_stream("Tell me a tale about a pirate."):
        if update.text:
            print(update.text, end="", flush=True)
    print()  # New line after streaming is complete

asyncio.run(main())
```

You will see the streaming in action!

## 5. Running the agent with a ChatMessage: The Power of Structured Multimodal Messages

Instead of a simple string, you can also provide one or more `ChatMessage` objects to the `run` and `run_stream` methods.

#### Understanding `ChatMessage`

`ChatMessage` is a structured object that represents a **single message within a conversation**, enabling clear definition of the message's properties:

1.  **`role` (Sender):** Specifies who sent the message (e.g., `Role.USER`, `Role.AGENT`/`MODEL`).
2.  **`contents` (Payload):** A list of content elements, supporting mixed data types.

#### Why Use `ChatMessage`?

The main advantage is support for **multimodality** and structured conversation context:

| Benefit                | Description                                                  |
| :--------------------- | :----------------------------------------------------------- |
| **Multimodal Support** | Allows you to combine various data types—text, images, video URIs—within a single, cohesive message. |
| **Clear Context**      | Explicitly setting the `role` is vital for managing conversation history and turns effectively. |

#### The Example Explained: A Multimodal Request

This code illustrates how `ChatMessage` allows the agent to process both a textual instruction and a visual element simultaneously.

```python
from agent_framework import ChatMessage, TextContent, UriContent, Role

message = ChatMessage(
    # The message is from the user
    role=Role.USER, 
    contents=[
        # The text part of the request
        TextContent(text="Tell me a joke about this image?"),
        # The image part of the request, referenced by a URI
        UriContent(uri="[https://www.fotosanimales.es/wp-content/uploads/2017/12/pinguino.jpg](https://www.fotosanimales.es/wp-content/uploads/2017/12/pinguino.jpg)", media_type="image/jpeg")
    ]
)

async def main():
    # The agent receives the question AND the image together
    result = await agent.run(message) 
    print(result.text) 

asyncio.run(main())
```

## 📝 Lab 01 Conclusion: Your First Agent

You have successfully completed the first foundational lab of the Microsoft Agent Framework workshop.

------

#### Key Takeaways from Lab 01

- **Agent Creation:** You learned how to instantiate a conversational agent by connecting it to an **Azure OpenAI** backend using the `AzureOpenAIChatClient` and defining its personality via the `instructions` parameter (e.g., "You are good at telling jokes.").
- **Basic Execution (`.run`):** You executed a simple, single-turn query using a standard Python string as input.
- **Streaming Execution (`.run_stream`):** You implemented response streaming, demonstrating how the framework processes and delivers tokens in real-time, which is essential for a responsive user experience.
- **Multimodal Communication (`ChatMessage`):** You explored the advanced pattern of using the `ChatMessage` object, which is crucial for sending **multimodal requests** (combining text and external media like images via URIs) and for managing complex **multi-turn conversations** effectively.

This initial agent serves as the basic building block for all subsequent, more complex scenarios in this workshop.

------

### Code Reference

The complete code implementations for this lab can be found in the repository:

- **[`app.py`](app.py):** Contains the basic agent creation, the `.run()` example, and the `.run_stream()` example (Steps 2, 3, and 4).
- **[`app_multimodal.py`](app_multimodal.py):** Contains the advanced example demonstrating the use of `ChatMessage` for multimodal input (Step 5).

------

## 🔗 Navigation

- **[🏠 Back to Workshop Home](../README.md)** — Return to the main workshop page and prerequisites
- **[➡️ Next: Lab 02 — Multi-Turn Conversations](../02-multi-turn-conversations/README.md)** — Continue to the next lab on managing multi-turn conversations

------