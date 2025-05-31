import unittest
import os
import json
from core.long_term_memory import LongTermMemory
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
        self.assertIn("AI", self.ltm.memory["user_preferences"]["preferred_keywords"])
        self.ltm.add_preferred_keyword("AI") # Test adding duplicate
        self.assertEqual(self.ltm.memory["user_preferences"]["preferred_keywords"].count("AI"), 1)
        self.ltm.add_preferred_keyword("ML")
        self.assertIn("ML", self.ltm.memory["user_preferences"]["preferred_keywords"])

    def test_add_irrelevant_keyword(self):
        self.ltm.add_irrelevant_keyword("sports")
        self.assertIn("sports", self.ltm.memory["user_preferences"]["irrelevant_keywords"])
        self.ltm.add_irrelevant_keyword("sports") # Test adding duplicate
        self.assertEqual(self.ltm.memory["user_preferences"]["irrelevant_keywords"].count("sports"), 1)

    def test_record_paper_feedback(self):
        title = "Test Paper"
        self.ltm.record_paper_feedback(title, "good", "Very informative.", "Summary text.")
        self.assertIn(title, self.ltm.memory["feedback_on_papers"])
        feedback_list = self.ltm.memory["feedback_on_papers"][title]
        self.assertEqual(len(feedback_list), 1)
        self.assertEqual(feedback_list[0]["rating"], "good")
        self.assertEqual(feedback_list[0]["comment"], "Very informative.")
        self.assertEqual(feedback_list[0]["summary_reviewed"], "Summary text.")
        self.assertTrue("timestamp" in feedback_list[0])

        # Add another feedback to the same paper
        self.ltm.record_paper_feedback(title, "excellent", "Loved it!")
        self.assertEqual(len(self.ltm.memory["feedback_on_papers"][title]), 2)
        
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
        self.assertEqual(ltm_corrupted.memory, ltm_corrupted._default_memory_structure())
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

if __name__ == '__main__':
    unittest.main()
