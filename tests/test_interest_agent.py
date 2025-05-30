import unittest
import os # For tearDown
from agents.interest_agent import InterestAgent
from core.models import PaperDetails, Summary
from core.long_term_memory import LongTermMemory # For future when agent uses memory

class TestInterestAgent(unittest.TestCase):
    def setUp(self):
        # self.memory = LongTermMemory(memory_file="test_ltm_for_interest_agent.json") # Optional
        # self.agent = InterestAgent(memory=self.memory) # Pass self.memory if agent uses it
        self.agent = InterestAgent() 
        
        self.dummy_paper_with_abstract = PaperDetails(
            arxiv_id="test.001", 
            title="Test Paper With Abstract", 
            authors=["Test Author"],
            publication_date="2023-01-01", 
            abstract="This is a test abstract with several interesting words for insight extraction. The agent should find this.",
            pdf_url="http://example.com/test.001.pdf"
        )
        self.dummy_summary_for_001 = Summary(
            paper_arxiv_id="test.001", 
            summary_text="Test summary for paper test.001.",
            model_used="test-model", 
            generated_at="2023-01-01T00:00:00Z"
        )
        
        self.dummy_paper_no_abstract = PaperDetails(
            arxiv_id="test.002", 
            title="Test Paper No Abstract", 
            authors=["Test Author"],
            publication_date="2023-01-01", 
            abstract=None, # No abstract
            pdf_url="http://example.com/test.002.pdf"
        )
        self.dummy_summary_for_002 = Summary( # Summary might still exist even if abstract was missing
            paper_arxiv_id="test.002", 
            summary_text="Summary for paper test.002 (no original abstract).",
            model_used="test-model", 
            generated_at="2023-01-01T00:00:00Z"
        )

        self.dummy_paper_short_abstract = PaperDetails(
            arxiv_id="test.003",
            title="Test Paper Short Abstract",
            authors=["Test Author"],
            publication_date="2023-01-03",
            abstract="Short one.",
            pdf_url="http://example.com/test.003.pdf"
        )
        self.dummy_summary_for_003 = Summary(
            paper_arxiv_id="test.003",
            summary_text="Summary for short abstract paper.",
            model_used="test-model",
            generated_at="2023-01-03T00:00:00Z"
        )


    def test_is_paper_interesting_default(self):
        """Tests the default behavior of is_paper_interesting."""
        result = self.agent.is_paper_interesting(self.dummy_paper_with_abstract, self.dummy_summary_for_001)
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get('is_interesting'), "Paper should be interesting by default.")
        self.assertEqual(result.get('preliminary_insights'), [], "Preliminary insights should be empty by default.")

    def test_extract_insights_default_with_abstract(self):
        """Tests insight extraction from a paper with a standard abstract."""
        insights = self.agent.extract_insights(self.dummy_paper_with_abstract, self.dummy_summary_for_001)
        self.assertIsInstance(insights, list)
        self.assertEqual(len(insights), 2, "Should return two insight snippets from abstract.")
        # Based on current InterestAgent.extract_insights logic:
        expected_insight_part_1 = "This is a test abstract with several interesting words for..." 
        # The actual implementation adds "..."
        self.assertTrue(insights[0].startswith("This is a test abstract with several interesting words for"))
        self.assertTrue(insights[0].endswith("..."))
        self.assertIn("words for insight extraction. The agent should find this.", self.dummy_paper_with_abstract.abstract) # Check original
        # Check second part
        self.assertTrue(insights[1].startswith("insight extraction. The agent should find this."))
        self.assertTrue(insights[1].endswith("..."))


    def test_extract_insights_empty_abstract(self):
        """Tests insight extraction when the paper has no abstract."""
        insights = self.agent.extract_insights(self.dummy_paper_no_abstract, self.dummy_summary_for_002)
        self.assertIsInstance(insights, list)
        self.assertEqual(insights, ["No abstract available to extract insights."], "Should return specific message for no abstract.")

    def test_extract_insights_short_abstract(self):
        """Tests insight extraction from a paper with a very short abstract."""
        insights = self.agent.extract_insights(self.dummy_paper_short_abstract, self.dummy_summary_for_003)
        self.assertIsInstance(insights, list)
        self.assertEqual(len(insights), 1) # Should return the whole abstract as one insight
        self.assertEqual(insights[0], "Short one.")


    # def tearDown(self):
    #     """Clean up any files created for testing LTM, if used."""
    #     # test_memory_file = "test_ltm_for_interest_agent.json"
    #     # if hasattr(self, 'memory') and self.memory.memory_file == test_memory_file:
    #     #     if os.path.exists(test_memory_file):
    #     #         os.remove(test_memory_file)
    #     pass # No LTM file created by InterestAgent directly in current setup

if __name__ == '__main__':
    unittest.main()
