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