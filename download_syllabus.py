#!/usr/bin/env python3
"""
CBSE Syllabus Downloader

This script downloads CBSE syllabus from byjus.com for classes 1-12 across
multiple subjects. The content is saved as markdown files and a JSON index
for LLM-based question paper generation.

Usage:
    python download_syllabus.py
"""

import os
import re
import json
import time
import random
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base configuration
BASE_URL = "https://byjus.com"
OUTPUT_DIR = "syllabus"
INDEX_FILE = "syllabus_index.json"

# Request headers to mimic a real browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
}

# Known syllabus URLs based on byjus.com structure
# Class-wise main syllabus pages
CLASS_SYLLABUS_URLS = {
    1: "/cbse-class-1-syllabus/",
    2: "/cbse/cbse-class-2-syllabus/",
    3: "/cbse/cbse-syllabus-for-class-3/",  # Fixed URL
    4: "/cbse/cbse-syllabus-for-class-4/",  # Fixed URL
    5: "/cbse/cbse-class-5th-syllabus/",
    6: "/cbse/cbse-class-6-syllabus/",
    7: "/cbse/cbse-class-7-syllabus/",
    8: "/cbse/cbse-class-8-syllabus/",
    9: "/cbse/cbse-class-9-syllabus/",
    10: "/cbse/cbse-class-10-syllabus/",
    11: "/cbse/cbse-class-11-syllabus/",
    12: "/cbse/cbse-class-12-syllabus/",
}

# Subject-specific syllabus URLs for different classes
# Note: byjus.com uses different URL patterns - mostly /cbse/class-X-subject-syllabus/
SUBJECT_SYLLABUS_URLS = {
    # Class 1 - URLs at root level
    (1, "maths"): "/cbse-class-1-maths-syllabus/",
    (1, "english"): "/cbse-class-1-english-syllabus/",
    (1, "hindi"): "/cbse-class-1-hindi-syllabus/",
    (1, "evs"): "/cbse/class-1-evs-syllabus/",  # Fixed URL

    # Class 2 - URLs at root level
    (2, "maths"): "/cbse-class-2-maths-syllabus/",  # Fixed URL
    (2, "english"): "/cbse-class-2-english-syllabus/",
    (2, "hindi"): "/cbse-class-2-hindi-syllabus/",
    (2, "evs"): "/cbse/class-2-evs-syllabus/",  # Fixed URL

    # Class 3 - URLs at root level (no /cbse/ prefix)
    (3, "maths"): "/cbse-class-3-maths-syllabus/",  # Fixed URL
    (3, "english"): "/cbse-class-3-english-syllabus/",
    (3, "hindi"): "/cbse-class-3-hindi-syllabus/",
    (3, "evs"): "/cbse/class-3-science-syllabus/",  # Fixed - uses science instead of evs

    # Class 4 - URLs at root level
    (4, "maths"): "/cbse-class-4-maths-syllabus/",  # Fixed URL
    (4, "english"): "/cbse-class-4-english-syllabus/",
    (4, "hindi"): "/cbse-class-4-hindi-syllabus/",
    (4, "evs"): "/cbse/class-4-evs-syllabus/",  # Fixed URL

    # Class 5 - URLs at root level
    (5, "maths"): "/cbse-class-5-maths-syllabus/",
    (5, "english"): "/cbse-class-5-english-syllabus/",
    (5, "hindi"): "/cbse-class-5-hindi-syllabus/",
    (5, "evs"): "/cbse/class-5-evs-syllabus/",  # Fixed URL

    # Class 6 - Use /cbse/class-X-subject-syllabus/ pattern (without cbse- prefix)
    (6, "maths"): "/cbse/class-6-maths-syllabus/",  # Fixed URL
    (6, "english"): "/cbse/class-6-english-syllabus/",
    (6, "hindi"): "/cbse/class-6-hindi-syllabus/",
    (6, "science"): "/cbse/class-6-science-syllabus/",
    (6, "social-science"): "/cbse/class-6-social-science-syllabus/",
    (6, "sanskrit"): "/cbse/class-6-sanskrit-syllabus/",  # Fixed URL

    # Class 7 - Use /cbse/class-X-subject-syllabus/ pattern
    (7, "maths"): "/cbse/class-7-maths-syllabus/",  # Fixed URL
    (7, "english"): "/cbse/class-7-english-syllabus/",
    (7, "hindi"): "/cbse/class-7-hindi-syllabus/",  # Fixed URL
    (7, "science"): "/cbse/class-7-science-syllabus/",
    (7, "social-science"): "/cbse/class-7-social-science-syllabus/",
    (7, "sanskrit"): "/cbse/class-7-sanskrit-syllabus/",  # Fixed URL

    # Class 8 - Use /cbse/class-X-subject-syllabus/ pattern
    (8, "maths"): "/cbse/class-8-maths-syllabus/",  # Fixed URL
    (8, "english"): "/cbse/class-8-english-syllabus/",
    (8, "hindi"): "/cbse/class-8-hindi-syllabus/",
    (8, "science"): "/cbse/class-8-science-syllabus/",
    (8, "social-science"): "/cbse-class-8-social-science-syllabus/",
    (8, "sanskrit"): "/cbse/class-8-sanskrit-syllabus/",  # Fixed URL

    # Class 9 - Use /cbse/class-X-subject-syllabus/ pattern
    (9, "maths"): "/cbse/class-9-maths-syllabus/",  # Fixed URL
    (9, "english"): "/cbse/class-9-english-syllabus/",
    (9, "hindi"): "/cbse/class-9-hindi-syllabus/",
    (9, "science"): "/cbse/class-9-science-syllabus/",
    (9, "social-science"): "/cbse/class-9-social-science-syllabus/",
    (9, "sanskrit"): "/cbse/class-9-sanskrit-syllabus/",  # Fixed URL

    # Class 10 - Use /cbse/class-X-subject-syllabus/ pattern
    (10, "maths"): "/cbse/class-10-maths-syllabus/",  # Fixed URL
    (10, "english"): "/cbse/class-10-english-syllabus/",  # Fixed URL
    (10, "hindi"): "/cbse/class-10-hindi-syllabus/",  # Fixed URL
    (10, "science"): "/cbse/class-10-science-syllabus/",
    (10, "social-science"): "/cbse/class-10-social-science-syllabus/",  # Fixed URL
    (10, "sanskrit"): "/cbse/class-10-sanskrit-syllabus/",  # Fixed URL

    # Class 11 - Use /cbse/class-X-subject-syllabus/ pattern
    (11, "maths"): "/cbse/class-11-maths-syllabus/",  # Fixed URL
    (11, "physics"): "/cbse/class-11-physics-syllabus/",  # Fixed URL
    (11, "chemistry"): "/cbse/class-11-chemistry-syllabus/",  # Fixed URL
    (11, "biology"): "/cbse/class-11-biology-syllabus/",  # Fixed URL
    (11, "english"): "/cbse/class-11-english-syllabus/",
    (11, "hindi"): "/cbse/class-11-hindi-syllabus/",
    (11, "accountancy"): "/cbse/class-11-accountancy-syllabus/",  # Fixed URL
    (11, "economics"): "/cbse/class-11-economics-syllabus/",  # Fixed URL
    (11, "business-studies"): "/cbse/class-11-business-studies-syllabus/",  # Fixed URL
    (11, "computer-science"): "/cbse/class-11-computer-science-syllabus/",
    (11, "physical-education"): "/cbse/class-11-physical-education-syllabus/",

    # Class 12 - Use /cbse/class-X-subject-syllabus/ pattern
    (12, "maths"): "/cbse/class-12-maths-syllabus/",  # Fixed URL
    (12, "physics"): "/cbse/class-12-physics-syllabus/",  # Fixed URL
    (12, "chemistry"): "/cbse/class-12-chemistry-syllabus/",  # Fixed URL
    (12, "biology"): "/cbse/class-12-biology-syllabus/",  # Fixed URL
    (12, "english"): "/cbse/class-12-english-syllabus/",
    (12, "hindi"): "/cbse/class-12-hindi-syllabus/",
    (12, "accountancy"): "/cbse/class-12-accountancy-syllabus/",  # Fixed URL
    (12, "economics"): "/cbse/class-12-economics-syllabus/",  # Fixed URL
    (12, "business-studies"): "/cbse/class-12-business-studies-syllabus/",  # Fixed URL
    (12, "computer-science"): "/cbse/class-12-computer-science-syllabus/",
    (12, "physical-education"): "/cbse/class-12-physical-education-syllabus/",
    (12, "history"): "/cbse/class-12-history-syllabus/",  # Fixed URL
    (12, "geography"): "/cbse/class-12-geography-syllabus/",  # Fixed URL
    (12, "political-science"): "/cbse/class-12-political-science-syllabus/",  # Fixed URL
}


class CBSESyllabusScraper:
    """Scraper for downloading CBSE syllabus from byjus.com"""

    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.syllabus_index: Dict[str, dict] = {}
        self.failed_urls: List[str] = []

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

    def _make_request(self, url: str, retries: int = 3) -> Optional[requests.Response]:
        """Make HTTP request with retry logic and rate limiting"""
        for attempt in range(retries):
            try:
                # Add random delay to avoid rate limiting
                time.sleep(random.uniform(1, 3))

                response = self.session.get(url, timeout=30)

                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    logger.warning(f"Access forbidden (403) for {url}")
                    # Try with different user agent
                    self.session.headers['User-Agent'] = random.choice([
                        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    ])
                    time.sleep(random.uniform(2, 5))
                elif response.status_code == 404:
                    logger.warning(f"Page not found (404) for {url}")
                    return None
                else:
                    logger.warning(f"Unexpected status {response.status_code} for {url}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error for {url}: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

        return None

    def _extract_syllabus_content(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract syllabus content from the page"""
        content = {
            "url": url,
            "title": "",
            "description": "",
            "units": [],
            "chapters": [],
            "topics": [],
            "marking_scheme": [],
            "raw_content": "",
            "extracted_at": datetime.now().isoformat(),
        }

        # Extract title
        title_elem = soup.find('h1')
        if title_elem:
            content["title"] = title_elem.get_text(strip=True)

        # Extract main content area
        main_content = soup.find('article') or soup.find('div', class_='post-content') or soup.find('div', class_='entry-content')

        if not main_content:
            # Try finding content by common class patterns
            for selector in ['content', 'main-content', 'article-content', 'post-body']:
                main_content = soup.find('div', class_=re.compile(selector, re.I))
                if main_content:
                    break

        if not main_content:
            main_content = soup.find('body')

        if main_content:
            # Extract all text content
            raw_text = []

            # Extract headings and their content
            for elem in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'table', 'tr', 'td', 'th']):
                text = elem.get_text(strip=True)
                if text and len(text) > 2:
                    raw_text.append(text)

            content["raw_content"] = "\n".join(raw_text)

            # Extract tables (often contain syllabus structure)
            tables = main_content.find_all('table')
            for table in tables:
                table_data = self._extract_table(table)
                if table_data:
                    # Check if it's marking scheme or syllabus units
                    headers = [h.lower() for h in table_data.get("headers", [])]
                    if any(word in str(headers) for word in ["mark", "weightage", "score"]):
                        content["marking_scheme"].append(table_data)
                    elif any(word in str(headers) for word in ["unit", "chapter", "topic", "content"]):
                        content["units"].append(table_data)

            # Extract lists (chapters/topics)
            for ul in main_content.find_all(['ul', 'ol']):
                items = [li.get_text(strip=True) for li in ul.find_all('li') if li.get_text(strip=True)]
                if items:
                    # Check context to categorize
                    prev_elem = ul.find_previous_sibling(['h2', 'h3', 'h4', 'p'])
                    context = prev_elem.get_text(strip=True).lower() if prev_elem else ""

                    if "chapter" in context:
                        content["chapters"].extend(items)
                    elif "topic" in context or "unit" in context:
                        content["topics"].extend(items)
                    else:
                        content["topics"].extend(items)

        # Extract description/overview
        desc_elem = soup.find('meta', attrs={'name': 'description'})
        if desc_elem:
            content["description"] = desc_elem.get('content', '')

        return content

    def _extract_table(self, table: BeautifulSoup) -> Optional[Dict]:
        """Extract table data into structured format"""
        try:
            headers = []
            rows = []

            # Get headers
            header_row = table.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]

            # Get data rows
            for row in table.find_all('tr')[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                if cells and any(cells):
                    rows.append(cells)

            if headers or rows:
                return {"headers": headers, "rows": rows}
        except Exception as e:
            logger.error(f"Error extracting table: {e}")

        return None

    def _find_additional_syllabus_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find additional syllabus links from the page"""
        links = []

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            text = a_tag.get_text(strip=True).lower()

            # Check if it's a syllabus link
            if 'syllabus' in href.lower() and 'cbse' in href.lower():
                full_url = urljoin(base_url, href)
                if full_url not in links and 'byjus.com' in full_url:
                    links.append(full_url)

        return links

    def _content_to_markdown(self, content: Dict, class_num: int, subject: str = None) -> str:
        """Convert extracted content to markdown format"""
        md_lines = []

        # Title
        title = content.get("title", f"CBSE Class {class_num} {subject.replace('-', ' ').title() if subject else ''} Syllabus")
        md_lines.append(f"# {title}\n")

        # Metadata
        md_lines.append("## Metadata\n")
        md_lines.append(f"- **Class**: {class_num}")
        if subject:
            md_lines.append(f"- **Subject**: {subject.replace('-', ' ').title()}")
        md_lines.append(f"- **Source**: {content.get('url', '')}")
        md_lines.append(f"- **Extracted At**: {content.get('extracted_at', '')}")
        md_lines.append("")

        # Description
        if content.get("description"):
            md_lines.append("## Overview\n")
            md_lines.append(content["description"])
            md_lines.append("")

        # Marking Scheme
        if content.get("marking_scheme"):
            md_lines.append("## Marking Scheme\n")
            for table in content["marking_scheme"]:
                if table.get("headers"):
                    md_lines.append("| " + " | ".join(table["headers"]) + " |")
                    md_lines.append("| " + " | ".join(["---"] * len(table["headers"])) + " |")
                for row in table.get("rows", []):
                    md_lines.append("| " + " | ".join(row) + " |")
                md_lines.append("")

        # Units/Syllabus Structure
        if content.get("units"):
            md_lines.append("## Syllabus Structure\n")
            for i, table in enumerate(content["units"], 1):
                if table.get("headers"):
                    md_lines.append("| " + " | ".join(table["headers"]) + " |")
                    md_lines.append("| " + " | ".join(["---"] * len(table["headers"])) + " |")
                for row in table.get("rows", []):
                    md_lines.append("| " + " | ".join(row) + " |")
                md_lines.append("")

        # Chapters
        if content.get("chapters"):
            md_lines.append("## Chapters\n")
            for i, chapter in enumerate(content["chapters"], 1):
                md_lines.append(f"{i}. {chapter}")
            md_lines.append("")

        # Topics
        if content.get("topics"):
            md_lines.append("## Topics\n")
            for topic in content["topics"]:
                md_lines.append(f"- {topic}")
            md_lines.append("")

        # Raw Content (for LLM processing)
        if content.get("raw_content"):
            md_lines.append("## Detailed Content\n")
            md_lines.append("```")
            md_lines.append(content["raw_content"][:10000])  # Limit size
            md_lines.append("```")
            md_lines.append("")

        # Footer for LLM
        md_lines.append("---")
        md_lines.append("*This syllabus is formatted for LLM question paper generation.*")
        md_lines.append("*Difficulty levels: Easy, Medium, Hard*")

        return "\n".join(md_lines)

    def download_class_syllabus(self, class_num: int) -> bool:
        """Download syllabus for a specific class"""
        url_path = CLASS_SYLLABUS_URLS.get(class_num)
        if not url_path:
            logger.warning(f"No URL configured for class {class_num}")
            return False

        url = urljoin(BASE_URL, url_path)
        logger.info(f"Downloading Class {class_num} syllabus from {url}")

        response = self._make_request(url)
        if not response:
            self.failed_urls.append(url)
            return False

        soup = BeautifulSoup(response.text, 'html.parser')
        content = self._extract_syllabus_content(soup, url)

        # Create class directory
        class_dir = os.path.join(self.output_dir, f"class_{class_num}")
        os.makedirs(class_dir, exist_ok=True)

        # Save as markdown
        md_content = self._content_to_markdown(content, class_num)
        md_file = os.path.join(class_dir, f"class_{class_num}_overview.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

        # Save as JSON
        json_file = os.path.join(class_dir, f"class_{class_num}_overview.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)

        # Update index
        self.syllabus_index[f"class_{class_num}"] = {
            "class": class_num,
            "overview_url": url,
            "md_file": md_file,
            "json_file": json_file,
            "subjects": {}
        }

        logger.info(f"✓ Saved Class {class_num} overview syllabus")

        # Find additional syllabus links from the page
        additional_links = self._find_additional_syllabus_links(soup, url)
        return True

    def download_subject_syllabus(self, class_num: int, subject: str) -> bool:
        """Download syllabus for a specific class and subject"""
        key = (class_num, subject)
        url_path = SUBJECT_SYLLABUS_URLS.get(key)

        if not url_path:
            logger.warning(f"No URL configured for Class {class_num} {subject}")
            return False

        url = urljoin(BASE_URL, url_path)
        logger.info(f"Downloading Class {class_num} {subject} syllabus from {url}")

        response = self._make_request(url)
        if not response:
            self.failed_urls.append(url)
            return False

        soup = BeautifulSoup(response.text, 'html.parser')
        content = self._extract_syllabus_content(soup, url)

        # Create class directory
        class_dir = os.path.join(self.output_dir, f"class_{class_num}")
        os.makedirs(class_dir, exist_ok=True)

        # Clean subject name for filename
        clean_subject = subject.replace('-', '_')

        # Save as markdown
        md_content = self._content_to_markdown(content, class_num, subject)
        md_file = os.path.join(class_dir, f"class_{class_num}_{clean_subject}_syllabus.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

        # Save as JSON
        json_file = os.path.join(class_dir, f"class_{class_num}_{clean_subject}_syllabus.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)

        # Update index
        class_key = f"class_{class_num}"
        if class_key not in self.syllabus_index:
            self.syllabus_index[class_key] = {
                "class": class_num,
                "subjects": {}
            }

        self.syllabus_index[class_key]["subjects"][subject] = {
            "url": url,
            "md_file": md_file,
            "json_file": json_file,
        }

        logger.info(f"✓ Saved Class {class_num} {subject.replace('-', ' ').title()} syllabus")
        return True

    def download_all(self):
        """Download all configured syllabus pages"""
        logger.info("=" * 60)
        logger.info("Starting CBSE Syllabus Download")
        logger.info("=" * 60)

        total_downloaded = 0
        total_failed = 0

        # Download class overview syllabi
        logger.info("\n--- Downloading Class Overview Syllabi ---")
        for class_num in range(1, 13):
            if self.download_class_syllabus(class_num):
                total_downloaded += 1
            else:
                total_failed += 1

        # Download subject-specific syllabi
        logger.info("\n--- Downloading Subject-Specific Syllabi ---")
        for (class_num, subject), url_path in SUBJECT_SYLLABUS_URLS.items():
            if self.download_subject_syllabus(class_num, subject):
                total_downloaded += 1
            else:
                total_failed += 1

        # Save master index
        index_file = os.path.join(self.output_dir, INDEX_FILE)
        master_index = {
            "generated_at": datetime.now().isoformat(),
            "total_downloaded": total_downloaded,
            "total_failed": total_failed,
            "failed_urls": self.failed_urls,
            "classes": self.syllabus_index,
        }

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(master_index, f, indent=2, ensure_ascii=False)

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("Download Summary")
        logger.info("=" * 60)
        logger.info(f"Total Downloaded: {total_downloaded}")
        logger.info(f"Total Failed: {total_failed}")
        logger.info(f"Output Directory: {os.path.abspath(self.output_dir)}")
        logger.info(f"Index File: {index_file}")

        if self.failed_urls:
            logger.warning("\nFailed URLs:")
            for url in self.failed_urls:
                logger.warning(f"  - {url}")

        return total_downloaded, total_failed


def main():
    """Main entry point"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           CBSE Syllabus Downloader for LLM                   ║
║      Downloads syllabus from byjus.com as MD/JSON files      ║
╚══════════════════════════════════════════════════════════════╝
    """)

    scraper = CBSESyllabusScraper()

    try:
        total_downloaded, total_failed = scraper.download_all()

        print(f"\n{'='*60}")
        print("Download Complete!")
        print(f"{'='*60}")
        print(f"Successfully downloaded: {total_downloaded} syllabus files")
        print(f"Failed: {total_failed}")
        print(f"\nFiles saved to: {os.path.abspath(OUTPUT_DIR)}")
        print(f"Index file: {os.path.join(OUTPUT_DIR, INDEX_FILE)}")
        print("\nYou can now use these files with an LLM to generate question papers.")

    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()