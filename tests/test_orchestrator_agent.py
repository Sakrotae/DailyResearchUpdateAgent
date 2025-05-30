import unittest
from unittest.mock import patch, MagicMock, ANY
from agents.orchestrator_agent import OrchestratorAgent
from core.models import PaperDetails, Summary, UserInterestFeedback
from datetime import datetime
import os


class TestOrchestratorAgent(unittest.TestCase):

    @patch('agents.orchestrator_agent.InterestAgent') # Added InterestAgent
    @patch('agents.orchestrator_agent.ReflectionEngine')
    @patch('agents.orchestrator_agent.LongTermMemory')
    @patch('agents.orchestrator_agent.SummarizerAgent')
    @patch('agents.orchestrator_agent.ArxivSearchAgent')
    def setUp(self, MockArxivSearchAgent, MockSummarizerAgent, MockLongTermMemory, MockReflectionEngine, MockInterestAgent):
        self.mock_arxiv_agent = MockArxivSearchAgent.return_value
        self.mock_summarizer_agent = MockSummarizerAgent.return_value
        self.mock_ltm = MockLongTermMemory.return_value
        self.mock_reflection_engine = MockReflectionEngine.return_value
        self.mock_interest_agent = MockInterestAgent.return_value # Store mock for InterestAgent

        self.mock_reflection_engine.get_keyword_suggestions.return_value = {"preferred": [], "irrelevant": []}

        self.test_memory_file = "test_orchestrator_for_unittest.json"
        # Ensure the test file doesn't exist from previous failed runs
        if os.path.exists(self.test_memory_file):
            os.remove(self.test_memory_file)
        self.orchestrator = OrchestratorAgent(memory_file=self.test_memory_file)

        # Dummy data using Pydantic models
        self.dummy_paper1 = PaperDetails(
            arxiv_id="pd.001", title="Paper 1 Title", authors=["Author A"],
            publication_date="2023-01-01", abstract="Abstract content for paper 1.",
            pdf_url="http://example.com/pd.001.pdf"
        )
        self.dummy_summary1 = Summary(
            paper_arxiv_id="pd.001", summary_text="Summary of paper 1.",
            model_used="mock-summarizer", generated_at=datetime.now().isoformat()
        )
        self.dummy_paper2_no_abstract = PaperDetails(
            arxiv_id="pd.002", title="Paper 2 No Abstract", authors=["Author B"],
            publication_date="2023-01-02", abstract="", # Empty abstract
            pdf_url="http://example.com/pd.002.pdf"
        )

    def tearDown(self):
        if os.path.exists(self.test_memory_file):
            os.remove(self.test_memory_file)


    def test_process_query_success(self):
        keywords = ["test query"]
        self.mock_arxiv_agent.search_papers.return_value = [self.dummy_paper1]
        # Orchestrator calls summarize with abstract string, not PaperDetails object
        # And Orchestrator creates the Summary object itself.
        # UPDATE: Based on my previous decision, OrchestratorAgent *should* get Summary object from SummarizerAgent
        self.mock_summarizer_agent.summarize.return_value = self.dummy_summary1
        
        self.mock_interest_agent.is_paper_interesting.return_value = {'is_interesting': True, 'preliminary_insights': ['insight zero']}
        self.mock_interest_agent.extract_insights.return_value = ['mock insight one']

        results = self.orchestrator.process_query(keywords, max_papers=1)

        self.mock_arxiv_agent.search_papers.assert_called_once_with(keywords)
        # SummarizerAgent.summarize expects (text_or_paper_details, paper_arxiv_id_override, max_length, min_length, do_sample)
        # Orchestrator calls it with: (abstract_to_summarize, max_length=100, min_length=20)
        # This needs to be aligned. Assuming Orchestrator passes the abstract string.
        self.mock_summarizer_agent.summarize.assert_called_once_with(self.dummy_paper1.abstract, max_length=100, min_length=20)
        
        self.mock_interest_agent.is_paper_interesting.assert_called_once_with(self.dummy_paper1, self.dummy_summary1)
        self.mock_interest_agent.extract_insights.assert_called_once_with(self.dummy_paper1, self.dummy_summary1)
        
        self.assertEqual(len(results), 1)
        result_item = results[0]
        self.assertIsInstance(result_item["paper_details"], PaperDetails)
        self.assertEqual(result_item["paper_details"].arxiv_id, self.dummy_paper1.arxiv_id)
        self.assertIsInstance(result_item["summary"], Summary)
        self.assertEqual(result_item["summary"].summary_text, self.dummy_summary1.summary_text)
        self.assertEqual(result_item["interest_assessment"]['is_interesting'], True)
        self.assertEqual(result_item["extracted_insights"], ['mock insight one'])


    def test_process_query_with_preferred_keywords_from_reflection(self):
        user_keywords = ["search term"]
        preferred_keywords = ["boost this"]
        self.mock_reflection_engine.get_keyword_suggestions.return_value = {"preferred": preferred_keywords, "irrelevant": []}
        
        expected_effective_keywords = sorted(list(set(user_keywords + preferred_keywords)))
        
        self.mock_arxiv_agent.search_papers.return_value = [self.dummy_paper1]
        self.mock_summarizer_agent.summarize.return_value = self.dummy_summary1
        self.mock_interest_agent.is_paper_interesting.return_value = {'is_interesting': False, 'preliminary_insights': []}
        # extract_insights should not be called if not interesting
        # self.mock_interest_agent.extract_insights.return_value = [] # Not called

        results = self.orchestrator.process_query(user_keywords, max_papers=1)

        self.mock_arxiv_agent.search_papers.assert_called_once()
        called_args, _ = self.mock_arxiv_agent.search_papers.call_args
        self.assertEqual(sorted(called_args[0]), expected_effective_keywords)
        
        self.mock_interest_agent.extract_insights.assert_not_called() # Since is_interesting is False
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["paper_details"].title, self.dummy_paper1.title)


    def test_process_query_invalid_keywords_input(self):
        # Test Orchestrator's own validation before any agent calls
        result = self.orchestrator.process_query(None) # type: ignore
        self.assertEqual(result, "Error: Invalid keywords provided. Please provide a list of strings.")
        result = self.orchestrator.process_query([])
        self.assertEqual(result, "Error: No keywords to search. Please provide keywords or set preferred keywords.")
        self.mock_arxiv_agent.search_papers.assert_not_called()


    def test_process_query_arxiv_search_error(self):
        self.mock_arxiv_agent.search_papers.side_effect = Exception("Arxiv Down")
        result = self.orchestrator.process_query(["some query"])
        self.assertEqual(result, "Error during Arxiv search: Arxiv Down")

    def test_process_query_no_papers_found_from_arxiv(self):
        self.mock_arxiv_agent.search_papers.return_value = []
        result = self.orchestrator.process_query(["rare query"])
        self.assertEqual(result, "No papers found for the given keywords.")

    def test_process_query_summarizer_returns_error_string(self):
        # Test how Orchestrator handles an error string from SummarizerAgent.summarize
        self.mock_arxiv_agent.search_papers.return_value = [self.dummy_paper1]
        # SummarizerAgent.summarize is expected to return a Summary object OR an error string
        self.mock_summarizer_agent.summarize.return_value = "Error: Summarizer failed badly"

        results = self.orchestrator.process_query(["query"], max_papers=1)
        self.assertEqual(len(results), 1)
        # Orchestrator should create a Summary object even if summarizer fails, but with error text
        self.assertIsInstance(results[0]["summary"], Summary)
        self.assertEqual(results[0]["summary"].summary_text, "Error: Abstract not available or summarization failed.") # Orchestrator's default error
        self.assertTrue(results[0]["summary"].summary_text.startswith("Error:"))


    def test_process_query_paper_with_no_abstract(self):
        # ArxivSearchAgent returns PaperDetails with abstract="" or abstract=None
        self.mock_arxiv_agent.search_papers.return_value = [self.dummy_paper2_no_abstract]
        # SummarizerAgent.summarize, if called with empty string, should return an error string/object
        # Let's assume it returns an error string as per its own contract
        self.mock_summarizer_agent.summarize.return_value = "Error: Input text is empty..." # What Summarizer returns for empty

        results = self.orchestrator.process_query(["query"], max_papers=1)
        
        self.assertEqual(len(results), 1)
        # Orchestrator should not call summarize if abstract is empty.
        # self.mock_summarizer_agent.summarize.assert_not_called() # This depends on Orchestrator logic
        # Current Orchestrator logic for empty abstract:
        #   abstract_to_summarize = paper_details.abstract (which is "")
        #   if abstract_to_summarize: -> this will be false
        #   summary_text = "Error: Abstract not available or summarization failed." (This is Orchestrator's message)
        #   summary_instance = Summary(..., summary_text=summary_text, ...)
        # So, summarize should NOT be called by Orchestrator.
        self.mock_summarizer_agent.summarize.assert_not_called()
        self.assertIsInstance(results[0]["summary"], Summary)
        self.assertEqual(results[0]["summary"].summary_text, "Error: Abstract not available or summarization failed.")


    def test_record_legacy_feedback(self): # Renamed from test_record_feedback
        title, rating, comment, summary_txt = "Feedback Paper", "good", "Helpful", "Summary..."
        self.orchestrator.record_legacy_feedback(title, rating, comment, summary_txt) # Call renamed method
        self.mock_ltm.record_paper_feedback.assert_called_once_with(title, rating, comment, summary_txt)

    def test_record_interest_feedback(self):
        arxiv_id = "test.001"
        is_interesting = True
        reasons = ["relevant", "good methods"]
        user_insights = ["insight 1"]
        user_rating = 5

        self.orchestrator.record_interest_feedback(arxiv_id, is_interesting, reasons, user_rating, user_insights)
        
        # Check that LTM's record_user_interest_feedback was called
        self.mock_ltm.record_user_interest_feedback.assert_called_once()
        
        # Get the actual UserInterestFeedback object passed to the mock
        call_args = self.mock_ltm.record_user_interest_feedback.call_args[0]
        feedback_instance_arg = call_args[0]
        
        self.assertIsInstance(feedback_instance_arg, UserInterestFeedback)
        self.assertEqual(feedback_instance_arg.paper_arxiv_id, arxiv_id)
        self.assertEqual(feedback_instance_arg.is_interesting, is_interesting)
        self.assertEqual(feedback_instance_arg.reasons, reasons)
        self.assertEqual(feedback_instance_arg.extracted_insights, user_insights) # maps to extracted_insights in model
        self.assertEqual(feedback_instance_arg.user_rating, user_rating)
        self.assertIsNotNone(feedback_instance_arg.feedback_at)


    def test_add_preferred_keyword_to_memory(self):
        keyword = "preferred_test"
        self.orchestrator.add_preferred_keyword_to_memory(keyword)
        self.mock_ltm.add_preferred_keyword.assert_called_once_with(keyword)

    def test_add_irrelevant_keyword_to_memory(self):
        keyword = "irrelevant_test"
        self.orchestrator.add_irrelevant_keyword_to_memory(keyword)
        self.mock_ltm.add_irrelevant_keyword.assert_called_once_with(keyword)
        
    def test_get_all_preferences_from_memory(self):
        expected_prefs = {"preferred_keywords": ["test"], "irrelevant_keywords": ["blah"]} # Updated to match LTM structure
        self.mock_ltm.get_user_preferences.return_value = expected_prefs
        prefs = self.orchestrator.get_all_preferences_from_memory()
        self.assertEqual(prefs, expected_prefs)
        self.mock_ltm.get_user_preferences.assert_called_once()

    def test_reflect_and_get_suggestions(self):
        mock_keyword_suggs = {"preferred": ["from_refl"], "irrelevant": []}
        # Ensure this matches what ReflectionEngine.get_summary_parameter_suggestions returns
        mock_summary_suggs = {"suggestion": "Try summary_length=medium", "avg_rating": 3.5, "confidence": 0.8} 
        self.mock_reflection_engine.get_keyword_suggestions.return_value = mock_keyword_suggs
        self.mock_reflection_engine.get_summary_parameter_suggestions.return_value = mock_summary_suggs

        suggestions = self.orchestrator.reflect_and_get_suggestions()
        
        self.mock_reflection_engine.get_keyword_suggestions.assert_called_once()
        self.mock_reflection_engine.get_summary_parameter_suggestions.assert_called_once()
        self.assertEqual(suggestions["keywords"], mock_keyword_suggs)
        self.assertEqual(suggestions["summary_params"], mock_summary_suggs)

if __name__ == '__main__':
    unittest.main()
