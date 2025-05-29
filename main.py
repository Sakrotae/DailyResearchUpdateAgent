from agents.orchestrator_agent import OrchestratorAgent
import os

def print_paper(index, paper):
    print(f"\n--- Paper {index + 1} ---")
    print(f"Title: {paper['title']}")
    print(f"Authors: {', '.join(paper['authors'])}")
    print(f"Publication Date: {paper['publication_date']}")
    print(f"Summary: {paper['summary']}")

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
            for i, paper in enumerate(results):
                print_paper(i, paper)
            
            # Feedback loop for papers
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
                            selected_paper = results[paper_idx]
                            rating = input(f"Rate summary for '{selected_paper['title']}' (good/neutral/bad/excellent/poor): ").strip().lower()
                            comment = input("Optional comment: ").strip()
                            if rating:
                                orchestrator.record_feedback(
                                    paper_title=selected_paper['title'],
                                    rating=rating,
                                    comment=comment,
                                    summary_text=selected_paper['summary']
                                )
                            else:
                                print("Rating is required.")
                        else:
                            print("Invalid paper number.")
                    except ValueError:
                        print("Invalid input for paper number.")
                elif fb_choice == 'k':
                    manage_keywords_interactive(orchestrator)
                else:
                    print("Invalid choice.")

        elif choice == '2':
            manage_keywords_interactive(orchestrator)
            
        elif choice == '3':
            prefs = orchestrator.get_all_preferences_from_memory()
            print("\nYour Preferences:")
            print(f"  Preferred Keywords: {prefs.get('preferred_keywords', [])}")
            print(f"  Irrelevant Keywords: {prefs.get('irrelevant_keywords', [])}")

        elif choice == '4':
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
