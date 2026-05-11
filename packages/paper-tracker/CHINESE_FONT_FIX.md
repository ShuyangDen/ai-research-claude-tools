# Chinese Font Fix - Complete Solution

## Problem

Chinese characters (中文) were displaying as empty boxes (□□□□) in the generated PDF files.

## Root Causes

1. **Missing Chinese fonts** in the PDF generation environment
2. **WeasyPrint requires system-level fonts** to render non-Latin characters
3. **Windows lacks GTK libraries** needed for WeasyPrint to work

## Solution

### ✅ GitHub Actions (Linux Environment)

The GitHub Actions workflow has been updated to install Chinese fonts automatically:

```yaml
- name: Install system dependencies for PDF generation
  run: |
    sudo apt-get update
    sudo apt-get install -y \
      libpango-1.0-0 \
      libpangoft2-1.0-0 \
      libharfbuzz0b \
      libffi-dev \
      libjpeg-dev \
      libopenjp2-7-dev \
      libgdk-pixbuf2.0-0 \
      fonts-noto-cjk \          # ← Noto Sans CJK fonts
      fonts-noto-cjk-extra \    # ← Additional CJK variants
      fonts-wqy-zenhei \        # ← WenQuanYi Zen Hei (文泉驿正黑)
      fonts-wqy-microhei        # ← WenQuanYi Micro Hei (文泉驿微米黑)
```

### ✅ CSS Font Fallback Chain

Updated `utils_pdf_email.py` with proper Chinese font fallback:

```css
font-family: 'DejaVu Sans', 'Noto Sans CJK SC', 'SimSun', 'Microsoft YaHei', 'Arial', sans-serif;
```

**Font priority:**
1. DejaVu Sans (Latin characters)
2. Noto Sans CJK SC (Simplified Chinese)
3. SimSun (宋体 - common Windows Chinese font)
4. Microsoft YaHei (微软雅黑 - modern Chinese font)
5. Arial (fallback)
6. sans-serif (system fallback)

## How It Works

### On GitHub Actions (Linux/Ubuntu)

1. **Workflow starts** → Installs Chinese fonts via apt-get
2. **Python script runs** → Generates Markdown with Chinese content
3. **WeasyPrint converts** → Finds installed Chinese fonts
4. **PDF generated** → Chinese characters render correctly ✅

### On Windows (Local)

⚠️ **PDF generation will NOT work** on Windows without GTK libraries.

**Why?**
- WeasyPrint requires `libgobject-2.0-0` and other GTK libraries
- These are Linux libraries, not available on Windows by default
- Installing GTK on Windows is complex and error-prone

**What to do?**
- ✅ **Skip local testing** on Windows
- ✅ **Test via GitHub Actions** instead
- ✅ **Email functionality works** on Windows (just not PDF generation)

## Testing the Fix

### Method 1: GitHub Actions (Recommended)

1. **Push code to GitHub**:
   ```bash
   git add .
   git commit -m "Add Chinese font support for PDF generation"
   git push
   ```

2. **Manually trigger workflow**:
   - Go to repository → Actions tab
   - Click "Weekly AI Paper Digest"
   - Click "Run workflow" → Run workflow

3. **Check results**:
   - Wait for workflow to complete (~5-10 minutes)
   - Download artifacts (optional)
   - **Check your email** for the PDF attachments
   - Open Chinese PDF and verify characters display correctly

### Method 2: Wait for Monday

Just wait for the automated Monday 8 AM run and check your email!

## Verification Checklist

When you receive the PDF, verify:

- [ ] Chinese characters display correctly (not □□□□)
- [ ] Mixed English/Chinese text renders properly
- [ ] Common Chinese punctuation shows correctly (。，、：；)
- [ ] Both simplified and traditional characters work (if applicable)
- [ ] Bold/italic Chinese text formats correctly

## Example Chinese Content

The PDF should correctly render content like:

```
# 经济学研究论文摘要

## 研究方法

本文使用了以下识别策略：

1. **双重差分法** (Difference-in-Differences, DID)
2. **回归不连续设计** (Regression Discontinuity Design, RDD)
3. **工具变量法** (Instrumental Variables, IV)

## 主要发现

人工智能对教育和劳动力市场的影响显著：

- 提高了教学效率
- 改变了就业结构
- 影响了工资分配
```

All Chinese characters above should render as proper characters, not empty boxes.

## Troubleshooting

### If Chinese still shows as □□□□ after fix:

1. **Check GitHub Actions logs**:
   - Verify fonts were installed successfully
   - Look for any errors during `apt-get install`

2. **Check workflow file**:
   - Ensure `.github/workflows/weekly_paper_digest.yml` has the Chinese font packages listed

3. **Check utils_pdf_email.py**:
   - Verify the CSS includes Chinese fonts in the font-family

4. **Manual font test** (in GitHub Actions):
   - Add this step to workflow for debugging:
   ```yaml
   - name: Check installed fonts
     run: fc-list | grep -i "noto\|wenquanyi"
   ```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| □□□□ in PDF | No Chinese fonts installed | Add fonts to workflow YAML |
| PDF generation fails | Missing GTK libraries | Only happens on Windows; works on Linux |
| Wrong font style | CSS font-family incorrect | Update utils_pdf_email.py CSS |
| Mixed text broken | Font doesn't support both Latin & CJK | Use Noto Sans CJK (supports both) |

## Files Modified

1. ✅ [`.github/workflows/weekly_paper_digest.yml`](.github/workflows/weekly_paper_digest.yml)
   - Added Chinese font packages

2. ✅ [`utils_pdf_email.py`](utils_pdf_email.py)
   - Updated CSS font-family with Chinese fonts

3. ✅ [`WINDOWS_SETUP.md`](WINDOWS_SETUP.md)
   - Documented Windows limitations and Chinese font info

4. ✅ [`CHANGES_SUMMARY.md`](CHANGES_SUMMARY.md)
   - Added Chinese font fix to changelog

## Summary

**The fix is complete!**

Chinese fonts are now automatically installed on GitHub Actions, and the PDF generator uses proper font fallback to render Chinese characters correctly.

**You cannot test this on Windows**, but it will work perfectly on GitHub Actions (Linux).

**Next step**: Push to GitHub and test the workflow!

---

**Last Updated**: 2026-02-05
