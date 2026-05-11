"""
extract_toc.py — Extract table of contents from a textbook PDF.

Usage:
    python extract_toc.py <pdf_path>

Output: JSON to stdout with chapter list and PDF page offset.
"""

import sys
import re
import json

try:
    import pdfplumber
except ImportError:
    print(json.dumps({"error": "pdfplumber not installed. Run: pip install pdfplumber"}))
    sys.exit(1)


def extract_text_safe(page):
    try:
        text = page.extract_text()
        return text if text else ""
    except Exception:
        return ""


def find_toc_pages(pdf, max_scan=30):
    """Find pages that contain a Table of Contents."""
    toc_pages = []
    for i in range(min(max_scan, len(pdf.pages))):
        text = extract_text_safe(pdf.pages[i])
        if re.search(r'\b(Contents|Table of Contents)\b', text, re.IGNORECASE):
            toc_pages.append(i)
    return toc_pages


def parse_toc_entries(toc_text):
    """
    Parse chapter-level entries from TOC text.
    Handles compact pdfplumber output where spaces are removed, e.g.:
      "1 SingularValueDecomposition(SVD) 3"
      "1 SingularValueDecomposition . . . . 3"
      "Chapter 1: Title ........ 3"
    Returns list of dicts with chapter_num, title, book_page_start.
    """
    entries = []

    # Pattern breakdown:
    #   ^(\d{1,2})       — chapter number at line start (1-2 digits)
    #   \s+              — whitespace
    #   ([A-Z]\S.{2,70}) — title starting with uppercase, min 3 chars
    #   [\s\.]*          — optional dots/spaces (may be absent in compact output)
    #   \s+(\d{1,4})\s*$ — trailing page number
    patterns = [
        # Standard: "1 Title . . . . 3"  or  "1 TitleNoSpaces 3"
        r'^(\d{1,2})\s+(\S.+?)\s+(\d{1,4})\s*$',
        # "Chapter 1: Title ... 3"
        r'^Chapter\s+(\d{1,2})[:\s]+(.{3,70?})\s+(\d{1,4})\s*$',
        # "1. Title ... 3"
        r'^(\d{1,2})\.\s+(.{3,70?})\s+(\d{1,4})\s*$',
    ]

    for line in toc_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Skip lines that are clearly section entries (e.g., "1.1 Overview . 4")
        if re.match(r'^\d{1,2}\.\d', line):
            continue
        for pat in patterns:
            m = re.match(pat, line, re.IGNORECASE)
            if m:
                chap_num = int(m.group(1))
                title = re.sub(r'\s+', ' ', m.group(2)).strip()
                # Remove trailing dots from title
                title = title.rstrip('. ')
                book_page = int(m.group(3))
                if 1 <= chap_num <= 20 and len(title) >= 3:
                    entries.append({
                        "chapter_num": chap_num,
                        "title": title,
                        "book_page_start": book_page
                    })
                break

    # Deduplicate (same chapter_num, keep first occurrence)
    seen = set()
    unique = []
    for e in entries:
        if e["chapter_num"] not in seen:
            seen.add(e["chapter_num"])
            unique.append(e)

    return sorted(unique, key=lambda x: x["chapter_num"])


def find_pdf_offset(pdf, chapters, toc_page_indices, max_scan=80):
    """
    Find the PDF page offset by searching for the first chapter's actual start page.
    Skips TOC pages to avoid false matches.
    Returns: pdf_offset  (pdf_page = book_page + pdf_offset)
    """
    if not chapters:
        return 0

    first_ch = chapters[0]
    ch_num = first_ch["chapter_num"]
    toc_set = set(toc_page_indices)

    # A real chapter-start page has "Chapter N" as a prominent heading
    # (typically one of the first lines) followed by the chapter title on the next line.
    for i in range(min(max_scan, len(pdf.pages))):
        if i in toc_set:
            continue
        text = extract_text_safe(pdf.pages[i])
        if not text:
            continue
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines:
            continue
        # First line should be "Chapter N" or just the number
        first_line = lines[0]
        if re.match(r'^Chapter\s+' + str(ch_num) + r'\s*$', first_line, re.IGNORECASE) or \
           re.match(r'^' + str(ch_num) + r'\s*$', first_line):
            offset = i - (first_ch["book_page_start"] - 1)
            if 0 < offset < 80:
                return offset

    return 0


def infer_page_ends(chapters, total_book_pages):
    """Fill in book_page_end for each chapter from the next chapter's start."""
    for i, ch in enumerate(chapters):
        if i + 1 < len(chapters):
            ch["book_page_end"] = chapters[i + 1]["book_page_start"] - 1
        else:
            ch["book_page_end"] = total_book_pages

    return chapters


def extract_book_title(pdf):
    """Try to extract book title from first 3 pages."""
    for i in range(min(3, len(pdf.pages))):
        text = extract_text_safe(pdf.pages[i])
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        # Title is usually the longest non-copyright line on page 1
        if lines:
            candidates = [l for l in lines if len(l) > 10 and 'copyright' not in l.lower()]
            if candidates:
                return candidates[0]
    return "Unknown"


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python extract_toc.py <pdf_path>"}))
        sys.exit(1)

    pdf_path = sys.argv[1]

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            book_title = extract_book_title(pdf)

            # Find TOC
            toc_page_indices = find_toc_pages(pdf)
            if not toc_page_indices:
                print(json.dumps({"error": "Could not find Table of Contents in first 30 pages"}))
                sys.exit(1)

            # Collect all TOC text
            toc_text = ""
            for idx in toc_page_indices:
                toc_text += extract_text_safe(pdf.pages[idx]) + "\n"

            # Parse chapters
            chapters = parse_toc_entries(toc_text)
            if not chapters:
                print(json.dumps({"error": "Could not parse any chapter entries from TOC", "toc_text": toc_text[:2000]}))
                sys.exit(1)

            # Find PDF offset
            pdf_offset = find_pdf_offset(pdf, chapters, toc_page_indices)

            # Fill page ends (estimate total book pages from last chapter's distance)
            estimated_total_book_pages = total_pages - pdf_offset
            chapters = infer_page_ends(chapters, estimated_total_book_pages)

            # Add PDF page numbers
            for ch in chapters:
                ch["pdf_page_start"] = ch["book_page_start"] + pdf_offset
                ch["pdf_page_end"] = ch["book_page_end"] + pdf_offset

            result = {
                "pdf_path": pdf_path,
                "title": book_title,
                "total_pdf_pages": total_pages,
                "pdf_offset": pdf_offset,
                "toc_page_indices": toc_page_indices,
                "chapters": chapters
            }

            # UTF-8 safe output
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            print(json.dumps(result, ensure_ascii=False, indent=2))

    except FileNotFoundError:
        print(json.dumps({"error": f"File not found: {pdf_path}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
