import unittest
from unittest.mock import patch, Mock
from agents.arxiv_search_agent import ArxivSearchAgent
import datetime
import arxiv # Import arxiv to access SortCriterion in tests

class TestArxivSearchAgent(unittest.TestCase):

    def setUp(self):
        self.agent = ArxivSearchAgent()
        # Accessing self.agent.arxiv.SortCriterion might be problematic if arxiv module
        # itself is not directly an attribute of agent. So, we use arxiv.SortCriterion.

    @patch('arxiv.Search')
    @patch('arxiv.Client')
    def test_search_papers_success(self, MockClient, MockSearch):
        # Mocking the arxiv.Search object and its results
        mock_search_instance = MockSearch.return_value
        
        mock_result1 = Mock()
        mock_result1.title = "Paper 1 Title"
        author_a_p1 = Mock()
        author_a_p1.name = "Author A"
        author_b_p1 = Mock()
        author_b_p1.name = "Author B"
        mock_result1.authors = [author_a_p1, author_b_p1]
        mock_result1.summary = "Abstract of Paper 1"
        mock_result1.published = datetime.datetime(2023, 1, 1)

        mock_result2 = Mock()
        mock_result2.title = "Paper 2 Title"
        author_c_p2 = Mock()
        author_c_p2.name = "Author C"
        mock_result2.authors = [author_c_p2]
        mock_result2.summary = "Abstract of Paper 2"
        mock_result2.published = datetime.datetime(2023, 1, 2)

        # Mocking the client.results behavior
        mock_client_instance = MockClient.return_value
        mock_client_instance.results.return_value = [mock_result1, mock_result2]

        keywords = ["AI", "LLM"]
        results = self.agent.search_papers(keywords)

        MockSearch.assert_called_once_with(
            query="AI AND LLM",
            max_results=10, # This is the default in ArxivSearchAgent
            sort_by=arxiv.SortCriterion.Relevance
        )
        MockClient.assert_called_once() # Client is instantiated
        mock_client_instance.results.assert_called_once_with(mock_search_instance)


        self.assertEqual(len(results), 2)
        
        self.assertEqual(results[0]["title"], "Paper 1 Title")
        self.assertEqual(results[0]["authors"], ["Author A", "Author B"])
        self.assertEqual(results[0]["abstract"], "Abstract of Paper 1")
        self.assertEqual(results[0]["publication_date"], "2023-01-01")

        self.assertEqual(results[1]["title"], "Paper 2 Title")
        self.assertEqual(results[1]["authors"], ["Author C"])
        self.assertEqual(results[1]["abstract"], "Abstract of Paper 2")
        self.assertEqual(results[1]["publication_date"], "2023-01-02")

    @patch('arxiv.Search')
    @patch('arxiv.Client')
    def test_search_papers_no_results(self, MockClient, MockSearch):
        mock_search_instance = MockSearch.return_value
        mock_client_instance = MockClient.return_value
        mock_client_instance.results.return_value = [] # Simulate no results

        keywords = ["obscure topic"]
        results = self.agent.search_papers(keywords)

        MockSearch.assert_called_once_with(
            query="obscure topic",
            max_results=10,
            sort_by=arxiv.SortCriterion.Relevance
        )
        self.assertEqual(len(results), 0)

    @patch('arxiv.Search', side_effect=Exception("Arxiv API Error"))
    @patch('arxiv.Client')
    def test_search_papers_api_error(self, MockClient, MockSearch):
        # MockClient is still needed as it's instantiated before Search in the code flow
        keywords = ["AI"]
        # Expect the agent to catch the exception and return an empty list or handle it
        # Currently, ArxivSearchAgent doesn't explicitly catch exceptions from arxiv.Search()
        # For robustness, it should. Let's assume it re-raises or we test for the raw exception.
        with self.assertRaises(Exception) as context:
            self.agent.search_papers(keywords)
        self.assertTrue("Arxiv API Error" in str(context.exception))


    def test_extract_metadata(self):
        mock_paper = Mock()
        mock_paper.title = "Test Title"
        author_x = Mock()
        author_x.name = "Author X"
        author_y = Mock()
        author_y.name = "Author Y"
        mock_paper.authors = [author_x, author_y]
        mock_paper.summary = "Test Abstract"
        mock_paper.published = datetime.datetime(2024, 5, 15, 12, 0, 0)

        metadata = self.agent.extract_metadata(mock_paper)

        self.assertEqual(metadata["title"], "Test Title")
        self.assertEqual(metadata["authors"], ["Author X", "Author Y"])
        self.assertEqual(metadata["abstract"], "Test Abstract")
        self.assertEqual(metadata["publication_date"], "2024-05-15")
        
    def test_search_papers_empty_keywords(self):
        # The Arxiv library might handle empty query strings in a specific way,
        # or our agent might choose to return early.
        # Current implementation of search_papers joins keywords with " AND ".
        # If keywords is empty, query becomes "".
        # The arxiv library might error or return no results.
        # Let's assume an empty query to arxiv.Search is valid and returns no results.
        with patch('arxiv.Search') as MockSearchInner, patch('arxiv.Client') as MockClientInner: # Renamed to avoid outer scope collision
            mock_client_instance_inner = MockClientInner.return_value
            mock_client_instance_inner.results.return_value = []
            
            results = self.agent.search_papers([])
            MockSearchInner.assert_called_once_with(query="", max_results=10, sort_by=arxiv.SortCriterion.Relevance)
            self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
