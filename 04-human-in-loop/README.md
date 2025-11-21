# Lab04 - Human in the loop

This lab shows you how to use function tools that require human approval with an agent.

When agents require any user input, for example to approve a function call, this is referred to as a human-in-the-loop pattern. An agent run that requires user input, will complete with a response that indicates what input is required from the user, instead of completing with a final answer. The caller of the agent is then responsible for getting the required input from the user, and passing it back to the agent as part of a new agent run.

## Create the agent with function tools requiring approval

When using functions, it's possible to indicate for each function, whether it requires human approval before being executed. This is done by setting the `approval_mode` parameter to `"always_require"` when using the `@ai_function` decorator.

Here is an example of a function tool that submits a payment to an external system. Because this operation has financial impact, it is configured so that it always requires human approval before being executed by the agent. To keep this lab organized, you should create a new file named [`payment_functions.py`](payment_functions.py) in this same folder, where you will place the full implementation of the payment function tool used in this example. The agent in this lab will reference that file when invoking operations that require explicit human approval.

```python
from typing import Annotated
from agent_framework import ai_function

@ai_function(approval_mode="always_require")
def submit_payment(
    amount: Annotated[float, "Payment amount in USD"],
    recipient: Annotated[str, "Recipient name or vendor ID"],
    reference: Annotated[str, "Short description for the payment reference"],
) -> str:
    """
    Submit a payment request to the external payments system.

    This operation has financial impact and should always be reviewed
    and approved by a human before it is executed.
    """
    # In a real scenario this would call an external payments API.
    # Here we just simulate the side effect.
    return (
        f"Payment of ${amount:.2f} to '{recipient}' has been submitted "
        f"with reference '{reference}'."
    )

```

When creating the agent, you can now provide the approval requiring function tool to the agent, by passing a list of tools to the `ChatAgent` constructor.

## Introducing the ChatAgent

In previous labs you worked with the Agent Framework using simpler execution patterns, where the agent was instantiated ad-hoc and runs were executed directly using helper functions or high-level wrappers. Those approaches are great for getting started, but they do not maintain long-lived conversational state, do not manage resources automatically, and do not provide a built-in lifecycle for tools or streaming.

The **`ChatAgent`** class is the more structured and stateful way to work with agents in the framework. It:

- keeps the conversation history internally
- manages tool registration and availability
- integrates cleanly with function tools (including those requiring approval)
- provides a context-manager (`async with`) lifecycle
- maintains a persistent agent identity (`name`, `instructions`, `memory`, etc.)
- allows multiple runs while keeping state consistent

In other words, while earlier labs focused on simple single-shot agent runs, `ChatAgent` represents a full conversational agent instance**, capable of tools, approvals, and complex multi-turn flows.

## OpenAIResponsesClient

In previous labs, you interacted with the Agent Framework using simplified helper functions that hid the underlying model client. In this lab, however, you instantiate a `ChatAgent` directly, and that requires providing an explicit chat client implementation. The `OpenAIResponsesClient` is the model client that enables the agent to communicate with Azure OpenAI or OpenAI-compatible inference services using the framework’s unified chat protocol. By importing it from `agent_framework.openai`, you make it available as the backend that the agent will use to generate responses, execute tools, and handle function approval flows. This is why the import appears now, even though earlier labs did not need it explicitly.

------

## Creating an agent that uses approval-requiring tools

Now that you have a function tool that requires explicit human approval, you can pass it to the agent by including it in the `tools` list of the `ChatAgent` constructor. This makes the tool available to the agent, but also ensures that the agent will request human approval whenever it needs to invoke that function.

Let's add the `app.py` to create an agent using the `ChatAgent` class together with function tools—some of which may require human approval:

```python
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient
from payment_functions import submit_payment  # Your approval-required tool

async with ChatAgent(
    chat_client=OpenAIResponsesClient(),
    name="FinanceAgent",
    instructions="You assist users with financial operations and provide clear explanations.",
    tools=[submit_payment],
) as agent:
    # Agent is now ready to be used

```

Since you now have a function that requires approval, the agent might respond with a request for approval, instead of executing the function directly and returning the result. You can check the response for any user input requests, which indicates that the agent requires user approval for a function.

```python
result = await agent.run(
    "Send a payment of 250 dollars to ACME Supplies with reference 'January invoice'."
)

# Since `submit_payment` always requires approval,
# the agent may respond with a user_input_request instead
# of executing the function immediately.
if result.user_input_requests:
    request = result.user_input_requests[0]

    print("=== Approval Required ===")
    print(f"Function: {request.function_call.name}")
    print(f"Arguments: {request.function_call.arguments}")

    # In a real application you would ask the end user for explicit approval.
    # For this lab, we simulate that step with a simple input prompt.
    approval = input("Do you approve this payment? (yes/no): ")

    if approval.lower() == "yes":
        # Resume the agent by providing the required user input
        # and referencing the prior run, so the agent continues the same flow.
        followup = await agent.run(user_input=approval, prior_run=result)

        print("=== Final result ===")
        print(followup.output_text)
    else:
        print("Payment was not approved.")


```

