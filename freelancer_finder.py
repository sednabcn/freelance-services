#!/usr/bin/env python3
"""
Freelancer Opportunity Finder & Business Model Identifier
Scrapes freelancer platforms, analyzes your Gmail, and identifies:
1. Jobs matching your skills
2. Potential business models you can offer to others
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
from typing import List, Dict, Optional, Set
import requests
from bs4 import BeautifulSoup
import argparse
import re
from collections import Counter

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Configuration for freelancer opportunity finder"""
    
    # YOUR PROFILE - CUSTOMIZE THIS!
    YOUR_SKILLS = [
        # Core Programming
        "Python", "JavaScript", "TypeScript", "Go", "Rust",
        
        # Web Development
        "Django", "Flask", "FastAPI", "React", "Vue.js", "Node.js",
        
        # Data & ML
        "Machine Learning", "Data Science", "Deep Learning", "NLP",
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
        
        # DevOps & Cloud
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "CI/CD",
        "Terraform", "GitHub Actions",
        
        # Databases
        "PostgreSQL", "MongoDB", "Redis", "MySQL", "Elasticsearch",
        
        # Specialized
        "Web Scraping", "API Development", "Automation", "ETL",
        "Computer Vision", "Chatbots", "REST APIs", "GraphQL"
    ]
    
    # Email configuration
    EMAIL = os.getenv('FREELANCER_EMAIL', 'freelancers.automation@gmail.com')
    PASSWORD = os.getenv('FREELANCER_PASSWORD', '')
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    IMAP_HOST = os.getenv('IMAP_HOST', 'imap.gmail.com')
    IMAP_PORT = int(os.getenv('IMAP_PORT', 993))
    
    # Matching thresholds
    MIN_MATCH_SCORE = 60  # Minimum match percentage
    MIN_BUSINESS_POTENTIAL_SCORE = 70  # For business model identification
    
    # Rate limiting
    DELAY_BETWEEN_REQUESTS = 3
    MAX_RESULTS_PER_PLATFORM = 30


# ============================================================================
# EMAIL EXTRACTOR
# ============================================================================

class GmailExtractor:
    """Extract freelancer opportunities from Gmail"""
    
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.imap = None
    
    def connect(self) -> bool:
        """Connect to Gmail IMAP"""
        try:
            self.imap = imaplib.IMAP4_SSL(Config.IMAP_HOST, Config.IMAP_PORT)
            self.imap.login(self.email, self.password)
            print(f"✅ Connected to Gmail: {self.email}")
            return True
        except Exception as e:
            print(f"❌ Gmail connection failed: {e}")
            return False
    
    def extract_opportunities(self, days_back: int = 7) -> List[Dict]:
        """Extract job opportunities from Gmail"""
        if not self.imap and not self.connect():
            return []
        
        try:
            self.imap.select('INBOX')
            
            # Search for emails from freelancer platforms
            date_since = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            
            # Common freelancer platform senders
            senders = [
                'upwork.com', 'fiverr.com', 'freelancer.com',
                'toptal.com', 'guru.com', 'peopleperhour.com',
                'freelance', 'job', 'opportunity', 'project'
            ]
            
            all_opportunities = []
            
            for sender in senders:
                try:
                    status, messages = self.imap.search(
                        None, 
                        f'(SINCE {date_since} OR FROM "{sender}")'
                    )
                    
                    if status == 'OK':
                        email_ids = messages[0].split()
                        for email_id in email_ids[-50:]:  # Last 50 emails per sender
                            try:
                                opportunity = self._parse_email(email_id)
                                if opportunity:
                                    all_opportunities.append(opportunity)
                            except Exception as e:
                                continue
                except Exception as e:
                    continue
            
            # Remove duplicates based on title
            unique_opportunities = {}
            for opp in all_opportunities:
                title = opp.get('title', '')
                if title and title not in unique_opportunities:
                    unique_opportunities[title] = opp
            
            opportunities = list(unique_opportunities.values())
            print(f"📧 Extracted {len(opportunities)} opportunities from Gmail")
            return opportunities
            
        except Exception as e:
            print(f"❌ Error extracting from Gmail: {e}")
            return []
    
    def _parse_email(self, email_id) -> Optional[Dict]:
        """Parse email and extract opportunity details"""
        try:
            status, msg_data = self.imap.fetch(email_id, '(RFC822)')
            if status != 'OK':
                return None
            
            msg = email.message_from_bytes(msg_data[0][1])
            subject = msg.get('Subject', '')
            from_addr = msg.get('From', '')
            date_str = msg.get('Date', '')
            
            # Get body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                        except:
                            continue
            else:
                try:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    body = ""
            
            # Extract details
            title = self._extract_title(subject, body)
            if not title or len(title) < 10:
                return None
            
            return {
                'id': f"email-{email_id.decode()}",
                'title': title,
                'description': body[:2000],
                'platform': self._detect_platform(from_addr, body),
                'url': self._extract_url(body),
                'budget': self._extract_budget(body),
                'skills': self._extract_skills(body),
                'received_date': date_str,
                'source': 'gmail',
                'raw_subject': subject,
                'from': from_addr
            }
            
        except Exception as e:
            return None
    
    def _extract_title(self, subject: str, body: str) -> str:
        """Extract job title"""
        patterns = [
            r'(?:Job|Project|Position):\s*(.+?)(?:\n|$)',
            r'(?:Looking for|Need|Hiring):\s*(.+?)(?:\n|$)',
            r'(?:Title|Role):\s*(.+?)(?:\n|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:100]
        
        # Clean up subject line
        subject = re.sub(r'^(Re:|Fwd:|FW:)\s*', '', subject, flags=re.IGNORECASE)
        return subject.strip()[:100]
    
    def _detect_platform(self, from_addr: str, body: str) -> str:
        """Detect platform"""
        text = f"{from_addr} {body}".lower()
        platforms = {
            'upwork': 'upwork',
            'fiverr': 'fiverr',
            'freelancer': 'freelancer.com',
            'toptal': 'toptal',
            'guru': 'guru',
            'peopleperhour': 'peopleperhour'
        }
        
        for key, value in platforms.items():
            if key in text:
                return value
        
        return 'unknown'
    
    def _extract_url(self, body: str) -> Optional[str]:
        """Extract URL"""
        urls = re.findall(r'https?://[^\s<>"]+', body)
        job_keywords = ['job', 'project', 'gig', 'work', 'freelanc']
        
        for url in urls:
            if any(keyword in url.lower() for keyword in job_keywords):
                return url.split()[0]
        
        return urls[0] if urls else None
    
    def _extract_budget(self, body: str) -> Optional[str]:
        """Extract budget"""
        patterns = [
            r'Budget:\s*\$?([\d,]+(?:-[\d,]+)?)',
            r'\$[\d,]+-\$[\d,]+',
            r'\$[\d,]+(?:\.\d{2})?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_skills(self, body: str) -> List[str]:
        """Extract skills mentioned"""
        body_lower = body.lower()
        found_skills = []
        
        for skill in Config.YOUR_SKILLS:
            if skill.lower() in body_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def close(self):
        """Close connection"""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
            except:
                pass


# ============================================================================
# PLATFORM SCRAPERS
# ============================================================================

class PlatformScraper:
    """Base scraper for freelancer platforms"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def match_to_profile(self, job: Dict) -> Dict:
        """Calculate match score and identify business potential"""
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        skills = job.get('skills', [])
        
        full_text = f"{title} {description} {' '.join(skills)}".lower()
        
        # Calculate skill matches
        matching_skills = []
        for skill in Config.YOUR_SKILLS:
            if skill.lower() in full_text:
                matching_skills.append(skill)
        
        # Calculate match score
        skill_score = (len(matching_skills) / max(len(Config.YOUR_SKILLS), 1)) * 100
        
        # Identify business model potential
        business_potential = self._identify_business_potential(full_text, title)
        
        match_score = min(100, skill_score)
        
        return {
            'match_score': round(match_score, 2),
            'matching_skills': matching_skills,
            'business_potential': business_potential,
            'meets_threshold': match_score >= Config.MIN_MATCH_SCORE
        }
    
    def _identify_business_potential(self, text: str, title: str) -> Dict:
        """Identify if this represents a business model you could offer"""
        
        # Business model patterns
        business_models = {
            'Web Scraping Service': {
                'keywords': ['scraping', 'scrape', 'extract data', 'crawl', 'harvest data'],
                'score': 0,
                'description': 'Automated web scraping and data extraction service'
            },
            'API Integration Platform': {
                'keywords': ['api integration', 'connect apis', 'api development', 'rest api', 'webhook'],
                'score': 0,
                'description': 'API development and integration service'
            },
            'Automation Workflow Builder': {
                'keywords': ['automate', 'automation', 'workflow', 'scheduled task', 'cron job'],
                'score': 0,
                'description': 'Business process automation service'
            },
            'ML/AI Solution Provider': {
                'keywords': ['machine learning', 'ai', 'nlp', 'computer vision', 'prediction', 'classification'],
                'score': 0,
                'description': 'Machine learning and AI model development'
            },
            'Data Pipeline Service': {
                'keywords': ['etl', 'data pipeline', 'data processing', 'data transformation', 'batch processing'],
                'score': 0,
                'description': 'Data pipeline and ETL service'
            },
            'Chatbot Development': {
                'keywords': ['chatbot', 'conversational ai', 'bot development', 'virtual assistant'],
                'score': 0,
                'description': 'Chatbot and conversational AI service'
            },
            'Dashboard & Analytics': {
                'keywords': ['dashboard', 'analytics', 'visualization', 'reporting', 'metrics'],
                'score': 0,
                'description': 'Business intelligence and analytics dashboard'
            },
            'SaaS Product Development': {
                'keywords': ['saas', 'software as a service', 'web application', 'platform', 'multi-tenant'],
                'score': 0,
                'description': 'SaaS product development service'
            }
        }
        
        # Calculate scores for each business model
        for model_name, model_info in business_models.items():
            keyword_matches = sum(1 for keyword in model_info['keywords'] if keyword in text)
            model_info['score'] = (keyword_matches / len(model_info['keywords'])) * 100
        
        # Find best matches
        top_models = sorted(
            business_models.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )[:3]
        
        # Filter models with significant score
        potential_models = [
            {
                'name': name,
                'score': info['score'],
                'description': info['description']
            }
            for name, info in top_models
            if info['score'] >= 30  # At least 30% keyword match
        ]
        
        return {
            'has_potential': len(potential_models) > 0,
            'models': potential_models,
            'best_model': potential_models[0] if potential_models else None
        }


class UpworkRSSScraper(PlatformScraper):
    """Scrape Upwork RSS feed"""
    
    def search_jobs(self, keywords: List[str]) -> List[Dict]:
        """Search Upwork RSS"""
        print("🔍 Searching Upwork RSS feed...")
        
        rss_url = "https://www.upwork.com/ab/feed/jobs/rss"
        params = {'q': ' '.join(keywords), 'sort': 'recency'}
        
        try:
            response = self.session.get(rss_url, params=params, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'xml')
            items = soup.find_all('item')
            
            jobs = []
            for item in items[:Config.MAX_RESULTS_PER_PLATFORM]:
                try:
                    job = {
                        'id': item.find('guid').text if item.find('guid') else '',
                        'title': item.find('title').text if item.find('title') else '',
                        'description': item.find('description').text if item.find('description') else '',
                        'url': item.find('link').text if item.find('link') else '',
                        'posted_date': item.find('pubDate').text if item.find('pubDate') else '',
                        'platform': 'upwork',
                        'budget': self._extract_budget(item),
                        'skills': self._extract_skills(item),
                        'source': 'scraper'
                    }
                    jobs.append(job)
                except:
                    continue
            
            print(f"✅ Found {len(jobs)} Upwork jobs")
            return jobs
            
        except Exception as e:
            print(f"❌ Upwork scraping failed: {e}")
            return []
    
    def _extract_budget(self, item) -> Optional[str]:
        desc = item.find('description').text if item.find('description') else ''
        match = re.search(r'\$[\d,]+(?:-\$[\d,]+)?', desc)
        return match.group(0) if match else None
    
    def _extract_skills(self, item) -> List[str]:
        desc = item.find('description').text if item.find('description') else ''
        return [skill for skill in Config.YOUR_SKILLS if skill.lower() in desc.lower()]


class FreelancerComScraper(PlatformScraper):
    """Scrape Freelancer.com job listings"""
    
    def search_jobs(self, keywords: List[str]) -> List[Dict]:
        """Search Freelancer.com"""
        print("🔍 Searching Freelancer.com...")
        
        base_url = "https://www.freelancer.com/jobs"
        params = {
            'keyword': ' '.join(keywords),
            'status': 'open'
        }
        
        try:
            response = self.session.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('div', class_='JobSearchCard-item')
            
            jobs = []
            for card in job_cards[:Config.MAX_RESULTS_PER_PLATFORM]:
                try:
                    title_elem = card.find('a', class_='JobSearchCard-primary-heading-link')
                    desc_elem = card.find('p', class_='JobSearchCard-primary-description')
                    budget_elem = card.find('div', class_='JobSearchCard-primary-price')
                    
                    if not title_elem:
                        continue
                    
                    job = {
                        'id': f"freelancer-{hash(title_elem.text)}",
                        'title': title_elem.text.strip(),
                        'description': desc_elem.text.strip() if desc_elem else '',
                        'url': f"https://www.freelancer.com{title_elem.get('href', '')}",
                        'posted_date': datetime.now().isoformat(),
                        'platform': 'freelancer.com',
                        'budget': budget_elem.text.strip() if budget_elem else None,
                        'skills': self._extract_skills_from_text(
                            f"{title_elem.text} {desc_elem.text if desc_elem else ''}"
                        ),
                        'source': 'scraper'
                    }
                    jobs.append(job)
                except Exception as e:
                    continue
            
            print(f"✅ Found {len(jobs)} Freelancer.com jobs")
            return jobs
            
        except Exception as e:
            print(f"❌ Freelancer.com scraping failed: {e}")
            return []
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        text_lower = text.lower()
        return [skill for skill in Config.YOUR_SKILLS if skill.lower() in text_lower]


class GuruScraper(PlatformScraper):
    """Scrape Guru.com job listings"""
    
    def search_jobs(self, keywords: List[str]) -> List[Dict]:
        """Search Guru.com"""
        print("🔍 Searching Guru.com...")
        
        base_url = "https://www.guru.com/d/jobs"
        params = {
            'searchTerm': ' '.join(keywords)
        }
        
        try:
            response = self.session.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            job_items = soup.find_all('div', class_='guruJobCard')
            
            jobs = []
            for item in job_items[:Config.MAX_RESULTS_PER_PLATFORM]:
                try:
                    title_elem = item.find('a', class_='jobTitle')
                    desc_elem = item.find('p', class_='jobDescription')
                    budget_elem = item.find('span', class_='budget')
                    
                    if not title_elem:
                        continue
                    
                    job = {
                        'id': f"guru-{hash(title_elem.text)}",
                        'title': title_elem.text.strip(),
                        'description': desc_elem.text.strip() if desc_elem else '',
                        'url': f"https://www.guru.com{title_elem.get('href', '')}",
                        'posted_date': datetime.now().isoformat(),
                        'platform': 'guru',
                        'budget': budget_elem.text.strip() if budget_elem else None,
                        'skills': self._extract_skills_from_text(
                            f"{title_elem.text} {desc_elem.text if desc_elem else ''}"
                        ),
                        'source': 'scraper'
                    }
                    jobs.append(job)
                except:
                    continue
            
            print(f"✅ Found {len(jobs)} Guru jobs")
            return jobs
            
        except Exception as e:
            print(f"❌ Guru scraping failed: {e}")
            return []
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        text_lower = text.lower()
        return [skill for skill in Config.YOUR_SKILLS if skill.lower() in text_lower]


class PeoplePerHourScraper(PlatformScraper):
    """Scrape PeoplePerHour job listings"""
    
    def search_jobs(self, keywords: List[str]) -> List[Dict]:
        """Search PeoplePerHour"""
        print("🔍 Searching PeoplePerHour...")
        
        base_url = "https://www.peopleperhour.com/freelance-jobs"
        params = {
            'keyword': ' '.join(keywords)
        }
        
        try:
            response = self.session.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('div', class_='project-card')
            
            jobs = []
            for card in job_cards[:Config.MAX_RESULTS_PER_PLATFORM]:
                try:
                    title_elem = card.find('h3') or card.find('a', class_='project-title')
                    desc_elem = card.find('p', class_='project-description')
                    budget_elem = card.find('span', class_='budget')
                    
                    if not title_elem:
                        continue
                    
                    job = {
                        'id': f"pph-{hash(title_elem.text)}",
                        'title': title_elem.text.strip(),
                        'description': desc_elem.text.strip() if desc_elem else '',
                        'url': card.find('a')['href'] if card.find('a') else '',
                        'posted_date': datetime.now().isoformat(),
                        'platform': 'peopleperhour',
                        'budget': budget_elem.text.strip() if budget_elem else None,
                        'skills': self._extract_skills_from_text(
                            f"{title_elem.text} {desc_elem.text if desc_elem else ''}"
                        ),
                        'source': 'scraper'
                    }
                    
                    # Fix relative URLs
                    if job['url'] and not job['url'].startswith('http'):
                        job['url'] = f"https://www.peopleperhour.com{job['url']}"
                    
                    jobs.append(job)
                except:
                    continue
            
            print(f"✅ Found {len(jobs)} PeoplePerHour jobs")
            return jobs
            
        except Exception as e:
            print(f"❌ PeoplePerHour scraping failed: {e}")
            return []
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        text_lower = text.lower()
        return [skill for skill in Config.YOUR_SKILLS if skill.lower() in text_lower]


# ============================================================================
# BUSINESS MODEL ANALYZER
# ============================================================================

class BusinessModelAnalyzer:
    """Analyze opportunities and identify business models"""
    
    def analyze_opportunities(self, opportunities: List[Dict]) -> Dict:
        """Analyze all opportunities and identify business models"""
        
        # Categorize opportunities
        matched_jobs = []
        business_models = {}
        skill_demand = Counter()
        platform_distribution = Counter()
        
        for opp in opportunities:
            # Track platforms
            platform_distribution[opp.get('platform', 'unknown')] += 1
            
            # Track skill demand
            for skill in opp.get('matching_skills', []):
                skill_demand[skill] += 1
            
            # Check if meets threshold
            if opp.get('meets_threshold', False):
                matched_jobs.append(opp)
            
            # Analyze business potential
            business_potential = opp.get('business_potential', {})
            if business_potential.get('has_potential'):
                for model in business_potential.get('models', []):
                    model_name = model['name']
                    if model_name not in business_models:
                        business_models[model_name] = {
                            'name': model_name,
                            'description': model['description'],
                            'count': 0,
                            'avg_score': 0,
                            'examples': []
                        }
                    
                    business_models[model_name]['count'] += 1
                    business_models[model_name]['avg_score'] += model['score']
                    
                    if len(business_models[model_name]['examples']) < 3:
                        business_models[model_name]['examples'].append({
                            'title': opp.get('title'),
                            'url': opp.get('url'),
                            'score': model['score']
                        })
        
        # Calculate averages
        for model in business_models.values():
            if model['count'] > 0:
                model['avg_score'] = round(model['avg_score'] / model['count'], 2)
        
        # Sort business models by potential
        top_business_models = sorted(
            business_models.values(),
            key=lambda x: (x['count'], x['avg_score']),
            reverse=True
        )[:5]
        
        return {
            'total_opportunities': len(opportunities),
            'matched_opportunities': len(matched_jobs),
            'top_skills_in_demand': skill_demand.most_common(10),
            'platform_distribution': dict(platform_distribution),
            'business_models': top_business_models,
            'matched_jobs': sorted(matched_jobs, key=lambda x: x.get('match_score', 0), reverse=True)
        }


# ============================================================================
# EMAIL NOTIFICATION SENDER
# ============================================================================

class NotificationSender:
    """Send email notifications with opportunities and business insights"""
    
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
    
    def send_notification(self, analysis: Dict):
        """Send detailed notification email"""
        
        # Generate email content
        subject = f"🎯 {analysis['matched_opportunities']} Freelance Opportunities + Business Model Insights"
        
        html_content = self._generate_html_report(analysis)
        text_content = self._generate_text_report(analysis)
        
        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.email
        msg['To'] = self.email
        
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        try:
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
            
            print(f"✅ Notification email sent to {self.email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send notification: {e}")
            return False
    
    def _generate_html_report(self, analysis: Dict) -> str:
        """Generate HTML email report"""
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 20px; border-radius: 8px; }}
        .section {{ margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 5px; }}
        .job {{ background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #667eea; }}
        .score {{ display: inline-block; padding: 5px 10px; background: #4CAF50; 
                  color: white; border-radius: 3px; font-weight: bold; }}
        .business-model {{ background: #fff3cd; padding: 15px; margin: 10px 0; 
                          border-left: 4px solid #ffc107; }}
        .metric {{ display: inline-block; padding: 10px 15px; margin: 5px; 
                  background: #e3f2fd; border-radius: 5px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #667eea; color: white; }}
        a {{ color: #667eea; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Freelancer Opportunity Report</h1>
        <p>{datetime.now().strftime('%B %d, %Y at %H:%M UTC')}</p>
    </div>
    
    <div class="section">
        <h2>📊 Summary</h2>
        <span class="metric">Total Scanned: <strong>{analysis['total_opportunities']}</strong></span>
        <span class="metric">Matched: <strong>{analysis['matched_opportunities']}</strong></span>
        <span class="metric">Business Models Found: <strong>{len(analysis['business_models'])}</strong></span>
    </div>
"""
        
        # Business Models Section
        if analysis['business_models']:
            html += """
    <div class="section">
        <h2>💼 Business Models You Can Offer</h2>
        <p><em>These are recurring service patterns you could turn into standardized offerings:</em></p>
"""
            
            for model in analysis['business_models']:
                html += f"""
        <div class="business-model">
            <h3>{model['name']} ({model['count']} opportunities)</h3>
            <p>{model['description']}</p>
            <p><strong>Average Match Score:</strong> {model['avg_score']}%</p>
            <p><strong>Example Projects:</strong></p>
            <ul>
"""
                for example in model['examples']:
                    html += f"<li><a href='{example.get('url', '#')}'>{example['title']}</a> (Score: {example['score']}%)</li>\n"
                
                html += """
            </ul>
        </div>
"""
            
            html += "</div>"
        
        # Top Matched Jobs
        if analysis['matched_jobs']:
            html += f"""
    <div class="section">
        <h2>🎯 Top {min(10, len(analysis['matched_jobs']))} Matched Opportunities</h2>
"""
            
            for i, job in enumerate(analysis['matched_jobs'][:10], 1):
                skills_html = ', '.join(job.get('matching_skills', [])[:5])
                url = job.get('url', '#')
                budget = job.get('budget', 'Not specified')
                platform = job.get('platform', 'unknown').upper()
                
                html += f"""
        <div class="job">
            <h3>{i}. {job['title']}</h3>
            <span class="score">{job['match_score']}% Match</span>
            <p><strong>Platform:</strong> {platform} | <strong>Budget:</strong> {budget}</p>
            <p><strong>Matching Skills:</strong> {skills_html}</p>
            <p><a href="{url}" target="_blank">View Opportunity →</a></p>
        </div>
"""
            
            html += "</div>"
        
        # Skills in Demand
        if analysis['top_skills_in_demand']:
            html += """
    <div class="section">
        <h2>🔥 Skills Most in Demand</h2>
        <table>
            <tr><th>Skill</th><th>Mentions</th></tr>
"""
            for skill, count in analysis['top_skills_in_demand']:
                html += f"<tr><td>{skill}</td><td>{count}</td></tr>\n"
            
            html += """
        </table>
    </div>
"""
        
        html += """
    <div class="section">
        <p><em>This is an automated report. Review opportunities and consider which business models align with your goals.</em></p>
    </div>
</body>
</html>
"""
        
        return html
    
    def _generate_text_report(self, analysis: Dict) -> str:
        """Generate plain text report"""
        
        text = f"""
FREELANCER OPPORTUNITY REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}

{'='*80}
SUMMARY
{'='*80}

Total Opportunities Scanned: {analysis['total_opportunities']}
Matched Opportunities: {analysis['matched_opportunities']}
Business Models Identified: {len(analysis['business_models'])}

"""
        
        # Business Models
        if analysis['business_models']:
            text += f"""
{'='*80}
BUSINESS MODELS YOU CAN OFFER
{'='*80}

"""
            for model in analysis['business_models']:
                text += f"""
{model['name']} ({model['count']} opportunities)
{'-'*80}
Description: {model['description']}
Average Match Score: {model['avg_score']}%

Example Projects:
"""
                for example in model['examples']:
                    text += f"  • {example['title']} (Score: {example['score']}%)\n"
                    if example.get('url'):
                        text += f"    {example['url']}\n"
                
                text += "\n"
        
        # Top Jobs
        if analysis['matched_jobs']:
            text += f"""
{'='*80}
TOP {min(10, len(analysis['matched_jobs']))} MATCHED OPPORTUNITIES
{'='*80}

"""
            for i, job in enumerate(analysis['matched_jobs'][:10], 1):
                skills = ', '.join(job.get('matching_skills', [])[:5])
                text += f"""
{i}. {job['title']}
   Match Score: {job['match_score']}%
   Platform: {job.get('platform', 'unknown').upper()}
   Budget: {job.get('budget', 'Not specified')}
   Skills: {skills}
   URL: {job.get('url', 'N/A')}

"""
        
        # Skills Demand
        if analysis['top_skills_in_demand']:
            text += f"""
{'='*80}
SKILLS MOST IN DEMAND
{'='*80}

"""
            for skill, count in analysis['top_skills_in_demand']:
                text += f"  {skill}: {count} mentions\n"
        
        text += f"""
{'='*80}

Review these opportunities and consider building standardized service offerings
around the identified business models.
"""
        
        return text


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Freelancer Opportunity Finder & Business Model Identifier'
    )
    parser.add_argument('--days-back', type=int, default=7,
                       help='Days back to search Gmail (default: 7)')
    parser.add_argument('--keywords', nargs='+', 
                       default=['python', 'automation', 'api', 'machine learning'],
                       help='Keywords for platform scraping')
    parser.add_argument('--output', type=str, default='opportunities.json',
                       help='Output JSON file')
    parser.add_argument('--skip-email', action='store_true',
                       help='Skip sending email notification')
    
    args = parser.parse_args()
    
    # Validate credentials
    if not Config.PASSWORD:
        print("❌ Error: FREELANCER_PASSWORD environment variable not set")
        print("   For Gmail, use an App Password: https://myaccount.google.com/apppasswords")
        return 1
    
    print("\n" + "="*80)
    print("🚀 FREELANCER OPPORTUNITY FINDER")
    print("="*80 + "\n")
    
    all_opportunities = []
    
    # Step 1: Extract from Gmail
    print("📧 STEP 1: Extracting from Gmail...")
    print("-"*80)
    
    gmail = GmailExtractor(Config.EMAIL, Config.PASSWORD)
    gmail_opps = gmail.extract_opportunities(days_back=args.days_back)
    gmail.close()
    
    all_opportunities.extend(gmail_opps)
    time.sleep(2)
    
    # Step 2: Scrape platforms
    print("\n🔍 STEP 2: Scraping Freelancer Platforms...")
    print("-"*80)
    
    upwork = UpworkRSSScraper()
    upwork_jobs = upwork.search_jobs(args.keywords)
    all_opportunities.extend(upwork_jobs)
    time.sleep(Config.DELAY_BETWEEN_REQUESTS)
    
    # Step 3: Match and analyze
    print("\n🎯 STEP 3: Matching to Your Profile & Analyzing Business Models...")
    print("-"*80)
    
    scraper = PlatformScraper()
    for opp in all_opportunities:
        match_data = scraper.match_to_profile(opp)
        opp.update(match_data)
    
    # Step 4: Analyze business models
    print("\n💼 STEP 4: Identifying Business Model Opportunities...")
    print("-"*80)
    
    analyzer = BusinessModelAnalyzer()
    analysis = analyzer.analyze_opportunities(all_opportunities)
    
    # Print summary
    print(f"\n📊 Analysis Complete!")
    print(f"   Total Opportunities: {analysis['total_opportunities']}")
    print(f"   Matched (≥{Config.MIN_MATCH_SCORE}%): {analysis['matched_opportunities']}")
    print(f"   Business Models Identified: {len(analysis['business_models'])}")
    
    if analysis['business_models']:
        print("\n💡 Top Business Model Opportunities:")
        for i, model in enumerate(analysis['business_models'][:3], 1):
            print(f"   {i}. {model['name']} ({model['count']} opportunities)")
    
    # Step 5: Save results
    print("\n💾 STEP 5: Saving Results...")
    print("-"*80)
    
    output_data = {
        'generated_at': datetime.now().isoformat(),
        'analysis': analysis,
        'all_opportunities': all_opportunities
    }
    
    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✅ Results saved to: {args.output}")
    
    # Step 6: Send notification email
    if not args.skip_email:
        print("\n📨 STEP 6: Sending Notification Email...")
        print("-"*80)
        
        sender = NotificationSender(Config.EMAIL, Config.PASSWORD)
        sender.send_notification(analysis)
    
    print("\n" + "="*80)
    print("✅ COMPLETE! Check your email for the full report.")
    print("="*80 + "\n")
    
    return 0


if __name__ == '__main__':
    exit(main())
