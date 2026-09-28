"""Azure Communication Services email helper."""
from __future__ import annotations
from opentelemetry import trace

_tracer = trace.get_tracer("sports-iq.acs")


_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
  <div style="background: #1a1a2e; padding: 20px; border-radius: 8px 8px 0 0;">
    <h1 style="color: #D4A017; margin: 0;">Sports-IQ Exclusive Offer</h1>
    <p style="color: #aaa; margin: 4px 0 0 0;">Exclusive Fan Offer</p>
  </div>
  <div style="border: 2px solid #D4A017; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
    <p style="font-size: 16px;">Hi <strong>{fan_name}</strong>,</p>
    <p>As a valued <strong>{loyalty_tier}</strong> member, here's an exclusive offer waiting for you right now at the venue:</p>
    <div style="background: #f5f0e8; border-left: 4px solid #D4A017; padding: 16px; margin: 16px 0; border-radius: 4px;">
      <h2 style="margin: 0 0 8px 0; color: #1a1a2e;">{offer_title}</h2>
      <p style="margin: 0; font-size: 15px;">{offer_description}</p>
      <p style="margin: 12px 0 0 0; font-size: 20px; font-weight: bold; color: #D4A017;">
        Code: <span style="letter-spacing: 2px;">{offer_code}</span>
      </p>
    </div>
    <p style="color: #666; font-size: 13px;">⏱ Valid until end of tonight's match &nbsp;|&nbsp; 📍 Check the offer details for pickup location</p>
    <p style="font-size: 14px; color: #333;">Enjoy the match! 🔥</p>
  </div>
  <p style="text-align: center; color: #aaa; font-size: 11px; margin-top: 16px;">
    Sports-IQ Fan Engagement Platform
  </p>
</body>
</html>
"""


def send_offer_email(
    connection_string: str,
    sender_address: str,
    to_email: str,
    fan_name: str,
    loyalty_tier: str,
    offer_title: str,
    offer_description: str,
    offer_code: str,
) -> str:
    """Send a branded offer email via ACS. Returns the message ID."""
    with _tracer.start_as_current_span("acs.send_offer_email") as span:
        span.set_attribute("acs.to_email", to_email)
        span.set_attribute("acs.fan_name", fan_name)
        span.set_attribute("acs.loyalty_tier", loyalty_tier)
        span.set_attribute("acs.offer_title", offer_title)
        span.set_attribute("acs.offer_code", offer_code)
        span.set_attribute("acs.sender_address", sender_address)
        try:
            from azure.communication.email import EmailClient
            client = EmailClient.from_connection_string(connection_string)
            html = _HTML_TEMPLATE.format(
                fan_name=fan_name,
                loyalty_tier=loyalty_tier,
                offer_title=offer_title,
                offer_description=offer_description,
                offer_code=offer_code,
            )
            message = {
                "senderAddress": sender_address,
                "recipients": {"to": [{"address": to_email, "displayName": fan_name}]},
                "content": {
                    "subject": f"Sports-IQ Exclusive for You: {offer_title}",
                    "html": html,
                    "plainText": f"Hi {fan_name}, use code {offer_code} for: {offer_title}. Valid until end of game.",
                },
            }
            poller = client.begin_send(message)
            result = poller.result()
            msg_id = result["id"]
            span.set_attribute("acs.message_id", msg_id)
            span.set_status(trace.StatusCode.OK)
            return msg_id
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
            raise
