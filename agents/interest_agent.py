from core.models import PaperDetails, Summary, UserInterestFeedback # Assuming models are in core.models
from core.long_term_memory import LongTermMemory # May be needed later

class InterestAgent:
    def __init__(self, memory: LongTermMemory | None = None):
        """
        Initializes the InterestAgent.
        Args:
            memory (LongTermMemory, optional): Reference to long-term memory
                                                to learn user preferences. Defaults to None.
        """
        self.memory = memory # Not used in the initial version but good for future use

    def is_paper_interesting(self, paper_details: PaperDetails, summary: Summary) -> dict:
        """
        Decides if a paper is interesting based on its details and summary.
        This is a preliminary implementation.
        
        Args:
            paper_details (PaperDetails): The details of the paper.
            summary (Summary): The summary of the paper.
            
        Returns:
            dict: A dictionary with keys 'is_interesting' (bool) and 'preliminary_insights' (list[str]).
        """
        # Initial heuristic: For now, let's consider every paper potentially interesting
        # and provide no preliminary insights.
        # TODO: Implement more sophisticated logic, possibly using self.memory
        print(f"InterestAgent: Checking interest for paper '{paper_details.title}'")
        return {
            "is_interesting": True, # Placeholder
            "preliminary_insights": [] 
        }

    def extract_insights(self, paper_details: PaperDetails, summary: Summary) -> list[str]:
        """
        Extracts key insights from a paper that has been deemed interesting.
        This is a preliminary implementation.

        Args:
            paper_details (PaperDetails): The details of the paper.
            summary (Summary): The summary of the paper.

        Returns:
            list[str]: A list of extracted insights.
        """
        # Placeholder: Real insight extraction would involve NLP or other methods.
        # For now, return a generic message or try to get some keywords from abstract.
        print(f"InterestAgent: Extracting insights for paper '{paper_details.title}'")
        
        # Simple placeholder: first few words of abstract as "insights"
        if paper_details.abstract:
            abstract_words = paper_details.abstract.split()
            return [" ".join(abstract_words[:10]) + "...", " ".join(abstract_words[10:20]) + "..."] if len(abstract_words) > 10 else [paper_details.abstract]
        
        return ["No abstract available to extract insights."]

if __name__ == '__main__':
    # Example Usage (requires dummy models and memory for testing if not available)
    # This part is for basic testing and might need adjustment based on actual model definitions
    
    # Create dummy PaperDetails
    dummy_paper = PaperDetails(
        arxiv_id="1234.56789",
        title="A Dummy Paper on Interesting Things",
        authors=["Author One", "Author Two"],
        publication_date="2023-01-01",
        abstract="This is a dummy abstract about interesting topics. It discusses various important concepts and findings that are relevant to the field. The implications are far-reaching.",
        pdf_url="http://arxiv.org/pdf/1234.56789"
    )
    
    # Create dummy Summary
    dummy_summary = Summary(
        paper_arxiv_id="1234.56789",
        summary_text="This is a dummy summary of the paper on interesting things.",
        model_used="test-model",
        generated_at="2023-01-01T12:00:00"
    )
    
    # Initialize agent (without memory for this test)
    agent = InterestAgent()
    
    # Test is_paper_interesting
    interest_decision = agent.is_paper_interesting(dummy_paper, dummy_summary)
    print(f"Interest Decision: {interest_decision}")
    assert isinstance(interest_decision, dict)
    assert "is_interesting" in interest_decision
    assert "preliminary_insights" in interest_decision
    
    # Test extract_insights if paper is deemed interesting
    if interest_decision["is_interesting"]:
        insights = agent.extract_insights(dummy_paper, dummy_summary)
        print(f"Extracted Insights: {insights}")
        assert isinstance(insights, list)

    print("InterestAgent basic tests passed.")
