"""
read_pages.py — Extract text from specific pages of a PDF.

Usage:
    python read_pages.py <pdf_path> <start_pdf_page> <end_pdf_page> [--max-chars N]

Pages are 1-indexed (PDF page 1 = first physical page).
Default max chars per page: 3000. Use --max-chars 0 for unlimited.

Output: plain text with page headers, UTF-8, to stdout.
"""

import sys
import argparse

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path")
    parser.add_argument("start_page", type=int, help="Start PDF page (1-indexed)")
    parser.add_argument("end_page", type=int, help="End PDF page (1-indexed, inclusive)")
    parser.add_argument("--max-chars", type=int, default=3000,
                        help="Max characters per page (0 = unlimited)")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    try:
        with pdfplumber.open(args.pdf_path) as pdf:
            total = len(pdf.pages)
            start = max(1, args.start_page)
            end = min(total, args.end_page)

            for page_num in range(start, end + 1):
                page = pdf.pages[page_num - 1]
                text = page.extract_text() or ""
                if args.max_chars > 0:
                    text = text[:args.max_chars]
                print(f"\n=== PDF PAGE {page_num} ===")
                print(text)

    except FileNotFoundError:
        print(f"ERROR: File not found: {args.pdf_path}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
