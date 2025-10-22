#!/usr/bin/env python3
"""
Drag and drop .eml/.mbox files to process
Usage: python email_processor.py file1.eml file2.eml folder/*.mbox
"""

import sys
import email
import json
import mailbox
from pathlib import Path
from datetime import datetime
import re

class FreelancerEmailProcessor:
    def __init__(self):
        self.jobs = []
    
    def process_files(self, file_paths):
        """Process list of email files"""
        for filepath in file_paths:
            path = Path(filepath)
            
            if not path.exists():
                print(f"⚠️  File not found: {filepath}")
                continue
            
            if path.suffix == '.eml':
                self.process_eml(path)
            elif path.suffix == '.mbox':
                self.process_mbox(path)
            else:
                print(f"⚠️  Unknown format: {filepath}")
    
    def process_eml(self, filepath):
        """Process single .eml file"""
        try:
            with open(filepath, 'rb') as f:
                msg = email.message_from_binary_file(f)
            
            job = self.extract_job_data(msg)
            if job:
                self.jobs.append(job)
                print(f"✅ Processed: {filepath.name}")
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")
    
    def process_mbox(self, filepath):
        """Process .mbox file (multiple emails)"""
        try:
            mbox = mailbox.mbox(filepath)
            count = 0
            
            for message in mbox:
                job = self.extract_job_data(message)
                if job:
                    self.jobs.append(job)
                    count += 1
            
            print(f"✅ Processed {count} emails from {filepath.name}")
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")
    
    def extract_job_data(self, msg):
        """Extract job information from email message"""
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
                try:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    body = str(msg.get_payload())
            
            # Extract job details
            job = {
                'id': f"export-{hash(subject + date_str)}",
                'title': self.extract_title(subject, body),
                'description': body[:1000],
                'platform': self.detect_platform(from_addr, subject, body),
                'url': self.extract_url(body),
                'budget': self.extract_budget(body),
                'skills_required': self.extract_skills(body),
                'received_date': date_str,
                'source': 'manual_export',
                'raw_subject': subject,
                'from_email': from_addr
            }
            
            return job
            
        except Exception as e:
            print(f"⚠️  Error extracting job data: {e}")
            return None
    
    def extract_title(self, subject, body):
        """Extract job title"""
        # Remove common email prefixes
        title = re.sub(r'^(Re:|Fwd?:|New job:)\s*', '', subject, flags=re.IGNORECASE)
        return title.strip()
    
    def detect_platform(self, from_addr, subject, body):
        """Detect which platform the email is from"""
        text = f"{from_addr} {subject} {body}".lower()
        
        platforms = {
            'upwork': ['upwork', 'jobs-noreply@upwork'],
            'fiverr': ['fiverr', 'no-reply@fiverr'],
            'freelancer': ['freelancer.com', 'noreply@freelancer'],
            'toptal': ['toptal', '@toptal.com'],
            'guru': ['guru.com', '@guru.com'],
            'peopleperhour': ['peopleperhour', '@peopleperhour']
        }
        
        for platform, keywords in platforms.items():
            if any(keyword in text for keyword in keywords):
                return platform
        
        return 'unknown'
    
    def extract_url(self, body):
        """Extract job URL"""
        urls = re.findall(r'https?://[^\s<>"]+', body)
        
        # Filter for job-related URLs
        job_domains = ['upwork.com/jobs', 'fiverr.com', 'freelancer.com/projects',
                       'toptal.com', 'guru.com', 'peopleperhour.com']
        
        for url in urls:
            if any(domain in url.lower() for domain in job_domains):
                return url
        
        return urls[0] if urls else None
    
    def extract_budget(self, body):
        """Extract budget information"""
        # Common patterns
        patterns = [
            r'Budget:\s*\$?([\d,]+(?:\.\d{2})?)',
            r'Rate:\s*\$?([\d,]+(?:\.\d{2})?)',
            r'Price:\s*\$?([\d,]+(?:\.\d{2})?)',
            r'\$[\d,]+(?:-\$?[\d,]+)?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def extract_skills(self, body):
        """Extract required skills"""
        common_skills = [
            'Python', 'JavaScript', 'Java', 'C++', 'PHP',
            'React', 'Angular', 'Vue', 'Node.js', 'Django',
            'Machine Learning', 'Data Science', 'AI',
            'Web Scraping', 'API', 'Database', 'SQL',
            'AWS', 'Azure', 'Docker', 'Kubernetes'
        ]
        
        found_skills = []
        body_lower = body.lower()
        
        for skill in common_skills:
            if skill.lower() in body_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def save_results(self, output_file='processed_emails.json'):
        """Save processed jobs to JSON"""
        output = {
            'total_emails': len(self.jobs),
            'processed_at': datetime.now().isoformat(),
            'jobs': self.jobs
        }
        
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Saved {len(self.jobs)} jobs to {output_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python email_processor.py file1.eml file2.eml folder/*.mbox")
        print("\nOr drag and drop email files onto this script")
        return
    
    print("🔧 FREELANCER EMAIL PROCESSOR")
    print("="*60)
    
    processor = FreelancerEmailProcessor()
    processor.process_files(sys.argv[1:])
    processor.save_results()
    
    print("\n✅ Processing complete!")
    print(f"   Total jobs extracted: {len(processor.jobs)}")
    print("\nNext steps:")
    print("  1. Review processed_emails.json")
    print("  2. Run: python .github/scripts/freelancer_automation.py --input processed_emails.json")

if __name__ == '__main__':
    main()

#========================================================
#**Usage**:
#```bash
# Drag and drop files, or:
# python email_processor.py freelancer_emails/*.eml
# python email_processor.py export.mbox

# Then process with automation
# python .github/scripts/freelancer_automation.py --input processed_emails.json --mode match
#============================================================`
