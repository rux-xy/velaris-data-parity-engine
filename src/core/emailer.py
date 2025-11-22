# emailer.py
# Optional: use this to send summary emails. Requires SMTP credentials.
import smtplib
from email.message import EmailMessage
from pathlib import Path

def send_email_smtp(smtp_host, smtp_port, username, password, to_address, subject, html_body, attachments=None):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = username
    msg['To'] = to_address
    msg.set_content("This email contains an HTML body. Please view in HTML capable client.")
    msg.add_alternative(html_body, subtype='html')
    if attachments:
        for p in attachments:
            p = Path(p)
            with p.open('rb') as f:
                data = f.read()
            msg.add_attachment(data, maintype='application', subtype='octet-stream', filename=p.name)
    with smtplib.SMTP_SSL(smtp_host, smtp_port) as s:
        s.login(username, password)
        s.send_message(msg)
