"""
Google Scholar research integration for fetching academic sources on debate topics.
"""
from __future__ import annotations

import logging
import signal
from typing import Dict, List, Optional

try:
    import scholarly
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False

logger = logging.getLogger("trainer.services.research")


class TimeoutError(Exception):
    """Custom timeout exception for research operations."""
    pass


def _timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutError("Research operation timed out")


class ScholarResearcher:
    """Fetches research papers and summaries from Google Scholar."""
    
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
    
    def search_topic(self, topic: str, timeout: int = 15) -> Dict[str, object]:
        """
        Search Google Scholar for papers on the topic.
        
        Args:
            topic: Research topic to search for
            timeout: Maximum time in seconds to wait for results (default: 15)
        
        Returns:
            Dictionary with research results or fallback data
        """
        if not SCHOLARLY_AVAILABLE:
            logger.debug(f"Scholarly not available, using fallback for topic: {topic}")
            return self._fallback_research(topic)
        
        try:
            logger.info(f"Searching Google Scholar for topic: {topic}")
            
            # Set up timeout (Unix only - Windows will skip this)
            try:
                signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(timeout)
            except (AttributeError, OSError):
                # Windows doesn't support SIGALRM, timeout handled differently
                pass
            
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
                    except Exception as e:
                        logger.debug(f"Error processing paper {i}: {str(e)}")
                        continue
                
                # Cancel timeout
                try:
                    signal.alarm(0)
                except (AttributeError, OSError):
                    pass
                
                result = {
                    "topic": topic,
                    "papers_found": len(papers),
                    "papers": papers,
                    "summary": self._summarize_papers(papers),
                }
                logger.info(f"Found {len(papers)} papers for topic: {topic}")
                return result
                
            except TimeoutError:
                logger.warning(f"Research timeout for topic: {topic} after {timeout}s")
                try:
                    signal.alarm(0)
                except (AttributeError, OSError):
                    pass
                return self._fallback_research(topic)
                
        except Exception as e:
            logger.error(f"Error searching Google Scholar for topic '{topic}': {str(e)}", exc_info=True)
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


# Curated reference sources for common debate topics
REFERENCE_SOURCES = {
    "artificial intelligence": [
        {
            "title": "Artificial Intelligence: A Modern Approach",
            "authors": ["Stuart Russell", "Peter Norvig"],
            "year": "2020",
            "type": "book",
            "url": "https://aima.cs.berkeley.edu/",
            "description": "The definitive textbook on AI covering machine learning, reasoning, planning, and ethics."
        },
        {
            "title": "Ethics of Artificial Intelligence and Robotics",
            "authors": ["Stanford Encyclopedia of Philosophy"],
            "year": "2023",
            "type": "article",
            "url": "https://plato.stanford.edu/entries/ethics-ai/",
            "description": "Comprehensive philosophical analysis of AI ethics, bias, and accountability."
        },
        {
            "title": "UNESCO Recommendation on the Ethics of AI",
            "authors": ["UNESCO"],
            "year": "2021",
            "type": "report",
            "url": "https://www.unesco.org/en/artificial-intelligence/recommendation-ethics",
            "description": "First global standard on AI ethics adopted by 193 countries."
        },
    ],
    "climate": [
        {
            "title": "IPCC Sixth Assessment Report",
            "authors": ["Intergovernmental Panel on Climate Change"],
            "year": "2023",
            "type": "report",
            "url": "https://www.ipcc.ch/assessment-report/ar6/",
            "description": "Authoritative scientific assessment of climate change causes, impacts, and solutions."
        },
        {
            "title": "The Economics of Climate Change",
            "authors": ["Nicholas Stern"],
            "year": "2007",
            "type": "book",
            "url": "https://www.lse.ac.uk/granthaminstitute/publication/the-economics-of-climate-change-the-stern-review/",
            "description": "Landmark economic analysis of climate change and policy responses."
        },
    ],
    "healthcare": [
        {
            "title": "World Health Organization Reports",
            "authors": ["WHO"],
            "year": "2023",
            "type": "report",
            "url": "https://www.who.int/publications",
            "description": "Global health statistics, guidelines, and policy recommendations."
        },
        {
            "title": "The Lancet",
            "authors": ["Various"],
            "year": "2023",
            "type": "journal",
            "url": "https://www.thelancet.com/",
            "description": "Leading peer-reviewed medical journal with high-impact research."
        },
    ],
    "education": [
        {
            "title": "OECD Education at a Glance",
            "authors": ["OECD"],
            "year": "2023",
            "type": "report",
            "url": "https://www.oecd.org/education/education-at-a-glance/",
            "description": "Comprehensive international statistics on education systems worldwide."
        },
        {
            "title": "Visible Learning",
            "authors": ["John Hattie"],
            "year": "2008",
            "type": "book",
            "url": "https://visible-learning.org/",
            "description": "Meta-analysis of educational research identifying effective teaching strategies."
        },
    ],
    "default": [
        {
            "title": "Stanford Encyclopedia of Philosophy",
            "authors": ["Stanford University"],
            "year": "2023",
            "type": "encyclopedia",
            "url": "https://plato.stanford.edu/",
            "description": "Authoritative reference for philosophical topics and ethical debates."
        },
        {
            "title": "Academic databases (JSTOR, Google Scholar)",
            "authors": ["Various"],
            "year": "2023",
            "type": "database",
            "url": "https://scholar.google.com/",
            "description": "Search peer-reviewed academic papers on your topic."
        },
        {
            "title": "Pew Research Center",
            "authors": ["Pew Research"],
            "year": "2023",
            "type": "report",
            "url": "https://www.pewresearch.org/",
            "description": "Non-partisan data and analysis on social issues and public opinion."
        },
    ],
}


def get_reference_sources(topic: str) -> List[Dict]:
    """
    Get curated reference sources relevant to the debate topic.
    
    Args:
        topic: The debate topic to find sources for
        
    Returns:
        List of source dictionaries with title, authors, url, etc.
    """
    topic_lower = topic.lower()
    sources = []
    
    # Check for keyword matches in topic
    for keyword, keyword_sources in REFERENCE_SOURCES.items():
        if keyword != "default" and keyword in topic_lower:
            sources.extend(keyword_sources)
    
    # Add default sources if no specific matches or to supplement
    if len(sources) < 3:
        sources.extend(REFERENCE_SOURCES["default"])
    
    # Remove duplicates while preserving order
    seen_titles = set()
    unique_sources = []
    for source in sources:
        if source["title"] not in seen_titles:
            seen_titles.add(source["title"])
            unique_sources.append(source)
    
    return unique_sources[:5]  # Return top 5 sources
