#!/usr/bin/env python3
"""
Job Keyword Extractor & Config Generator
Analyzes job listings from multiple sources and automatically generates
job-manager-config.yml with extracted keywords and requirements.
"""

import json
import yaml
import re
from collections import Counter, defaultdict
from typing import List, Dict, Set
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KeywordExtractor:
    """Extract and analyze keywords from job listings"""

    # Common technical skills and tools
    TECH_KEYWORDS = {
        'languages': ['python', 'javascript', 'java', 'c++', 'go', 'rust', 'ruby', 'php', 'typescript', 'scala', 'kotlin'],
        'frameworks': ['react', 'vue', 'angular', 'django', 'flask', 'spring', 'express', 'fastapi', 'node.js', 'next.js'],
        'databases': ['postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'dynamodb', 'cassandra', 'oracle'],
        'cloud': ['aws', 'azure', 'gcp', 'google cloud', 'cloud computing', 'serverless'],
        'devops': ['docker', 'kubernetes', 'terraform', 'ansible', 'jenkins', 'gitlab', 'github actions', 'ci/cd'],
        'architecture': ['microservices', 'distributed systems', 'event-driven', 'rest api', 'graphql', 'grpc'],
        'methodologies': ['agile', 'scrum', 'kanban', 'tdd', 'continuous integration', 'continuous delivery']
    }

    # Common soft skills
    SOFT_SKILLS = [
        'leadership', 'communication', 'teamwork', 'problem solving', 'analytical',
        'mentoring', 'collaboration', 'innovation', 'creative', 'adaptable'
    ]

    # Red flags to exclude
    RED_FLAGS = [
        'unpaid', 'no salary', 'commission only', 'work from home scam',
        'entry level', 'junior', 'graduate', 'intern', 'must relocate'
    ]

    def __init__(self, job_positions: List[str]):
        self.job_positions = job_positions
        self.all_keywords = defaultdict(Counter)
        self.salary_data = []
        self.locations = Counter()
        self.companies = Counter()
        self.required_skills = Counter()
        self.preferred_skills = Counter()
        self.analysis_results = {}

    # -------------------------------------------------------------------------
    # Support for offline testing
    # -------------------------------------------------------------------------
    def _get_sample_jobs(self) -> List[Dict]:
        """Return sample jobs for testing"""
        return [{
            'id': 'sample-1',
            'title': 'Python Automation Developer Needed',
            'description_snippet': 'Looking for Python developer with web scraping and API experience...',
            'full_description': 'We need a skilled developer experienced with Flask, Selenium, and REST APIs.',
            'attributes': ['Python', 'Flask', 'Automation'],
            'job_type': 'Contract',
            'location': 'Remote',
            'company': 'Tech Innovators',
            'salary': '$3000 - $5000',
            'platform': 'sample'
        }]

    # -------------------------------------------------------------------------
    # Data loading
    # -------------------------------------------------------------------------
    def load_jobs_from_files(self, file_patterns: List[str]) -> List[Dict]:
        """Load job listings from JSON files"""
        all_jobs = []

        for pattern in file_patterns:
            files = list(Path('.').glob(pattern))
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        jobs = json.load(f)
                        if isinstance(jobs, list):
                            all_jobs.extend(jobs)
                            logger.info(f"Loaded {len(jobs)} jobs from {file_path}")
                        else:
                            all_jobs.append(jobs)
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {str(e)}")

        if not all_jobs:
            logger.warning("⚠️ No job files found — using sample job for testing.")
            all_jobs = self._get_sample_jobs()

        return all_jobs

    # -------------------------------------------------------------------------
    # Keyword extraction
    # -------------------------------------------------------------------------
    def extract_keywords(self, jobs: List[Dict]):
        """Extract and categorize keywords from job listings"""
        logger.info(f"Analyzing {len(jobs)} job listings...")

        for job in jobs:
            text_fields = [
                job.get('title', ''),
                job.get('description_snippet', ''),
                job.get('full_description', ''),
                ' '.join(job.get('attributes', [])),
                job.get('job_type', '')
            ]
            full_text = ' '.join(text_fields).lower()

            # Extract technical keywords
            for category, keywords in self.TECH_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in full_text:
                        self.all_keywords[category][keyword] += 1

            # Extract soft skills
            for skill in self.SOFT_SKILLS:
                if skill in full_text:
                    self.all_keywords['soft_skills'][skill] += 1

            # Categorize required vs preferred
            if 'required' in full_text or 'must have' in full_text:
                for category, keywords in self.TECH_KEYWORDS.items():
                    for keyword in keywords:
                        if keyword in full_text:
                            self.required_skills[keyword] += 1

            if 'preferred' in full_text or 'nice to have' in full_text or 'bonus' in full_text:
                for category, keywords in self.TECH_KEYWORDS.items():
                    for keyword in keywords:
                        if keyword in full_text:
                            self.preferred_skills[keyword] += 1

            # Salary extraction
            salary = job.get('salary', '')
            if salary:
                salary_nums = self._extract_salary_range(salary)
                if salary_nums:
                    self.salary_data.append(salary_nums)

            # Track metadata
            location = job.get('location', '').strip()
            if location:
                self.locations[location] += 1

            company = job.get('company', '').strip()
            if company and company.lower() != 'unknown':
                self.companies[company] += 1

    # -------------------------------------------------------------------------
    def _extract_salary_range(self, salary_text: str) -> Dict:
        """Extract numeric salary values"""
        try:
            cleaned = re.sub(r'[£$€,]', '', salary_text.lower())
            numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', cleaned)
            numbers = [float(n.replace(',', '')) for n in numbers]

            if numbers:
                if 'k' in cleaned:
                    numbers = [n * 1000 if n < 1000 else n for n in numbers]
                return {
                    'min': min(numbers),
                    'max': max(numbers),
                    'currency': 'GBP' if '£' in salary_text else 'USD'
                }
        except Exception:
            pass
        return None

    # -------------------------------------------------------------------------
    def get_top_keywords(self, category: str, top_n: int = 10) -> List[str]:
        """Get most common keywords in a category"""
        return [kw for kw, count in self.all_keywords[category].most_common(top_n)]

    def get_salary_stats(self) -> Dict:
        """Calculate salary statistics"""
        if not self.salary_data:
            return {'minimum': 50000, 'currency': 'GBP', 'period': 'yearly'}

        all_mins = [s['min'] for s in self.salary_data if s]
        all_maxs = [s['max'] for s in self.salary_data if s]

        return {
            'minimum': int(sum(all_mins) / len(all_mins)) if all_mins else 50000,
            'maximum': int(sum(all_maxs) / len(all_maxs)) if all_maxs else 100000,
            'currency': 'GBP',
            'period': 'yearly'
        }

    # -------------------------------------------------------------------------
    def export_analysis_report(self, output_file):
        """
        Export the keyword analysis results to a JSON file.
        Ensures 'analysis' key always exists to prevent KeyError.
        """
        if not hasattr(self, 'analysis_results') or not self.analysis_results:
            logger.warning("⚠️ No analysis results found, creating empty report")
            self.analysis_results = {}

        data = self.analysis_results

        # ✅ Safety block: ensure 'analysis' always exists
        if 'analysis' not in data:
            logger.warning("⚠️ 'analysis' key missing — using fallback structure.")
            data = {'analysis': data, 'keyword_analysis': data}

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"✅ Analysis report exported to {output_file}")

    # -------------------------------------------------------------------------
    def generate_config(self, output_file: str = 'job-manager-config.yml'):
        """Generate configuration file based on extracted keywords"""

        top_languages = self.get_top_keywords('languages', 5)
        top_cloud = self.get_top_keywords('cloud', 5)
        top_devops = self.get_top_keywords('devops', 5)
        top_databases = self.get_top_keywords('databases', 5)
        top_frameworks = self.get_top_keywords('frameworks', 5)

        top_required = [k for k, v in self.required_skills.most_common(10)]
        top_preferred = [k for k, v in self.preferred_skills.most_common(10)]

        if not top_required:
            all_tech = []
            for category in ['languages', 'cloud', 'devops', 'databases']:
                all_tech.extend(self.all_keywords[category].most_common(3))
            top_required = [k for k, v in sorted(all_tech, key=lambda x: x[1], reverse=True)[:5]]

        if not top_preferred:
            top_preferred = self.get_top_keywords('devops', 5) + self.get_top_keywords('frameworks', 3)

        top_locations = [loc for loc, count in self.locations.most_common(10)]
        salary_stats = self.get_salary_stats()

        CONFIG_TEMPLATE = {
            'search': {
                'linkedin': {
                    'enabled': True,
                    'url': 'https://linkedin.com/jobs/search',
                    'filters': ['title', 'location', 'experience']
                },
                'glassdoor': {
                    'enabled': True,
                    'url': 'https://glassdoor.com/jobs',
                    'filters': ['title', 'location']
                },
                'indeed': {
                    'enabled': True,
                    'url': 'https://indeed.com/jobs',
                    'filters': ['title', 'company']
                }
            },
            'output': {
                'report_format': 'json',
                'update_frequency': 'weekly'
            }
        }

        config = {
            'search': {
                'target_roles': self.job_positions,
                'required_keywords': list(set(top_required[:10])),
                'preferred_keywords': list(set(top_preferred[:10])),
                'locations': top_locations
            },
            'salary': salary_stats,
            'generated_at': datetime.now().isoformat()
        }

        CONFIG_TEMPLATE['search'].update(config['search'])

        with open(output_file, 'w') as f:
            yaml.safe_dump(CONFIG_TEMPLATE, f, sort_keys=False)

        logger.info(f"✅ Configuration saved to {output_file}")
