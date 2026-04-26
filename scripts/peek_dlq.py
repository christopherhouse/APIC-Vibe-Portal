"""One-off: peek messages in analytics-events/cosmos-writer DLQ."""

from azure.identity import AzureCliCredential
from azure.servicebus import ServiceBusClient, ServiceBusSubQueue

NS = "apicvibe-sb-dev-gixl2mha64l56.servicebus.windows.net"
TOPIC = "analytics-events"
SUB = "cosmos-writer"

with ServiceBusClient(NS, AzureCliCredential()) as c:
    receiver = c.get_subscription_receiver(
        TOPIC, SUB, sub_queue=ServiceBusSubQueue.DEAD_LETTER, max_wait_time=10
    )
    with receiver:
        msgs = receiver.peek_messages(max_message_count=5)
        print(f"Peeked {len(msgs)} DLQ messages")
        for i, m in enumerate(msgs, 1):
            print(f"\n--- DLQ msg {i} ---")
            print(f"  reason     : {m.dead_letter_reason}")
            desc = m.dead_letter_error_description or ""
            print(f"  description: {desc[:600]}")
            print(f"  delivery#  : {m.delivery_count}")
            try:
                body_bytes = b"".join(m.body)
            except TypeError:
                body_bytes = bytes(m.body) if not isinstance(m.body, (bytes, bytearray)) else m.body
            print(f"  body       : {body_bytes[:300]!r}")
