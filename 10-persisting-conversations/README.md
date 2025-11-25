# Lab10 - Persisting and Resuming Agent Conversations
This lab shows how to persist an agent conversation (AgentThread) to storage and reload it later.

When hosting an agent in a service or even in a client application, you often want to maintain conversation state across multiple requests or sessions. By persisting the AgentThread, you can save the conversation context and reload it later.

## Persisting and resuming the conversation

Create an agent and obtain a new thread that will hold the conversation state.

```python
import os
import asyncos
import json
import tempfile
from agent_framework import ChatAgent, ChatMessage, Role
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential



agent = ChatAgent(
    chat_client=AzureOpenAIChatClient(
        credential=AzureCliCredential(),
        endpoint=os.environ["AOAI_ENDPOINT"],
        deployment_name=os.environ["AOAI_DEPLOYMENT"]
    ),
    name="Assistant",
    instructions="You are a helpful assistant."
)

thread = agent.get_new_thread()
```

Run the agent, passing in the thread, so that the `AgentThread` includes this exchange.

```python
async def main():
    # Run the agent and append the exchange to the thread
    response = await agent.run("Tell me a short pirate joke.", thread=thread)
    print(response.text)

if __name__ == "__main__":
    asyncio.run(main())
```

Call the `serialize` method on the thread to serialize it to a dictionary. It can then be converted to JSON for storage and saved to a database, blob storage, or file.

```python
# Serialize the thread state
serialized_thread = await thread.serialize()
serialized_json = json.dumps(serialized_thread)

# Example: save to a local file (replace with DB or blob storage in production)
temp_dir = tempfile.gettempdir()
file_path = os.path.join(temp_dir, "agent_thread.json")
with open(file_path, "w") as f:
    f.write(serialized_json)
```

## Build an interactive persistence demo

Now that you know how to serialize an `AgentThread`, try a console app that manages **multiple persisted conversations**. The [`app.py`](app.py) sample keeps a permanent `USER>` prompt on screen and listens for Windows function-key shortcuts (via `msvcrt`) so you can create, save, list, and load threads without leaving the session. Every save writes a JSON snapshot to `10-persisting-conversations/persisted_threads/<slug>.json`, ready to reload whenever you need it.

- **Enter** — Sends whatever you just typed to the active `AgentThread`, keeping full context.
- **F2** — Starts a fresh thread (you’re prompted to save pending changes first).
- **F4** — Loads a saved thread by printing every available slug and prompting for the one you want (e.g., `demo-call`).
- **F10** — Saves the current thread. If it has never been saved, you are prompted for a friendly name; otherwise the existing slug is overwritten.
- **F12** — Opens the `persisted_threads/` folder in File Explorer so you can inspect or share the JSON snapshots.

When the script starts it clears the console, centers the title/menu block with decorative borders, and prints the current thread name (or `UNNAMED`) before showing the persistent `USER>` prompt. Assistant responses stack underneath so you can keep the banner visible while watching the conversation evolve.

Any time you send a prompt, the UI marks the thread as dirty (`*`) to remind you that you have unsaved changes. Saving resets the dirty flag until you send another message.

### Run the interactive experience

```powershell
cd 10-persisting-conversations
python app.py
```

Type a message, use the function keys as needed, and observe how the JSON files change under `persisted_threads/`. This makes it easy to demonstrate persisting/resuming without restarting the process.

------

## 📝 Lab 10 Conclusion: Persistence On-Demand

You built a console agent that can pause and resume any conversation by serializing `AgentThread` state to disk. With hotkeys to create, save, load, and inspect stored sessions, you can prove how Agent Framework lets you swap between multiple conversations without re-running prior prompts.

------

#### Key Takeaways from Lab 10

- `AgentThread.serialize()` captures every message in the conversation so you can recreate full context on any machine.
- Deserializing threads avoids rerunning prompts, which lowers token usage and preserves business decisions or approvals.
- Storing conversations as JSON makes them portable across services, letting you resume from CLI tools, web apps, or background jobs with the same state.

------

## 🔗 Navigation

- **[⬅️ Back: Lab 09 — Agents Middleware](../09-agents-middleware/README.md)** — Review how to wrap agents and tools with middleware.
- **[🏠 Back to Workshop Home](../README.md)** — Return to the full lab index and prerequisites.
- **[➡️ Next: Lab 11 — External Persistence](../11-external-persistence/README.md)** — Explore persisting conversation state with external data stores.
