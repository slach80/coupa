# GitHub Pages Setup Guide

## Quick Setup (5 Minutes)

### Step 1: Commit Documentation to Your Repo

```bash
cd /home/slach/Projects/coupa

# Add all documentation files
git add docs/classification-system/

# Commit
git commit -m "Add Activity Code Classification System documentation and demo"

# Push to GitHub
git push origin main
```

### Step 2: Enable GitHub Pages

1. Go to your GitHub repository: `https://github.com/YOUR_USERNAME/coupa`
2. Click **Settings** (top right)
3. Scroll down to **Pages** (left sidebar)
4. Under **Source**, select:
   - Branch: `main`
   - Folder: `/docs`
5. Click **Save**

### Step 3: Access Your Documentation

After 1-2 minutes, your site will be live at:

```
https://YOUR_USERNAME.github.io/coupa/classification-system/
```

**Direct links:**
- **Executive Overview:** `https://YOUR_USERNAME.github.io/coupa/classification-system/`
- **Interactive Demo:** `https://YOUR_USERNAME.github.io/coupa/classification-system/demo.html`
- **Business Case:** `https://YOUR_USERNAME.github.io/coupa/classification-system/business-case.html`
- **Technical Spec:** `https://YOUR_USERNAME.github.io/coupa/classification-system/technical-spec.html`

---

## Presentation Tips

### For Executive Presentation

**Share this link:**
```
https://YOUR_USERNAME.github.io/coupa/classification-system/
```

**Flow:**
1. Show executive overview (main stats, capabilities)
2. Click **"Launch Demo"** button (big green button)
3. Demonstrate interactive filtering, confidence scores
4. Click "View Suggestions" on a "Needs Review" invoice
5. Click "Approve" on an admin alert
6. Navigate to Business Case for ROI details

### For Development Team

**Share this link:**
```
https://YOUR_USERNAME.github.io/coupa/classification-system/technical-spec.html
```

Discuss:
- Tech stack
- Project structure
- Database schema
- API contracts
- Testing strategy

### For Finance Team (End Users)

**Share this link:**
```
https://YOUR_USERNAME.github.io/coupa/classification-system/user-guide.html
```

Walk through:
- How to review classifications
- Understanding confidence scores
- Making corrections
- Feedback loop

---

## Customization

### Add Your Company Logo

Edit `index.html` and add at line 45 (inside `<header>`):

```html
<img src="path/to/your-logo.png" alt="Company Logo" style="height: 50px; margin-bottom: 15px;">
```

### Change Brand Colors

Edit CSS variables in each HTML file (top of `<style>` section):

```css
/* Change purple gradient to your brand colors */
background: linear-gradient(135deg, #YOUR_COLOR_1 0%, #YOUR_COLOR_2 100%);
```

### Update Company-Specific Data

In `demo.html`, modify the `mockInvoices` array (line ~150) to use your actual:
- Supplier names
- Invoice numbers
- Activity codes
- Dollar amounts

---

## Troubleshooting

### Site Not Loading?

1. Check GitHub Pages is enabled (Settings → Pages)
2. Verify branch is `main` and folder is `/docs`
3. Wait 2-3 minutes for initial deployment
4. Check for any build errors in Settings → Pages

### Demo Not Working?

1. Open browser console (F12)
2. Check for JavaScript errors
3. Ensure you're viewing over `https://` (not `file://`)

### Links Broken?

If internal links don't work, check:
- All HTML files are in same directory
- Relative paths are correct (e.g., `href="demo.html"` not `href="/demo.html"`)

---

## Offline Presentation

If you need to present without internet:

1. **Download the entire folder:**
   ```bash
   cd /home/slach/Projects/coupa/docs
   zip -r classification-docs.zip classification-system/
   ```

2. **Unzip on presentation machine**

3. **Open `index.html` in browser**
   - All files work offline (no external dependencies)
   - Demo is fully client-side JavaScript

---

## Sharing Links

### Executive Email Template

```
Subject: Activity Code Classification System - Executive Review

Hi [Name],

I'd like to share our proposal for automating activity code classification for Coupa invoices.

📊 Executive Overview: https://YOUR_USERNAME.github.io/coupa/classification-system/
🎯 Interactive Demo: https://YOUR_USERNAME.github.io/coupa/classification-system/demo.html

Key highlights:
• 95%+ time savings (months → hours)
• 343% first-year ROI ($138K annual savings)
• 60%+ auto-assignment rate with 95%+ accuracy

The interactive demo shows exactly how the system will work with realistic sample data.

Looking forward to your feedback!
```

### Development Team Email Template

```
Subject: Activity Code Classification - Technical Spec & Implementation Plan

Team,

Please review the technical specification for the new classification system:

🔧 Technical Spec: https://YOUR_USERNAME.github.io/coupa/classification-system/technical-spec.html
📋 Implementation Plan: https://YOUR_USERNAME.github.io/coupa/classification-system/implementation-plan.html
🏗️ Deployment Options: https://YOUR_USERNAME.github.io/coupa/classification-system/deployment-options.html

Tech stack: Python 3.10+, Pydantic, RapidFuzz, SQLAlchemy, SQLite
Timeline: 5-week phased rollout
Estimated effort: 1 backend developer full-time

Review and let me know if you have questions for the kickoff meeting.
```

---

## Next Steps

1. ✅ Commit & push to GitHub
2. ✅ Enable GitHub Pages
3. ✅ Test all links work
4. ✅ Customize with company branding (optional)
5. ✅ Share appropriate links with stakeholders
6. ✅ Demo in executive meeting
7. ✅ Get approval to proceed
8. 🚀 Start Week 1 development!

---

**Questions?** Check the main [README.md](README.md) for documentation structure and usage guide.
