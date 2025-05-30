import os
from datetime import datetime # Added
from agents.arxiv_search_agent import ArxivSearchAgent
from agents.summarizer_agent import SummarizerAgent
from agents.interest_agent import InterestAgent # Added
from core.long_term_memory import LongTermMemory
from core.reflection_engine import ReflectionEngine
from core.models import PaperDetails, Summary, UserInterestFeedback # Added

class OrchestratorAgent:
    def __init__(self, memory_file="orchestrator_memory.json"):
        self.arxiv_agent = ArxivSearchAgent()
        self.summarizer_agent = SummarizerAgent()
        self.memory = LongTermMemory(memory_file=memory_file)
        self.reflection_engine = ReflectionEngine(self.memory)
        self.interest_agent = InterestAgent(memory=self.memory) # Added

    def reflect_and_get_suggestions(self):
        """
        Performs reflection based on legacy feedback and returns actionable suggestions.
        Note: This may need updates if reflection should also consider UserInterestFeedback.
        """
        print("\nOrchestrator: Running reflection engine...")
        keyword_suggs = self.reflection_engine.get_keyword_suggestions()
        summary_param_suggs = self.reflection_engine.get_summary_parameter_suggestions()
        
        suggestions = {
            "keywords": keyword_suggs,
            "summary_params": summary_param_suggs
        }
        
        print(f"  Keyword Suggestions: Preferred={keyword_suggs['preferred']}, Irrelevant={keyword_suggs['irrelevant']}")
        print(f"  Summary Parameter Suggestion: {summary_param_suggs['suggestion']} (Avg Rating: {summary_param_suggs.get('avg_rating')})") # type: ignore
        return suggestions

    def record_legacy_feedback(self, paper_title, rating, comment=None, summary_text=None):
        """
        Records basic (legacy) feedback for a paper's summary.
        For more detailed interest tracking, use record_interest_feedback.
        """
        self.memory.record_paper_feedback(paper_title, rating, comment, summary_text)
        print(f"Orchestrator: Legacy feedback recorded for '{paper_title}'.")

    def record_interest_feedback(self, paper_arxiv_id: str, is_interesting: bool, reasons: list[str] | None = None, user_rating: int | None = None, user_insights: list[str] | None = None):
        """Records detailed user interest feedback for a paper."""
        feedback_instance = UserInterestFeedback(
            paper_arxiv_id=paper_arxiv_id,
            is_interesting=is_interesting,
            reasons=reasons if reasons else [],
            extracted_insights=user_insights if user_insights else [], # These are insights from user
            user_rating=user_rating,
            feedback_at=datetime.now().isoformat()
        )
        self.memory.record_user_interest_feedback(feedback_instance)
        print(f"Orchestrator: Detailed interest feedback recorded for paper ID {paper_arxiv_id}.")

    def add_preferred_keyword_to_memory(self, keyword):
        """Adds a preferred keyword to long-term memory (used by ReflectionEngine)."""
        self.memory.add_preferred_keyword(keyword)

    def add_irrelevant_keyword_to_memory(self, keyword):
        """Adds an irrelevant keyword to long-term memory."""
        self.memory.add_irrelevant_keyword(keyword)
        
    def get_all_preferences_from_memory(self):
        """Retrieves all user preferences from long-term memory."""
        return self.memory.get_user_preferences()

    def process_query(self, keywords, max_papers=5):
        """
        Processes a user query by searching Arxiv, summarizing abstracts,
        and returning the findings.

        Args:
            keywords (list): A list of keywords for the Arxiv search.
            max_papers (int): The maximum number of papers to process.

        Returns:
            list: A list of dictionaries, each containing PaperDetails, Summary,
                  interest assessment, and extracted insights.
                  Returns an error message string if something goes wrong.
        """
        if not keywords or not isinstance(keywords, list):
            return "Error: Invalid keywords provided. Please provide a list of strings."

        keyword_suggestions = self.reflection_engine.get_keyword_suggestions()
        effective_keywords = list(set(keywords + keyword_suggestions.get("preferred", [])))
        
        if not effective_keywords:
            return "Error: No keywords to search. Please provide keywords or set preferred keywords."

        print(f"Orchestrator: Original keywords: {keywords}")
        print(f"Orchestrator: Effective keywords (with preferred): {effective_keywords}")

        print(f"Orchestrator: Searching Arxiv for keywords: {effective_keywords}")
        try:
            papers_data = self.arxiv_agent.search_papers(effective_keywords) # papers_data is list of dicts
        except Exception as e:
            return f"Error during Arxiv search: {str(e)}"

        if not papers_data:
            return "No papers found for the given keywords."

        processed_papers_enhanced = []
        print(f"Orchestrator: Found {len(papers_data)} papers. Processing top {min(max_papers, len(papers_data))}...")

        for paper_data in papers_data[:max_papers]:
            try:
                paper_details = PaperDetails(
                    arxiv_id=paper_data.get('arxiv_id', f"N/A_{datetime.now().timestamp()}"), # Ensure unique enough ID if missing
                    title=paper_data.get('title', 'No Title Provided'),
                    authors=paper_data.get('authors', []),
                    publication_date=paper_data.get('publication_date', 'N/A'),
                    abstract=paper_data.get('abstract', ''),
                    pdf_url=paper_data.get('pdf_url', '')
                )

                abstract_to_summarize = paper_details.abstract
                # Default error string, though summarize() itself should also handle empty abstracts.
                summary_output_from_agent: Summary | str = "Error: Abstract not available for summarization." 

                if abstract_to_summarize:
                    # This call now returns a Summary object or an error string
                    # Pass paper_details.arxiv_id for context, in case the summarizer needs it (it does for creating Summary obj)
                    # Also pass other relevant params like max_length, min_length as defined in Orchestrator
                    summary_output_from_agent = self.summarizer_agent.summarize(
                        abstract_to_summarize, # Pass the text directly
                        paper_arxiv_id_override=paper_details.arxiv_id, # Pass arxiv_id for context
                        max_length=100, # Keep consistent with previous direct call if any
                        min_length=20  # Keep consistent
                    )
                
                summary_instance_to_store: Summary # Type hint for clarity
                if isinstance(summary_output_from_agent, Summary):
                    summary_instance_to_store = summary_output_from_agent
                    # Check if the summary text itself indicates an error from the summarizer
                    if summary_output_from_agent.summary_text.startswith("Error:"):
                         print(f"Orchestrator: Summarization for '{paper_details.title}' resulted in Summary object with error text: {summary_output_from_agent.summary_text}")
                else: # It's an error string from summarize() or our default before calling summarize
                    error_message_from_summarizer = summary_output_from_agent # This is actually the error string
                    print(f"Orchestrator: Summarization failed for '{paper_details.title}'. Using error string as summary: {error_message_from_summarizer}")
                    summary_instance_to_store = Summary(
                        paper_arxiv_id=paper_details.arxiv_id,
                        summary_text=error_message_from_summarizer, # Store the error string here
                        model_used=self.summarizer_agent.model_name if hasattr(self.summarizer_agent, 'model_name') else "unknown_error_case",
                        generated_at=datetime.now().isoformat()
                    )
                
                print(f"Orchestrator: Assessing interest for paper: {paper_details.title}")
                # Use summary_instance_to_store which is guaranteed to be a Summary object
                interest_assessment = self.interest_agent.is_paper_interesting(paper_details, summary_instance_to_store)
                
                extracted_insights = []
                if interest_assessment.get("is_interesting"):
                    print(f"Orchestrator: Extracting insights for paper: {paper_details.title}")
                    # Pass summary_instance_to_store here as well
                    extracted_insights = self.interest_agent.extract_insights(paper_details, summary_instance_to_store)

                processed_papers_enhanced.append({
                    "paper_details": paper_details,
                    "summary": summary_instance_to_store, # Use the guaranteed Summary object
                    "interest_assessment": interest_assessment,
                    "extracted_insights": extracted_insights 
                })

            except Exception as e:
                print(f"Orchestrator: Error processing paper {paper_data.get('title', 'Unknown Title')}: {e}")
                # Optionally append an error structure or skip
                continue 
        
        print("Orchestrator: Processing complete.")
        return processed_papers_enhanced

if __name__ == '__main__':
    # Ensure a clean slate for testing
    test_memory_file = "test_orchestrator_memory.json"
    if os.path.exists(test_memory_file):
        os.remove(test_memory_file)

    orchestrator = OrchestratorAgent(memory_file=test_memory_file)
    
    
    # Test case 1: Valid query
    search_keywords = ["transformer models", "attention mechanism"]
    print(f"\n--- Test Case 1: Processing query for keywords: {search_keywords} ---")
    processed_results = orchestrator.process_query(search_keywords, max_papers=1) 
    
    first_paper_arxiv_id = None
    if isinstance(processed_results, str):
        print(processed_results)
    elif processed_results:
        for res_item in processed_results:
            paper_details = res_item["paper_details"]
            summary = res_item["summary"]
            interest = res_item["interest_assessment"]
            insights = res_item["extracted_insights"]
            
            print(f"\nPaper Arxiv ID: {paper_details.arxiv_id}")
            print(f"Title: {paper_details.title}")
            print(f"Authors: {', '.join(paper_details.authors)}")
            print(f"Publication Date: {paper_details.publication_date}")
            print(f"Summary: {summary.summary_text} (Model: {summary.model_used}, Generated: {summary.generated_at})")
            print(f"Interest Assessment: Interesting? {interest.get('is_interesting')}, Prelim. Insights: {interest.get('preliminary_insights')}")
            print(f"Agent Extracted Insights: {insights}")

            if not first_paper_arxiv_id:
                 first_paper_arxiv_id = paper_details.arxiv_id
    else:
        print("No results processed.")

    # Test case 1b: Record interest feedback for the first processed paper
    if first_paper_arxiv_id:
        print(f"\n--- Test Case 1b: Recording INTEREST feedback for paper: {first_paper_arxiv_id} ---")
        orchestrator.record_interest_feedback(
            paper_arxiv_id=first_paper_arxiv_id,
            is_interesting=True,
            reasons=["relevant to my work", "novel method"],
            user_rating=5,
            user_insights=["insight from user 1", "insight from user 2"]
        )
        # Also record a legacy feedback to ensure it still works
        # Assuming we have a title for legacy system. For this test, we'll use arxiv_id as title.
        orchestrator.record_legacy_feedback(
            paper_title=first_paper_arxiv_id, # Using arxiv_id as title for legacy
            rating="excellent",
            comment="This was a great paper, highly relevant (legacy feedback)."
        )
        
        # Check if new feedback was stored
        retrieved_feedbacks = orchestrator.memory.get_user_interest_feedback(paper_arxiv_id=first_paper_arxiv_id)
        assert len(retrieved_feedbacks) == 1
        assert retrieved_feedbacks[0].user_rating == 5
        print(f"  Retrieved {len(retrieved_feedbacks)} new interest feedback entries for {first_paper_arxiv_id}.")

    # Test case 1c: Manage preferences (still uses legacy system for ReflectionEngine)
    print("\n--- Test Case 1c: Managing preferences (legacy for reflection) ---")
    orchestrator.add_preferred_keyword_to_memory("transformer models") 
    orchestrator.add_preferred_keyword_to_memory("natural language processing")
    orchestrator.add_irrelevant_keyword_to_memory("sports")
    current_prefs = orchestrator.get_all_preferences_from_memory()
    print(f"Current preferences (legacy): {current_prefs}")

    # Test case 1d: Perform reflection (still uses legacy system)
    print("\n--- Test Case 1d: Performing reflection (based on legacy feedback) ---")
    suggestions = orchestrator.reflect_and_get_suggestions()
    # In a real app, these suggestions would be used to guide future actions or settings.

    # Test case 1e: Process query again, this time benefiting from preferred keywords
    search_keywords_generic = ["deep learning"] 
    print(f"\n--- Test Case 1e: Processing generic query ('{search_keywords_generic}') with preferred keywords active ---")
    results_with_reflection = orchestrator.process_query(search_keywords_generic, max_papers=1)
    if isinstance(results_with_reflection, str):
        print(results_with_reflection)
    elif results_with_reflection:
        for res_item in results_with_reflection: # Corrected variable name
            print(f"\nTitle: {res_item['paper_details'].title}")
            print(f"Summary: {res_item['summary'].summary_text}")
    else:
        print("No results from reflected query.")


    # Test case 2: Query that might return no results
    search_keywords_no_results = ["nonexistenttopicxyz123unlikely", "anotheroneabc456unlikely"]
    print(f"\n--- Test Case 2: Processing query for keywords: {search_keywords_no_results} ---")
    results_no_results = orchestrator.process_query(search_keywords_no_results)
    if isinstance(results_no_results, str):
        print(results_no_results) # Expected: "No papers found..."
    else:
        print(f"Unexpected results for no-result query: {results_no_results}")


    # Test case 3: Invalid keywords
    search_keywords_invalid = "this is not a list" # type: ignore
    print(f"\n--- Test Case 3: Processing query for invalid keywords: {search_keywords_invalid} ---")
    results_invalid = orchestrator.process_query(search_keywords_invalid) # type: ignore
    if isinstance(results_invalid, str):
        print(results_invalid) # Expected: "Error: Invalid keywords..."
    else:
        print(f"Unexpected results for invalid keywords: {results_invalid}")
            
    # Test case 4: Empty keywords list (but preferred keywords might exist)
    search_keywords_empty = []
    print(f"\n--- Test Case 4: Processing query for empty keywords list ---")
    # Add a preferred keyword if none, to ensure it doesn't fail on "No keywords to search" immediately
    if not orchestrator.memory.get_user_preferences()['preferred_keywords']:
         orchestrator.add_preferred_keyword_to_memory("temporary_preferred")
    results_empty = orchestrator.process_query(search_keywords_empty)
    if isinstance(results_empty, str):
        print(results_empty) # Might return results if preferred keywords are set
    elif results_empty:
         for res_item in results_empty:
            print(f"\nTitle: {res_item['paper_details'].title} (from preferred keywords)")
            print(f"Summary: {res_item['summary'].summary_text}")
    else:
        print("No results for empty query (and no/irrelevant preferred keywords).")
    
    # Clean up test memory file
    if os.path.exists(test_memory_file):
        os.remove(test_memory_file)
        print(f"\nCleaned up {test_memory_file}")
    print("\nOrchestratorAgent tests completed.")
