# Microsoft Agent Framework Step by Step Workshop

Hands-on, step-by-step guide to building and operating AI agents with Microsoft’s Agent Framework.

This repository provides the end-to-end materials for a hands-on workshop focused on building, operating, and scaling AI Agents with Microsoft’s Agent Framework. It brings together architecture guidance, multi-agent design patterns, workflow orchestration examples, Responsible AI practices, and secure deployment strategies tailored for enterprise scenarios.

Inside this repo you’ll find structured labs, reference implementations, and modular components that demonstrate how to connect agents with MCP servers, integrate external systems through typed workflows, implement human-in-the-loop flows, and run agents safely within private network environments. Everything is designed to help teams move from conceptual understanding to real-world application—covering low-code agents, data-driven agents, and advanced multi-agent coordination.

This workshop reflects the collective learnings from partner engagements across the Americas, offering a practical path for architects and developers to adopt agentic patterns, accelerate solution delivery, and build AI-first applications with confidence.

## Prerequisites

Before you begin, ensure you have the following prerequisites:

- [Python 3.12](https://www.python.org/downloads/) **(recommended)** — This workshop is based on `agent-framework==1.0.0b251114`, which runs optimally with Python 3.12. While Python 3.10+ may work, Python 3.12 is strongly recommended for best compatibility.
- [Azure OpenAI service endpoint and deployment configured](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/create-resource)
- [Azure CLI installed](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) and [authenticated (for Azure credential authentication)](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli)
  - For [these](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli-interactively?view=azure-cli-latest#sign-in-with-a-browser) exercises this is the recommended authentication method for your CLI
- [User has the `Cognitive Services OpenAI User` or `Cognitive Services OpenAI Contributor` roles for the Azure OpenAI resource.](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/role-based-access-control)

> [!NOTE]
>
> You can also use VS Code to follow the labs in this workshop. Please make sure you are signed in to VS Code using the **same Azure AD user account that has access to the Azure OpenAI resource**, so that the Azure extension can authenticate correctly and allow the CLI and SDK to run against your Azure environment.

> [!IMPORTANT]
>
> Clear any existing Azure OpenAI environment variables before using Azure AD authentication. 
> If you have previously set `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, or `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` environment variables, they will take precedence over the credentials passed in code and may cause authentication failures with old/invalid values.

## Prepare Environment

To keep the setup lightweight and avoid downloading the `agent-framework` package inside every lab folder, this workshop uses a **single shared virtual environment** created at the **root of the repository**. All lab folders (`01-first-agent`, `02-agents`, etc.) will reuse the same environment.

This approach keeps installations consistent, reduces disk usage, and ensures that any updates to dependencies automatically apply across all exercises.

### Create the virtual environment at the root of the repo

Before proceeding with any lab, create a `.venv` folder in the root directory:

> [!NOTE]
>
> #### **About executables:**
>
>  Depending on your operating system, Python may be invoked as `py`, `python`, or `python3`.
>  Replace the command accordingly:
>
> - Windows → `py` or `python`
> - macOS / Linux → `python3`
>
> Examples below use `py`, but you may substitute it with the one that works in your environment.

------

### 1. Create and activate the environment

> [!IMPORTANT]
>
> **Use Python 3.12** to create the virtual environment for best compatibility with `agent-framework==1.0.0b251114`.

#### **Windows:**

```
py -3.12 -m venv .venv
```

#### **macOS / Linux:**

```
python3.12 -m venv .venv
```

Activate it:

#### **macOS / Linux:**

```
source .venv/bin/activate
```

#### **Windows:**

```
.venv\Scripts\activate
```

------

### 2. Upgrade pip (recommended)

```
py -m pip install --upgrade pip
```

------

### 3. Install the Agent Framework package

Install the specific version of the Agent Framework used in this workshop:

```
pip install agent-framework==1.0.0b251114
```

------

With all of this in place, you are ready to start learning and exploring the Microsoft Agent Framework in a structured and progressive way. Each lab within this workshop is organized into its own dedicated folder, and each folder contains a `README.md` file with the corresponding instructions, code walkthroughs, and the background theory needed to understand the sample. This structure keeps the content modular, makes navigation easier, and allows you to focus on one concept at a time as you build up your skills throughout the workshop.

Here is the index for each lab:

## **📘 Workshop Labs**

1. **[Lab 01 — Create and Run Your First Agent](01-first-agent/README.md)**
    *Learn how to build and run a basic conversational agent using the Microsoft Agent Framework. This foundational lab covers agent creation, basic execution, streaming responses, and multimodal communication with ChatMessage objects.*

2. **[Lab 02 — Multi-Turn Conversations](02-multi-turn-conversations/README.md)**
    *Discover how to manage stateful, multi-turn conversations with agents. Learn about AgentThread objects, conversation state management, and how to handle multiple independent conversations with a single agent instance.*

3. **[Lab 03 — Function Tools](03-function-tools/README.MD)**
    *Extend your agents with custom function tools to interact with external systems and business logic. Learn how to use the @ai_function decorator, Pydantic Field annotations, and class-based tool organization to give your agents powerful capabilities beyond conversation.*

4. **[Lab 04 — Human-in-the-loop Approvals](04-human-in-loop/README.md)**
    *Keep humans in control of high-impact actions. Build a stateful `ChatAgent`, capture multiple approval requests per turn using `ChatMessage`, and resume tool execution safely with `prior_run` once each decision is collected.*

5. **[Lab 05 — Structured Output](05-structured-output/README.md)**
    *Collect strongly typed JSON from your agents using Pydantic response schemas. Compare blocking and streaming executions, aggregate streaming deltas with `AgentRunResponse.from_agent_response_generator`, and surface the results in an interactive console app.*
