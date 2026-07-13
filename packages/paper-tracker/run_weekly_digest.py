"""
Weekly AI Economics Paper Digest - Combined Runner

Runs the English extractor, translates the report to Chinese via LLM,
then sends both reports in a single email.
"""
import datetime as dt
import os
import sys

from tracker_core import parse_recipients, safe_error_summary


def translate_report_to_chinese(en_md_path: str, google_api_key: str) -> str:
    """Translate an English markdown report to Chinese using Gemini."""
    from google.genai import Client

    client = Client(api_key=google_api_key)

    with open(en_md_path, "r", encoding="utf-8") as f:
        en_content = f.read()

    prompt = (
        "You are a professional academic translator. Translate the following weekly AI economics "
        "paper digest from English to Simplified Chinese. Rules:\n"
        "1. Translate all public-facing text to Chinese, including field labels, section headers, "
        "and blockquote content.\n"
        "2. Use these exact Chinese field names:\n"
        "   - Authors -> 作者\n"
        "   - Source -> 来源\n"
        "   - Abstract -> 摘要\n"
        "   - Tier 1 - Priority Papers -> 一档 - 重点论文\n"
        "   - Tier 2 - Additional Relevant Papers -> 二档 - 其他相关论文\n"
        "   - Tier 3 - Methodology Papers -> 三档 - 方法论文\n"
        "3. Translate paper titles into natural Chinese.\n"
        "4. Translate abstract text inside blockquotes. Do not leave blockquote content in English.\n"
        "5. Keep markdown formatting, URLs, and author names unchanged.\n"
        "6. Do not add recommendation reasons, private profile details, reading preferences, or "
        "research-interest explanations that are not already in the public report.\n\n"
        "Report to translate:\n\n" + en_content
    )

    model = os.environ.get(
        "PAPER_TRACKER_TRANSLATION_MODEL",
        os.environ.get("PAPER_TRACKER_MODEL", "gemini-2.5-flash"),
    )
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text


def main() -> int:
    """Run English extractor, translate to Chinese, then send combined email."""
    print("=" * 60)
    print("Weekly AI Economics Paper Digest - Combined Runner")
    print("=" * 60)

    today = dt.date.today()
    en_md = f"Econ_JMP_Report_EN_{today}.md"
    cn_md = f"Econ_JMP_Report_CN_{today}.md"
    en_pdf = f"Econ_JMP_Report_EN_{today}.pdf"
    cn_pdf = f"Econ_JMP_Report_CN_{today}.pdf"

    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        print("ERROR: GOOGLE_API_KEY not set")
        sys.exit(1)

    print("\n[1/3] Running English extractor...")
    print("-" * 60)
    import paperextract

    extraction_result = paperextract.main()
    if os.path.exists(en_md):
        print(f"English report saved: {en_md}")
    else:
        raise FileNotFoundError(f"English extractor did not create {en_md}")

    print("\n[2/3] Translating report to Chinese...")
    print("-" * 60)
    cn_content = translate_report_to_chinese(en_md, google_api_key)
    if not cn_content or not cn_content.strip():
        raise RuntimeError("Translation model returned empty content")
    with open(cn_md, "w", encoding="utf-8") as f:
        f.write(cn_content)
    print(f"Chinese report saved: {cn_md}")

    attachment_paths = []
    try:
        from utils_pdf_email import markdown_to_pdf

        for md_file, pdf_file in [(en_md, en_pdf), (cn_md, cn_pdf)]:
            if os.path.exists(md_file):
                try:
                    markdown_to_pdf(md_file, pdf_file)
                    attachment_paths.append(pdf_file)
                    print(f"PDF generated: {pdf_file}")
                except Exception as e:
                    print(f"PDF generation failed for {md_file}: {safe_error_summary(e)}")
                    attachment_paths.append(md_file)
    except ImportError:
        for md_file in [en_md, cn_md]:
            if os.path.exists(md_file):
                attachment_paths.append(md_file)

    source_health_path = extraction_result.get("source_health_path", "source_health.json")
    if os.path.exists(source_health_path):
        attachment_paths.append(source_health_path)

    print("\n[3/3] Sending combined email...")
    print("-" * 60)

    if not attachment_paths:
        raise RuntimeError("No digest or source-health files are available to attach")

    sender_email = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_PASSWORD")
    recipient_email = os.environ.get("RECIPIENT_EMAIL")

    if not (sender_email and sender_password and recipient_email):
        raise RuntimeError(
            "Email credentials are incomplete; set SENDER_EMAIL, SENDER_PASSWORD, and RECIPIENT_EMAIL"
        )

    try:
        from utils_pdf_email import send_email_with_attachment

        health_status = extraction_result.get("health_status", "unknown")
        subject_prefix = "[DEGRADED] " if health_status == "degraded" else ""
        subject = f"{subject_prefix}Weekly AI Economics Paper Digest - {today}"

        en_attach = os.path.basename(en_pdf if os.path.exists(en_pdf) else en_md)
        cn_attach = os.path.basename(cn_pdf if os.path.exists(cn_pdf) else cn_md)
        sender_name = os.environ.get("SENDER_NAME", "Your Name")

        body = f"""Dear Researcher,

Please find attached the weekly digest of AI + Economics papers.

Papers are classified into three tiers:
- Tier 1 (Priority Papers): highest-priority papers from this week's screened sources
- Tier 2 (Additional Relevant Papers): other relevant AI + economics papers
- Tier 3 (Methodology Papers): methods or tools that may be useful for economics research

Sources covered:
- NBER (Working Papers via RSS + NEP-AIN/LAB/EDU/LMA feeds)
- IZA (Discussion Papers via NEP/RePEC)
- AEA Journals (AER, AEJ series, JEL, JEP via CrossRef)
- CEPR (Discussion Papers)
- World Bank (Policy Research Working Papers)
- OpenAlex (Economics & Econometrics) + arXiv

Source coverage status: {health_status.upper()}
See source_health.json for per-source counts and errors.

Attachments:
- English report: {en_attach}
- Chinese report: {cn_attach}

Best regards,
{sender_name}"""

        recipient_count = len(parse_recipients(recipient_email))
        print(f"Sending digest to {recipient_count} recipient(s)")
        print(f"Attachments: {', '.join([os.path.basename(p) for p in attachment_paths])}")

        send_email_with_attachment(
            sender_email=sender_email,
            sender_password=sender_password,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            attachment_paths=attachment_paths,
        )

        print("Email sent successfully!")
        print("=" * 60)
        print("Weekly digest completed successfully!")
        print("=" * 60)
        return 0

    except Exception as e:
        raise RuntimeError(f"Email delivery failed ({type(e).__name__})") from None


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        import traceback

        print(f"FATAL: weekly digest failed: {safe_error_summary(exc)}")
        traceback.print_tb(exc.__traceback__)
        raise SystemExit(1)
