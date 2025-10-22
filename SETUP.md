# ⚙️ Complete Setup Guide

Detailed instructions for setting up your automated freelancer opportunity finder.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Gmail Setup](#gmail-setup)
3. [GitHub Repository Setup](#github-repository-setup)
4. [GitHub Secrets Configuration](#github-secrets-configuration)
5. [Customization](#customization)
6. [First Run](#first-run)
7. [Scheduling](#scheduling)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Configuration](#advanced-configuration)

---

## 📦 Prerequisites

Before you begin, make sure you have:

- ✅ GitHub account
- ✅ Gmail account (or other email provider)
- ✅ Basic familiarity with GitHub (or willingness to learn!)
- ✅ 15 minutes of setup time

**No coding experience required!**

---

## 📧 Gmail Setup

### Step 1: Enable 2-Factor Authentication

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Find "2-Step Verification"
3. Click "Get Started" and follow the prompts
4. Verify using your phone

**Why?** Gmail requires 2FA to create app passwords.

### Step 2: Create App Password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Sign in again if prompted
3. Under "Select app" choose: **Mail**
4. Under "Select device" choose: **Other (Custom name)**
5. Enter name: **Freelancer Finder**
6. Click **Generate**

You'll see a 16-character password like: abcd efgh ijkl mnop

⚠️ **IMPORTANT:**
- Copy this password immediately
- Remove the spaces: `abcdefghijklmnop`
- Save it securely (you won't see it again!)
- This is what you'll use as `FREELANCER_PASSWORD`

### Step 3: Verify Email Settings

**For Gmail:**
- IMAP Host: `imap.gmail.com`
- IMAP Port: `993`
- SMTP Host: `smtp.gmail.com`
- SMTP Port: `587`

**For Other Providers:**

**Outlook/Hotmail:**

---

## 🐙 GitHub Repository Setup

### Option 1: Clone This Repository (Recommended)

1. Click "Fork" button (top right of GitHub page)
2. Name your fork: `freelance-services` or similar
3. Click "Create fork"

### Option 2: Create New Repository

1. Go to [github.com/new](https://github.com/new)
2. Name: `freelance-services` (or your choice)
3. Visibility: **Private** recommended (to protect your data)
4. Initialize with README: Yes
5. Click "Create repository"

### Option 3: Use Existing Repository

If you already have a repository, just add the files:

1. Upload `freelancer_finder.py`
2. Create `.github/workflows/` folder
3. Upload `freelancer-finder.yml` to that folder
4. Upload `requirements.txt`

---

## 🔐 GitHub Secrets Configuration

Secrets keep your passwords safe and encrypted.

### How to Add Secrets

1. **Go to your repository on GitHub**

2. **Click:** Settings (top menu)

3. **Click:** Secrets and variables → Actions (left sidebar)

4. **Click:** "New repository secret" (green button)

5. **Add each secret:**

### Secret #1: FREELANCER_EMAIL

Name: FREELANCER_EMAIL
Secret: your.email@gmail.com
(Your actual Gmail address)

### Secret #2: FREELANCER_PASSWORD
Name: FREELANCER_PASSWORD
Secret: abcdefghijklmnop
(The 16-character app password from Step 2, no spaces!)

### Secret #3: IMAP_HOST
Name: IMAP_HOST
Secret: imap.gmail.com
(Or your email provider's IMAP server)

### Secret #4: IMAP_PORT
Name: IMAP_PORT
Secret: 993
(Standard IMAP SSL port)

### Secret #5: SMTP_HOST
Name: SMTP_HOST
Secret: smtp.gmail.com
(Or your email provider's SMTP server)

### Secret #6: SMTP_PORT
Name: SMTP_PORT
Secret: 587

(Standard SMTP TLS port)

### Verification Checklist

After adding all secrets, verify:
- [ ] All 6 secrets are listed
- [ ] Names are exactly as shown (case-sensitive!)
- [ ] No extra spaces in values
- [ ] Password is 16 characters, no spaces

---

## ⚙️ Customization

### Customize Your Skills

Edit `freelancer_finder.py` to match your skills:

**Find this section (around line 25):**
```python
YOUR_SKILLS = [
    # Core Programming
    "Python", "JavaScript", "TypeScript", "Go", "Rust",
    
    # Web Development
    "Django", "Flask", "FastAPI", "React", "Vue.js", "Node.js",
    
    # ... more skills
]

Tips for customizing:

1. Remove skills you don't have:

# Don't know Rust? Remove it:
"Python", "JavaScript", "TypeScript", "Go",  # Removed "Rust"

2. Add skills you have:

# Add your specific skills:
"Angular", "Svelte", "Laravel", "Ruby on Rails",

3. Be specific:

# Instead of just "Database":
"PostgreSQL", "MongoDB", "MySQL", "Redis"

4. Include tools and frameworks:

# Not just languages:
"Docker", "Kubernetes", "AWS", "GitHub Actions"

Example Profiles
Web Developer:
pythonYOUR_SKILLS = [
    "JavaScript", "TypeScript", "React", "Next.js", "Node.js",
    "HTML", "CSS", "Tailwind CSS", "MongoDB", "PostgreSQL",
    "REST APIs", "GraphQL", "Git", "Docker", "AWS"
]
Data Scientist:
pythonYOUR_SKILLS = [
    "Python", "Pandas", "NumPy", "Scikit-learn",
    "TensorFlow", "PyTorch", "Machine Learning", "Deep Learning",
    "Data Visualization", "SQL", "Statistics", "Jupyter"
]
DevOps Engineer:
pythonYOUR_SKILLS = [
    "Docker", "Kubernetes", "AWS", "Azure", "GCP",
    "Terraform", "Ansible", "CI/CD", "GitHub Actions",
    "Linux", "Bash", "Python", "Monitoring", "Prometheus"
]

Adjust Match Threshold
Find this line (around line 50):
pythonMIN_MATCH_SCORE = 60  # Minimum match percentage
Adjust based on your needs:
pythonMIN_MATCH_SCORE = 70  # Fewer, higher quality matches
MIN_MATCH_SCORE = 50  # More matches, lower threshold
MIN_MATCH_SCORE = 80  # Very selective, only best matches

🏃 First Run
🏃 First Run
Run Manually First (Recommended)

Go to: Actions tab in your repository
Click: "Freelancer Opportunity Finder" (left sidebar)
Click: "Run workflow" (right side, blue button)
Configure (optional):

Days back: 7 (how many days of Gmail to search)
Keywords: python,automation,api (comma-separated)
Skip email: unchecked (to receive email)


Click: "Run workflow" (green button)

What Happens Next
The workflow will:

✅ Install dependencies (30 seconds)
✅ Connect to Gmail (10 seconds)
✅ Scrape platforms (1-2 minutes)
✅ Match opportunities (30 seconds)
✅ Send email report (10 seconds)

Total time: 2-3 minutes
Check Results
**In GitHub:</h3>

Green checkmark = Success! ✅
Red X = Failed (see Troubleshooting)
Click the workflow run to see detailed logs

In Your Email:

Check inbox for "🎯 Freelance Opportunities + Business Model Insights"
Check spam folder if not there
Email arrives within 2-3 minutes of workflow completion


📅 Scheduling
Default Schedule
The workflow runs automatically:

9:00 AM UTC (Morning scan)
5:00 PM UTC (Evening scan)

Convert to Your Timezone
Examples:

UTC 9:00 = 4:00 AM EST = 1:00 AM PST
UTC 17:00 = 12:00 PM EST = 9:00 AM PST

Change Schedule
Edit .github/workflows/freelancer-finder.yml:
Find this section:
yamlon:
  schedule:
    - cron: '0 9,17 * * *'  # 9 AM and 5 PM UTC
Change to your preferred times:
yaml# 8 AM and 8 PM UTC:
- cron: '0 8,20 * * *'

# Every 6 hours:
- cron: '0 */6 * * *'

# Only once per day at noon UTC:
- cron: '0 12 * * *'

# Three times: morning, noon, evening:
- cron: '0 6,12,18 * * *'
Cron syntax:
*    *    *    *    *
│    │    │    │    │
│    │    │    │    └─ Day of week (0-7, both 0 and 7 are Sunday)
│    │    │    └────── Month (1-12)
│    │    └─────────── Day of month (1-31)
│    └──────────────── Hour (0-23)
└───────────────────── Minute (0-59)
Use crontab.guru to generate schedules!

🐛 Troubleshooting
"❌ Gmail connection failed"
Possible causes:

App password incorrect
2FA not enabled
IMAP/SMTP settings wrong
Secrets not set correctly

Solutions:

Verify app password:

Re-generate at myaccount.google.com/apppasswords
Ensure no spaces: abcdefghijklmnop
Update FREELANCER_PASSWORD secret


Check 2FA:

Must be enabled for app passwords
Enable at myaccount.google.com/security


Verify secrets:

Settings → Secrets → Actions
All 6 secrets present?
Names exactly right (case-sensitive)?


Test locally:

python   python freelancer_finder.py --skip-email
"No opportunities found"
Possible causes:

Skills too specific/narrow
Match threshold too high
Platforms temporarily down
Keywords not matching jobs

Solutions:

Broaden skills:

python   # Add more related skills
   YOUR_SKILLS = ["Python", "JavaScript", "APIs", "Automation", ...]

Lower threshold:

python   MIN_MATCH_SCORE = 50  # Was 60

Add more keywords:

   Keywords: python,javascript,web,api,automation,data,ml

Check workflow logs:

Actions → Click failed run → See what platforms succeeded



"Workflow failed"
Check the error logs:

Go to Actions tab
Click the failed workflow run
Click the failed job
Expand the failed step
Read the error message

Common errors:
Import Error:
ModuleNotFoundError: No module named 'requests'
Solution: Check requirements.txt exists and has:
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
Syntax Error:
SyntaxError: invalid syntax
Solution: Check freelancer_finder.py for typos if you edited it
Permission Error:
Error: Resource not accessible by integration
Solution: Settings → Actions → General → Workflow permissions → Check "Read and write permissions"
"Not receiving emails"
Solutions:

Check spam folder
Verify FREELANCER_EMAIL secret is correct
Test with skip_email: false in manual run
Check Gmail's "Less secure apps" settings (shouldn't be needed with app passwords)
Run workflow manually with logs:

   Actions → Run workflow → Check logs for "✅ Notification email sent"
"Rate limited by platforms"
If you see many 429 errors:
Solution:

Increase delay between requests:

python   DELAY_BETWEEN_REQUESTS = 5  # Was 3

Reduce max results:

python   MAX_RESULTS_PER_PLATFORM = 20  # Was 30

Run less frequently:

yaml   - cron: '0 12 * * *'  # Once per day

🚀 Advanced Configuration
Add More Keywords
Edit workflow file or pass when running manually:
yamlkeywords:
  description: 'Search keywords (comma-separated)'
  required: true
  default: 'python,javascript,automation,api,machine learning,data science'
Email to Different Address
Keep notifications separate from scraping account:
python#
In freelancer_finder.py, modify send_notification():
notification_email = "your-notifications@gmail.com"

# Different from FREELANCER_EMAIL

Save to Google Sheets

Add this after line 800 in freelancer_finder.py:
python

import gspread
from oauth2client.service_account import ServiceAccountCredentials

def save_to_sheets(opportunities):
    scope = ['https://spreadsheets.google.com/feeds']
    creds = ServiceAccountCredentials.from_json_keyfile_name('creds.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open('Freelance Opportunities').sheet1
    
    for opp in opportunities:
        sheet.append_row([
            opp['title'],
            opp['platform'],
            opp['budget'],
            opp['match_score'],
            opp['url']
        ])

Database Storage

Save to PostgreSQL:
python

import psycopg2

def save_to_database(opportunities):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    for opp in opportunities:
        cur.execute("""
            INSERT INTO opportunities (title, platform, budget, match_score, url, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (url) DO NOTHING
        """, (opp['title'], opp['platform'], opp['budget'], opp['match_score'], opp['url']))
    
    conn.commit()
    cur.close()
    conn.close()


Slack Notifications
Install slack-sdk and add:
python

from slack_sdk import WebClient

def notify_slack(opportunities):
    client = WebClient(token=os.getenv('SLACK_TOKEN'))
    
    message = f"Found {len(opportunities)} new opportunities!"
    for opp in opportunities[:5]:
        message += f"\n• {opp['title']} ({opp['match_score']}%)"
    
    client.chat_postMessage(channel='#jobs', text=message)
    
✅ Post-Setup Checklist
After completing setup:

 All 6 GitHub secrets added correctly
 Skills customized in freelancer_finder.py
 First manual run successful
 Email notification received
 Opportunities show good matches (60%+)
 Schedule set to preferred times
 Added to calendar/reminders to check emails

All done? 🎉 You're all set!

📞 Need Help?
Still stuck? Here's how to get help:

Re-read relevant section above
Check GitHub Actions logs for error messages
Search existing issues in repository
Create new issue with:

What you tried
Error message (copy/paste from logs)
Screenshots if helpful



Average response time: 24-48 hours

🎯 What's Next?
Now that setup is complete:

Let it run for a week to gather data
Review daily emails and apply to top opportunities
Note business model patterns that appear frequently
Tune match threshold based on quality of matches
Build your first productized service based on insights!

The system gets smarter over time. Trust the process!

<div align="center">
🎉 Congratulations on completing the setup!
Questions? Check QUICK_START.md or FAQ
Made with ❤️ for freelancers
</div>
```

📋 Summary
You now have 10 complete files ready to add to your repository:
✅ Core Files (You Already Have)

freelancer_finder.py ✓
.github/workflows/freelancer-finder.yml ✓

📥 Files to Create (From This Artifact)

README.md - Main portfolio & documentation
QUICK_START.md - 5-minute setup guide
SETUP.md - Detailed setup instructions
requirements.txt - Python dependencies
.gitignore - Protected files
services/web-automation.md - Web scraping service page
services/ai-ml-solutions.md - AI/ML service page
services/data-analysis.md - Data analysis service page
portfolio/case-studies.md - Project case studies
portfolio/projects.md - Project showcase
docs/PRICING.md - Pricing guide
docs/FAQ.md - Frequently asked questions


🎯 Quick Action Plan
Today (15 minutes):

✅ Copy README.md to your repository
✅ Copy QUICK_START.md
✅ Create services/ folder and add service files
✅ Update README.md with your actual contact info

This Week:

✅ Complete all service pages with your offerings
✅ Add your real portfolio projects
✅ Customize pricing based on your rates
✅ Run first job finder workflow

This Month:

✅ Build out case studies from past work
✅ Add testimonials (get permission from clients)
✅ Create blog posts if desired
✅ Share your repository/portfolio


Need the individual files? They're all in this artifact above - just copy each section!