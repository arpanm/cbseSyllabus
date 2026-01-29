#!/usr/bin/env python3
"""
CBSE Syllabus Downloader

This script downloads CBSE syllabus from byjus.com for classes 1-12 across
multiple subjects. The content is saved as markdown files and a JSON index
for LLM-based question paper generation.

Features:
- Downloads HTML content from syllabus pages
- Detects and downloads embedded PDF files
- Parses PDF content using multiple methods (pymupdf, pdfplumber, PyPDF2)
- Extracts structured syllabus data for LLM consumption

Usage:
    python download_syllabus.py
"""

import os
import re
import json
import time
import random
import logging
import tempfile
import io
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# PDF parsing libraries - try multiple options for compatibility
PDF_PARSER_AVAILABLE = False
PDF_PARSER_NAME = None

try:
    import fitz  # PyMuPDF - best for complex PDFs
    PDF_PARSER_AVAILABLE = True
    PDF_PARSER_NAME = "pymupdf"
except ImportError:
    pass

if not PDF_PARSER_AVAILABLE:
    try:
        import pdfplumber  # Good alternative
        PDF_PARSER_AVAILABLE = True
        PDF_PARSER_NAME = "pdfplumber"
    except ImportError:
        pass

if not PDF_PARSER_AVAILABLE:
    try:
        import PyPDF2  # Basic fallback
        PDF_PARSER_AVAILABLE = True
        PDF_PARSER_NAME = "PyPDF2"
    except ImportError:
        pass

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
    2: "/cbse-class-2-syllabus/",  # Fixed: root level URL
    3: "/cbse/cbse-syllabus-for-class-3/",
    4: "/cbse/cbse-syllabus-class-4/",
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
    # Class 1 - URLs at root level (no EVS for class 1-2)
    (1, "maths"): "/cbse-class-1-maths-syllabus/",
    (1, "english"): "/cbse-class-1-english-syllabus/",
    (1, "hindi"): "/cbse-class-1-hindi-syllabus/",

    # Class 2 - URLs at root level (no EVS for class 1-2)
    (2, "maths"): "/cbse-class-2-maths-syllabus/",
    (2, "english"): "/cbse-class-2-english-syllabus/",
    (2, "hindi"): "/cbse-class-2-hindi-syllabus/",

    # Class 3 - URLs at root level
    (3, "maths"): "/cbse-class-3-maths-syllabus/",
    (3, "english"): "/cbse-class-3-english-syllabus/",
    (3, "hindi"): "/cbse-class-3-hindi-syllabus/",
    (3, "evs"): "/cbse/class-3-science-syllabus/",  # Uses science URL for EVS

    # Class 4 - URLs with /cbse/ prefix for maths
    (4, "maths"): "/cbse/class-4-maths-syllabus/",
    (4, "english"): "/cbse-class-4-english-syllabus/",
    (4, "hindi"): "/cbse-class-4-hindi-syllabus/",
    (4, "evs"): "/cbse/class-4-evs-syllabus/",

    # Class 5 - URLs with /cbse/ prefix for maths and evs
    (5, "maths"): "/cbse/class-5-maths-syllabus/",
    (5, "english"): "/cbse-class-5-english-syllabus/",
    (5, "hindi"): "/cbse-class-5-hindi-syllabus/",
    (5, "evs"): "/cbse/class-5-science-syllabus/",  # Fixed: uses science URL

    # Class 6 - Mixed URL patterns
    (6, "maths"): "/cbse/class-6-maths-syllabus/",
    (6, "english"): "/cbse-class-6-english-syllabus/",  # Fixed: root level URL
    (6, "hindi"): "/cbse-class-6-hindi-syllabus/",  # Added back: exists at root level
    (6, "science"): "/cbse/cbse-class-6-science-syllabus/",  # Fixed: with cbse- prefix
    (6, "social-science"): "/cbse-class-6-social-science-syllabus/",  # Fixed: root level URL

    # Class 7 - Mixed URL patterns
    (7, "maths"): "/cbse/class-7-maths-syllabus/",
    (7, "english"): "/cbse-class-7-english-syllabus/",  # Fixed: root level URL
    (7, "science"): "/cbse/cbse-class-7-science-syllabus/",  # Fixed: with cbse- prefix
    (7, "social-science"): "/cbse-class-7-social-science-syllabus/",  # Fixed: root level URL

    # Class 8 - Mixed URL patterns
    (8, "maths"): "/cbse/class-8-maths-syllabus/",
    (8, "english"): "/cbse-class-8-english-syllabus/",  # Fixed: root level URL
    (8, "science"): "/cbse/cbse-class-8-science-syllabus/",  # Fixed: with cbse- prefix
    (8, "social-science"): "/cbse-class-8-social-science-syllabus/",

    # Class 9 - Mixed URL patterns
    (9, "maths"): "/cbse/class-9-maths-syllabus/",
    (9, "english"): "/cbse-class-9-english-syllabus/",  # Fixed: root level URL
    (9, "science"): "/cbse/cbse-class-9-science-syllabus/",  # Fixed: with cbse- prefix
    (9, "social-science"): "/cbse/class-9-social-science-syllabus/",

    # Class 10 - Mixed URL patterns with different naming conventions
    (10, "maths"): "/cbse/class-10-maths-syllabus/",
    (10, "english"): "/cbse/english-language-literature-class-10-syllabus/",  # Fixed: different pattern
    (10, "science"): "/cbse/cbse-class-10-science-syllabus/",  # Fixed: with cbse- prefix
    (10, "social-science"): "/cbse/social-science-class-10-syllabus/",  # Fixed: different pattern

    # Class 11 - Mixed URL patterns
    (11, "maths"): "/cbse/class-11-maths-syllabus/",
    (11, "physics"): "/cbse/class-11-physics-syllabus/",
    (11, "chemistry"): "/cbse/class-11-chemistry-syllabus/",
    (11, "biology"): "/cbse/class-11-biology-syllabus/",
    (11, "english"): "/cbse-class-11-english-syllabus/",  # Root level URL
    (11, "accountancy"): "/cbse/class-11-accountancy-syllabus/",
    (11, "economics"): "/cbse/class-11-economics-syllabus/",
    (11, "business-studies"): "/cbse/class-11-business-studies-syllabus/",
    (11, "computer-science"): "/cbse-class-11-computer-science-syllabus/",  # Root level URL
    (11, "physical-education"): "/cbse-class-11-physical-education-syllabus/",  # Root level URL

    # Class 12 - Mixed URL patterns
    (12, "maths"): "/cbse/class-12-maths-syllabus/",
    (12, "physics"): "/cbse/class-12-physics-syllabus/",
    (12, "chemistry"): "/cbse/class-12-chemistry-syllabus/",
    (12, "biology"): "/cbse/class-12-biology-syllabus/",
    (12, "english"): "/cbse-class-12-english-syllabus/",  # Root level URL
    (12, "accountancy"): "/cbse/class-12-accountancy-syllabus/",
    (12, "economics"): "/cbse/class-12-economics-syllabus/",
    (12, "business-studies"): "/cbse/class-12-business-studies-syllabus/",
    (12, "computer-science"): "/cbse-class-12-computer-science-syllabus/",  # Root level URL
    (12, "physical-education"): "/cbse-class-12-physical-education-syllabus/",  # Root level URL
}


class CBSESyllabusScraper:
    """Scraper for downloading CBSE syllabus from byjus.com"""

    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.syllabus_index: Dict[str, dict] = {}
        self.failed_urls: List[str] = []
        self.pdf_dir = os.path.join(output_dir, "pdfs")

        # Create output directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(self.pdf_dir, exist_ok=True)

        if PDF_PARSER_AVAILABLE:
            logger.info(f"PDF parser available: {PDF_PARSER_NAME}")
        else:
            logger.warning("No PDF parser available. Install pymupdf, pdfplumber, or PyPDF2")

    def _find_pdf_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find all PDF links on the page"""
        pdf_links = []

        # Find direct PDF links
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href.lower().endswith('.pdf') or '/pdf/' in href.lower() or 'pdf' in href.lower():
                full_url = urljoin(base_url, href)
                if full_url not in pdf_links:
                    pdf_links.append(full_url)

        # Find PDF links in iframes or embeds
        for iframe in soup.find_all(['iframe', 'embed', 'object']):
            src = iframe.get('src') or iframe.get('data')
            if src and ('.pdf' in src.lower() or '/pdf/' in src.lower()):
                full_url = urljoin(base_url, src)
                if full_url not in pdf_links:
                    pdf_links.append(full_url)

        # Find PDF links in onclick handlers or data attributes
        for elem in soup.find_all(attrs={'onclick': True}):
            onclick = elem.get('onclick', '')
            pdf_match = re.search(r"['\"]([^'\"]*\.pdf[^'\"]*)['\"]", onclick, re.I)
            if pdf_match:
                full_url = urljoin(base_url, pdf_match.group(1))
                if full_url not in pdf_links:
                    pdf_links.append(full_url)

        # Look for CDN links (byjus uses cdn1.byjus.com for PDFs)
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if 'cdn' in href.lower() and ('byjus' in href.lower() or '.pdf' in href.lower()):
                if href not in pdf_links:
                    pdf_links.append(href)

        return pdf_links

    def _download_pdf(self, url: str, retries: int = 3) -> Optional[bytes]:
        """Download PDF content with multiple retry strategies"""
        headers_options = [
            # Standard browser headers
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/pdf,*/*',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            # PDF-specific headers
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
                'Accept': 'application/pdf',
            },
            # Minimal headers
            {
                'User-Agent': 'Mozilla/5.0',
            },
        ]

        for headers in headers_options:
            for attempt in range(retries):
                try:
                    time.sleep(random.uniform(1, 2))
                    response = requests.get(url, headers=headers, timeout=60, stream=True)

                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        if 'pdf' in content_type or url.lower().endswith('.pdf'):
                            return response.content
                        # Some servers don't set content-type correctly
                        content = response.content
                        if content[:4] == b'%PDF':
                            return content
                    elif response.status_code == 403:
                        logger.debug(f"PDF access forbidden with current headers, trying alternative")
                        break  # Try next headers
                    elif response.status_code == 404:
                        logger.warning(f"PDF not found: {url}")
                        return None

                except requests.exceptions.RequestException as e:
                    logger.debug(f"PDF download attempt {attempt + 1} failed: {e}")
                    time.sleep(2 ** attempt)

        logger.warning(f"Failed to download PDF: {url}")
        return None

    def _parse_pdf_pymupdf(self, pdf_content: bytes) -> str:
        """Parse PDF using PyMuPDF (fitz)"""
        try:
            import fitz
            text_parts = []

            with fitz.open(stream=pdf_content, filetype="pdf") as doc:
                for page_num, page in enumerate(doc):
                    text = page.get_text()
                    if text.strip():
                        text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"PyMuPDF parsing error: {e}")
            return ""

    def _parse_pdf_pdfplumber(self, pdf_content: bytes) -> str:
        """Parse PDF using pdfplumber"""
        try:
            import pdfplumber
            text_parts = []

            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

                    # Also try to extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            table_text = "\n".join([" | ".join([cell or "" for cell in row]) for row in table if row])
                            if table_text.strip():
                                text_parts.append(f"[Table]\n{table_text}")

            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"pdfplumber parsing error: {e}")
            return ""

    def _parse_pdf_pypdf2(self, pdf_content: bytes) -> str:
        """Parse PDF using PyPDF2"""
        try:
            import PyPDF2
            text_parts = []

            reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"PyPDF2 parsing error: {e}")
            return ""

    def _parse_pdf(self, pdf_content: bytes, pdf_url: str) -> str:
        """Parse PDF content using available parser with fallbacks"""
        if not PDF_PARSER_AVAILABLE:
            logger.warning("No PDF parser available")
            return ""

        text = ""

        # Try parsers in order of preference
        if PDF_PARSER_NAME == "pymupdf" or not text:
            try:
                import fitz
                text = self._parse_pdf_pymupdf(pdf_content)
                if text:
                    logger.debug(f"Successfully parsed PDF with PyMuPDF: {pdf_url}")
            except ImportError:
                pass

        if not text:
            try:
                import pdfplumber
                text = self._parse_pdf_pdfplumber(pdf_content)
                if text:
                    logger.debug(f"Successfully parsed PDF with pdfplumber: {pdf_url}")
            except ImportError:
                pass

        if not text:
            try:
                import PyPDF2
                text = self._parse_pdf_pypdf2(pdf_content)
                if text:
                    logger.debug(f"Successfully parsed PDF with PyPDF2: {pdf_url}")
            except ImportError:
                pass

        return text

    def _extract_pdf_content(self, soup: BeautifulSoup, url: str, class_num: int, subject: str = None) -> Dict:
        """Extract content from PDFs linked on the page"""
        pdf_content = {
            "pdf_urls": [],
            "pdf_text": "",
            "pdf_count": 0
        }

        if not PDF_PARSER_AVAILABLE:
            return pdf_content

        pdf_links = self._find_pdf_links(soup, url)

        if pdf_links:
            logger.info(f"Found {len(pdf_links)} PDF link(s) on {url}")

            all_pdf_text = []
            for pdf_url in pdf_links:
                logger.info(f"  Downloading PDF: {pdf_url}")
                pdf_bytes = self._download_pdf(pdf_url)

                if pdf_bytes:
                    # Save PDF file
                    pdf_filename = f"class_{class_num}_{subject or 'overview'}_{len(pdf_content['pdf_urls']) + 1}.pdf"
                    pdf_path = os.path.join(self.pdf_dir, pdf_filename)
                    try:
                        with open(pdf_path, 'wb') as f:
                            f.write(pdf_bytes)
                        logger.info(f"  Saved PDF: {pdf_filename}")
                    except Exception as e:
                        logger.error(f"  Failed to save PDF: {e}")

                    # Parse PDF
                    text = self._parse_pdf(pdf_bytes, pdf_url)
                    if text:
                        all_pdf_text.append(f"=== PDF: {pdf_url} ===\n{text}")
                        pdf_content["pdf_urls"].append(pdf_url)
                        pdf_content["pdf_count"] += 1
                        logger.info(f"  ✓ Extracted {len(text)} characters from PDF")
                    else:
                        logger.warning(f"  Could not extract text from PDF: {pdf_url}")
                else:
                    logger.warning(f"  Failed to download PDF: {pdf_url}")

            pdf_content["pdf_text"] = "\n\n".join(all_pdf_text)

        return pdf_content

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

    def _extract_syllabus_content(self, soup: BeautifulSoup, url: str, class_num: int = None, subject: str = None) -> Dict:
        """Extract syllabus content from the page including PDFs"""
        content = {
            "url": url,
            "title": "",
            "description": "",
            "units": [],
            "chapters": [],
            "topics": [],
            "marking_scheme": [],
            "raw_content": "",
            "pdf_content": "",
            "pdf_urls": [],
            "extracted_at": datetime.now().isoformat(),
        }

        # Extract PDF content first
        if class_num is not None:
            pdf_data = self._extract_pdf_content(soup, url, class_num, subject)
            content["pdf_content"] = pdf_data.get("pdf_text", "")
            content["pdf_urls"] = pdf_data.get("pdf_urls", [])

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

        # PDF Content (extracted from syllabus PDFs)
        if content.get("pdf_content"):
            md_lines.append("## PDF Syllabus Content\n")
            if content.get("pdf_urls"):
                md_lines.append("**Source PDFs:**")
                for pdf_url in content["pdf_urls"]:
                    md_lines.append(f"- {pdf_url}")
                md_lines.append("")
            md_lines.append("### Extracted Content\n")
            md_lines.append("```")
            # Include more PDF content since it's the primary source
            md_lines.append(content["pdf_content"][:50000])
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
        content = self._extract_syllabus_content(soup, url, class_num=class_num)

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
        content = self._extract_syllabus_content(soup, url, class_num=class_num, subject=subject)

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

    def reparse_local_pdfs(self):
        """Parse all local PDFs and update corresponding JSON/MD files"""
        if not PDF_PARSER_AVAILABLE:
            logger.error("No PDF parser available. Install pymupdf, pdfplumber, or PyPDF2")
            return 0, 0

        logger.info("=" * 60)
        logger.info("Re-parsing Local PDFs and Updating JSON/MD Files")
        logger.info("=" * 60)

        updated = 0
        failed = 0

        # Get all PDF files
        pdf_files = []
        if os.path.exists(self.pdf_dir):
            pdf_files = [f for f in os.listdir(self.pdf_dir) if f.endswith('.pdf')]

        logger.info(f"Found {len(pdf_files)} PDF files in {self.pdf_dir}")

        # Group PDFs by class and subject
        pdf_groups = {}
        for pdf_file in pdf_files:
            # Parse filename: class_{num}_{subject}_{index}.pdf
            match = re.match(r'class_(\d+)_(.+?)_(\d+)\.pdf', pdf_file)
            if match:
                class_num = int(match.group(1))
                subject = match.group(2)
                key = (class_num, subject)
                if key not in pdf_groups:
                    pdf_groups[key] = []
                pdf_groups[key].append(pdf_file)

        # Process each class/subject combination
        for (class_num, subject), pdfs in pdf_groups.items():
            logger.info(f"\nProcessing Class {class_num} {subject}: {len(pdfs)} PDF(s)")

            # Read and parse all PDFs for this subject
            all_pdf_text = []
            pdf_urls = []

            for pdf_file in sorted(pdfs):
                pdf_path = os.path.join(self.pdf_dir, pdf_file)
                try:
                    with open(pdf_path, 'rb') as f:
                        pdf_bytes = f.read()

                    text = self._parse_pdf(pdf_bytes, pdf_path)
                    if text:
                        all_pdf_text.append(f"=== PDF: {pdf_file} ===\n{text}")
                        pdf_urls.append(pdf_path)
                        logger.info(f"  ✓ Parsed {pdf_file}: {len(text)} chars")
                    else:
                        logger.warning(f"  Could not extract text from {pdf_file}")
                except Exception as e:
                    logger.error(f"  Error reading {pdf_file}: {e}")

            if not all_pdf_text:
                logger.warning(f"  No text extracted for Class {class_num} {subject}")
                failed += 1
                continue

            pdf_content = "\n\n".join(all_pdf_text)

            # Find corresponding JSON file
            class_dir = os.path.join(self.output_dir, f"class_{class_num}")
            clean_subject = subject.replace('-', '_')

            # Try different filename patterns
            json_patterns = [
                f"class_{class_num}_{clean_subject}_syllabus.json",
                f"class_{class_num}_{subject}_syllabus.json",
                f"class_{class_num}_{clean_subject}.json",
                f"class_{class_num}_overview.json" if subject == "overview" else None,
            ]

            json_file = None
            for pattern in json_patterns:
                if pattern:
                    candidate = os.path.join(class_dir, pattern)
                    if os.path.exists(candidate):
                        json_file = candidate
                        break

            if not json_file:
                logger.warning(f"  No JSON file found for Class {class_num} {subject}")
                failed += 1
                continue

            # Update JSON file
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)

                # Update PDF content
                content["pdf_content"] = pdf_content
                content["pdf_local_files"] = [os.path.join(self.pdf_dir, p) for p in pdfs]
                content["pdf_parsed_at"] = datetime.now().isoformat()

                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(content, f, indent=2, ensure_ascii=False)

                logger.info(f"  ✓ Updated JSON: {json_file}")

                # Update corresponding MD file
                md_file = json_file.replace('.json', '.md')
                if os.path.exists(md_file):
                    md_content = self._content_to_markdown(content, class_num, subject if subject != "overview" else None)
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(md_content)
                    logger.info(f"  ✓ Updated MD: {md_file}")

                updated += 1

            except Exception as e:
                logger.error(f"  Error updating files for Class {class_num} {subject}: {e}")
                failed += 1

        logger.info("\n" + "=" * 60)
        logger.info(f"Re-parse Summary: Updated {updated}, Failed {failed}")
        logger.info("=" * 60)

        return updated, failed

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
    import argparse

    parser = argparse.ArgumentParser(
        description="CBSE Syllabus Downloader - Downloads syllabus from byjus.com as MD/JSON files"
    )
    parser.add_argument(
        '--reparse-pdfs',
        action='store_true',
        help='Re-parse local PDF files and update JSON/MD files with extracted content'
    )
    parser.add_argument(
        '--download',
        action='store_true',
        help='Download syllabus from byjus.com (default action if no flags specified)'
    )

    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════════════╗
║           CBSE Syllabus Downloader for LLM                   ║
║      Downloads syllabus from byjus.com as MD/JSON files      ║
╚══════════════════════════════════════════════════════════════╝
    """)

    scraper = CBSESyllabusScraper()

    try:
        if args.reparse_pdfs:
            # Re-parse local PDFs and update JSON/MD files
            updated, failed = scraper.reparse_local_pdfs()

            print(f"\n{'='*60}")
            print("PDF Re-parsing Complete!")
            print(f"{'='*60}")
            print(f"Successfully updated: {updated} files")
            print(f"Failed: {failed}")
            print(f"\nFiles updated in: {os.path.abspath(OUTPUT_DIR)}")
        else:
            # Default: download all syllabus
            total_downloaded, total_failed = scraper.download_all()

            print(f"\n{'='*60}")
            print("Download Complete!")
            print(f"{'='*60}")
            print(f"Successfully downloaded: {total_downloaded} syllabus files")
            print(f"Failed: {total_failed}")
            print(f"\nFiles saved to: {os.path.abspath(OUTPUT_DIR)}")
            print(f"Index file: {os.path.join(OUTPUT_DIR, INDEX_FILE)}")
            print("\nYou can now use these files with an LLM to generate question papers.")
            print("\nTip: Run with --reparse-pdfs to re-parse local PDFs and update JSON/MD files.")

    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()