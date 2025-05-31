import arxiv
import re # For extracting arxiv_id
from core.models import PaperDetails

class ArxivSearchAgent:
    def __init__(self):
        self.client = arxiv.Client()

    def _extract_arxiv_id(self, entry_id: str) -> str:
        """Extracts the core arXiv ID from the entry_id URL."""
        # Entry ID is usually like 'http://arxiv.org/abs/2301.12345v1'
        # We want '2301.12345'
        match = re.search(r'abs/(\d+\.\d+)(v\d+)?', entry_id)
        if match:
            return match.group(1)
        # Fallback if parsing somehow fails, though entry_id is usually consistent
        # This might happen if a direct ID like "2301.12345" is passed (though not from arxiv.Result)
        parts = entry_id.split('/')
        return parts[-1].replace('v1', '').replace('v2', '') # basic cleanup

    def extract_metadata(self, paper: arxiv.Result) -> PaperDetails:
        """Extracts relevant metadata and returns a PaperDetails object."""
        arxiv_id = self._extract_arxiv_id(paper.entry_id)
        pdf_url = paper.pdf_url
        if not pdf_url and arxiv_id: # Construct PDF URL if missing (common)
             pdf_url = f"http://arxiv.org/pdf/{arxiv_id}"

        return PaperDetails(
            arxiv_id=arxiv_id,
            title=paper.title,
            authors=[author.name for author in paper.authors],
            publication_date=paper.published.strftime('%Y-%m-%d'),
            abstract=paper.summary, # In arxiv library, 'summary' is the abstract
            pdf_url=pdf_url
            # source defaults to 'arxiv' in the Pydantic model
        )

    def search_papers(self, keywords: list[str], max_results: int = 10) -> list[PaperDetails]:
        """
        Searches Arxiv for papers based on keywords and returns a list of PaperDetails objects.
        """
        if not keywords:
            return []
            
        search_query = " AND ".join(keywords)
        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        paper_details_list: list[PaperDetails] = []
        try:
            for result in self.client.results(search):
                paper_details_list.append(self.extract_metadata(result))
        except Exception as e:
            print(f"ArxivSearchAgent: Error during Arxiv search or metadata extraction: {e}")
            # Depending on desired robustness, could return partial results or an empty list.
            return [] 
            
        return paper_details_list

if __name__ == '__main__':
    agent = ArxivSearchAgent()
    # Test _extract_arxiv_id
    test_id_1 = agent._extract_arxiv_id("http://arxiv.org/abs/2301.12345v1")
    assert test_id_1 == "2301.12345", f"Expected 2301.12345, got {test_id_1}"
    test_id_2 = agent._extract_arxiv_id("http://arxiv.org/abs/cond-mat/0703123v2") # Older format
    assert test_id_2 == "cond-mat/0703123", f"Expected cond-mat/0703123, got {test_id_2}"
    print("ArxivSearchAgent: _extract_arxiv_id tests passed.")

    search_keywords = ["quantum machine learning", "LLM"]
    print(f"\nArxivSearchAgent: Searching for keywords: {search_keywords} (max 2 results for test)")
    papers: list[PaperDetails] = agent.search_papers(search_keywords, max_results=2)
    
    if papers:
        print(f"\nFound {len(papers)} papers:")
        for i, paper_detail in enumerate(papers):
            print(f"\n--- Paper {i+1} ---")
            assert isinstance(paper_detail, PaperDetails), f"Item {i} is not a PaperDetails object"
            print(f"Arxiv ID: {paper_detail.arxiv_id}")
            print(f"Title: {paper_detail.title}")
            print(f"Authors: {', '.join(paper_detail.authors)}")
            print(f"Publication Date: {paper_detail.publication_date}")
            print(f"PDF URL: {paper_detail.pdf_url}")
            print(f"Source: {paper_detail.source}")
            print(f"Abstract Snippet: {paper_detail.abstract[:100]}...")
        print("\nArxivSearchAgent: Basic search test completed.")
    else:
        print("ArxivSearchAgent: No papers found for the test query, or an error occurred.")
    
    print("\nArxivSearchAgent tests finished.")
