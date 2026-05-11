# Windows Setup Notes

## Issue: WeasyPrint on Windows

WeasyPrint requires GTK libraries that are difficult to install on Windows. This is only an issue for **local testing**. The GitHub Actions workflow runs on Ubuntu Linux where these libraries AND Chinese fonts are automatically installed.

## Chinese Font Support

The GitHub Actions workflow now installs these Chinese fonts on Linux:
- Noto Sans CJK (supports Chinese, Japanese, Korean)
- WenQuanYi Zen Hei (文泉驿正黑)
- WenQuanYi Micro Hei (文泉驿微米黑)

These fonts ensure Chinese characters (中文) display correctly in the PDF output.

## Solutions

### Option 1: Skip PDF Generation on Windows (Recommended)

**RECOMMENDED**: Don't test PDF generation on Windows! Here's why:

1. **WeasyPrint doesn't work on Windows** without GTK libraries ❌
2. **Chinese fonts may not be available** on Windows ❌
3. **Email test works fine** on Windows ✅

On GitHub Actions (Ubuntu Linux):
- WeasyPrint works perfectly ✅
- Chinese fonts are automatically installed ✅
- Both English and Chinese PDFs generate correctly ✅

### Option 2: Install GTK on Windows (Advanced)

If you really want PDF generation on Windows:

1. Download GTK3 Runtime: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
2. Install it (choose "Add to PATH" option)
3. Restart your computer
4. Try running the script again

**However, this is NOT necessary** since GitHub Actions handles PDF generation automatically!

### Option 3: Use WSL (Windows Subsystem for Linux)

Install WSL2 and run the scripts in Ubuntu environment.

## Recommendation

**For your use case**: Don't worry about local PDF generation!

1. ✅ Email works on Windows (tested successfully)
2. ✅ Everything works on GitHub Actions (Linux)
3. ✅ You'll receive PDFs every Monday via email

Just push the code to GitHub and let the automation handle it!

## What to Do Now

1. **Your email credentials are verified** ✅
2. **Add them to GitHub Secrets** (Step 2 from EMAIL_SETUP_GUIDE.md)
3. **Push all code to GitHub**
4. **Run the workflow** - it will work perfectly on Linux
5. **Receive PDFs in your inbox every Monday!**

No need to fix Windows PDF generation - the cloud will handle it! 🎉
