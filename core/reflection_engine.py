from collections import Counter

class ReflectionEngine:
    def __init__(self, long_term_memory):
        self.ltm = long_term_memory

    def analyze_summary_feedback(self, min_feedback_threshold=3):
        """
        Analyzes feedback on summaries to identify trends.
        For now, this is a placeholder for more sophisticated analysis.
        It could identify if papers with certain keywords get better summary ratings.
        Returns:
            dict: Analysis results (e.g., average ratings per keyword).
        """
        feedback_on_papers = self.ltm.get_all_feedback()
        keyword_ratings = {} # e.g. {"keyword1": {"sum_ratings": N, "count": M, "avg_rating": X}}
        
        # This is a simplified model: assumes ratings are numerical or easily convertible.
        # Our current LTM stores ratings as strings like "good", "bad".
        # For a real system, we'd need a consistent rating scale (e.g., 1-5).
        # Let's simulate a conversion for now: good=4, neutral=3, bad=2 (very rough)
        rating_map = {"good": 4, "excellent": 5, "neutral": 3, "bad": 2, "poor": 1}

        # This analysis is quite basic. True insights would require linking feedback to paper content/keywords.
        # For now, let's just calculate overall average rating to show the mechanism.
        all_ratings = []
        for paper_title, feedbacks in feedback_on_papers.items():
            for fb_item in feedbacks:
                rating_value = rating_map.get(fb_item.get("rating", "").lower())
                if rating_value:
                    all_ratings.append(rating_value)
        
        if not all_ratings:
            return {"average_summary_rating": None, "message": "Not enough feedback to analyze summary ratings."}

        avg_rating = sum(all_ratings) / len(all_ratings)
        return {"average_summary_rating": avg_rating}

    def get_keyword_suggestions(self):
        """
        Consolidates preferred and irrelevant keywords from LTM.
        Returns:
            dict: {"preferred": list_of_keywords, "irrelevant": list_of_keywords}
        """
        preferences = self.ltm.get_user_preferences()
        return {
            "preferred": preferences.get("preferred_keywords", []),
            "irrelevant": preferences.get("irrelevant_keywords", [])
        }

    def get_summary_parameter_suggestions(self):
        """
        Suggests adjustments for summarization parameters.
        Placeholder: Real implementation would need more data, e.g.,
        feedback on summary length, or correlation of ratings with lengths used.
        """
        # Example: If avg rating is low, suggest trying shorter summaries (more concise).
        # This is highly speculative without more data.
        analysis = self.analyze_summary_feedback()
        avg_rating = analysis.get("average_summary_rating")

        if avg_rating is not None:
            if avg_rating < 2.8: # Assuming a 1-5 scale where <3 is not great
                return {"suggestion": "Consider trying shorter, more concise summaries if possible.", "avg_rating": avg_rating}
            elif avg_rating > 4.0:
                return {"suggestion": "Current summarization approach seems well-received.", "avg_rating": avg_rating}
        return {"suggestion": "Not enough data for summary parameter suggestions.", "avg_rating": avg_rating}

if __name__ == '__main__':
    # Mock LTM for testing ReflectionEngine
    class MockLongTermMemory:
        def __init__(self):
            self.preferences = {
                "preferred_keywords": ["AI ethics", "LLM security"],
                "irrelevant_keywords": ["sports"]
            }
            self.feedback = {
                "Paper on AI Ethics": [
                    {"rating": "excellent", "comment": "Great!"},
                    {"rating": "good", "comment": "Solid."}
                ],
                "Paper on LLM Security": [
                    {"rating": "good", "comment": "Important topic."}
                ],
                "Paper on Sports": [
                    {"rating": "bad", "comment": "Not for me."}
                ]
            }

        def get_user_preferences(self):
            return self.preferences

        def get_all_feedback(self):
            return self.feedback
            
        def add_preferred_keyword(self, keyword): # Added to satisfy Orchestrator tests
            if keyword not in self.preferences["preferred_keywords"]:
                self.preferences["preferred_keywords"].append(keyword)
        
        def add_irrelevant_keyword(self, keyword): # Added
            if keyword not in self.preferences["irrelevant_keywords"]:
                self.preferences["irrelevant_keywords"].append(keyword)

        def record_paper_feedback(self, paper_title, rating, comment=None, summary_text=None): # Added
            if paper_title not in self.feedback:
                self.feedback[paper_title] = []
            self.feedback[paper_title].append({"rating": rating, "comment": comment, "summary_text": summary_text})


    mock_ltm = MockLongTermMemory()
    engine = ReflectionEngine(mock_ltm)

    print("--- Keyword Suggestions ---")
    keyword_suggs = engine.get_keyword_suggestions()
    print(f"  Preferred: {keyword_suggs['preferred']}")
    print(f"  Irrelevant: {keyword_suggs['irrelevant']}")

    print("\n--- Summary Feedback Analysis ---")
    summary_analysis = engine.analyze_summary_feedback()
    print(f"  Average Summary Rating (simulated 1-5): {summary_analysis.get('average_summary_rating')}")
    
    print("\n--- Summary Parameter Suggestions ---")
    param_suggs = engine.get_summary_parameter_suggestions()
    print(f"  Suggestion: {param_suggs['suggestion']} (Avg Rating: {param_suggs.get('avg_rating')})")

    # Add more feedback to change average
    mock_ltm.record_paper_feedback("Another Paper", "poor", "Not good.")
    mock_ltm.record_paper_feedback("Yet Another", "bad", "Still bad.")
    summary_analysis_after = engine.analyze_summary_feedback()
    param_suggs_after = engine.get_summary_parameter_suggestions()
    print("\n--- After adding poor feedback ---")
    print(f"  Average Summary Rating: {summary_analysis_after.get('average_summary_rating')}")
    print(f"  Suggestion: {param_suggs_after['suggestion']} (Avg Rating: {param_suggs_after.get('avg_rating')})")
