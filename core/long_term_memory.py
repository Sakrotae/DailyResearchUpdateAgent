import json
import os
from datetime import datetime

class LongTermMemory:
    def __init__(self, memory_file="long_term_memory.json"):
        self.memory_file = memory_file
        self.memory = self._load_memory()

    def _load_memory(self):
        """Loads memory from the JSON file."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {self.memory_file}. Starting with empty memory.")
                # For a corrupted file, we want to save the default structure back.
                default_mem = self._default_memory_structure()
                self._save_memory_content(default_mem) # Save default if corrupted
                return default_mem
        # If file does not exist, create it with default structure
        default_mem = self._default_memory_structure()
        self._save_memory_content(default_mem)
        return default_mem

    def _save_memory_content(self, memory_content):
        """Saves the given memory content to the JSON file."""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(memory_content, f, indent=4)
        except IOError as e:
            print(f"Error saving memory to {self.memory_file}: {e}")

    def _default_memory_structure(self):
        """Returns the default structure for the memory."""
        return {
            "user_preferences": {
                "preferred_keywords": [],
                "irrelevant_keywords": []
            },
            "feedback_on_papers": {} # Store feedback per paper title
        }

    def _save_memory(self):
        """Saves the current internal memory state to the JSON file."""
        self._save_memory_content(self.memory)

    def add_preferred_keyword(self, keyword):
        """Adds a keyword to the user's preferred list."""
        if keyword and keyword not in self.memory["user_preferences"]["preferred_keywords"]:
            self.memory["user_preferences"]["preferred_keywords"].append(keyword)
            self._save_memory()
            print(f"Memory: Added '{keyword}' to preferred keywords.")

    def add_irrelevant_keyword(self, keyword):
        """Adds a keyword to the user's irrelevant list."""
        if keyword and keyword not in self.memory["user_preferences"]["irrelevant_keywords"]:
            self.memory["user_preferences"]["irrelevant_keywords"].append(keyword)
            self._save_memory()
            print(f"Memory: Added '{keyword}' to irrelevant keywords.")

    def record_paper_feedback(self, paper_title, rating, comment=None, summary_text=None):
        """
        Records feedback for a specific paper.
        Rating should be something simple (e.g., "good", "bad", "neutral" or 1-5).
        """
        if not paper_title:
            print("Error: Paper title is required to record feedback.")
            return

        feedback_entry = {
            "rating": rating,
            "comment": comment,
            "summary_reviewed": summary_text, # Optional: store the summary that was reviewed
            "timestamp": datetime.now().isoformat()
        }
        
        if paper_title not in self.memory["feedback_on_papers"]:
            self.memory["feedback_on_papers"][paper_title] = []
        
        self.memory["feedback_on_papers"][paper_title].append(feedback_entry)
        self._save_memory()
        print(f"Memory: Recorded feedback for paper '{paper_title}'. Rating: {rating}")

    def get_user_preferences(self):
        """Returns the user's stored preferences."""
        return self.memory.get("user_preferences", self._default_memory_structure()["user_preferences"])

    def get_feedback_for_paper(self, paper_title):
        """Returns all feedback recorded for a specific paper."""
        return self.memory["feedback_on_papers"].get(paper_title, [])

    def get_all_feedback(self):
        """Returns all recorded feedback."""
        return self.memory["feedback_on_papers"]

if __name__ == '__main__':
    # Test the LongTermMemory class
    ltm = LongTermMemory(memory_file="test_ltm.json") # Use a test file

    print("Initial Preferences:", ltm.get_user_preferences())
    ltm.add_preferred_keyword("quantum computing")
    ltm.add_preferred_keyword("AI ethics")
    ltm.add_irrelevant_keyword("sports scores")
    print("Updated Preferences:", ltm.get_user_preferences())

    ltm.record_paper_feedback(
        paper_title="Test Paper A: Intro to Quantum AI",
        rating="good",
        comment="Very insightful, but a bit dense.",
        summary_text="Quantum AI combines quantum computing with AI..."
    )
    ltm.record_paper_feedback(
        paper_title="Test Paper A: Intro to Quantum AI",
        rating="excellent",
        comment="Follow-up: The examples were great!",
    )
    ltm.record_paper_feedback(
        paper_title="Test Paper B: Sports Analytics",
        rating="bad",
        comment="Not relevant to my interests."
    )

    print("\nFeedback for 'Test Paper A: Intro to Quantum AI':")
    for feedback in ltm.get_feedback_for_paper("Test Paper A: Intro to Quantum AI"):
        print(f"  - Rating: {feedback['rating']}, Comment: {feedback['comment']}, Timestamp: {feedback['timestamp']}")

    print("\nAll Feedback:")
    all_fb = ltm.get_all_feedback()
    for title, feedbacks in all_fb.items():
        print(f"  {title}: {len(feedbacks)} feedback entries")

    # Clean up the test file
    if os.path.exists("test_ltm.json"):
        os.remove("test_ltm.json")
    print("\nCleaned up test_ltm.json")
