from agents.orchestrator_agent import OrchestratorAgent
# from core.models import PaperDetails, Summary # Not strictly needed for direct use here, orchestrator returns dicts with models
import os

def print_paper_details(index, result_item): # result_item is an element from orchestrator.process_query output
    paper_details = result_item['paper_details'] # This is a PaperDetails object
    summary = result_item['summary'] # This is a Summary object
    interest_assessment = result_item['interest_assessment']
    agent_insights = result_item['extracted_insights']

    print(f"\n--- Paper {index + 1} (ID: {paper_details.arxiv_id}) ---")
    print(f"Title: {paper_details.title}")
    print(f"Authors: {', '.join(paper_details.authors) if paper_details.authors else 'N/A'}")
    print(f"Publication Date: {paper_details.publication_date}")
    print(f"Source: {paper_details.source}, PDF: {paper_details.pdf_url}")
    print(f"Abstract snippet: {paper_details.abstract[:200]}..." if paper_details.abstract else "N/A")
    print(f"Summary: {summary.summary_text}")
    print(f"  (Summary model: {summary.model_used}, Generated at: {summary.generated_at})")
    print(f"Agent Assessment: {'Interesting' if interest_assessment.get('is_interesting') else 'Not rated interesting by agent (or agent error)'}")
    if interest_assessment.get('preliminary_insights'):
        print(f"Agent Preliminary Insights: {'; '.join(interest_assessment.get('preliminary_insights',[]))}")
    if agent_insights:
        print(f"Agent Extracted Insights (post-interest): {'; '.join(agent_insights)}")


def main():
    # Use a persistent memory file for the CLI application
    memory_file = "cli_agent_memory.json"
    orchestrator = OrchestratorAgent(memory_file=memory_file)
    
    print("Research Paper Assistant CLI")
    print("Type 'quit' or 'exit' to stop.")

    while True:
        print("\nMain Menu:")
        print("1. Search for papers")
        print("2. Manage keyword preferences")
        print("3. View all my preferences")
        print("4. Run reflection engine (see suggestions)")
        print("5. Exit")
        
        choice = input("Enter your choice: ").strip().lower()

        if choice in ['quit', 'exit', '5']:
            print("Exiting Research Paper Assistant. Your preferences and feedback are saved.")
            break
        
        elif choice == '1':
            query_str = input("Enter search keywords (comma-separated): ").strip()
            if not query_str:
                print("No keywords entered.")
                continue
            
            keywords = [k.strip() for k in query_str.split(',')]
            print(f"Searching for: {keywords}")
            
            results = orchestrator.process_query(keywords, max_papers=5)

            if isinstance(results, str): # Error message
                print(results)
                continue
            if not results:
                print("No papers found for your query.")
                continue

            print(f"\nFound {len(results)} papers:")
            for i, result_item in enumerate(results):
                print_paper_details(i, result_item)
            
            # New Feedback loop for papers using UserInterestFeedback
            while True:
                fb_choice = input("\nFeedback options: [p]aper feedback, [k]eyword prefs, [c]ontinue to main menu: ").strip().lower()
                if fb_choice == 'c':
                    break
                elif fb_choice == 'p':
                    try:
                        paper_idx_str = input(f"Enter paper number (1-{len(results)}) to give feedback on, or 'cancel': ").strip()
                        if paper_idx_str == 'cancel':
                            continue
                        paper_idx = int(paper_idx_str) - 1
                        
                        if 0 <= paper_idx < len(results):
                            selected_paper_result = results[paper_idx]
                            paper_details_model = selected_paper_result['paper_details']

                            print(f"\n--- Providing Feedback for Paper: {paper_details_model.title} (ID: {paper_details_model.arxiv_id}) ---")

                            interest_input = input("Is this paper interesting for your research? (yes/no/skip): ").strip().lower()
                            if interest_input == 'skip':
                                continue
                            
                            is_interesting = interest_input == 'yes'

                            reasons_str = input("Reasons for your rating (e.g., relevant_topic, good_methodology; comma-separated, optional): ").strip()
                            reasons_list = [r.strip() for r in reasons_str.split(',') if r.strip()] if reasons_str else None
                            
                            user_insights_str = input("Key insights YOU identified (comma-separated, optional): ").strip()
                            user_insights_list = [i.strip() for i in user_insights_str.split(',') if i.strip()] if user_insights_str else None

                            rating_str = input("Your overall rating for this paper (1-5 stars, optional): ").strip()
                            user_rating_val = None
                            if rating_str.isdigit():
                                user_rating_val = int(rating_str)
                                if not (1 <= user_rating_val <= 5):
                                    print("Invalid rating, should be between 1 and 5. Skipping rating.")
                                    user_rating_val = None
                            elif rating_str: # If not empty and not digit
                                print("Invalid input for rating. Skipping rating.")

                            orchestrator.record_interest_feedback(
                                paper_arxiv_id=paper_details_model.arxiv_id,
                                is_interesting=is_interesting,
                                reasons=reasons_list,
                                user_insights=user_insights_list, # This was 'extracted_insights' in model, but 'user_insights' in orchestrator method signature
                                user_rating=user_rating_val
                            )
                            print(f"Detailed interest feedback recorded for '{paper_details_model.title}'.")
                            
                            # Optionally, ask for legacy feedback if needed for reflection engine, or phase out.
                            # For now, the new feedback is primary. The reflection engine might need an update later.

                        else:
                            print("Invalid paper number.")
                    except ValueError:
                        print("Invalid input for paper number.")
                elif fb_choice == 'k':
                    manage_keywords_interactive(orchestrator)
                else:
                    print("Invalid choice.")

        elif choice == '2': # Manage keyword preferences
            manage_keywords_interactive(orchestrator)
            
        elif choice == '3':
            prefs = orchestrator.get_all_preferences_from_memory()
            print("\nYour Preferences:")
            print(f"  Preferred Keywords: {prefs.get('preferred_keywords', [])}") # type: ignore
            print(f"  Irrelevant Keywords: {prefs.get('irrelevant_keywords', [])}") # type: ignore
            # TODO: Future: Optionally show some stats from UserInterestFeedback, e.g., number of papers marked interesting.

        elif choice == '4': # Run reflection engine
            print("Note: Reflection engine currently uses legacy feedback for keyword suggestions.")
            orchestrator.reflect_and_get_suggestions()
            
        else:
            print("Invalid choice. Please try again.")

def manage_keywords_interactive(orchestrator):
    while True:
        print("\nManage Keyword Preferences:")
        print("1. Add preferred keyword")
        print("2. Add irrelevant keyword")
        print("3. Back to main menu")
        kw_choice = input("Enter choice: ").strip()

        if kw_choice == '1':
            p_kw = input("Enter keyword to add to preferred list: ").strip()
            if p_kw:
                orchestrator.add_preferred_keyword_to_memory(p_kw)
            else:
                print("No keyword entered.")
        elif kw_choice == '2':
            i_kw = input("Enter keyword to add to irrelevant list: ").strip()
            if i_kw:
                orchestrator.add_irrelevant_keyword_to_memory(i_kw)
            else:
                print("No keyword entered.")
        elif kw_choice == '3':
            break
        else:
            print("Invalid choice.")

if __name__ == '__main__':
    main()
