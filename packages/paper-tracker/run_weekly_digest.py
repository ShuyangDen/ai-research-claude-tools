"""
Weekly AI Economics Paper Digest - Combined Runner
Runs the English extractor, translates the report to Chinese via LLM,
then sends both reports in a single email.
"""
import os
import sys
import datetime as dt


def translate_report_to_chinese(en_md_path: str, google_api_key: str) -> str:
    """Translate an English markdown report to Chinese using Gemini."""
    from google.genai import Client
    client = Client(api_key=google_api_key)

    with open(en_md_path, "r", encoding="utf-8") as f:
        en_content = f.read()

    prompt = (
        "You are a professional academic translator. Translate the following weekly AI economics "
        "paper digest from English to Simplified Chinese. Rules:\n"
        "1. Translate ALL text to Chinese, including field labels and section headers\n"
        "2. Use these exact Chinese field names:\n"
        "   - Authors -> 作者\n"
        "   - Source -> 来源\n"
        "   - Method & Why included -> 方法与收录理由\n"
        "   - Abstract -> 摘要\n"
        "   - Tier 1 — Priority Read -> 一档 — 重点阅读\n"
        "   - Tier 2 — For Reference -> 二档 — 参考阅读\n"
        "   - Directly targets active research directions. Read in full. -> 直接对应当前研究方向，建议全文阅读。\n"
        "   - Rigorous AI + labor/education papers. Scan abstract and note if relevant. -> 严谨的AI+劳动/教育论文，浏览摘要，标注感兴趣的部分。\n"
        "3. Translate paper titles into natural Chinese\n"
        "4. Keep all markdown formatting (##, **, ---, links, emoji) intact\n"
        "5. Keep URLs and links unchanged\n"
        "6. Keep author names in their original language (do not translate names)\n\n"
        "Report to translate:\n\n" + en_content
    )

    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text


def main():
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

    # 1. Run English extractor
    print("\n[1/3] Running English extractor...")
    print("-" * 60)
    try:
        import paperextract
        paperextract.main()
        if os.path.exists(en_md):
            print(f"English report saved: {en_md}")
        else:
            print(f"WARNING: English markdown not found: {en_md}")
    except Exception as e:
        print(f"ERROR in English extractor: {e}")
        import traceback
        traceback.print_exc()

    # 2. Translate EN report to Chinese
    print("\n[2/3] Translating report to Chinese...")
    print("-" * 60)
    try:
        if os.path.exists(en_md):
            cn_content = translate_report_to_chinese(en_md, google_api_key)
            with open(cn_md, "w", encoding="utf-8") as f:
                f.write(cn_content)
            print(f"Chinese report saved: {cn_md}")
        else:
            print(f"WARNING: Cannot translate — English markdown not found: {en_md}")
    except Exception as e:
        print(f"ERROR translating to Chinese: {e}")
        import traceback
        traceback.print_exc()

    # 3. Convert both reports to PDF
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
                    print(f"PDF generation failed for {md_file}: {e}")
                    attachment_paths.append(md_file)  # fall back to markdown
    except ImportError:
        # WeasyPrint not available (e.g. Windows dev), attach markdown files
        for md_file in [en_md, cn_md]:
            if os.path.exists(md_file):
                attachment_paths.append(md_file)

    # 4. Send combined email
    print("\n[3/3] Sending combined email...")
    print("-" * 60)

    if not attachment_paths:
        print("ERROR: No files to attach!")
        return

    sender_email = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_PASSWORD")
    recipient_email = os.environ.get("RECIPIENT_EMAIL")

    if not (sender_email and sender_password and recipient_email):
        print("ERROR: Email credentials not configured!")
        print("Please set SENDER_EMAIL, SENDER_PASSWORD, and RECIPIENT_EMAIL environment variables")
        return

    try:
        from utils_pdf_email import send_email_with_attachment

        subject = f"Weekly AI Economics Paper Digest - {today}"

        en_attach = os.path.basename(en_pdf if os.path.exists(en_pdf) else en_md)
        cn_attach = os.path.basename(cn_pdf if os.path.exists(cn_pdf) else cn_md)

        # Customize the sender name in the email signature
        sender_name = os.environ.get("SENDER_NAME", "Your Name")

        body = f"""Dear Researcher,

Please find attached your weekly digest of AI + Economics papers focusing on education and labor markets.

Papers are classified into two tiers:
- Tier 1 (Priority Read): Directly targets your active research directions — read in full
- Tier 2 (For Reference): Rigorous AI + labor/education papers — scan abstract and note if relevant

Sources covered:
- NBER (Working Papers via RSS + NEP-AIN/LAB/EDU/LMA feeds)
- IZA (Discussion Papers via NEP/RePEC)
- AEA Journals (AER, AEJ series, JEL, JEP via CrossRef)
- CEPR (Discussion Papers)
- World Bank (Policy Research Working Papers)
- OpenAlex (Economics & Econometrics) + arXiv

Attachments:
- English report: {en_attach}
- Chinese report: {cn_attach}

Best regards,
{sender_name}"""

        print(f"Sending to: {recipient_email}")
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

    except Exception as e:
        print(f"ERROR sending email: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
