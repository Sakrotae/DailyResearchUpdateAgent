from transformers import pipeline

class SummarizerAgent:
    def __init__(self, model_name="sshleifer/distilbart-cnn-6-6"):
        """
        Initializes the SummarizerAgent with a pre-trained summarization model.
        Args:
            model_name (str): The name of the pre-trained model to use.
        """
        self.summarizer = pipeline("summarization", model=model_name)

    def summarize(self, text, max_length=150, min_length=30, do_sample=False):
        """
        Summarizes the given text.
        Args:
            text (str): The text to summarize.
            max_length (int): The maximum length of the summary.
            min_length (int): The minimum length of the summary.
            do_sample (bool): Whether to use sampling for generation.
        Returns:
            str: The summarized text.
        """
        if not text or not isinstance(text, str):
            return "Error: Input text is invalid."

        try:
            summary = self.summarizer(text, max_length=max_length, min_length=min_length, do_sample=do_sample)
            return summary[0]['summary_text']
        except Exception as e:
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
    
    summary = agent.summarize(example_text)
    print("Original Text:\n", example_text)
    print("\nSummary:\n", summary)

    # Test with a longer abstract
    longer_abstract = (
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
    summary_long = agent.summarize(longer_abstract, max_length=100, min_length=25)
    print("\nOriginal Long Text:\n", longer_abstract)
    print("\nSummary of Long Text:\n", summary_long)

    # Test with invalid input
    summary_invalid = agent.summarize(None)
    print("\nSummary of Invalid Input:\n", summary_invalid)

    summary_empty = agent.summarize("")
    print("\nSummary of Empty Input:\n", summary_empty)
