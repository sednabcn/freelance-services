#!/usr/bin/env python3
"""
Freelancer Opportunity Finder & Business Model Identifier
Scrapes freelancer platforms, analyzes your Gmail, and identifies:
1. Jobs matching your skills
2. Potential business models you can offer to others

WITH DEBUG LOGGING
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
import sys
import psycopg2
from psycopg2.extras import execute_values
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sqlite3
from datetime import datetime
# ============================================================================
# CONFIGURATION
# ============================================================================
class Config:
    """Configuration for freelancer opportunity finder - IMPROVED"""
    
    # YOUR PROFILE - CUSTOMIZE THIS!
    YOUR_SKILLS = [
        # Core Programming
        "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "C++", "PHP",
        
        # Web Development
        "Django", "Flask", "FastAPI", "React", "Vue.js", "Vue", "Node.js", "Node",
        "Angular", "Next.js", "Express", "HTML", "CSS", "Tailwind",
        
        # Data & ML
        "Machine Learning", "Data Science", "Deep Learning", "NLP", "AI",
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
        "Data Analysis", "Data Visualization",
        
        # DevOps & Cloud
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "CI/CD",
        "Terraform", "GitHub Actions", "Jenkins", "Linux",
        
        # Databases
        "PostgreSQL", "MongoDB", "Redis", "MySQL", "Elasticsearch",
        "SQL", "NoSQL", "Database",
        
        # Specialized
        "Web Scraping", "Scraping", "API Development", "Automation", "ETL",
        "Computer Vision", "Chatbots", "REST APIs", "REST", "GraphQL",
        "Testing", "Selenium", "Playwright",
        
        # Soft skills that appear in job posts
        "Backend", "Frontend", "Full Stack", "Development", "Programming",
        "Software", "Engineer", "Developer"
    ]
    
    # Email configuration
    EMAIL = os.getenv('FREELANCER_EMAIL', 'freelancers.automation@gmail.com')
    PASSWORD = os.getenv('FREELANCER_PASSWORD', '')
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    IMAP_HOST = os.getenv('IMAP_HOST', 'imap.gmail.com')
    IMAP_PORT = int(os.getenv('IMAP_PORT', 993))
    
    # IMPROVED MATCHING THRESHOLDS
    MIN_MATCH_SCORE = 15  # Lower to see more matches (was 60)
    MIN_BUSINESS_POTENTIAL_SCORE = 40  # Lower threshold (was 70)
    
    # Rate limiting
    DELAY_BETWEEN_REQUESTS = 3
    MAX_RESULTS_PER_PLATFORM = 50  # Increased from 30
    
    # Debug mode
    DEBUG = False


def debug_print(message: str):
    """Print debug message if debug mode is enabled"""
    if Config.DEBUG:
        print(f"🐛 DEBUG: {message}")


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
            debug_print(f"Connecting to IMAP: {Config.IMAP_HOST}:{Config.IMAP_PORT}")
            self.imap = imaplib.IMAP4_SSL(Config.IMAP_HOST, Config.IMAP_PORT)
            
            debug_print(f"Attempting login for: {self.email}")
            self.imap.login(self.email, self.password)
            
            print(f"✅ Connected to Gmail: {self.email}")
            return True
        except Exception as e:
            print(f"❌ Gmail connection failed: {e}")
            debug_print(f"Full error: {type(e).__name__}: {str(e)}")
            return False
    
    def extract_opportunities(self, days_back: int = 7) -> List[Dict]:
        """Extract job opportunities from Gmail"""
        if not self.imap and not self.connect():
            return []
        
        try:
            debug_print("Selecting INBOX")
            self.imap.select('INBOX')
            
            # Search for emails from freelancer platforms
            date_since = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            debug_print(f"Searching emails since: {date_since}")
            
            # Common freelancer platform senders
            senders = [
                'upwork.com', 'fiverr.com', 'freelancer.com',
                'toptal.com', 'guru.com', 'peopleperhour.com',
                'freelance', 'job', 'opportunity', 'project'
            ]
            
            all_opportunities = []
            
            for sender in senders:
                try:
                    debug_print(f"Searching for sender: {sender}")
                    status, messages = self.imap.search(
                        None, 
                        f'(SINCE {date_since} OR FROM "{sender}")'
                    )
                    
                    if status == 'OK':
                        email_ids = messages[0].split()
                        debug_print(f"Found {len(email_ids)} emails from {sender}")
                        
                        for email_id in email_ids[-50:]:  # Last 50 emails per sender
                            try:
                                opportunity = self._parse_email(email_id)
                                if opportunity:
                                    all_opportunities.append(opportunity)
                                    debug_print(f"Parsed opportunity: {opportunity['title'][:50]}...")
                            except Exception as e:
                                debug_print(f"Error parsing email {email_id}: {e}")
                                continue
                    else:
                        debug_print(f"Search failed for {sender}: {status}")
                except Exception as e:
                    debug_print(f"Error searching {sender}: {e}")
                    continue
            
            # Remove duplicates based on title
            unique_opportunities = {}
            for opp in all_opportunities:
                title = opp.get('title', '')
                if title and title not in unique_opportunities:
                    unique_opportunities[title] = opp
            
            opportunities = list(unique_opportunities.values())
            print(f"📧 Extracted {len(opportunities)} unique opportunities from Gmail (from {len(all_opportunities)} total)")
            debug_print(f"Removed {len(all_opportunities) - len(opportunities)} duplicates")
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Error extracting from Gmail: {e}")
            debug_print(f"Full error: {type(e).__name__}: {str(e)}")
            return []
    
    def _parse_email(self, email_id) -> Optional[Dict]:
        """Parse email and extract opportunity details"""
        try:
            status, msg_data = self.imap.fetch(email_id, '(RFC822)')
            if status != 'OK':
                debug_print(f"Failed to fetch email {email_id}: {status}")
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
                debug_print(f"Skipping email - title too short: {title}")
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
            debug_print(f"Error parsing email: {e}")
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
                debug_print("Gmail connection closed")
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

    def _get_sample_jobs(self) -> List[Dict]:
        """Return sample jobs for testing"""
        return [{
            'id': 'sample-1',
            'title': 'Python Automation Developer Needed',
            'description': 'Looking for Python developer with web scraping and API experience...',
            'platform': 'upwork',
            'skills': ['Python', 'Web Scraping', 'API Development'],
            'budget': '$200 - $500',
            'source': 'sample'
        }]

    def match_to_profile(self, job: Dict) -> Dict:
        """Calculate match score and identify business potential - IMPROVED"""
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        skills = job.get('skills', [])
    
        full_text = f"{title} {description} {' '.join(skills)}".lower()
    
        # Calculate skill matches
        matching_skills = []
        for skill in Config.YOUR_SKILLS:
            if skill.lower() in full_text:
                matching_skills.append(skill)
    
        # Remove duplicates (e.g., "Python" and "python")
        matching_skills = list(set(matching_skills))
    
        # IMPROVED SCORING: Weight title matches higher
        title_matches = sum(1 for skill in Config.YOUR_SKILLS if skill.lower() in title)
        description_matches = len(matching_skills)
    
        # Title matches are worth 3x more
        weighted_matches = (title_matches * 3) + description_matches
    
        # Calculate percentage based on weighted matches
        # Scale: if you match 5 skills with 2 in title, that's (2*3 + 5) = 11 points
        # Max reasonable score: 15 points = 100%
        match_score = min(100, (weighted_matches / 15) * 100)
    
        # Bonus: If job explicitly lists your skills
        if skills:
            skill_list_bonus = len(skills) * 5  # 5% per explicitly listed skill
            match_score = min(100, match_score + skill_list_bonus)
    
        # Identify business model potential
        business_potential = self._identify_business_potential(full_text, title)
    
        debug_print(f"Job '{job.get('title', '')[:40]}...' - Match: {match_score:.1f}%, "
                f"Skills: {len(matching_skills)}, Title matches: {title_matches}")
    
        return {
            'match_score': round(match_score, 2),
            'matching_skills': matching_skills,
            'title_matches': title_matches,
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
        debug_print(f"Keywords: {keywords}")
        
        rss_url = "https://www.upwork.com/ab/feed/jobs/rss"
        params = {'q': ' '.join(keywords), 'sort': 'recency'}
        
        try:
            debug_print(f"GET {rss_url} with params: {params}")
            response = self.session.get(rss_url, params=params, timeout=10)
            debug_print(f"Response status: {response.status_code}")
            debug_print(f"Content length: {len(response.text)} bytes")
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'xml')
            items = soup.find_all('item')
            debug_print(f"Found {len(items)} items in RSS feed")
            
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
                    debug_print(f"Parsed job: {job['title'][:50]}...")
                except Exception as e:
                    debug_print(f"Error parsing Upwork item: {e}")
                    continue
            
            print(f"✅ Found {len(jobs)} Upwork jobs")
            return jobs
            
        except Exception as e:
            print(f"❌ Upwork scraping failed: {e}")
            debug_print(f"Full error: {type(e).__name__}: {str(e)}")
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
        debug_print(f"Keywords: {keywords}")
        
        base_url = "https://www.freelancer.com/jobs"
        params = {
            'keyword': ' '.join(keywords),
            'status': 'open'
        }
        
        try:
            debug_print(f"GET {base_url} with params: {params}")
            response = self.session.get(base_url, params=params, timeout=10)
            debug_print(f"Response status: {response.status_code}")
            debug_print(f"Content length: {len(response.text)} bytes")
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('div', class_='JobSearchCard-item')
            debug_print(f"Found {len(job_cards)} job cards")
            
            jobs = []
            for card in job_cards[:Config.MAX_RESULTS_PER_PLATFORM]:
                try:
                    title_elem = card.find('a', class_='JobSearchCard-primary-heading-link')
                    desc_elem = card.find('p', class_='JobSearchCard-primary-description')
                    budget_elem = card.find('div', class_='JobSearchCard-primary-price')
                    
                    if not title_elem:
                        debug_print("Skipping card - no title element")
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
                    debug_print(f"Parsed job: {job['title'][:50]}...")
                except Exception as e:
                    debug_print(f"Error parsing Freelancer.com card: {e}")
                    continue
            
            print(f"✅ Found {len(jobs)} Freelancer.com jobs")
            return jobs
            
        except Exception as e:
            print(f"❌ Freelancer.com scraping failed: {e}")
            debug_print(f"Full error: {type(e).__name__}: {str(e)}")
            return []
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        text_lower = text.lower()
        return [skill for skill in Config.YOUR_SKILLS if skill.lower() in text_lower]


class GuruScraper(PlatformScraper):
    """Scrape Guru.com job listings"""
    
    def search_jobs(self, keywords: List[str]) -> List[Dict]:
        """Search Guru.com"""
        print("🔍 Searching Guru.com...")
        debug_print(f"Keywords: {keywords}")
        
        base_url = "https://www.guru.com/d/jobs"
        params = {
            'searchTerm': ' '.join(keywords)
        }
        
        try:
            debug_print(f"GET {base_url} with params: {params}")
            response = self.session.get(base_url, params=params, timeout=10)
            debug_print(f"Response status: {response.status_code}")
            debug_print(f"Content length: {len(response.text)} bytes")
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            job_items = soup.find_all('div', class_='guruJobCard')
            debug_print(f"Found {len(job_items)} job items")
            
            jobs = []
            for item in job_items[:Config.MAX_RESULTS_PER_PLATFORM]:
                try:
                    title_elem = item.find('a', class_='jobTitle')
                    desc_elem = item.find('p', class_='jobDescription')
                    budget_elem = item.find('span', class_='budget')
                    
                    if not title_elem:
                        debug_print("Skipping item - no title element")
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
                    debug_print(f"Parsed job: {job['title'][:50]}...")
                except Exception as e:
                    debug_print(f"Error parsing Guru item: {e}")
                    continue
            
            print(f"✅ Found {len(jobs)} Guru jobs")
            return jobs
            
        except Exception as e:
            print(f"❌ Guru scraping failed: {e}")
            debug_print(f"Full error: {type(e).__name__}: {str(e)}")
            return []
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        text_lower = text.lower()
        return [skill for skill in Config.YOUR_SKILLS if skill.lower() in text_lower]


class PeoplePerHourScraper(PlatformScraper):
    """Scrape PeoplePerHour job listings"""
    
    def search_jobs(self, keywords: List[str]) -> List[Dict]:
        """Search PeoplePerHour"""
        print("🔍 Searching PeoplePerHour...")
        debug_print(f"Keywords: {keywords}")
        
        base_url = "https://www.peopleperhour.com/freelance-jobs"
        params = {
            'keyword': ' '.join(keywords)
        }
        
        try:
            debug_print(f"GET {base_url} with params: {params}")
            response = self.session.get(base_url, params=params, timeout=10)
            debug_print(f"Response status: {response.status_code}")
            debug_print(f"Content length: {len(response.text)} bytes")
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('div', class_='project-card')
            debug_print(f"Found {len(job_cards)} job cards")
            
            jobs = []
            for card in job_cards[:Config.MAX_RESULTS_PER_PLATFORM]:
                try:
                    title_elem = card.find('h3') or card.find('a', class_='project-title')
                    desc_elem = card.find('p', class_='project-description')
                    budget_elem = card.find('span', class_='budget')
                    
                    if not title_elem:
                        debug_print("Skipping card - no title element")
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
                    debug_print(f"Parsed job: {job['title'][:50]}...")
                except Exception as e:
                    debug_print(f"Error parsing PeoplePerHour card: {e}")
                    continue
            
            print(f"✅ Found {len(jobs)} PeoplePerHour jobs")
            return jobs
            
        except Exception as e:
            print(f"❌ PeoplePerHour scraping failed: {e}")
            debug_print(f"Full error: {type(e).__name__}: {str(e)}")
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
        
        debug_print(f"Analyzing {len(opportunities)} opportunities")
        
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
        
        debug_print(f"Found {len(matched_jobs)} matched jobs")
        debug_print(f"Identified {len(top_business_models)} business models")
        
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
        
        debug_print("Preparing notification email")
        
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
            debug_print(f"Connecting to SMTP: {Config.SMTP_HOST}:{Config.SMTP_PORT}")
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
            
            print(f"✅ Notification email sent to {self.email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send notification: {e}")
            debug_print(f"Full error: {type(e).__name__}: {str(e)}")
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
# GOOGLE SHEETS INTEGRATION
# ============================================================================

class GoogleSheetsStorage:
    """Save opportunities to Google Sheets"""
    
    def __init__(self, credentials_file: str = 'credentials.json', 
                 spreadsheet_name: str = 'Freelance Opportunities'):
        """
        Initialize Google Sheets connection
        
        Setup instructions:
        1. Go to Google Cloud Console (console.cloud.google.com)
        2. Create a project
        3. Enable Google Sheets API
        4. Create Service Account credentials
        5. Download JSON key as 'credentials.json'
        6. Share your spreadsheet with the service account email
        """
        self.credentials_file = credentials_file
        self.spreadsheet_name = spreadsheet_name
        self.client = None
        self.sheet = None
    
    def connect(self) -> bool:
        """Connect to Google Sheets"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_file, scope
            )
            self.client = gspread.authorize(creds)
            
            # Try to open existing spreadsheet, create if doesn't exist
            try:
                self.sheet = self.client.open(self.spreadsheet_name).sheet1
            except gspread.SpreadsheetNotFound:
                spreadsheet = self.client.create(self.spreadsheet_name)
                self.sheet = spreadsheet.sheet1
                self._setup_headers()
            
            print(f"✅ Connected to Google Sheets: {self.spreadsheet_name}")
            return True
            
        except FileNotFoundError:
            print(f"❌ Credentials file not found: {self.credentials_file}")
            print("   Create credentials at: https://console.cloud.google.com")
            return False
        except Exception as e:
            print(f"❌ Google Sheets connection failed: {e}")
            return False
    
    def _setup_headers(self):
        """Setup spreadsheet headers"""
        headers = [
            'Timestamp', 'Title', 'Platform', 'Budget', 
            'Match Score', 'Matching Skills', 'URL', 'Source',
            'Business Model', 'Description Preview'
        ]
        self.sheet.append_row(headers)
        # Format header row
        self.sheet.format('A1:J1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.4, 'green': 0.5, 'blue': 0.9}
        })
    
    def save_opportunities(self, opportunities: List[Dict]) -> bool:
        """Save opportunities to Google Sheets"""
        if not self.sheet and not self.connect():
            return False
        
        try:
            rows = []
            for opp in opportunities:
                # Only save matched opportunities
                if not opp.get('meets_threshold', False):
                    continue
                
                business_model = ''
                if opp.get('business_potential', {}).get('best_model'):
                    business_model = opp['business_potential']['best_model']['name']
                
                row = [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    opp.get('title', 'N/A')[:200],  # Truncate long titles
                    opp.get('platform', 'unknown').upper(),
                    opp.get('budget', 'Not specified'),
                    f"{opp.get('match_score', 0):.1f}%",
                    ', '.join(opp.get('matching_skills', [])[:5]),
                    opp.get('url', 'N/A'),
                    opp.get('source', 'unknown'),
                    business_model,
                    opp.get('description', '')[:100]  # Preview
                ]
                rows.append(row)
            
            if rows:
                self.sheet.append_rows(rows)
                print(f"✅ Saved {len(rows)} opportunities to Google Sheets")
                return True
            else:
                print("ℹ️ No matched opportunities to save")
                return True
                
        except Exception as e:
            print(f"❌ Failed to save to Google Sheets: {e}")
            return False
    
    def get_spreadsheet_url(self) -> str:
        """Get the URL of the spreadsheet"""
        if self.sheet:
            return f"https://docs.google.com/spreadsheets/d/{self.sheet.spreadsheet.id}"
        return ""


# ============================================================================
# POSTGRESQL DATABASE INTEGRATION
# ============================================================================

class PostgreSQLStorage:
    """Save opportunities to PostgreSQL database"""
    
    def __init__(self, database_url: str = None):
        """
        Initialize PostgreSQL connection
        
        Database URL format:
        postgresql://user:password@host:port/database
        
        Or set environment variable: DATABASE_URL
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        self.conn = None
    
    def connect(self) -> bool:
        """Connect to PostgreSQL"""
        if not self.database_url:
            print("❌ PostgreSQL DATABASE_URL not configured")
            print("   Set environment variable: export DATABASE_URL='postgresql://...'")
            return False
        
        try:
            self.conn = psycopg2.connect(self.database_url)
            print("✅ Connected to PostgreSQL database")
            self._create_tables()
            return True
            
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            return False
    
    def _create_tables(self):
        """Create tables if they don't exist"""
        with self.conn.cursor() as cur:
            # Main opportunities table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    id SERIAL PRIMARY KEY,
                    external_id VARCHAR(255) UNIQUE,
                    title TEXT NOT NULL,
                    description TEXT,
                    platform VARCHAR(50),
                    url TEXT,
                    budget VARCHAR(100),
                    match_score DECIMAL(5,2),
                    source VARCHAR(50),
                    posted_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Skills junction table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS opportunity_skills (
                    opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE CASCADE,
                    skill VARCHAR(100),
                    PRIMARY KEY (opportunity_id, skill)
                )
            """)
            
            # Business models table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS opportunity_business_models (
                    opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE CASCADE,
                    model_name VARCHAR(100),
                    model_score DECIMAL(5,2),
                    PRIMARY KEY (opportunity_id, model_name)
                )
            """)
            
            # Create indexes for better query performance
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_opportunities_platform 
                ON opportunities(platform)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_opportunities_match_score 
                ON opportunities(match_score DESC)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_opportunities_created_at 
                ON opportunities(created_at DESC)
            """)
            
            self.conn.commit()
    
    def save_opportunities(self, opportunities: List[Dict]) -> bool:
        """Save opportunities to database"""
        if not self.conn and not self.connect():
            return False
        
        try:
            with self.conn.cursor() as cur:
                saved_count = 0
                
                for opp in opportunities:
                    # Insert opportunity (or update if exists)
                    cur.execute("""
                        INSERT INTO opportunities 
                        (external_id, title, description, platform, url, budget, 
                         match_score, source, posted_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (external_id) 
                        DO UPDATE SET
                            match_score = EXCLUDED.match_score,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """, (
                        opp.get('id'),
                        opp.get('title', 'N/A'),
                        opp.get('description', ''),
                        opp.get('platform', 'unknown'),
                        opp.get('url'),
                        opp.get('budget'),
                        opp.get('match_score', 0),
                        opp.get('source', 'unknown'),
                        opp.get('posted_date')
                    ))
                    
                    opportunity_id = cur.fetchone()[0]
                    
                    # Insert skills
                    if opp.get('matching_skills'):
                        skills_data = [
                            (opportunity_id, skill) 
                            for skill in opp['matching_skills']
                        ]
                        execute_values(
                            cur,
                            """
                            INSERT INTO opportunity_skills (opportunity_id, skill)
                            VALUES %s
                            ON CONFLICT DO NOTHING
                            """,
                            skills_data
                        )
                    
                    # Insert business models
                    if opp.get('business_potential', {}).get('models'):
                        models_data = [
                            (opportunity_id, model['name'], model['score'])
                            for model in opp['business_potential']['models']
                        ]
                        execute_values(
                            cur,
                            """
                            INSERT INTO opportunity_business_models 
                            (opportunity_id, model_name, model_score)
                            VALUES %s
                            ON CONFLICT DO NOTHING
                            """,
                            models_data
                        )
                    
                    saved_count += 1
                
                self.conn.commit()
                print(f"✅ Saved {saved_count} opportunities to PostgreSQL")
                return True
                
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Failed to save to PostgreSQL: {e}")
            return False
    
    def get_top_opportunities(self, limit: int = 10) -> List[Dict]:
        """Retrieve top opportunities from database"""
        if not self.conn:
            return []
        
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    o.title, o.platform, o.budget, o.match_score, 
                    o.url, o.created_at,
                    ARRAY_AGG(DISTINCT os.skill) as skills
                FROM opportunities o
                LEFT JOIN opportunity_skills os ON o.id = os.opportunity_id
                GROUP BY o.id
                ORDER BY o.match_score DESC, o.created_at DESC
                LIMIT %s
            """, (limit,))
            
            results = []
            for row in cur.fetchall():
                results.append({
                    'title': row[0],
                    'platform': row[1],
                    'budget': row[2],
                    'match_score': float(row[3]),
                    'url': row[4],
                    'created_at': row[5],
                    'skills': row[6] if row[6] else []
                })
            
            return results
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# ============================================================================
# SQLITE LOCAL DATABASE
# ============================================================================

class SQLiteStorage:
    """Save opportunities to local SQLite database (no setup required)"""
    
    def __init__(self, db_path: str = 'freelance_opportunities.db'):
        """Initialize SQLite connection"""
        self.db_path = db_path
        self.conn = None
    
    def connect(self) -> bool:
        """Connect to SQLite"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            print(f"✅ Connected to SQLite database: {self.db_path}")
            self._create_tables()
            return True
            
        except Exception as e:
            print(f"❌ SQLite connection failed: {e}")
            return False
    
    def _create_tables(self):
        """Create tables if they don't exist"""
        cur = self.conn.cursor()
        
        # Main opportunities table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT UNIQUE,
                title TEXT NOT NULL,
                description TEXT,
                platform TEXT,
                url TEXT,
                budget TEXT,
                match_score REAL,
                source TEXT,
                posted_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Skills table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS opportunity_skills (
                opportunity_id INTEGER,
                skill TEXT,
                PRIMARY KEY (opportunity_id, skill),
                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
            )
        """)
        
        # Create indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_match_score 
            ON opportunities(match_score DESC)
        """)
        
        self.conn.commit()
    
    def save_opportunities(self, opportunities: List[Dict]) -> bool:
        """Save opportunities to SQLite"""
        if not self.conn and not self.connect():
            return False
        
        try:
            cur = self.conn.cursor()
            saved_count = 0
            
            for opp in opportunities:
                # Insert or replace opportunity
                cur.execute("""
                    INSERT OR REPLACE INTO opportunities 
                    (external_id, title, description, platform, url, budget, 
                     match_score, source, posted_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    opp.get('id'),
                    opp.get('title', 'N/A'),
                    opp.get('description', ''),
                    opp.get('platform', 'unknown'),
                    opp.get('url'),
                    opp.get('budget'),
                    opp.get('match_score', 0),
                    opp.get('source', 'unknown'),
                    opp.get('posted_date')
                ))
                
                opportunity_id = cur.lastrowid
                
                # Insert skills
                if opp.get('matching_skills'):
                    for skill in opp['matching_skills']:
                        cur.execute("""
                            INSERT OR IGNORE INTO opportunity_skills 
                            (opportunity_id, skill)
                            VALUES (?, ?)
                        """, (opportunity_id, skill))
                
                saved_count += 1
            
            self.conn.commit()
            print(f"✅ Saved {saved_count} opportunities to SQLite")
            return True
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Failed to save to SQLite: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        if not self.conn:
            return {}
        
        cur = self.conn.cursor()
        
        stats = {}
        
        # Total opportunities
        cur.execute("SELECT COUNT(*) FROM opportunities")
        stats['total_opportunities'] = cur.fetchone()[0]
        
        # Opportunities by platform
        cur.execute("""
            SELECT platform, COUNT(*) 
            FROM opportunities 
            GROUP BY platform
        """)
        stats['by_platform'] = dict(cur.fetchall())
        
        # Average match score
        cur.execute("SELECT AVG(match_score) FROM opportunities")
        stats['avg_match_score'] = cur.fetchone()[0] or 0
        
        # Top skills
        cur.execute("""
            SELECT skill, COUNT(*) as count
            FROM opportunity_skills
            GROUP BY skill
            ORDER BY count DESC
            LIMIT 10
        """)
        stats['top_skills'] = dict(cur.fetchall())
        
        return stats
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# ============================================================================
# USAGE EXAMPLE - ADD TO YOUR main() FUNCTION
# ============================================================================

def save_to_all_storage(opportunities: List[Dict], args):
    """
    Save opportunities to all configured storage systems
    Add this function call in your main() after analysis
    """
    
    # 1. SQLite (always available, no setup)
    sqlite_storage = SQLiteStorage()
    if sqlite_storage.connect():
        sqlite_storage.save_opportunities(opportunities)
        
        # Print stats
        stats = sqlite_storage.get_stats()
        print(f"\n📊 SQLite Stats:")
        print(f"   Total stored: {stats.get('total_opportunities', 0)}")
        print(f"   Avg match: {stats.get('avg_match_score', 0):.1f}%")
        
        sqlite_storage.close()
    
    # 2. Google Sheets (requires credentials.json)
    if os.path.exists('credentials.json'):
        sheets_storage = GoogleSheetsStorage()
        if sheets_storage.connect():
            sheets_storage.save_opportunities(opportunities)
            url = sheets_storage.get_spreadsheet_url()
            if url:
                print(f"📊 View in Google Sheets: {url}")
    else:
        print("\nℹ️  Google Sheets: Add 'credentials.json' to enable")
        print("   Instructions: https://console.cloud.google.com")
    
    # 3. PostgreSQL (requires DATABASE_URL)
    if os.getenv('DATABASE_URL'):
        pg_storage = PostgreSQLStorage()
        if pg_storage.connect():
            pg_storage.save_opportunities(opportunities)
            
            # Show top opportunities from database
            top_opps = pg_storage.get_top_opportunities(5)
            if top_opps:
                print("\n🏆 Top 5 from database:")
                for i, opp in enumerate(top_opps, 1):
                    print(f"   {i}. {opp['title'][:50]}... ({opp['match_score']:.1f}%)")
            
            pg_storage.close()
    else:
        print("\nℹ️  PostgreSQL: Set DATABASE_URL to enable")
        print("   Example: export DATABASE_URL='postgresql://user:pass@host/db'")


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
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Enable debug mode
    Config.DEBUG = args.debug
    
    if Config.DEBUG:
        print("\n🐛 DEBUG MODE ENABLED\n")
    
    # Validate credentials
    if not Config.PASSWORD:
        print("⚠️ Gmail password not found — skipping Gmail extraction.")
        gmail_jobs = []
    else:
        gmail_extractor = GmailExtractor(Config.EMAIL, Config.PASSWORD)
        gmail_jobs = gmail_extractor.extract_opportunities(days_back=args.days_back)
        gmail_extractor.close()

    # =========================================================================
    # PLATFORM SCRAPING
    # =========================================================================
    upwork_scraper = UpworkRSSScraper()
    freelancer_scraper = FreelancerComScraper()
    guru_scraper = GuruScraper()
    pph_scraper = PeoplePerHourScraper()

    print("\n🌍 Searching freelancer platforms...\n")

    all_jobs = []
    try:
        all_jobs.extend(upwork_scraper.search_jobs(args.keywords))
        all_jobs.extend(freelancer_scraper.search_jobs(args.keywords))
        all_jobs.extend(guru_scraper.search_jobs(args.keywords))
        all_jobs.extend(pph_scraper.search_jobs(args.keywords))
    except Exception as e:
        print(f"⚠️ Error during scraping: {e}")

    # If no jobs found, use sample
    if not all_jobs and not gmail_jobs:
        print("⚠️ No jobs found. Using sample jobs for testing...")
        all_jobs = upwork_scraper._get_sample_jobs()

    # =========================================================================
    # MATCHING & ANALYSIS
    # =========================================================================
    print("\n🧩 Matching jobs to your profile...\n")
    platform_scraper = PlatformScraper()
    enriched_jobs = []

    for job in all_jobs + gmail_jobs:
        match_info = platform_scraper.match_to_profile(job)
        job.update(match_info)
        enriched_jobs.append(job)

    print(f"✅ Analyzed {len(enriched_jobs)} total opportunities")

    analyzer = BusinessModelAnalyzer()
    analysis = analyzer.analyze_opportunities(enriched_jobs)

    # =========================================================================
    # SAVE RESULTS WITH PROPER STRUCTURE
    # =========================================================================
    output_data = {
        'generated_at': datetime.now().isoformat(),
        'search_params': {
            'keywords': args.keywords,
            'days_back': args.days_back
        },
        'opportunities': enriched_jobs,
        'analysis': analysis
    }
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    print(f"📁 Results saved to {args.output}")

    # =========================================================================
    # EMAIL NOTIFICATION
    # =========================================================================
    if not args.skip_email and Config.PASSWORD:
        notifier = NotificationSender(Config.EMAIL, Config.PASSWORD)
        notifier.send_notification(analysis)
    else:
        print("📧 Email notification skipped (use --skip-email to silence this message)")

    print("\n🎯 Done! Review your opportunities and consider recurring business models.\n")
    
    # Save to all configured storage systems
    save_to_all_storage(enriched_jobs, args)
    
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if Config.DEBUG:
            import traceback
            traceback.print_exc()
