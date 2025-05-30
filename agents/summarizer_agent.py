from transformers import pipeline
from core.models import Summary, PaperDetails # Added
from datetime import datetime # Added

class SummarizerAgent:
    def __init__(self, model_name="sshleifer/distilbart-cnn-6-6"):
        """
        Initializes the SummarizerAgent with a pre-trained summarization model.
        Args:
            model_name (str): The name of the pre-trained model to use.
        """
        self.summarizer = pipeline("summarization", model=model_name)
        self.model_name = model_name # Store for use in Summary model

    def summarize(self, text_or_paper_details: str | PaperDetails, 
                  paper_arxiv_id_override: str | None = None, # Allow overriding ID
                  max_length=150, min_length=30, do_sample=False) -> Summary | str:
        """
        Summarizes the given text or abstract from PaperDetails.
        Args:
            text_or_paper_details (str | PaperDetails): The text or PaperDetails object to summarize.
            paper_arxiv_id_override (str | None): Optional override for the paper's arxiv_id.
            max_length (int): The maximum length of the summary.
            min_length (int): The minimum length of the summary.
            do_sample (bool): Whether to use sampling for generation.
        Returns:
            Summary | str: A Summary object on success, or an error string on failure.
        """
        
        text_to_summarize: str
        current_arxiv_id: str | None = paper_arxiv_id_override

        if isinstance(text_or_paper_details, PaperDetails):
            text_to_summarize = text_or_paper_details.abstract
            if current_arxiv_id is None: # Prioritize override, then from PaperDetails
                current_arxiv_id = text_or_paper_details.arxiv_id
        elif isinstance(text_or_paper_details, str):
            text_to_summarize = text_or_paper_details
        else:
            return "Error: Input must be a string or PaperDetails object."

        if not text_to_summarize: # Handles empty string or empty abstract
            return "Error: Input text is empty or not available from PaperDetails."

        try:
            summary_output = self.summarizer(text_to_summarize, max_length=max_length, min_length=min_length, do_sample=do_sample)
            # Ensure summary_output is not empty and has the expected structure
            if not summary_output or not isinstance(summary_output, list) or not summary_output[0].get('summary_text'):
                return "Error: Summarization model returned unexpected output."

            return Summary(
                paper_arxiv_id=current_arxiv_id if current_arxiv_id else "N/A", # Ensure arxiv_id is not None
                summary_text=summary_output[0]['summary_text'],
                model_used=self.model_name,
                generated_at=datetime.now().isoformat()
            )
        except Exception as e:
            # Log the exception for debugging if a logger is available
            # print(f"SummarizerAgent encountered an exception: {e}") 
            return f"Error during summarization: {str(e)}"

if __name__ == '__main__':
    agent = SummarizerAgent()
    
    example_text = (
        "Artificial intelligence (AI) is rapidly transforming various industries. "
        "Machine learning, a subset of AI, enables systems to learn from data and make decisions. "
        "Natural language processing (NLP) allows computers to understand and generate human language. "
        "Computer vision focuses on enabling machines to interpret and understand visual information. "
        "These technologies are driving innovation in healthcare, finance, and transportation. "
        "The most interesting finding is the potential for AI to solve complex global challenges, "
        "such as climate change and disease outbreaks, by analyzing vast amounts of data and identifying patterns."
    )
    longer_abstract = ( # Defined here for use in PaperDetails test
        "Large language models (LLMs) have gained significant interest in industry due to their impressive "
        "capabilities across a wide range of tasks. However, the widespread adoption of LLMs presents several "
        "challenges, such as integration into existing applications and infrastructure, utilization of company "
        "proprietary data, models, and APIs, and meeting cost, quality, responsiveness, and other requirements. "
        "To address these challenges, there is a notable shift from monolithic models to compound AI systems, "
        "with the premise of more powerful, versatile, and reliable applications. However, progress thus far has "
        "been piecemeal, with proposals for agentic workflows, programming models, and extended LLM capabilities, "
        "without a clear vision of an overall architecture. In this paper, we propose a 'blueprint architecture' "
        "for compound AI systems for orchestrating agents and data for enterprise applications. In our proposed "
        "architecture the key orchestration concept is 'streams' to coordinate the flow of data and instructions "
        "among agents. Existing proprietary models and APIs in the enterprise are mapped to 'agents', defined in an "
        "'agent registry' that serves agent metadata and learned representations for search and planning. Agents can "
        "utilize proprietary data through a 'data registry' that similarly registers enterprise data of various "
        "modalities. Tying it all together, data and task 'planners' break down, map, and optimize tasks and "
        "queries for given quality of service (QoS) requirements such as cost, accuracy, and latency. We "
        "illustrate an implementation of the architecture for a use-case in the HR domain and discuss "
        "opportunities and challenges for 'agentic AI' in the enterprise. The core finding is the proposed blueprint "
        "architecture itself, which offers a structured approach to building complex AI systems by orchestrating "
        "specialized agents and data sources, potentially leading to more adaptable and efficient enterprise AI solutions."
    )

    # Test 1: Summarize plain text
    print("--- Test 1: Summarizing plain text ---")
    summary_obj = agent.summarize(example_text)
    print("Original Text:\n", example_text)
    if isinstance(summary_obj, Summary):
        print("\nSummary (from text):\n", summary_obj.summary_text)
        print(f"  Model: {summary_obj.model_used}, Arxiv ID: {summary_obj.paper_arxiv_id}, Generated: {summary_obj.generated_at}")
        assert summary_obj.paper_arxiv_id == "N/A" # No ID provided for plain text
        assert summary_obj.model_used == agent.model_name
    else:
        print("\nError summarizing text:", summary_obj)
    assert isinstance(summary_obj, Summary)


    # Test 2: Summarize with a PaperDetails object
    print("\n--- Test 2: Summarizing with PaperDetails ---")
    dummy_paper = PaperDetails(
        arxiv_id="1234.56789",
        title="A Dummy Paper for Summarization",
        authors=["Test Author"],
        publication_date="2023-01-01",
        abstract=longer_abstract, 
        pdf_url="http://example.com/1234.56789.pdf"
    )
    summary_from_paper = agent.summarize(dummy_paper, max_length=100, min_length=25)
    print("\nOriginal Long Text (from PaperDetails object):\n", dummy_paper.abstract)
    if isinstance(summary_from_paper, Summary):
        print("\nSummary (from PaperDetails):\n", summary_from_paper.summary_text)
        print(f"  Model: {summary_from_paper.model_used}, Arxiv ID: {summary_from_paper.paper_arxiv_id}, Generated: {summary_from_paper.generated_at}")
        assert summary_from_paper.paper_arxiv_id == "1234.56789"
    else:
        print("\nError summarizing from PaperDetails:", summary_from_paper)
    assert isinstance(summary_from_paper, Summary)

    # Test 3: Summarize with PaperDetails and ID override
    print("\n--- Test 3: Summarizing with PaperDetails and ID override ---")
    summary_id_override = agent.summarize(dummy_paper, paper_arxiv_id_override="override.001")
    if isinstance(summary_id_override, Summary):
        print("\nSummary (with ID override):\n", summary_id_override.summary_text)
        print(f"  Arxiv ID: {summary_id_override.paper_arxiv_id}")
        assert summary_id_override.paper_arxiv_id == "override.001"
    else:
        print("\nError summarizing with ID override:", summary_id_override)
    assert isinstance(summary_id_override, Summary)


    # Test 4: Invalid input type
    print("\n--- Test 4: Invalid input type (int) ---")
    summary_invalid_type = agent.summarize(12345) # type: ignore 
    print("Result for invalid input type:\n", summary_invalid_type)
    assert isinstance(summary_invalid_type, str) and summary_invalid_type.startswith("Error: Input must be a string")

    # Test 5: Empty string input
    print("\n--- Test 5: Empty string input ---")
    summary_empty_str = agent.summarize("")
    print("Result for empty string input:\n", summary_empty_str)
    assert isinstance(summary_empty_str, str) and summary_empty_str.startswith("Error: Input text is empty")

    # Test 6: PaperDetails with empty abstract
    print("\n--- Test 6: PaperDetails with empty abstract ---")
    empty_abstract_paper = PaperDetails(
        arxiv_id="empty.000", title="Empty Abstract", authors=[], publication_date="2023-01-01", abstract="", pdf_url=""
    )
    summary_empty_abstract = agent.summarize(empty_abstract_paper)
    print("Result for PaperDetails with empty abstract:\n", summary_empty_abstract)
    assert isinstance(summary_empty_abstract, str) and summary_empty_abstract.startswith("Error: Input text is empty")
    
    print("\nSummarizerAgent tests completed.")
