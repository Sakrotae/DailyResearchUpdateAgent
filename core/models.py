from pydantic import BaseModel
from typing import List, Optional

# Import date/datetime if you decide to use them
# from datetime import date, datetime

class PaperDetails(BaseModel):
    arxiv_id: str  # Primary identifier from Arxiv
    title: str
    authors: List[str]
    publication_date: str  # Consider using `datetime.date`
    abstract: str
    pdf_url: str  # Full PDF link on Arxiv
    source: str = "arxiv"  # Default to arxiv

class Summary(BaseModel):
    paper_arxiv_id: str  # To link back to PaperDetails
    summary_text: str
    model_used: Optional[str] = None  # e.g., name of the summarization model
    generated_at: str  # Consider `datetime.datetime`

class UserInterestFeedback(BaseModel):
    paper_arxiv_id: str  # To link back to PaperDetails
    is_interesting: bool
    reasons: Optional[List[str]] = None  # User's reasons for their rating
    extracted_insights: Optional[List[str]] = None  # Key insights
    user_rating: Optional[int] = None  # e.g., 1-5 stars
    feedback_at: str  # Consider `datetime.datetime`

class AgentInput(BaseModel):
    task_id: Optional[str] = None
    # pass  # as a starting point

class AgentOutput(BaseModel):
    pass  # as a starting point
