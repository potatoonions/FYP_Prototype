"""
Google Scholar research integration for fetching academic sources on debate topics.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

try:
    import scholarly
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False


class ScholarResearcher:
    """Fetches research papers and summaries from Google Scholar."""
    
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
    
    def search_topic(self, topic: str) -> Dict[str, object]:
        """Search Google Scholar for papers on the topic."""
        if not SCHOLARLY_AVAILABLE:
            return self._fallback_research(topic)
        
        try:
            search_query = scholarly.search_pubs(topic)
            papers = []
            
            for i, paper in enumerate(search_query):
                if i >= self.max_results:
                    break
                
                try:
                    paper_data = {
                        "title": paper.get("bib", {}).get("title", "Unknown"),
                        "authors": paper.get("bib", {}).get("author", ["Unknown"]),
                        "year": paper.get("bib", {}).get("pub_year", "Unknown"),
                        "abstract": paper.get("bib", {}).get("abstract", "No abstract available"),
                        "url": paper.get("eprint_url", "") or paper.get("pub_url", ""),
                    }
                    papers.append(paper_data)
                except Exception:
                    continue
            
            return {
                "topic": topic,
                "papers_found": len(papers),
                "papers": papers,
                "summary": self._summarize_papers(papers),
            }
        except Exception as e:
            # Fallback if scholarly fails
            return self._fallback_research(topic)
    
    def _summarize_papers(self, papers: List[Dict]) -> str:
        """Create a summary of the research papers."""
        if not papers:
            return "No research papers found."
        
        summary = f"Found {len(papers)} relevant research papers:\n\n"
        for i, paper in enumerate(papers, 1):
            summary += f"{i}. {paper['title']}\n"
            summary += f"   Authors: {', '.join(paper['authors'][:3])}\n"
            summary += f"   Year: {paper['year']}\n"
            if paper['abstract']:
                summary += f"   Summary: {paper['abstract'][:200]}...\n\n"
        
        return summary
    
    def _fallback_research(self, topic: str) -> Dict[str, object]:
        """Fallback research when Google Scholar is unavailable."""
        return {
            "topic": topic,
            "papers_found": 0,
            "papers": [],
            "summary": f"Research context: This is a debate on '{topic}'. "
                      f"Use your knowledge and critical thinking to construct arguments.",
            "note": "Scholarly search unavailable - using fallback mode",
        }


def get_research_context(topic: str, max_results: int = 5) -> Dict[str, object]:
    """Convenience function to fetch research for a debate topic."""
    researcher = ScholarResearcher(max_results=max_results)
    return researcher.search_topic(topic)
