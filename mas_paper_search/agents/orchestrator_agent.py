import logging
from mas_paper_search.agents.arxiv_search_agent import ArxivSearchAgent
from mas_paper_search.agents.content_extraction_agent import ContentExtractionAgent
from mas_paper_search.agents.summarize_agent import SummarizeAgent
from mas_paper_search.agents.reflection_agent import ReflectionAgent
from mas_paper_search.core.base_agent import AgentOutput # For consistent return types if needed
import asyncio # For running async agent tasks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrchestratorAgent:
    '''
    Orchestrates the workflow between various specialized agents to find,
    process, summarize, and store academic papers.
    '''
    def __init__(self):
        self.arxiv_search_agent = ArxivSearchAgent()
        self.content_extraction_agent = ContentExtractionAgent()
        self.summarize_agent = SummarizeAgent()
        self.reflection_agent = ReflectionAgent()
        logger.info("OrchestratorAgent: Initialized with all specialized agents.")

    async def process_daily_search_and_summarize(self, search_queries: list[str], max_papers_per_query: int = 5) -> list[dict]:
        '''
        Main workflow to search for papers, extract content, summarize, and store.

        Args:
            search_queries (list[str]): A list of search queries/keywords for Arxiv.
            max_papers_per_query (int): Max number of papers to process for each query.

        Returns:
            list[dict]: A list of dictionaries, each containing info about a processed paper
                        (original data, summary, and status).
        '''
        processed_papers_overall = []

        for query_idx, query in enumerate(search_queries):
            logger.info(f"Orchestrator: Starting processing for query {query_idx+1}/{len(search_queries)}: '{query}'")

            # 1. Search Arxiv
            arxiv_task_input = {"query": query, "max_results": max_papers_per_query}
            arxiv_output = await self.arxiv_search_agent.execute_task(arxiv_task_input)

            if not arxiv_output.success or not arxiv_output.data.get("papers"):
                logger.error(f"Orchestrator: Arxiv search failed for query '{query}' or no papers found. Error: {arxiv_output.error_message}")
                continue

            papers_to_process = arxiv_output.data["papers"]
            logger.info(f"Orchestrator: Found {len(papers_to_process)} papers for query '{query}'. Processing them...")

            for paper_idx, paper_meta in enumerate(papers_to_process):
                paper_arxiv_id = paper_meta.get("arxiv_id", f"unknown_arxiv_id_{query_idx}_{paper_idx}")
                paper_title = paper_meta.get("title", "Unknown Title")
                pdf_url = paper_meta.get("pdf_url")

                current_paper_result = {
                    "query": query,
                    "arxiv_id": paper_arxiv_id,
                    "title": paper_title,
                    "pdf_url": pdf_url,
                    "status": "started",
                    "summary": None,
                    "error": None
                }
                logger.info(f"Orchestrator: Processing paper {paper_idx+1}/{len(papers_to_process)}: '{paper_title}' ({paper_arxiv_id})")

                if not pdf_url:
                    logger.warning(f"Orchestrator: No PDF URL for paper '{paper_title}'. Skipping content extraction and summarization.")
                    current_paper_result["status"] = "skipped_no_pdf_url"
                    current_paper_result["error"] = "No PDF URL provided by Arxiv."
                    processed_papers_overall.append(current_paper_result)
                    continue

                # 2. Extract Content
                extract_task_input = {"pdf_url": pdf_url}
                extract_output = await self.content_extraction_agent.execute_task(extract_task_input)

                if not extract_output.success or not extract_output.data.get("extracted_text"):
                    logger.error(f"Orchestrator: Content extraction failed for '{paper_title}' ({pdf_url}). Error: {extract_output.error_message}")
                    current_paper_result["status"] = "failed_extraction"
                    current_paper_result["error"] = extract_output.error_message or "Content extraction failed or returned no text."
                    processed_papers_overall.append(current_paper_result)
                    continue

                extracted_text = extract_output.data["extracted_text"]
                logger.info(f"Orchestrator: Successfully extracted text for '{paper_title}'. Length: {len(extracted_text)} chars.")

                # 3. Summarize Content
                # User interests could be dynamic later, for now use defaults or pass them in.
                summarize_task_input = {
                    "text_content": extracted_text,
                    "user_interests": ["AI agents", "Large Language Models", "computer vision"] # Example
                }
                summarize_output = await self.summarize_agent.execute_task(summarize_task_input)

                if not summarize_output.success or not summarize_output.data.get("summary"):
                    logger.error(f"Orchestrator: Summarization failed for '{paper_title}'. Error: {summarize_output.error_message}")
                    current_paper_result["status"] = "failed_summarization"
                    current_paper_result["error"] = summarize_output.error_message or "Summarization failed or returned no summary."
                    processed_papers_overall.append(current_paper_result)
                    continue

                summary_text = summarize_output.data["summary"]
                current_paper_result["summary"] = summary_text
                logger.info(f"Orchestrator: Successfully summarized '{paper_title}'. Summary length: {len(summary_text)} chars.")

                # 4. Store Summary and Metadata via ReflectionAgent
                # Convert authors and categories lists to strings for ChromaDB compatibility
                authors_list = paper_meta.get("authors", [])
                authors_str = ", ".join(author.name for author in authors_list) if all(hasattr(author, 'name') for author in authors_list) else ", ".join(authors_list)

                categories_list = paper_meta.get("categories", [])
                categories_str = ", ".join(categories_list)

                reflection_metadata = {
                    "arxiv_id": paper_arxiv_id,
                    "title": paper_title,
                    "pdf_url": pdf_url,
                    "authors": authors_str,
                    "published_date": paper_meta.get("published_date"),
                    "source_query": query, # The query that found this paper
                    "categories": categories_str
                }
                store_summary_input = {
                    "action": "store_paper_summary",
                    "data": {
                        "paper_id": paper_arxiv_id, # Use Arxiv ID as the unique ID in Chroma
                        "summary_text": summary_text,
                        "metadata": reflection_metadata
                    }
                }
                reflection_output = await self.reflection_agent.execute_task(store_summary_input)

                if not reflection_output.success:
                    logger.error(f"Orchestrator: Failed to store summary for '{paper_title}' in ChromaDB. Error: {reflection_output.error_message}")
                    current_paper_result["status"] = "failed_storage"
                    current_paper_result["error"] = reflection_output.error_message or "Failed to store summary."
                else:
                    logger.info(f"Orchestrator: Successfully stored summary for '{paper_title}' in ChromaDB.")
                    current_paper_result["status"] = "processed_and_stored"

                processed_papers_overall.append(current_paper_result)

                # Small delay to avoid overwhelming APIs, especially Arxiv if downloading many PDFs quickly
                await asyncio.sleep(1)

        logger.info(f"Orchestrator: Finished processing all queries. Total papers processed/attempted: {len(processed_papers_overall)}")
        return processed_papers_overall

# Example Usage (for testing purposes, requires valid OpenAI API key for summarization and storage)
# if __name__ == "__main__":
#     async def main_orchestrator_test():
#         orchestrator = OrchestratorAgent()
#
#         # Define search queries based on user's interests
#         # Using specific Arxiv categories for focused results in testing
#         # cat:cs.AI (AI), cat:cs.CL (Computation and Language -> LLMs), cat:cs.CV (Computer Vision)
#         test_queries = [
#             "cat:cs.AI AND (agent OR multi-agent)",
#             "cat:cs.CL AND (LLM OR \"large language model\")", # Corrected missing quote
#             "cat:cs.CV AND (recognition OR detection)"
#         ]
#
#         # To avoid excessive API calls during a typical test run, limit max_papers_per_query
#         # Set this higher for actual daily runs.
#         # For testing, especially with PDF downloads and LLM calls, 1-2 papers per query is often enough.
#         results = await orchestrator.process_daily_search_and_summarize(
#             search_queries=test_queries,
#             max_papers_per_query=1 # Low number for quick testing
#         )
#
#         print("\n--- Orchestrator Test Results ---")
#         if results:
#             for i, result in enumerate(results):
#                 print(f"Result {i+1}:")
#                 print(f"  Query: {result['query']}")
#                 print(f"  Title: {result['title']}")
#                 print(f"  Arxiv ID: {result['arxiv_id']}")
#                 print(f"  Status: {result['status']}")
#                 if result.get('summary'):
#                     print(f"  Summary: {result['summary'][:100]}...") # Print first 100 chars
#                 if result.get('error'):
#                     print(f"  Error: {result['error']}")
#                 print("-" * 20)
#         else:
#             print("No results returned from orchestrator, or an issue occurred.")

#     # Setup PYTHONPATH for local module resolution if needed when running directly
#     # import sys
#     # import os
#     # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
#
#     asyncio.run(main_orchestrator_test())
