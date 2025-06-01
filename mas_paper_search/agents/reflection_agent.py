from mas_paper_search.core.base_agent import BaseAgent, AgentOutput
from mas_paper_search.database.chroma_utils import get_chromadb_manager, ChromaDBManager
import logging
import uuid # For generating unique paper IDs if not provided from Arxiv ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReflectionAgent(BaseAgent):
    '''
    An agent responsible for interacting with the long-term memory (ChromaDB)
    to store paper summaries, user feedback, and retrieve learned preferences.
    '''
    def __init__(self):
        super().__init__()
        self.db_manager: ChromaDBManager = get_chromadb_manager()
        if not self.db_manager.get_collection():
            logger.error("ReflectionAgent: ChromaDB collection is not available. Agent may not function correctly.")

    async def execute_task(self, task_input: dict) -> AgentOutput:
        '''
        Executes tasks related to long-term memory.

        Supported actions (specified in task_input['action']):
        - 'store_paper_summary': Stores a paper's summary and metadata.
            Required in task_input['data']: 'summary_text', 'metadata' (dict including 'arxiv_id', 'title', etc.)
            Optional 'paper_id' in task_input['data'], defaults to metadata['arxiv_id'] or a new UUID.
        - 'store_user_feedback': Stores user feedback for a paper.
            Required in task_input['data']: 'paper_id'.
            Optional in task_input['data']: 'rating' (int), 'notes' (str).
        - 'query_similar_papers': Queries for papers similar to a given text.
            Required in task_input['data']: 'query_text' (str).
            Optional in task_input['data']: 'n_results' (int), 'where_filter' (dict).
        - 'get_papers_by_rating': Retrieves papers based on user rating.
            Required in task_input['data']: 'min_rating' (int).
            Optional in task_input['data']: 'n_results' (int).


        Returns:
            AgentOutput: Contains results of the action or an error message.
        '''
        if not self.db_manager.get_collection():
            return AgentOutput(success=False, error_message="ReflectionAgent: ChromaDB is not available.")

        action = task_input.get('action')
        data = task_input.get('data', {})

        if not action:
            return AgentOutput(success=False, error_message="ReflectionAgent: 'action' not provided in task_input.")

        logger.info(f"ReflectionAgent: Executing action '{action}' with data: {data}")

        try:
            if action == 'store_paper_summary':
                summary_text = data.get('summary_text')
                metadata = data.get('metadata')
                if not summary_text or not metadata or not isinstance(metadata, dict):
                    return AgentOutput(success=False, error_message="Missing 'summary_text' or 'metadata' for store_paper_summary.")

                # Use arxiv_id from metadata as the primary paper_id if available, else title, else UUID
                paper_id = data.get('paper_id', metadata.get('arxiv_id', metadata.get('title', str(uuid.uuid4()))))
                # Ensure arxiv_id is in metadata if not used as paper_id directly
                if 'arxiv_id' not in metadata and 'arxiv_id' in paper_id: # Heuristic if paper_id looks like an arxiv_id
                     metadata['arxiv_id'] = paper_id

                success = self.db_manager.add_paper_summary(paper_id, summary_text, metadata)
                if success:
                    return AgentOutput(success=True, data={"paper_id": paper_id, "message": "Summary stored."})
                else:
                    return AgentOutput(success=False, error_message="Failed to store summary in ChromaDB.")

            elif action == 'store_user_feedback':
                paper_id = data.get('paper_id')
                if not paper_id:
                    return AgentOutput(success=False, error_message="Missing 'paper_id' for store_user_feedback.")

                rating = data.get('rating')
                notes = data.get('notes')
                success = self.db_manager.add_user_feedback(paper_id, rating, notes)
                if success:
                    return AgentOutput(success=True, data={"paper_id": paper_id, "message": "Feedback stored."})
                else:
                    return AgentOutput(success=False, error_message="Failed to store feedback in ChromaDB.")

            elif action == 'query_similar_papers':
                query_text = data.get('query_text')
                if not query_text:
                    return AgentOutput(success=False, error_message="Missing 'query_text' for query_similar_papers.")

                n_results = data.get('n_results', 5)
                where_filter = data.get('where_filter') # e.g., {"source_query_keywords": "LLM"}

                results = self.db_manager.query_summaries(query_texts=[query_text], n_results=n_results, where_filter=where_filter)
                if results is not None:
                    return AgentOutput(success=True, data={"papers": results})
                else:
                    return AgentOutput(success=False, error_message="Error querying similar papers from ChromaDB.")

            elif action == 'get_papers_by_rating':
                min_rating = data.get('min_rating')
                if min_rating is None: # Check for None explicitly as 0 is a valid rating
                    return AgentOutput(success=False, error_message="Missing 'min_rating' for get_papers_by_rating.")

                n_results = data.get('n_results', 10)
                # Query by text that is likely to be in all papers, then filter by metadata
                # This is a workaround as ChromaDB query capabilities might be more focused on semantic similarity
                # rather than direct metadata-only queries without a query_text.
                # A common term like "research" or "model" or even a wildcard text could be used if API allows.
                # Or, query with a broad concept and then filter.
                # For now, let's assume we query broadly and filter.
                # A better way would be `collection.get` with a where filter if we don't need semantic search.
                # However, `get` might not allow complex queries like `$gte`.
                # So we use `query` with a generic query string.

                # This is a placeholder for a more robust way to get all items matching a metadata filter.
                # ChromaDB's primary use is vector search. For pure metadata filtering,
                # you might need to use `collection.get(where={"user_rating": {"$gte": min_rating}})`
                # but this might have limitations on result size or query complexity.
                # The `query` method is more flexible with `where` clauses usually.

                # Let's try querying with a very generic term and rely on the metadata filter.
                # This part may need adjustment based on ChromaDB version and capabilities.
                results = self.db_manager.query_summaries(
                    query_texts=["summary"], # Generic query text
                    n_results=n_results,
                    where_filter={"user_rating": {"$gte": int(min_rating)}}
                )
                if results is not None:
                    return AgentOutput(success=True, data={"papers": results})
                else:
                    return AgentOutput(success=False, error_message=f"Error querying papers with rating >= {min_rating}.")


            else:
                return AgentOutput(success=False, error_message=f"Unknown action: {action}")

        except Exception as e:
            logger.exception(f"ReflectionAgent: Unexpected error during action '{action}': {e}")
            return AgentOutput(success=False, error_message=f"Unexpected error in ReflectionAgent: {str(e)}")

# Example Usage (for testing purposes)
# if __name__ == "__main__":
#     import asyncio
#     async def test_reflection_agent():
#         # Ensure OPENAI_API_KEY is set if using OpenAI embeddings for Chroma
#         # This test will use the default if key is not found.
#         agent = ReflectionAgent()
#
#         # Test 1: Store paper summary
#         print("\n--- Test Case 1: Store Paper Summary ---")
#         paper_arxiv_id = "2303.10130v1" # Example Arxiv ID
#         summary_data = {
#             "action": "store_paper_summary",
#             "data": {
#                 "paper_id": paper_arxiv_id, # Using arxiv_id as the primary ID
#                 "summary_text": "This paper discusses advanced techniques in large language models and their impact on AI-driven search.",
#                 "metadata": {
#                     "arxiv_id": paper_arxiv_id,
#                     "title": "Advanced LLM Techniques",
#                     "pdf_url": f"https://arxiv.org/pdf/{paper_arxiv_id}.pdf",
#                     "authors": "Dr. AI Researcher",
#                     "source_query_keywords": "LLM, AI search"
#                 }
#             }
#         }
#         output = await agent.execute_task(summary_data)
#         print(f"Output: {output.to_dict()}")
#         stored_paper_id = output.data.get("paper_id") if output.success else paper_arxiv_id

#         # Test 2: Store user feedback
#         if stored_paper_id:
#             print("\n--- Test Case 2: Store User Feedback ---")
#             feedback_data = {
#                 "action": "store_user_feedback",
#                 "data": {
#                     "paper_id": stored_paper_id,
#                     "rating": 5,
#                     "notes": "Excellent paper, very insightful for my research on AI search."
#                 }
#             }
#             output = await agent.execute_task(feedback_data)
#             print(f"Output: {output.to_dict()}")

#         # Test 3: Query similar papers (based on the summary text of the stored paper)
#         if stored_paper_id:
#             print("\n--- Test Case 3: Query Similar Papers ---")
#             query_data = {
#                 "action": "query_similar_papers",
#                 "data": {
#                     "query_text": "impact of large language models on search technology",
#                     "n_results": 1
#                 }
#             }
#             output = await agent.execute_task(query_data)
#             print(f"Output: {output.to_dict()}")
#             if output.success and output.data.get("papers"):
#                 for paper in output.data["papers"]:
#                     print(f"  Found paper: ID {paper['paper_id']}, Title: {paper['metadata'].get('title')}, Dist: {paper.get('distance')}")

#         # Test 4: Get papers by rating
#         if stored_paper_id:
#             print("\n--- Test Case 4: Get Papers by Rating (>= 4) ---")
#             rating_query_data = {
#                 "action": "get_papers_by_rating",
#                 "data": {
#                     "min_rating": 4,
#                     "n_results": 1
#                 }
#             }
#             output = await agent.execute_task(rating_query_data)
#             print(f"Output: {output.to_dict()}")
#             if output.success and output.data.get("papers"):
#                 for paper in output.data["papers"]:
#                     print(f"  Found paper: ID {paper['paper_id']}, Title: {paper['metadata'].get('title')}, Rating: {paper['metadata'].get('user_rating')}")
#
#         # Test 5: Unknown action
#         print("\n--- Test Case 5: Unknown Action ---")
#         unknown_action_data = {"action": "non_existent_action", "data": {}}
#         output = await agent.execute_task(unknown_action_data)
#         print(f"Output: {output.to_dict()}")


#     asyncio.run(test_reflection_agent())
