
class GmailFreelancerExtractor:
    """Extract emails from Gmail freelancer folder"""
    
    def __init__(self, email_address: str, password: str, folder: str = 'freelancer_emails'):
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


