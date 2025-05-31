import os
from agents.arxiv_search_agent import ArxivSearchAgent
from agents.summarizer_agent import SummarizerAgent
from core.long_term_memory import LongTermMemory
from core.reflection_engine import ReflectionEngine

class OrchestratorAgent:
    def __init__(self, memory_file="orchestrator_memory.json"):
        self.arxiv_agent = ArxivSearchAgent()
        self.summarizer_agent = SummarizerAgent()
        self.memory = LongTermMemory(memory_file=memory_file)
        self.reflection_engine = ReflectionEngine(self.memory)

    def reflect_and_get_suggestions(self):
        """Performs reflection and returns actionable suggestions."""
        print("\nOrchestrator: Running reflection engine...")
        keyword_suggs = self.reflection_engine.get_keyword_suggestions()
        summary_param_suggs = self.reflection_engine.get_summary_parameter_suggestions()
        
        suggestions = {
            "keywords": keyword_suggs,
            "summary_params": summary_param_suggs
        }
        
        print(f"  Keyword Suggestions: Preferred={keyword_suggs['preferred']}, Irrelevant={keyword_suggs['irrelevant']}")
        print(f"  Summary Parameter Suggestion: {summary_param_suggs['suggestion']} (Avg Rating: {summary_param_suggs.get('avg_rating')})")
        return suggestions

    def record_feedback(self, paper_title, rating, comment=None, summary_text=None):
        """Records feedback for a paper's summary."""
        self.memory.record_paper_feedback(paper_title, rating, comment, summary_text)
        print(f"Orchestrator: Feedback recorded for '{paper_title}'.")

    def add_preferred_keyword_to_memory(self, keyword):
        """Adds a preferred keyword to long-term memory."""
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
            list: A list of dictionaries, where each dictionary contains
                  the original paper metadata and its summary.
                  Returns an error message string if something goes wrong.
        """
        if not keywords or not isinstance(keywords, list):
            return "Error: Invalid keywords provided. Please provide a list of strings."

        # Incorporate reflection: Use preferred keywords to augment the search
        keyword_suggestions = self.reflection_engine.get_keyword_suggestions()
        effective_keywords = list(set(keywords + keyword_suggestions.get("preferred", []))) # Combine and remove duplicates
        
        if not effective_keywords: # If original keywords were empty and no preferred ones.
            return "Error: No keywords to search. Please provide keywords or set preferred keywords."

        print(f"Orchestrator: Original keywords: {keywords}")
        print(f"Orchestrator: Effective keywords (with preferred): {effective_keywords}")
        
        # TODO: Consider how to use irrelevant_keywords if Arxiv API allows exclusion.
        # For now, we are only boosting with preferred keywords.

        print(f"Orchestrator: Searching Arxiv for keywords: {effective_keywords}")
        try:
            papers = self.arxiv_agent.search_papers(effective_keywords)
        except Exception as e:
            return f"Error during Arxiv search: {str(e)}"

        if not papers:
            return "No papers found for the given keywords."

        summarized_findings = []
        print(f"Orchestrator: Found {len(papers)} papers. Summarizing top {min(max_papers, len(papers))} abstracts...")

        for i, paper_meta in enumerate(papers):
            if i >= max_papers:
                break
            
            current_paper_title = paper_meta['title']
            print(f"Orchestrator: Summarizing abstract for paper: {current_paper_title}")
            abstract = paper_meta.get("abstract")
            
            if not abstract:
                summary = "Error: Abstract not available for this paper."
            else:
                # Using a slightly shorter max_length for abstracts
                summary = self.summarizer_agent.summarize(abstract, max_length=100, min_length=20)
                if summary.startswith("Error:"):
                    print(f"Orchestrator: Summarization failed for '{current_paper_title}'. Error: {summary}")

            summarized_findings.append({
                "title": current_paper_title,
                "authors": paper_meta['authors'],
                "publication_date": paper_meta['publication_date'],
                "original_abstract": abstract,
                "summary": summary
            })
        
        print("Orchestrator: Processing complete.")
        return summarized_findings

if __name__ == '__main__':
    orchestrator = OrchestratorAgent(memory_file="test_orchestrator_memory.json")
    
    # Test case 1: Valid query
    search_keywords = ["AI agents", "LLM"]
    print(f"\n--- Test Case 1: Processing query for keywords: {search_keywords} ---")
    results = orchestrator.process_query(search_keywords, max_papers=1) # Reduced for brevity in test
    processed_paper_title = None
    processed_paper_summary = None
    if isinstance(results, str):
        print(results)
    else:
        for finding in results:
            print(f"\nTitle: {finding['title']}")
            print(f"Authors: {', '.join(finding['authors'])}")
            print(f"Publication Date: {finding['publication_date']}")
            # print(f"Original Abstract: {finding['original_abstract']}") # Optionally print
            print(f"Summary: {finding['summary']}")
            if not processed_paper_title: # Store first paper for feedback
                processed_paper_title = finding['title']
                processed_paper_summary = finding['summary']

    # Test case 1b: Record feedback for the first processed paper
    if processed_paper_title:
        print(f"\n--- Test Case 1b: Recording feedback for paper: {processed_paper_title} ---")
        orchestrator.record_feedback(
            paper_title=processed_paper_title,
            rating="good",
            comment="This summary was helpful and concise.",
            summary_text=processed_paper_summary
        )
        orchestrator.record_feedback(
            paper_title=processed_paper_title,
            rating="neutral",
            comment="Second thought: it could have mentioned X."
        )
        # Check if feedback was stored
        # print(orchestrator.memory.get_feedback_for_paper(processed_paper_title))

    # Test case 1c: Manage preferences
    print("\n--- Test Case 1c: Managing preferences ---")
    orchestrator.add_preferred_keyword_to_memory("LLM")
    # orchestrator.add_preferred_keyword_to_memory("AI agents") # Already added by user query
    orchestrator.add_preferred_keyword_to_memory("explainable AI") # Add a new one
    orchestrator.add_irrelevant_keyword_to_memory("blockchain")
    current_prefs = orchestrator.get_all_preferences_from_memory()
    print(f"Current preferences: {current_prefs}")

    # Test case 1d: Perform reflection
    print("\n--- Test Case 1d: Performing reflection ---")
    suggestions = orchestrator.reflect_and_get_suggestions()
    # In a real app, these suggestions would be used to guide future actions or settings.

    # Test case 1e: Process query again, this time benefiting from preferred keywords
    search_keywords_generic = ["machine learning"] # A more generic query
    print(f"\n--- Test Case 1e: Processing generic query ('{search_keywords_generic}') with preferred keywords active ---")
    results_with_reflection = orchestrator.process_query(search_keywords_generic, max_papers=1)
    if isinstance(results_with_reflection, str):
        print(results_with_reflection)
    else:
        for finding in results_with_reflection:
            print(f"\nTitle: {finding['title']}")
            print(f"Summary: {finding['summary']}")


    # Test case 2: Query that might return no results
    search_keywords_no_results = ["nonexistenttopicxyz123", "anotheroneabc456"]
    print(f"\n--- Test Case 2: Processing query for keywords: {search_keywords_no_results} ---")
    results_no_results = orchestrator.process_query(search_keywords_no_results)
    if isinstance(results_no_results, str):
        print(results_no_results)
    else:
        for finding in results_no_results:
            print(f"\nTitle: {finding['title']}")
            print(f"Summary: {finding['summary']}")

    # Test case 3: Invalid keywords
    search_keywords_invalid = "AI agents" # Not a list
    print(f"\n--- Test Case 3: Processing query for invalid keywords: {search_keywords_invalid} ---")
    results_invalid = orchestrator.process_query(search_keywords_invalid)
    if isinstance(results_invalid, str):
        print(results_invalid)
    else:
        # This part should not be reached if error handling is correct
        for finding in results_invalid:
            print(f"\nTitle: {finding['title']}")
            print(f"Summary: {finding['summary']}")
            
    # Test case 4: Empty keywords list
    search_keywords_empty = []
    print(f"\n--- Test Case 4: Processing query for empty keywords list: {search_keywords_empty} ---")
    results_empty = orchestrator.process_query(search_keywords_empty)
    if isinstance(results_empty, str):
        print(results_empty)
    else:
        for finding in results_empty:
            print(f"\nTitle: {finding['title']}")
            print(f"Summary: {finding['summary']}")
    
    # Clean up test memory file
    if os.path.exists("test_orchestrator_memory.json"):
        os.remove("test_orchestrator_memory.json")
        print("\nCleaned up test_orchestrator_memory.json")
