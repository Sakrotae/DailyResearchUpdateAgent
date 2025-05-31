import unittest
import os
import json
from core.long_term_memory import LongTermMemory
from core.models import UserInterestFeedback # Added
from datetime import datetime

class TestLongTermMemory(unittest.TestCase):
    def setUp(self):
        self.test_memory_file = "test_ltm_for_unittest.json"
        # Ensure no old test file exists
        if os.path.exists(self.test_memory_file):
            os.remove(self.test_memory_file)
        self.ltm = LongTermMemory(memory_file=self.test_memory_file)

    def tearDown(self):
        # Clean up the test file after each test
        if os.path.exists(self.test_memory_file):
            os.remove(self.test_memory_file)

    def test_initialization_creates_file_if_not_exists(self):
        self.assertTrue(os.path.exists(self.test_memory_file))
        data = self.ltm._load_memory()
        self.assertEqual(data, self.ltm._default_memory_structure())

    def test_add_preferred_keyword(self):
        self.ltm.add_preferred_keyword("AI")
        self.assertIn("AI", self.ltm.data["user_preferences"]["preferred_keywords"]) # memory -> data
        self.ltm.add_preferred_keyword("AI") # Test adding duplicate
        self.assertEqual(self.ltm.data["user_preferences"]["preferred_keywords"].count("AI"), 1) # memory -> data
        self.ltm.add_preferred_keyword("ML")
        self.assertIn("ML", self.ltm.data["user_preferences"]["preferred_keywords"]) # memory -> data

    def test_add_irrelevant_keyword(self):
        self.ltm.add_irrelevant_keyword("sports")
        self.assertIn("sports", self.ltm.data["user_preferences"]["irrelevant_keywords"]) # memory -> data
        self.ltm.add_irrelevant_keyword("sports") # Test adding duplicate
        self.assertEqual(self.ltm.data["user_preferences"]["irrelevant_keywords"].count("sports"), 1) # memory -> data

    def test_record_paper_feedback(self):
        title = "Test Paper"
        self.ltm.record_paper_feedback(title, "good", "Very informative.", "Summary text.")
        self.assertIn(title, self.ltm.data["feedback_on_papers"]) # memory -> data
        feedback_list = self.ltm.data["feedback_on_papers"][title] # memory -> data
        self.assertEqual(len(feedback_list), 1)
        self.assertEqual(feedback_list[0]["rating"], "good")
        self.assertEqual(feedback_list[0]["comment"], "Very informative.")
        self.assertEqual(feedback_list[0]["summary_reviewed"], "Summary text.")
        self.assertTrue("timestamp" in feedback_list[0])

        # Add another feedback to the same paper
        self.ltm.record_paper_feedback(title, "excellent", "Loved it!")
        self.assertEqual(len(self.ltm.data["feedback_on_papers"][title]), 2) # memory -> data
        
        # Test recording feedback with no title (should print error, not store)
        initial_feedback_count = len(self.ltm.get_all_feedback().get(title, []))
        self.ltm.record_paper_feedback("", "bad", "No title") # Should be handled gracefully
        self.assertEqual(len(self.ltm.get_all_feedback().get(title, [])), initial_feedback_count, "Feedback count should not change for empty title")


    def test_get_user_preferences(self):
        self.ltm.add_preferred_keyword("quantum")
        prefs = self.ltm.get_user_preferences()
        self.assertIn("quantum", prefs["preferred_keywords"])

    def test_get_feedback_for_paper(self):
        title = "Another Test Paper"
        self.ltm.record_paper_feedback(title, "neutral", "It was okay.")
        feedback = self.ltm.get_feedback_for_paper(title)
        self.assertEqual(len(feedback), 1)
        self.assertEqual(feedback[0]["rating"], "neutral")
        self.assertEqual(len(self.ltm.get_feedback_for_paper("NonExistentPaper")), 0)

    def test_get_all_feedback(self):
        self.ltm.record_paper_feedback("Paper1", "good")
        self.ltm.record_paper_feedback("Paper2", "bad")
        all_feedback = self.ltm.get_all_feedback()
        self.assertIn("Paper1", all_feedback)
        self.assertIn("Paper2", all_feedback)
        self.assertEqual(len(all_feedback["Paper1"]), 1)

    def test_load_memory_corrupted_json(self):
        # Create a corrupted JSON file
        with open(self.test_memory_file, 'w') as f:
            f.write("{'invalid_json': ") # Corrupted content
        
        # Initialize new LTM instance to trigger _load_memory on the corrupted file
        ltm_corrupted = LongTermMemory(memory_file=self.test_memory_file)
        # Should load default structure instead of crashing
        self.assertEqual(ltm_corrupted.data, ltm_corrupted._default_memory_structure()) # memory -> data
        self.assertTrue(os.path.exists(self.test_memory_file)) # File should still exist or be recreated

    def test_save_and_load_persistence(self):
        self.ltm.add_preferred_keyword("persistence_test")
        self.ltm.record_paper_feedback("Persistent Paper", "good", "Persisted well")
        
        # Create a new instance, forcing it to load from the file
        ltm_new_instance = LongTermMemory(memory_file=self.test_memory_file)
        prefs = ltm_new_instance.get_user_preferences()
        self.assertIn("persistence_test", prefs["preferred_keywords"])
        
        feedback = ltm_new_instance.get_feedback_for_paper("Persistent Paper")
        self.assertEqual(len(feedback), 1)
        self.assertEqual(feedback[0]["rating"], "good")

    # --- New tests for UserInterestFeedback ---
    def test_record_and_get_user_interest_feedback_single(self):
        feedback_data = UserInterestFeedback(
            paper_arxiv_id="2303.00001",
            is_interesting=True,
            reasons=["very relevant", "novel method"],
            extracted_insights=["insight X", "insight Y"],
            user_rating=5,
            feedback_at=datetime.now().isoformat()
        )
        self.ltm.record_user_interest_feedback(feedback_data)
        
        retrieved_feedbacks = self.ltm.get_user_interest_feedback("2303.00001")
        self.assertEqual(len(retrieved_feedbacks), 1)
        self.assertIsInstance(retrieved_feedbacks[0], UserInterestFeedback)
        self.assertEqual(retrieved_feedbacks[0].paper_arxiv_id, "2303.00001")
        self.assertTrue(retrieved_feedbacks[0].is_interesting)
        self.assertEqual(retrieved_feedbacks[0].reasons, ["very relevant", "novel method"])
        self.assertEqual(retrieved_feedbacks[0].user_rating, 5)

    def test_record_and_get_user_interest_feedback_multiple(self):
        feedback1 = UserInterestFeedback(paper_arxiv_id="2303.00002", is_interesting=False, feedback_at=datetime.now().isoformat())
        feedback2 = UserInterestFeedback(paper_arxiv_id="2303.00003", is_interesting=True, user_rating=4, feedback_at=datetime.now().isoformat())
        self.ltm.record_user_interest_feedback(feedback1)
        self.ltm.record_user_interest_feedback(feedback2)

        all_feedbacks = self.ltm.get_user_interest_feedback()
        self.assertEqual(len(all_feedbacks), 2)
        # Check if IDs are present, specific content checked in other tests
        self.assertTrue(any(fb.paper_arxiv_id == "2303.00002" for fb in all_feedbacks))
        self.assertTrue(any(fb.paper_arxiv_id == "2303.00003" for fb in all_feedbacks))

    def test_get_user_interest_feedback_specific_id(self):
        feedback1 = UserInterestFeedback(paper_arxiv_id="2303.00004", is_interesting=True, feedback_at=datetime.now().isoformat())
        feedback2 = UserInterestFeedback(paper_arxiv_id="2303.00005", is_interesting=False, feedback_at=datetime.now().isoformat())
        feedback3 = UserInterestFeedback(paper_arxiv_id="2303.00004", is_interesting=False, reasons=["outdated"], feedback_at=datetime.now().isoformat()) # Another for .00004
        
        self.ltm.record_user_interest_feedback(feedback1)
        self.ltm.record_user_interest_feedback(feedback2)
        self.ltm.record_user_interest_feedback(feedback3)

        specific_feedbacks = self.ltm.get_user_interest_feedback("2303.00004")
        self.assertEqual(len(specific_feedbacks), 2)
        self.assertTrue(all(fb.paper_arxiv_id == "2303.00004" for fb in specific_feedbacks))
        
        # Check that the two feedbacks for 2303.00004 are distinct (e.g. by is_interesting or reasons)
        self.assertTrue(specific_feedbacks[0].is_interesting != specific_feedbacks[1].is_interesting or \
                        specific_feedbacks[0].reasons != specific_feedbacks[1].reasons)


    def test_get_user_interest_feedback_non_existent_id(self):
        feedback1 = UserInterestFeedback(paper_arxiv_id="2303.00006", is_interesting=True, feedback_at=datetime.now().isoformat())
        self.ltm.record_user_interest_feedback(feedback1)
        
        no_feedbacks = self.ltm.get_user_interest_feedback("0000.00000") # Non-existent ID
        self.assertEqual(len(no_feedbacks), 0)

    def test_get_user_interest_feedback_empty(self):
        # No feedback recorded yet in this test instance (setUp creates clean LTM)
        empty_feedbacks = self.ltm.get_user_interest_feedback()
        self.assertEqual(len(empty_feedbacks), 0)
        
        empty_feedbacks_specific = self.ltm.get_user_interest_feedback("any.id")
        self.assertEqual(len(empty_feedbacks_specific), 0)
        
    def test_default_memory_structure_includes_user_interest_feedbacks(self):
        default_struct = self.ltm._default_memory_structure()
        self.assertIn("user_interest_feedbacks", default_struct)
        self.assertEqual(default_struct["user_interest_feedbacks"], [])


if __name__ == '__main__':
    unittest.main()
