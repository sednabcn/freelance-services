#!/usr/bin/env python3
"""
Process exported email files (.eml or .mbox)
"""

import email
import os
import json
from pathlib import Path
from datetime import datetime

def process_eml_file(filepath):
    """Process a single .eml file"""
    with open(filepath, 'rb') as f:
        msg = email.message_from_binary_file(f)
    
    subject = msg.get('Subject', '')
    from_addr = msg.get('From', '')
    date_str = msg.get('Date', '')
    
    # Get body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                break
    else:
        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
    
    return {
        'subject': subject,
        'from': from_addr,
        'date': date_str,
        'body': body
    }

def process_mbox_file(filepath):
    """Process .mbox file (multiple emails)"""
    import mailbox
    
    mbox = mailbox.mbox(filepath)
    emails = []
    
    for message in mbox:
        emails.append({
            'subject': message.get('Subject', ''),
            'from': message.get('From', ''),
            'date': message.get('Date', ''),
            'body': str(message.get_payload())
        })
    
    return emails

def main():
    emails_dir = Path('freelancer_emails')
    all_emails = []
    
    # Process .eml files
    for eml_file in emails_dir.glob('*.eml'):
        print(f"Processing: {eml_file.name}")
        email_data = process_eml_file(eml_file)
        all_emails.append(email_data)
    
    # Process .mbox files
    for mbox_file in emails_dir.glob('*.mbox'):
        print(f"Processing: {mbox_file.name}")
        emails = process_mbox_file(mbox_file)
        all_emails.extend(emails)
    
    # Save to JSON
    output = {
        'total_emails': len(all_emails),
        'exported_at': datetime.now().isoformat(),
        'emails': all_emails
    }
    
    with open('exported_freelancer_emails.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ Processed {len(all_emails)} emails")
    print(f"   Saved to: exported_freelancer_emails.json")

if __name__ == '__main__':
    main()
