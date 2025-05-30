import json
import os
from datetime import datetime
from core.models import UserInterestFeedback # Added import

class LongTermMemory:
    def __init__(self, memory_file="long_term_memory.json"):
        self.memory_file = memory_file
        self.data = self._load_memory() # Renamed self.memory to self.data for clarity
        self.data.setdefault('user_interest_feedbacks', []) # Initialize storage for interest feedback

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
            "feedback_on_papers": {}, # Store feedback per paper title
            "user_interest_feedbacks": [] # Added for new feedback model
        }

    def _save_memory(self):
        """Saves the current internal memory state to the JSON file."""
        self._save_memory_content(self.data) # Changed self.memory to self.data

    def add_preferred_keyword(self, keyword):
        """Adds a keyword to the user's preferred list."""
        if keyword and keyword not in self.data["user_preferences"]["preferred_keywords"]: # Changed self.memory to self.data
            self.data["user_preferences"]["preferred_keywords"].append(keyword) # Changed self.memory to self.data
            self._save_memory()
            print(f"Memory: Added '{keyword}' to preferred keywords.")

    def add_irrelevant_keyword(self, keyword):
        """Adds a keyword to the user's irrelevant list."""
        if keyword and keyword not in self.data["user_preferences"]["irrelevant_keywords"]: # Changed self.memory to self.data
            self.data["user_preferences"]["irrelevant_keywords"].append(keyword) # Changed self.memory to self.data
            self._save_memory()
            print(f"Memory: Added '{keyword}' to irrelevant keywords.")

    def record_paper_feedback(self, paper_title, rating, comment=None, summary_text=None):
        """
        Note: This method is for basic feedback. For more detailed interest tracking,
        use record_user_interest_feedback.
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
        
        if paper_title not in self.data["feedback_on_papers"]: # Changed self.memory to self.data
            self.data["feedback_on_papers"][paper_title] = [] # Changed self.memory to self.data
        
        self.data["feedback_on_papers"][paper_title].append(feedback_entry) # Changed self.memory to self.data
        self._save_memory()
        print(f"Memory: Recorded feedback for paper '{paper_title}'. Rating: {rating}")

    def get_user_preferences(self):
        """Returns the user's stored preferences."""
        return self.data.get("user_preferences", self._default_memory_structure()["user_preferences"]) # Changed self.memory to self.data

    def get_feedback_for_paper(self, paper_title):
        """Returns all feedback recorded for a specific paper."""
        return self.data["feedback_on_papers"].get(paper_title, []) # Changed self.memory to self.data

    def get_all_feedback(self):
        """Returns all recorded feedback."""
        return self.data["feedback_on_papers"] # Changed self.memory to self.data

    # New methods for UserInterestFeedback
    def record_user_interest_feedback(self, feedback_data: UserInterestFeedback):
        """Records detailed user interest feedback for a paper."""
        self.data.setdefault('user_interest_feedbacks', []).append(feedback_data.model_dump())
        self.save_memory() # Corrected: was self.save_memory() in instructions, should be self._save_memory()
        print(f"LongTermMemory: Recorded interest feedback for paper ID {feedback_data.paper_arxiv_id}.")

    def get_user_interest_feedback(self, paper_arxiv_id: str | None = None) -> list[UserInterestFeedback]:
        """
        Retrieves user interest feedback, optionally filtered by paper_arxiv_id.
        Returns a list of UserInterestFeedback objects.
        """
        feedbacks_as_dicts = self.data.get('user_interest_feedbacks', [])
        if not feedbacks_as_dicts:
            return []

        all_feedback_objects = [UserInterestFeedback(**data) for data in feedbacks_as_dicts]

        if paper_arxiv_id:
            return [fb for fb in all_feedback_objects if fb.paper_arxiv_id == paper_arxiv_id]
        return all_feedback_objects

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

    print("\nAll Feedback (old system):")
    all_fb = ltm.get_all_feedback()
    for title, feedbacks in all_fb.items():
        print(f"  {title}: {len(feedbacks)} feedback entries")

    print("\n--- Testing UserInterestFeedback ---")
    # Create some UserInterestFeedback instances
    feedback1_data = {
        "paper_arxiv_id": "2301.00001",
        "is_interesting": True,
        "reasons": ["novel approach", "potential impact"],
        "extracted_insights": ["insight A", "insight B"],
        "user_rating": 5,
        "feedback_at": datetime.now().isoformat()
    }
    feedback1 = UserInterestFeedback(**feedback1_data)
    ltm.record_user_interest_feedback(feedback1)

    feedback2_data = {
        "paper_arxiv_id": "2301.00002",
        "is_interesting": False,
        "reasons": ["not relevant to my field"],
        "feedback_at": datetime.now().isoformat()
    }
    feedback2 = UserInterestFeedback(**feedback2_data)
    ltm.record_user_interest_feedback(feedback2)
    
    feedback3_data = {
        "paper_arxiv_id": "2301.00001", # Another feedback for the first paper
        "is_interesting": True,
        "reasons": ["follow-up thoughts", "good methodology"],
        "user_rating": 4,
        "feedback_at": datetime.now().isoformat()
    }
    feedback3 = UserInterestFeedback(**feedback3_data)
    ltm.record_user_interest_feedback(feedback3)

    print("\nRetrieving all UserInterestFeedback:")
    all_interest_feedback = ltm.get_user_interest_feedback()
    for fb in all_interest_feedback:
        print(f"  Paper ID: {fb.paper_arxiv_id}, Interesting: {fb.is_interesting}, Reasons: {fb.reasons}, Rating: {fb.user_rating}")
    assert len(all_interest_feedback) == 3

    print("\nRetrieving UserInterestFeedback for paper '2301.00001':")
    paper1_feedback = ltm.get_user_interest_feedback(paper_arxiv_id="2301.00001")
    for fb in paper1_feedback:
        print(f"  Paper ID: {fb.paper_arxiv_id}, Interesting: {fb.is_interesting}, Reasons: {fb.reasons}, Rating: {fb.user_rating}")
    assert len(paper1_feedback) == 2
    assert paper1_feedback[0].reasons == ["novel approach", "potential impact"]
    
    print("\nRetrieving UserInterestFeedback for non-existent paper '0000.00000':")
    non_existent_feedback = ltm.get_user_interest_feedback(paper_arxiv_id="0000.00000")
    print(f"  Found: {non_existent_feedback}")
    assert len(non_existent_feedback) == 0
    
    # Clean up the test file
    if os.path.exists("test_ltm.json"):
        os.remove("test_ltm.json")
    print("\nCleaned up test_ltm.json")
    print("LongTermMemory tests with UserInterestFeedback passed.")
