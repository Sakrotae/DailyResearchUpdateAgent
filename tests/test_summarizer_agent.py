import unittest
from unittest.mock import patch, Mock
from agents.summarizer_agent import SummarizerAgent

class TestSummarizerAgent(unittest.TestCase):

    @patch('agents.summarizer_agent.pipeline') # Target pipeline where it's used
    def setUp(self, MockPipeline):
        # Mock the pipeline globally for all tests in this class
        self.mock_summarizer_pipeline = Mock()
        MockPipeline.return_value = self.mock_summarizer_pipeline
        
        # Instantiate the agent - this will now use the mocked pipeline
        self.agent = SummarizerAgent(model_name="sshleifer/distilbart-cnn-6-6")
        MockPipeline.assert_called_once_with("summarization", model="sshleifer/distilbart-cnn-6-6")

    def test_summarize_success(self):
        input_text = "This is a long text that needs to be summarized effectively by the great summarizer."
        expected_summary = "Long text summarized."
        
        # Configure the mock pipeline's behavior for this test
        self.mock_summarizer_pipeline.return_value = [{'summary_text': expected_summary}]
        
        summary = self.agent.summarize(input_text, max_length=50, min_length=10)
        
        self.mock_summarizer_pipeline.assert_called_with(input_text, max_length=50, min_length=10, do_sample=False)
        self.assertEqual(summary, expected_summary)

    def test_summarize_empty_input(self):
        summary = self.agent.summarize("")
        self.assertEqual(summary, "Error: Input text is invalid.")
        self.mock_summarizer_pipeline.assert_not_called()

    def test_summarize_none_input(self):
        summary = self.agent.summarize(None)
        self.assertEqual(summary, "Error: Input text is invalid.")
        self.mock_summarizer_pipeline.assert_not_called()

    def test_summarize_non_string_input(self):
        summary = self.agent.summarize(12345)
        self.assertEqual(summary, "Error: Input text is invalid.")
        self.mock_summarizer_pipeline.assert_not_called()

    def test_summarize_pipeline_exception(self):
        input_text = "Some valid text for summarization."
        self.mock_summarizer_pipeline.side_effect = Exception("Pipeline error")
        
        summary = self.agent.summarize(input_text)
        
        self.assertTrue(summary.startswith("Error during summarization:"))
        self.assertIn("Pipeline error", summary)

    @patch('agents.summarizer_agent.pipeline') # Target pipeline where it's used
    def test_init_with_different_model(self, MockPipelineSpecific):
        mock_specific_pipeline = Mock()
        MockPipelineSpecific.return_value = mock_specific_pipeline
        
        agent_specific = SummarizerAgent(model_name="another/model")
        
        MockPipelineSpecific.assert_called_once_with("summarization", model="another/model")
        self.assertIsNotNone(agent_specific.summarizer)

if __name__ == '__main__':
    unittest.main()
