import arxiv

class ArxivSearchAgent:
    def __init__(self):
        pass

    def search_papers(self, keywords):
        """
        Searches Arxiv for papers based on keywords.
        """
        # TODO: Implement Arxiv search functionality
        search_query = " AND ".join(keywords)
        search = arxiv.Search(
            query=search_query,
            max_results=10,  # Limiting results for now
            sort_by=arxiv.SortCriterion.Relevance
        )
        client = arxiv.Client()
        results = []
        for result in client.results(search):
            results.append(self.extract_metadata(result))
        return results

    def extract_metadata(self, paper):
        """
        Extracts relevant metadata from an Arxiv paper object.
        """
        # TODO: Implement metadata extraction
        metadata = {
            "title": paper.title,
            "authors": [author.name for author in paper.authors],
            "abstract": paper.summary,
            "publication_date": paper.published.strftime('%Y-%m-%d')
        }
        return metadata

if __name__ == '__main__':
    agent = ArxivSearchAgent()
    keywords = ["AI agents", "LLM", "computer vision"]
    papers = agent.search_papers(keywords)
    for paper in papers:
        print(f"Title: {paper['title']}")
        print(f"Authors: {', '.join(paper['authors'])}")
        print(f"Publication Date: {paper['publication_date']}")
        print(f"Abstract: {paper['abstract']}\n")
