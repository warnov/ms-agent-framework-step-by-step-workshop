import asyncio
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from bank_functions import submit_payment, get_account_balance

agent = ChatAgent(
    chat_client=AzureOpenAIChatClient(
        credential=AzureCliCredential(),
        endpoint="https://warstandalone.openai.azure.com/",
        deployment_name="dep-gpt-5-mini"
    ),
    name="FinanceAgent",
    instructions="You are an agent from Contoso Bank. You assist users with financial operations and provide clear explanations. For transfers only amount, recipient name, and reference are needed",
    tools=[submit_payment, get_account_balance],
)

async def main():
    # Create a thread to maintain conversation state
    thread = agent.get_new_thread()
    
    print("=== FinanceAgent - Interactive Session ===")
    print("Type 'exit' or 'quit' to end the conversation\n")
    
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['exit', 'quit']:
            print("Goodbye!")
            break
        
        if not user_input:
            continue
        
        # Send to agent
        print("\nAgent: ", end="", flush=True)
        result = await agent.run(user_input, thread=thread)
        
        # Check if approval is required
        if result.user_input_requests:
            request = result.user_input_requests[0]
            print(f"\n\n=== APPROVAL REQUIRED ===")
            print(f"Function: {request.function_call.name}")
            print(f"Arguments: {request.function_call.arguments}")
            
            approval = input("\nDo you approve? (yes/no): ").strip()
            
            if approval.lower() == "yes":
                # Approve the request by providing the approval response
                print("\nAgent: ", end="", flush=True)
                # Pass the approval as a message to continue the conversation
                request.response = approval
                followup = await agent.run(approval, thread=thread, prior_run=result)
                print(followup.text if hasattr(followup, 'text') else str(followup))
            else:
                print("\nPayment cancelled.")
        else:
            print(result.text)
        
        print()

if __name__ == "__main__":
    asyncio.run(main())