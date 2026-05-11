"""
Utility functions for PDF conversion and email sending
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
import markdown
from weasyprint import HTML, CSS


def markdown_to_pdf(md_file_path: str, output_pdf_path: str = None) -> str:
    """
    Convert markdown file to PDF with proper formatting.

    Args:
        md_file_path: Path to the markdown file
        output_pdf_path: Path for output PDF (optional, defaults to same name as MD)

    Returns:
        Path to the generated PDF file
    """
    # Read markdown file
    with open(md_file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Convert markdown to HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['extra', 'codehilite', 'tables', 'fenced_code']
    )

    # Add CSS styling for better PDF appearance with Chinese font support
    css_style = """
    <style>
        @page {
            size: A4;
            margin: 2cm;
        }
        body {
            font-family: 'DejaVu Sans', 'Noto Sans CJK SC', 'SimSun', 'Microsoft YaHei', 'Arial', sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }
        h1 {
            color: #2c3e50;
            font-size: 24pt;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 20px;
            margin-bottom: 15px;
        }
        h2 {
            color: #34495e;
            font-size: 18pt;
            margin-top: 20px;
            margin-bottom: 10px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }
        h3 {
            color: #7f8c8d;
            font-size: 14pt;
            margin-top: 15px;
        }
        p {
            margin-bottom: 10px;
            text-align: justify;
        }
        ul, ol {
            margin-left: 20px;
            margin-bottom: 10px;
        }
        li {
            margin-bottom: 5px;
        }
        strong {
            color: #2c3e50;
        }
        a {
            color: #3498db;
            text-decoration: none;
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 10pt;
        }
        hr {
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 20px 0;
        }
        blockquote {
            border-left: 4px solid #bdc3c7;
            padding-left: 15px;
            margin-left: 0;
            font-style: italic;
            color: #7f8c8d;
        }
    </style>
    """

    # Combine CSS and HTML
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        {css_style}
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Generate output PDF path if not provided
    if output_pdf_path is None:
        output_pdf_path = md_file_path.replace('.md', '.pdf')

    # Convert HTML to PDF
    HTML(string=full_html).write_pdf(output_pdf_path)

    print(f"PDF generated: {output_pdf_path}")
    return output_pdf_path


def send_email_with_attachment(
    sender_email: str,
    sender_password: str,
    recipient_email: str,
    subject: str,
    body: str,
    attachment_paths: list,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587
):
    """
    Send email with PDF attachments.

    Args:
        sender_email: Sender's email address
        sender_password: Sender's email password (or app password for Gmail)
        recipient_email: Recipient's email address (can be comma-separated for multiple recipients)
        subject: Email subject
        body: Email body text
        attachment_paths: List of file paths to attach
        smtp_server: SMTP server address (default: Gmail)
        smtp_port: SMTP port (default: 587 for TLS)
    """
    # Parse recipient emails (support comma-separated list)
    if isinstance(recipient_email, str):
        recipient_list = [email.strip() for email in recipient_email.split(',')]
    else:
        recipient_list = recipient_email

    # Create message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipient_list)  # Display all recipients
    msg['Subject'] = subject

    # Add body
    msg.attach(MIMEText(body, 'plain'))

    # Attach files
    for file_path in attachment_paths:
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                attachment = MIMEApplication(f.read(), _subtype="pdf")
                attachment.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=os.path.basename(file_path)
                )
                msg.attach(attachment)
            print(f"Attached: {os.path.basename(file_path)}")
        else:
            print(f"Warning: File not found: {file_path}")

    # Send email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        # Send to all recipients in the list
        server.sendmail(sender_email, recipient_list, msg.as_string())
        server.quit()
        print(f"Email sent successfully to {len(recipient_list)} recipient(s): {', '.join(recipient_list)}")
    except Exception as e:
        print(f"Error sending email: {e}")
        raise


def convert_and_send_reports(
    md_files: list,
    sender_email: str,
    sender_password: str,
    recipient_email: str
):
    """
    Convert markdown reports to PDF and send via email.

    Args:
        md_files: List of markdown file paths
        sender_email: Sender's email
        sender_password: Sender's email password
        recipient_email: Recipient's email
    """
    pdf_files = []

    # Convert all markdown files to PDF
    for md_file in md_files:
        if os.path.exists(md_file):
            try:
                pdf_path = markdown_to_pdf(md_file)
                pdf_files.append(pdf_path)
            except Exception as e:
                print(f"Error converting {md_file} to PDF: {e}")

    if not pdf_files:
        print("No PDF files to send")
        return

    # Prepare email
    from datetime import date
    subject = f"Weekly AI Economics Paper Digest - {date.today()}"
    body = f"""Dear Researcher,

Please find attached your weekly digest of AI + Economics papers focusing on education and labor markets.

This report includes papers from:
- OpenAlex (Economics & Econometrics)
- arXiv (Quantitative Finance & Econometrics)
- NBER (Working Papers)
- IZA (Discussion Papers via RePEc)

All papers have been filtered for rigorous economic methodology (causal inference focus).

Attachments:
{chr(10).join([f"- {os.path.basename(pdf)}" for pdf in pdf_files])}

Best regards,
Automated Paper Tracker
"""

    # Send email
    try:
        send_email_with_attachment(
            sender_email=sender_email,
            sender_password=sender_password,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            attachment_paths=pdf_files
        )
        print("Report delivery completed successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")
