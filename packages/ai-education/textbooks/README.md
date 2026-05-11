# Textbooks

Place your economics textbook PDFs in this folder.

Before using a textbook in tutoring sessions, build its index:
1. Open Claude Code in the AI Education project folder
2. Run `/index-textbook <textbook-filename.pdf>`

This creates `textbooks/index/<slug>/` with:
- `index.md` — chapter list and descriptions
- `paper_relevance.md` — updated per paper to show which chapters are relevant
- `chapter_N.md` — detailed notes per chapter

**During sessions**: Claude reads only index files, never the raw PDF. This keeps token use low.

**scripts/** — utilities for building indexes:
- `extract_toc.py` — extract table of contents from a PDF (JSON output)
- `read_pages.py` — extract text from specific PDF pages (used when chapter index isn't precise enough)

**Dependency**: `pip install pdfplumber`
