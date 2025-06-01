import arxiv
from mas_paper_search.core.base_agent import BaseAgent, AgentOutput
from mas_paper_search.config.settings import settings
import logging
import httpx

# Configure logging for the agent
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArxivSearchAgent(BaseAgent):
    '''
    An agent responsible for searching academic papers on Arxiv
    based on given keywords and parameters.
    '''

    async def execute_task(self, task_input: dict) -> AgentOutput:
        '''
        Executes the Arxiv search task.

        Args:
            task_input (dict): A dictionary containing:
                - 'query' (str): The search query (e.g., keywords).
                - 'max_results' (int, optional): Maximum number of papers to retrieve.
                                                 Defaults to settings.ARXIV_MAX_RESULTS.

        Returns:
            AgentOutput: An object containing the search results or an error message.
        '''
        query = task_input.get('query')
        if not query:
            logger.error("ArxivSearchAgent: 'query' not provided in task_input.")
            return AgentOutput(success=False, error_message="'query' is required for Arxiv search.")

        max_results = task_input.get('max_results', settings.ARXIV_MAX_RESULTS)
        logger.info(f"ArxivSearchAgent: Searching Arxiv for query='{query}' with max_results={max_results}")

        try:
            # Using httpx.Client as a context manager for the arxiv client
            # The arxiv library's default client can sometimes hang in async environments
            # if not properly managed. Using our own client instance is safer.
            # However, the `arxiv` library itself is synchronous.
            # For a truly async operation, one would need to run this in a thread pool
            # or use an async-native arxiv library if one exists.
            # For now, we'll call it synchronously but within an async method.

            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate # Get the latest papers
            )

            # The arxiv library's Search.results() is a generator.
            # We need to consume it to get the list of papers.
            # The library handles its own client internally for fetching.

            papers_data = []
            for r in search.results():
                paper_info = {
                    "arxiv_id": r.entry_id.split('/')[-1], # Extract ID like '2303.10130v1'
                    "title": r.title,
                    "summary": r.summary,
                    "authors": [author.name for author in r.authors],
                    "pdf_url": r.pdf_url,
                    "published_date": r.published.isoformat(),
                    "updated_date": r.updated.isoformat(),
                    "primary_category": r.primary_category,
                    "categories": r.categories
                }
                papers_data.append(paper_info)

            if not papers_data:
                logger.info(f"ArxivSearchAgent: No papers found for query='{query}'.")
                return AgentOutput(success=True, data={"papers": [], "message": "No papers found."})

            logger.info(f"ArxivSearchAgent: Found {len(papers_data)} papers for query='{query}'.")
            return AgentOutput(success=True, data={"papers": papers_data})

        except httpx.RequestError as e:
            logger.error(f"ArxivSearchAgent: Network error during Arxiv search for query='{query}': {e}")
            return AgentOutput(success=False, error_message=f"Network error during Arxiv search: {str(e)}")
        except Exception as e:
            logger.exception(f"ArxivSearchAgent: An unexpected error occurred during Arxiv search for query='{query}': {e}")
            return AgentOutput(success=False, error_message=f"An unexpected error occurred: {str(e)}")

# Example Usage (for testing purposes, can be removed or commented out later)
if __name__ == "__main__":
    import asyncio
    async def test_arxiv_search():
        agent = ArxivSearchAgent()
        # Test case 1: Valid query
        output = await agent.execute_task({"query": "LLM agents", "max_results": 3})
        print("\n--- Test Case 1: Valid Query ---")
        if output.success:
            print(f"Found papers: {len(output.data.get('papers', []))}")
            for paper in output.data.get('papers', []):
                print(f"  Title: {paper['title']}")
                print(f"  Arxiv ID: {paper['arxiv_id']}")
                print(f"  PDF URL: {paper['pdf_url']}")
                print(f"  Published: {paper['published_date']}")
                print("-" * 20)
        else:
            print(f"Error: {output.error_message}")

        # Test case 2: Query that might return no results
        output_no_results = await agent.execute_task({"query": "nonexistenttopicxyz123", "max_results": 3})
        print("\n--- Test Case 2: No Results ---")
        if output_no_results.success:
            print(f"Message: {output_no_results.data.get('message')}")
            print(f"Found papers: {len(output_no_results.data.get('papers', []))}")
        else:
            print(f"Error: {output_no_results.error_message}")

        # Test case 3: Missing query
        output_missing_query = await agent.execute_task({})
        print("\n--- Test Case 3: Missing Query ---")
        if not output_missing_query.success:
            print(f"Error: {output_missing_query.error_message}")
        else:
            print("Test failed: Should have reported an error for missing query.")


    #     asyncio.run(test_arxiv_search())
