import unittest
from unittest.mock import patch, Mock, MagicMock
from agents.orchestrator_agent import OrchestratorAgent
# Assuming ArxivSearchAgent, SummarizerAgent, LongTermMemory, ReflectionEngine
# are in the PYTHONPATH or discoverable.

class TestOrchestratorAgent(unittest.TestCase):

    @patch('agents.orchestrator_agent.ReflectionEngine')
    @patch('agents.orchestrator_agent.LongTermMemory')
    @patch('agents.orchestrator_agent.SummarizerAgent')
    @patch('agents.orchestrator_agent.ArxivSearchAgent')
    def setUp(self, MockArxivSearchAgent, MockSummarizerAgent, MockLongTermMemory, MockReflectionEngine):
        # Instantiate mocks for all dependencies
        self.mock_arxiv_agent = MockArxivSearchAgent.return_value
        self.mock_summarizer_agent = MockSummarizerAgent.return_value
        self.mock_ltm = MockLongTermMemory.return_value
        self.mock_reflection_engine = MockReflectionEngine.return_value

        # Configure default behaviors for mocks
        self.mock_reflection_engine.get_keyword_suggestions.return_value = {
            "preferred": [], "irrelevant": []
        }

        # Instantiate the OrchestratorAgent. It will receive the mocked dependencies.
        self.test_memory_file = "test_orchestrator_for_unittest.json"
        self.orchestrator = OrchestratorAgent(memory_file=self.test_memory_file)

    def tearDown(self):
        # Clean up if OrchestratorAgent creates any files itself (e.g., its own LTM file if not mocked properly)
        # However, LongTermMemory itself is mocked, so OrchestratorAgent won't be creating
        # the actual LTM file unless its __init__ is not patched correctly.
        # The memory_file is passed to LTM, which is mocked.
        # If the Orchestrator's LTM instance `self.memory` was creating files, we'd clean `self.test_memory_file`.
        # But since `self.memory` is a mock (`self.mock_ltm`), it doesn't interact with the filesystem.
        pass


    def test_process_query_success(self):
        keywords = ["test query"]
        arxiv_results = [
            {"title": "Paper 1", "authors": ["AuthA"], "publication_date": "2023-01-01", "abstract": "Abstract 1"},
            {"title": "Paper 2", "authors": ["AuthB"], "publication_date": "2023-01-02", "abstract": "Abstract 2"}
        ]
        self.mock_arxiv_agent.search_papers.return_value = arxiv_results
        self.mock_summarizer_agent.summarize.side_effect = lambda text, max_length, min_length: f"Summary of {text[:10]}"

        results = self.orchestrator.process_query(keywords, max_papers=2)

        self.mock_arxiv_agent.search_papers.assert_called_once_with(keywords) # Before reflection, keywords are direct
        self.assertEqual(self.mock_summarizer_agent.summarize.call_count, 2)
        self.mock_summarizer_agent.summarize.assert_any_call("Abstract 1", max_length=100, min_length=20)
        self.mock_summarizer_agent.summarize.assert_any_call("Abstract 2", max_length=100, min_length=20)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Paper 1")
        self.assertEqual(results[0]["summary"], "Summary of Abstract 1")
        self.assertEqual(results[1]["title"], "Paper 2")
        self.assertEqual(results[1]["summary"], "Summary of Abstract 2")

    def test_process_query_with_preferred_keywords_from_reflection(self):
        user_keywords = ["search term"]
        preferred_keywords = ["boost this", "also this"]
        self.mock_reflection_engine.get_keyword_suggestions.return_value = {
            "preferred": preferred_keywords, "irrelevant": []
        }
        
        expected_effective_keywords = sorted(list(set(user_keywords + preferred_keywords)))
        
        self.mock_arxiv_agent.search_papers.return_value = [
             {"title": "Reflected Paper", "authors": ["AuthR"], "publication_date": "2023-02-01", "abstract": "Reflected Abstract"}
        ]
        self.mock_summarizer_agent.summarize.return_value = "Summary of Reflected Abstract"

        results = self.orchestrator.process_query(user_keywords, max_papers=1)

        # Arxiv agent should be called with combined keywords
        # The argument to search_papers is a list, order might vary due to set conversion.
        # So, we check that the call was made and then inspect the arguments.
        self.mock_arxiv_agent.search_papers.assert_called_once()
        called_args, _ = self.mock_arxiv_agent.search_papers.call_args
        self.assertEqual(sorted(called_args[0]), expected_effective_keywords)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Reflected Paper")

    def test_process_query_no_keywords_no_preferred(self):
        # If keywords is an empty list, the initial validation in process_query should catch it.
        # `not []` is True.
        result = self.orchestrator.process_query([])
        self.assertEqual(result, "Error: Invalid keywords provided. Please provide a list of strings.")
        self.mock_arxiv_agent.search_papers.assert_not_called()

    def test_process_query_arxiv_error(self):
        self.mock_arxiv_agent.search_papers.side_effect = Exception("Arxiv Down")
        result = self.orchestrator.process_query(["some query"])
        self.assertEqual(result, "Error during Arxiv search: Arxiv Down")

    def test_process_query_no_papers_found(self):
        self.mock_arxiv_agent.search_papers.return_value = []
        result = self.orchestrator.process_query(["rare query"])
        self.assertEqual(result, "No papers found for the given keywords.")

    def test_process_query_summarizer_error(self):
        arxiv_results = [{"title": "Paper X", "authors": [], "publication_date": "", "abstract": "Content X"}]
        self.mock_arxiv_agent.search_papers.return_value = arxiv_results
        self.mock_summarizer_agent.summarize.return_value = "Error: Summarizer failed" # Simulate error string

        results = self.orchestrator.process_query(["query"], max_papers=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["summary"], "Error: Summarizer failed")
        
    def test_process_query_paper_with_no_abstract(self):
        arxiv_results = [{"title": "Paper Y", "authors": [], "publication_date": "", "abstract": None}]
        self.mock_arxiv_agent.search_papers.return_value = arxiv_results
        
        results = self.orchestrator.process_query(["query"], max_papers=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["summary"], "Error: Abstract not available for this paper.")
        self.mock_summarizer_agent.summarize.assert_not_called()


    def test_record_feedback(self):
        title, rating, comment, summary = "Feedback Paper", "good", "Helpful", "Summary..."
        self.orchestrator.record_feedback(title, rating, comment, summary)
        self.mock_ltm.record_paper_feedback.assert_called_once_with(title, rating, comment, summary)

    def test_add_preferred_keyword_to_memory(self):
        keyword = "preferred_test"
        self.orchestrator.add_preferred_keyword_to_memory(keyword)
        self.mock_ltm.add_preferred_keyword.assert_called_once_with(keyword)

    def test_add_irrelevant_keyword_to_memory(self):
        keyword = "irrelevant_test"
        self.orchestrator.add_irrelevant_keyword_to_memory(keyword)
        self.mock_ltm.add_irrelevant_keyword.assert_called_once_with(keyword)
        
    def test_get_all_preferences_from_memory(self):
        expected_prefs = {"preferred": ["test"], "irrelevant": ["blah"]}
        self.mock_ltm.get_user_preferences.return_value = expected_prefs
        prefs = self.orchestrator.get_all_preferences_from_memory()
        self.assertEqual(prefs, expected_prefs)
        self.mock_ltm.get_user_preferences.assert_called_once()

    def test_reflect_and_get_suggestions(self):
        mock_keyword_suggs = {"preferred": ["from_refl"], "irrelevant": []}
        mock_summary_suggs = {"suggestion": "Try harder", "avg_rating": 2.5}
        self.mock_reflection_engine.get_keyword_suggestions.return_value = mock_keyword_suggs
        self.mock_reflection_engine.get_summary_parameter_suggestions.return_value = mock_summary_suggs

        suggestions = self.orchestrator.reflect_and_get_suggestions()
        
        self.mock_reflection_engine.get_keyword_suggestions.assert_called_once()
        self.mock_reflection_engine.get_summary_parameter_suggestions.assert_called_once()
        self.assertEqual(suggestions["keywords"], mock_keyword_suggs)
        self.assertEqual(suggestions["summary_params"], mock_summary_suggs)

if __name__ == '__main__':
    unittest.main()
