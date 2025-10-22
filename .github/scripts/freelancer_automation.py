#!/usr/bin/env python3
"""
Freelancer Platform Automation System
Scrapes freelance job platforms, matches to your profile, and sends proposals

Supports: Upwork, Fiverr, Freelancer.com, Toptal, PeoplePerHour
"""

import os
import json
import time
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import argparse
import re

# ============================================================================
# CONFIGURATION
# ============================================================================

class FreelancerConfig:
    """Configuration for freelancer automation"""
    
    # Your profile/expertise
    YOUR_SKILLS = [
        "Python", "Machine Learning", "Data Science", "AI",
        "Django", "Flask", "FastAPI", "PostgreSQL",
        "AWS", "Docker", "Kubernetes", "CI/CD",
        "Web Scraping", "API Development", "Automation"
    ]
    
    YOUR_SERVICES = {
        "Web Scraping & Data Extraction": {
            "description": "Expert web scraping with Python (BeautifulSoup, Scrapy, Selenium)",
            "rate": "$50-100/hour",
            "delivery": "1-3 days for most projects"
        },
        "Machine Learning & AI Solutions": {
            "description": "Custom ML models, NLP, computer vision, predictive analytics",
            "rate": "$75-150/hour",
            "delivery": "1-2 weeks depending on complexity"
        },
        "API Development & Integration": {
            "description": "RESTful APIs, FastAPI, Django REST, third-party integrations",
            "rate": "$60-120/hour",
            "delivery": "3-7 days for typical projects"
        },
        "Automation & Workflow Development": {
            "description": "Business process automation, GitHub Actions, scheduled tasks",
            "rate": "$50-100/hour",
            "delivery": "2-5 days"
        },
        "Full-Stack Web Development": {
            "description": "Django, React, Vue.js, modern web applications",
            "rate": "$60-120/hour",
            "delivery": "2-4 weeks for complete applications"
        }
    }
    
    # Email settings
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    EMAIL_ADDRESS = os.getenv('FREELANCER_EMAIL', 'your.email@gmail.com')
    EMAIL_PASSWORD = os.getenv('FREELANCER_EMAIL_PASSWORD', '')
    
    # IMAP settings for reading emails from freelancer folder
    IMAP_HOST = os.getenv('IMAP_HOST', 'imap.gmail.com')
    IMAP_PORT = int(os.getenv('IMAP_PORT', 993))
    IMAP_FOLDER = 'freelancer'  # Gmail label/folder
    
    # Matching thresholds
    MIN_SKILL_MATCH = 2  # Minimum matching skills
    MIN_MATCH_SCORE = 60  # Minimum match percentage
    
    # Rate limiting
    DELAY_BETWEEN_REQUESTS = 3  # seconds
    MAX_PROPOSALS_PER_DAY = 10


# ============================================================================
# EMAIL EXTRACTOR FROM GMAIL FOLDER
# ============================================================================

class GmailFreelancerExtractor:
    """Extract emails from Gmail freelancer folder"""
    
    def __init__(self, email_address: str, password: str, folder: str = 'freelancer'):
        self.email_address = email_address
        self.password = password
        self.folder = folder
        self.imap = None
    
    def connect(self):
        """Connect to Gmail IMAP"""
        try:
            self.imap = imaplib.IMAP4_SSL(FreelancerConfig.IMAP_HOST, 
                                         FreelancerConfig.IMAP_PORT)
            self.imap.login(self.email_address, self.password)
            print(f"✅ Connected to Gmail: {self.email_address}")
            return True
        except Exception as e:
            print(f"❌ Gmail connection failed: {e}")
            return False
    
    def extract_freelancer_emails(self, days_back: int = 30) -> List[Dict]:
        """
        Extract emails from freelancer folder
        
        Args:
            days_back: How many days back to search
        
        Returns:
            List of email dictionaries with extracted job information
        """
        if not self.imap:
            if not self.connect():
                return []
        
        try:
            # Select freelancer folder
            # Gmail uses [Gmail]/Label-Name format
            status, messages = self.imap.select(f'[Gmail]/{self.folder}')
            
            if status != 'OK':
                # Try without [Gmail] prefix
                status, messages = self.imap.select(self.folder)
            
            if status != 'OK':
                print(f"❌ Could not select folder: {self.folder}")
                return []
            
            print(f"✅ Selected folder: {self.folder}")
            
            # Search for emails from last N days
            date_since = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            status, message_ids = self.imap.search(None, f'(SINCE {date_since})')
            
            if status != 'OK':
                print("❌ Search failed")
                return []
            
            email_ids = message_ids[0].split()
            print(f"📧 Found {len(email_ids)} emails in last {days_back} days")
            
            extracted_jobs = []
            
            for email_id in email_ids:
                try:
                    # Fetch email
                    status, msg_data = self.imap.fetch(email_id, '(RFC822)')
                    
                    if status != 'OK':
                        continue
                    
                    # Parse email
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # Extract job information
                    job = self._extract_job_from_email(msg)
                    
                    if job:
                        extracted_jobs.append(job)
                
                except Exception as e:
                    print(f"⚠️  Error processing email {email_id}: {e}")
                    continue
            
            print(f"✅ Extracted {len(extracted_jobs)} job opportunities")
            return extracted_jobs
            
        except Exception as e:
            print(f"❌ Error extracting emails: {e}")
            return []
    
    def _extract_job_from_email(self, msg) -> Optional[Dict]:
        """Extract job details from email message"""
        try:
            subject = msg.get('Subject', '')
            from_addr = msg.get('From', '')
            date_str = msg.get('Date', '')
            
            # Get email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Extract job information using patterns
            job_data = {
                'id': f"email-{int(time.time())}",
                'title': self._extract_title(subject, body),
                'description': body[:1000],  # First 1000 chars
                'client_email': self._extract_email(from_addr),
                'platform': self._detect_platform(from_addr, subject, body),
                'url': self._extract_url(body),
                'budget': self._extract_budget(body),
                'deadline': self._extract_deadline(body),
                'skills_required': self._extract_skills(body),
                'received_date': date_str,
                'source': 'gmail_folder',
                'raw_subject': subject,
                'raw_body': body
            }
            
            return job_data
            
        except Exception as e:
            print(f"⚠️  Error extracting job data: {e}")
            return None
    
    def _extract_title(self, subject: str, body: str) -> str:
        """Extract job title from subject or body"""
        # Common patterns in freelancer emails
        patterns = [
            r'Job Title:\s*(.+?)(?:\n|$)',
            r'Project:\s*(.+?)(?:\n|$)',
            r'Looking for:\s*(.+?)(?:\n|$)',
            r'Need help with:\s*(.+?)(?:\n|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback to subject
        return subject.strip()
    
    def _extract_email(self, from_addr: str) -> str:
        """Extract email address from From field"""
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_addr)
        return match.group(0) if match else from_addr
    
    def _detect_platform(self, from_addr: str, subject: str, body: str) -> str:
        """Detect which freelancer platform the email is from"""
        text = f"{from_addr} {subject} {body}".lower()
        
        if 'upwork' in text:
            return 'upwork'
        elif 'fiverr' in text:
            return 'fiverr'
        elif 'freelancer' in text:
            return 'freelancer'
        elif 'toptal' in text:
            return 'toptal'
        elif 'peopleperhour' in text:
            return 'peopleperhour'
        elif 'guru' in text:
            return 'guru'
        else:
            return 'unknown'
    
    def _extract_url(self, body: str) -> Optional[str]:
        """Extract job URL from body"""
        urls = re.findall(r'https?://[^\s<>"]+', body)
        
        # Filter for likely job URLs
        for url in urls:
            if any(platform in url.lower() for platform in 
                   ['upwork.com/jobs', 'fiverr.com/gigs', 'freelancer.com/projects']):
                return url
        
        return urls[0] if urls else None
    
    def _extract_budget(self, body: str) -> Optional[str]:
        """Extract budget from body"""
        patterns = [
            r'Budget:\s*\$?([\d,]+(?:\.\d{2})?)',
            r'Rate:\s*\$?([\d,]+(?:\.\d{2})?)',
            r'Price:\s*\$?([\d,]+(?:\.\d{2})?)',
            r'\$[\d,]+(?:\.\d{2})?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_deadline(self, body: str) -> Optional[str]:
        """Extract deadline from body"""
        patterns = [
            r'Deadline:\s*(.+?)(?:\n|$)',
            r'Due date:\s*(.+?)(?:\n|$)',
            r'Needed by:\s*(.+?)(?:\n|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_skills(self, body: str) -> List[str]:
        """Extract required skills from body"""
        skills = []
        
        # Check for common skill keywords
        for skill in FreelancerConfig.YOUR_SKILLS:
            if skill.lower() in body.lower():
                skills.append(skill)
        
        return skills
    
    def close(self):
        """Close IMAP connection"""
        if self.imap:
            self.imap.close()
            self.imap.logout()
            print("✅ Disconnected from Gmail")


# ============================================================================
# FREELANCER PLATFORM SCRAPERS
# ============================================================================

class FreelancerPlatformScraper:
    """Base scraper for freelancer platforms"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.jobs = []
    
    def search_jobs(self, keywords: List[str], max_results: int = 20) -> List[Dict]:
        """Search for jobs - to be implemented by subclasses"""
        raise NotImplementedError
    
    def match_job_to_profile(self, job: Dict) -> Dict:
        """
        Match job to your profile and calculate score
        
        Returns:
            Dictionary with match_score, matching_skills, and matched_services
        """
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        required_skills = job.get('skills_required', [])
        
        full_text = f"{title} {description} {' '.join(required_skills)}".lower()
        
        # Calculate skill matches
        matching_skills = []
        for skill in FreelancerConfig.YOUR_SKILLS:
            if skill.lower() in full_text:
                matching_skills.append(skill)
        
        # Calculate service matches
        matched_services = []
        for service_name, service_info in FreelancerConfig.YOUR_SERVICES.items():
            service_keywords = service_name.lower().split()
            if any(keyword in full_text for keyword in service_keywords):
                matched_services.append(service_name)
        
        # Calculate match score (0-100)
        skill_score = (len(matching_skills) / len(FreelancerConfig.YOUR_SKILLS)) * 60
        service_score = (len(matched_services) / len(FreelancerConfig.YOUR_SERVICES)) * 40
        match_score = min(100, skill_score + service_score)
        
        return {
            'match_score': round(match_score, 2),
            'matching_skills': matching_skills,
            'matched_services': matched_services,
            'meets_threshold': (
                len(matching_skills) >= FreelancerConfig.MIN_SKILL_MATCH and
                match_score >= FreelancerConfig.MIN_MATCH_SCORE
            )
        }


class UpworkScraper(FreelancerPlatformScraper):
    """Scraper for Upwork (requires RSS feed or API)"""
    
    def __init__(self):
        super().__init__()
        self.rss_url = "https://www.upwork.com/ab/feed/jobs/rss"
    
    def search_jobs(self, keywords: List[str], max_results: int = 20) -> List[Dict]:
        """Search Upwork via RSS feed"""
        print("🔍 Searching Upwork...")
        
        params = {
            'q': ' '.join(keywords),
            'sort': 'recency'
        }
        
        try:
            response = self.session.get(self.rss_url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'xml')
            items = soup.find_all('item')
            
            jobs = []
            for item in items[:max_results]:
                job = {
                    'id': item.find('guid').text if item.find('guid') else '',
                    'title': item.find('title').text if item.find('title') else '',
                    'description': item.find('description').text if item.find('description') else '',
                    'url': item.find('link').text if item.find('link') else '',
                    'posted_date': item.find('pubDate').text if item.find('pubDate') else '',
                    'platform': 'upwork',
                    'budget': self._extract_budget(item),
                    'skills_required': self._extract_skills(item)
                }
                jobs.append(job)
            
            self.jobs.extend(jobs)
            print(f"✅ Found {len(jobs)} Upwork jobs")
            return jobs
            
        except Exception as e:
            print(f"❌ Upwork search failed: {e}")
            return []
    
    def _extract_budget(self, item) -> Optional[str]:
        """Extract budget from RSS item"""
        description = item.find('description').text if item.find('description') else ''
        match = re.search(r'\$[\d,]+(?:\.\d{2})?', description)
        return match.group(0) if match else None
    
    def _extract_skills(self, item) -> List[str]:
        """Extract skills from RSS item"""
        description = item.find('description').text if item.find('description') else ''
        skills = []
        
        for skill in FreelancerConfig.YOUR_SKILLS:
            if skill.lower() in description.lower():
                skills.append(skill)
        
        return skills


class FiverrScraper(FreelancerPlatformScraper):
    """Scraper for Fiverr buyer requests"""
    
    def search_jobs(self, keywords: List[str], max_results: int = 20) -> List[Dict]:
        """Note: Fiverr doesn't have public job listings - uses buyer requests"""
        print("ℹ️  Fiverr uses buyer requests (requires login)")
        return []


# ============================================================================
# PROPOSAL GENERATOR & EMAIL SENDER
# ============================================================================

class FreelancerProposalSender:
    """Generate and send proposals to clients"""
    
    def __init__(self, email_address: str, email_password: str):
        self.email_address = email_address
        self.email_password = email_password
        self.proposals_sent = 0
    
    def generate_proposal(self, job: Dict, match_data: Dict) -> str:
        """
        Generate personalized proposal based on job and match data
        
        Args:
            job: Job dictionary
            match_data: Match analysis data
        
        Returns:
            Proposal text
        """
        title = job.get('title', 'your project')
        matched_services = match_data.get('matched_services', [])
        matching_skills = match_data.get('matching_skills', [])
        
        # Build proposal
        proposal = f"""Hello!

I'm excited about your project: "{title}"

RELEVANT EXPERTISE:
"""
        
        # Add matched services
        for service_name in matched_services:
            service_info = FreelancerConfig.YOUR_SERVICES.get(service_name, {})
            proposal += f"""
• {service_name}
  {service_info.get('description', '')}
  Rate: {service_info.get('rate', 'Negotiable')}
  Typical Delivery: {service_info.get('delivery', 'Flexible')}
"""
        
        proposal += f"""
MATCHING SKILLS:
{', '.join(matching_skills)}

WHY CHOOSE ME:
✓ 5+ years of professional experience
✓ Strong portfolio of successful projects
✓ Clear communication and regular updates
✓ Quality code with documentation
✓ On-time delivery guaranteed

I'd love to discuss your project in detail. When would be a good time for a brief call?

Best regards,
[Your Name]

Portfolio: [Your Website]
LinkedIn: [Your LinkedIn]
"""
        
        return proposal
    
    def send_proposal_email(self, job: Dict, proposal: str, to_email: str) -> bool:
        """
        Send proposal email to client
        
        Args:
            job: Job dictionary
            proposal: Proposal text
            to_email: Client email address
        
        Returns:
            True if sent successfully
        """
        if self.proposals_sent >= FreelancerConfig.MAX_PROPOSALS_PER_DAY:
            print(f"⚠️  Daily proposal limit reached ({FreelancerConfig.MAX_PROPOSALS_PER_DAY})")
            return False
        
        try:
            # Create email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Proposal: {job.get('title', 'Your Project')}"
            msg['From'] = self.email_address
            msg['To'] = to_email
            
            # Add proposal as plain text
            text_part = MIMEText(proposal, 'plain')
            msg.attach(text_part)
            
            # Send email
            with smtplib.SMTP(FreelancerConfig.SMTP_HOST, FreelancerConfig.SMTP_PORT) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            self.proposals_sent += 1
            print(f"✅ Proposal sent to {to_email} ({self.proposals_sent}/{FreelancerConfig.MAX_PROPOSALS_PER_DAY})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send proposal: {e}")
            return False
    
    def send_summary_email(self, matched_jobs: List[Dict], proposals_sent: int):
        """Send daily summary email to yourself"""
        try:
            summary = f"""FREELANCER AUTOMATION DAILY SUMMARY
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

STATISTICS:
• Total jobs analyzed: {len(matched_jobs)}
• Proposals sent: {proposals_sent}
• Daily limit: {FreelancerConfig.MAX_PROPOSALS_PER_DAY}

TOP MATCHES:
"""
            
            # Sort by match score
            top_matches = sorted(matched_jobs, 
                               key=lambda x: x.get('match_score', 0), 
                               reverse=True)[:10]
            
            for i, job in enumerate(top_matches, 1):
                summary += f"""
{i}. {job.get('title', 'Untitled')}
   Platform: {job.get('platform', 'Unknown')}
   Match Score: {job.get('match_score', 0)}%
   Budget: {job.get('budget', 'Not specified')}
   URL: {job.get('url', 'N/A')}
"""
            
            # Send to yourself
            msg = MIMEText(summary, 'plain')
            msg['Subject'] = f"Freelancer Automation Summary - {datetime.now().strftime('%Y-%m-%d')}"
            msg['From'] = self.email_address
            msg['To'] = self.email_address
            
            with smtplib.SMTP(FreelancerConfig.SMTP_HOST, FreelancerConfig.SMTP_PORT) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            print("✅ Summary email sent to yourself")
            
        except Exception as e:
            print(f"❌ Failed to send summary: {e}")


# ============================================================================
# MAIN AUTOMATION WORKFLOW
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Freelancer Platform Automation'
    )
    parser.add_argument(
        '--mode',
        choices=['gmail', 'scrape', 'both'],
        default='both',
        help='Mode: gmail (extract from folder), scrape (scrape platforms), or both'
    )
    parser.add_argument(
        '--send-proposals',
        action='store_true',
        help='Actually send proposals (default: dry-run)'
    )
    parser.add_argument(
        '--keywords',
        nargs='+',
        default=['python', 'automation', 'web scraping', 'api'],
        help='Keywords to search'
    )
    parser.add_argument(
        '--days-back',
        type=int,
        default=7,
        help='Days back to search Gmail folder'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='matched_freelancer_jobs.json',
        help='Output file for matched jobs'
    )
    
    args = parser.parse_args()
    
    # Validate email credentials
    email_address = FreelancerConfig.EMAIL_ADDRESS
    email_password = FreelancerConfig.EMAIL_PASSWORD
    
    if not email_password:
        print("❌ Error: Email password not set")
        print("   Set FREELANCER_EMAIL_PASSWORD environment variable")
        return 1
    
    all_jobs = []
    
    # ========================================================================
    # STEP 1: Extract from Gmail freelancer folder
    # ========================================================================
    if args.mode in ['gmail', 'both']:
        print("\n" + "="*80)
        print("STEP 1: EXTRACTING FROM GMAIL FREELANCER FOLDER")
        print("="*80)
        
        extractor = GmailFreelancerExtractor(
            email_address=email_address,
            password=email_password,
            folder='freelancer'
        )
        
        gmail_jobs = extractor.extract_freelancer_emails(days_back=args.days_back)
        all_jobs.extend(gmail_jobs)
        extractor.close()
    
    # ========================================================================
    # STEP 2: Scrape freelancer platforms
    # ========================================================================
    if args.mode in ['scrape', 'both']:
        print("\n" + "="*80)
        print("STEP 2: SCRAPING FREELANCER PLATFORMS")
        print("="*80)
        
        # Upwork
        upwork = UpworkScraper()
        upwork_jobs = upwork.search_jobs(args.keywords, max_results=20)
        all_jobs.extend(upwork_jobs)
        
        time.sleep(FreelancerConfig.DELAY_BETWEEN_REQUESTS)
    
    # ========================================================================
    # STEP 3: Match jobs to your profile
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 3: MATCHING JOBS TO YOUR PROFILE")
    print("="*80)
    
    scraper = FreelancerPlatformScraper()
    matched_jobs = []
    
    for job in all_jobs:
        match_data = scraper.match_job_to_profile(job)
        job.update(match_data)
        
        if match_data['meets_threshold']:
            matched_jobs.append(job)
            print(f"✅ MATCH ({match_data['match_score']}%): {job.get('title', 'Untitled')[:60]}")
        else:
            print(f"❌ Skip ({match_data['match_score']}%): {job.get('title', 'Untitled')[:60]}")
    
    print(f"\n📊 Total jobs analyzed: {len(all_jobs)}")
    print(f"✅ Matched jobs: {len(matched_jobs)}")
    
    # ========================================================================
    # STEP 4: Generate and send proposals
    # ========================================================================
    if args.send_proposals and matched_jobs:
        print("\n" + "="*80)
        print("STEP 4: SENDING PROPOSALS")
        print("="*80)
        
        sender = FreelancerProposalSender(email_address, email_password)
        proposals_sent = 0
        
        for job in sorted(matched_jobs, key=lambda x: x.get('match_score', 0), reverse=True):
            client_email = job.get('client_email')
            
            if not client_email:
                print(f"⚠️  No client email for: {job.get('title')}")
                continue
            
            # Generate proposal
            proposal = sender.generate_proposal(job, job)
            
            print(f"\n📝 Proposal for: {job.get('title')}")
            print(f"   Client: {client_email}")
            print(f"   Match Score: {job.get('match_score')}%")
            
            # Send proposal
            if sender.send_proposal_email(job, proposal, client_email):
                proposals_sent += 1
            
            time.sleep(FreelancerConfig.DELAY_BETWEEN_REQUESTS)
        
        # Send summary email
        sender.send_summary_email(matched_jobs, proposals_sent)
    
    # ========================================================================
    # STEP 5: Save results
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 5: SAVING RESULTS")
    print("="*80)
    
    output_data = {
        'generated_at': datetime.now().isoformat(),
        'total_jobs': len(all_jobs),
        'matched_jobs': len(matched_jobs),
        'jobs': matched_jobs
    }
    
    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✅ Results saved to: {args.output}")
    
    print("\n" + "="*80)
    print("AUTOMATION COMPLETE!")
    print("="*80)
    
    return 0


if __name__ == '__main__':
    exit(main())
