import chromadb
from chromadb.utils import embedding_functions
from mas_paper_search.config.settings import settings
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChromaDBManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ChromaDBManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
            # Using OpenAI's embedding function if API key is available, else default.
            # Note: This requires the openai library to be installed and API key configured.
            # If you prefer not to use OpenAI embeddings here or want a fallback,
            # you could use chromadb's default SentenceTransformer based embeddings.
            # For this project, we'll try to use OpenAI if available for consistency with SummarizeAgent.
            if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "YOUR_OPENAI_API_KEY_HERE":
                self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=settings.OPENAI_API_KEY,
                    model_name="text-embedding-ada-002" # A common OpenAI embedding model
                )
                logger.info("ChromaDBManager: Initialized with OpenAI embeddings.")
            else:
                logger.warning("ChromaDBManager: OpenAI API key not found or is a placeholder. Falling back to default ChromaDB embedding function. This may have performance/accuracy implications.")
                self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
                logger.info("ChromaDBManager: Initialized with default ChromaDB embeddings.")

            self.collection_name = settings.CHROMA_COLLECTION_NAME
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"ChromaDBManager: Successfully connected to ChromaDB and got/created collection '{self.collection_name}'. Path: {settings.CHROMA_DB_PATH}")
            self._initialized = True

        except Exception as e:
            logger.exception(f"ChromaDBManager: Failed to initialize ChromaDB client or collection: {e}")
            # Set client and collection to None so agent can check and fail gracefully
            self.client = None
            self.collection = None
            self._initialized = True # Mark as initialized to prevent re-attempts in singleton

    def get_collection(self):
        if not self.collection:
            logger.error("ChromaDBManager: Collection is not available.")
            return None
        return self.collection

    def add_paper_summary(self, paper_id: str, summary_text: str, metadata: Dict) -> bool:
        collection = self.get_collection()
        if not collection:
            logger.error("Failed to add paper summary: Collection not available.")
            return False
        try:
            # We use the paper_id as the document ID in ChromaDB.
            # The summary_text is the document content that gets embedded.
            collection.add(
                documents=[summary_text],
                metadatas=[metadata],  # Store title, arxiv_id, pdf_url, original_query etc.
                ids=[paper_id]
            )
            logger.info(f"Added summary for paper_id '{paper_id}' to ChromaDB collection '{self.collection_name}'.")
            return True
        except Exception as e:
            logger.exception(f"Error adding summary for paper_id '{paper_id}' to ChromaDB: {e}")
            return False

    def add_user_feedback(self, paper_id: str, rating: Optional[int] = None, notes: Optional[str] = None) -> bool:
        collection = self.get_collection()
        if not collection:
            logger.error("Failed to add user feedback: Collection not available.")
            return False
        try:
            # Retrieve the existing document to update its metadata
            existing_doc = collection.get(ids=[paper_id], include=['metadatas'])

            if not existing_doc or not existing_doc['ids']:
                logger.error(f"Cannot add feedback: Paper with id '{paper_id}' not found in ChromaDB.")
                return False

            current_metadata = existing_doc['metadatas'][0] if existing_doc['metadatas'] else {}

            # Update metadata with feedback
            if rating is not None:
                current_metadata['user_rating'] = rating
            if notes is not None:
                current_metadata['user_notes'] = notes
            import datetime # Add import for datetime
            current_metadata['feedback_timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat() # Record feedback time

            # ChromaDB's update semantics: use upsert for simplicity if item exists.
            # We need the document content to upsert, so we fetch it first if not updating embeddings.
            # However, if we are only updating metadata, it's simpler to just update the metadata.
            # `collection.update` can update metadata, embeddings, or documents.
            # Here, we primarily want to update metadata.

            collection.update(
                ids=[paper_id],
                metadatas=[current_metadata]
            )
            logger.info(f"Added/Updated feedback for paper_id '{paper_id}' in ChromaDB.")
            return True
        except Exception as e:
            logger.exception(f"Error adding/updating feedback for paper_id '{paper_id}' in ChromaDB: {e}")
            return False

    def query_summaries(self, query_texts: List[str], n_results: int = 5, where_filter: Optional[Dict] = None) -> Optional[List[Dict]]:
        collection = self.get_collection()
        if not collection:
            logger.error("Failed to query summaries: Collection not available.")
            return None
        try:
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where_filter, # e.g., {"user_rating": {"$gte": 4}}
                include=['metadatas', 'documents', 'distances'] # Include summaries and distances
            )

            # Reconstruct the results into a more usable list of dicts
            processed_results = []
            if results and results.get('ids'):
                for i in range(len(results['ids'][0])):
                    paper_id = results['ids'][0][i]
                    distance = results['distances'][0][i] if results.get('distances') else None
                    summary = results['documents'][0][i] if results.get('documents') else None
                    metadata = results['metadatas'][0][i] if results.get('metadatas') else None
                    processed_results.append({
                        "paper_id": paper_id,
                        "summary": summary,
                        "metadata": metadata,
                        "distance": distance
                    })
            logger.info(f"Queried ChromaDB with '{query_texts}', found {len(processed_results)} results.")
            return processed_results
        except Exception as e:
            logger.exception(f"Error querying ChromaDB: {e}")
            return None

# To ensure a single instance is used throughout the application
def get_chromadb_manager():
    return ChromaDBManager()

# Example Usage (for testing purposes)
# if __name__ == "__main__":
#     import datetime
#     manager = get_chromadb_manager()
#     if not manager.get_collection():
#         print("ChromaDB collection could not be initialized. Check logs and API key.")
#     else:
#         print(f"ChromaDB Manager initialized. Collection: {manager.collection_name}")
#
#         # Test adding a summary
#         test_paper_id = "arxiv_test_001"
#         test_summary = "This is a test summary about LLMs and their applications in AI."
#         # Convert list to comma-separated string for query_keywords
#         test_metadata = {"title": "Test Paper on LLMs", "arxiv_id": "test001", "pdf_url": "http://example.com/test.pdf", "query_keywords": "LLM,AI"}
#
#         added_summary = manager.add_paper_summary(test_paper_id, test_summary, test_metadata)
#         print(f"Add summary successful: {added_summary}")

#         # Test adding feedback
#         added_feedback = manager.add_user_feedback(test_paper_id, rating=5, notes="Very relevant!")
#         print(f"Add feedback successful: {added_feedback}")

#         # Test querying
#         query_results = manager.query_summaries(query_texts=["applications of large language models"], n_results=1)
#         print(f"Query results: {query_results}")
#
#         if query_results:
#             for res in query_results:
#                 print(f"  ID: {res['paper_id']}, Dist: {res['distance']:.4f}, Summary: {res['summary'][:50]}...")
#                 print(f"  Metadata: {res['metadata']}")
#
#         # Test querying with filter (assuming the above feedback was added)
#         # Note: Metadata filters on string values require exact matches. Numerical values can use $gte, $lte etc.
#         # ChromaDB's metadata filtering capabilities depend on its version and configuration.
#         # This example assumes user_rating is stored as a number that can be filtered.
#         # If OpenAI embeddings are not used, this query might behave differently or require string for rating.
#         # For robust filtering, ensure metadata fields are consistently typed.
#         filtered_results = manager.query_summaries(query_texts=["AI applications"], n_results=1, where_filter={"user_rating": {"$gte": 4}})
#         print(f"Filtered query results (rating >= 4): {filtered_results}")
