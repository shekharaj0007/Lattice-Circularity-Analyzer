"""Fetch papers from arXiv and process PDFs."""
import os
import requests
import PyPDF2
from typing import List, Dict
import time


class PaperFetcher:
    """Fetch and process arXiv papers."""
    
    PAPERS = [
        {"title": "Attention Is All You Need", "arxiv_id": "1706.03762v7"},
        {"title": "Moshi: a speech-text foundation model for real-time dialogue", "arxiv_id": "2410.00037v1"},
        {"title": "Dynamic Chunking for End-to-End Hierarchical Sequence Modeling", "arxiv_id": "2507.07955v2"}
    ]
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def fetch_all_papers(self) -> List[str]:
        """Fetch all configured papers and return their file paths."""
        paper_paths = []
        for paper in self.PAPERS:
            filepath = self.fetch_paper(paper["arxiv_id"], paper["title"])
            if filepath:
                paper_paths.append(filepath)
                print(f"✓ Fetched: {paper['title']}")
            else:
                print(f"✗ Failed to fetch: {paper['title']}")
        return paper_paths
    
    def fetch_paper(self, arxiv_id: str, title: str) -> str:
        """Fetch a single paper from arXiv."""
        # Remove version suffix for URL
        base_id = arxiv_id.split('v')[0]
        url = f"https://arxiv.org/pdf/{base_id}.pdf"
        
        # Sanitize filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title[:50]  # Limit length
        filepath = os.path.join(self.data_dir, f"{safe_title}_{arxiv_id}.pdf")
        
        # Skip if already downloaded
        if os.path.exists(filepath):
            print(f"Already exists: {filepath}")
            return filepath
        
        try:
            print(f"Downloading {arxiv_id} from {url}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            time.sleep(1)  # Be nice to arXiv
            return filepath
            
        except Exception as e:
            print(f"Error fetching {arxiv_id}: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def extract_all_texts(self, paper_paths: List[str]) -> List[Dict[str, str]]:
        """Extract text from all papers."""
        papers_data = []
        for path in paper_paths:
            text = self.extract_text_from_pdf(path)
            if text:
                papers_data.append({
                    "path": path,
                    "filename": os.path.basename(path),
                    "text": text,
                    "char_count": len(text)
                })
                print(f"Extracted {len(text)} characters from {os.path.basename(path)}")
        return papers_data


if __name__ == "__main__":
    fetcher = PaperFetcher()
    paths = fetcher.fetch_all_papers()
    papers_data = fetcher.extract_all_texts(paths)
    print(f"\nTotal papers: {len(papers_data)}")
    for p in papers_data:
        print(f"  {p['filename']}: {p['char_count']:,} chars")
