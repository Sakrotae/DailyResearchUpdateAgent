import openai # Import the OpenAI library
from mas_paper_search.core.base_agent import BaseAgent, AgentOutput
from mas_paper_search.config.settings import settings
import logging
import httpx # For potential OpenAI client configuration, though not strictly needed for basic usage

# Configure logging for the agent
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SummarizeAgent(BaseAgent):
    '''
    An agent responsible for summarizing text content using an LLM (GPT-4o).
    '''

    def __init__(self):
        super().__init__()
        # Initialize the OpenAI client.
        # It will automatically pick up the OPENAI_API_KEY from environment variables
        # if `settings.OPENAI_API_KEY` is correctly loaded into the environment,
        # or by direct assignment if preferred.
        # Ensure the API key is set in your .env file and loaded by settings.
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            logger.error("SummarizeAgent: OpenAI API key is not configured. Please set it in your .env file.")
            # This agent might be initialized even if the key is missing,
            # but execute_task will fail.

        # Starting with OpenAI SDK v1.0.0, client instantiation is required.
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


    async def execute_task(self, task_input: dict) -> AgentOutput:
        '''
        Executes the text summarization task.

        Args:
            task_input (dict): A dictionary containing:
                - 'text_content' (str): The text to be summarized.
                - 'user_interests' (list[str], optional): A list of user interests
                                                          to guide the summary.
                                                          Defaults to a general prompt.
                - 'max_tokens_summary' (int, optional): Max tokens for the summary. Default 300.

        Returns:
            AgentOutput: An object containing the summary or an error message.
        '''
        text_content = task_input.get('text_content')
        if not text_content:
            logger.error("SummarizeAgent: 'text_content' not provided in task_input.")
            return AgentOutput(success=False, error_message="'text_content' is required for summarization.")

        user_interests = task_input.get('user_interests', ["AI agents", "Large Language Models (LLMs)", "computer vision"])
        max_tokens_summary = task_input.get('max_tokens_summary', 300) # Max tokens for the summary itself

        # Basic check for API key
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            logger.error("SummarizeAgent: OpenAI API key is not configured.")
            return AgentOutput(success=False, error_message="OpenAI API key is not configured.")

        logger.info(f"SummarizeAgent: Attempting to summarize text (approx {len(text_content)} chars).")

        # Constructing the prompt
        # The base model gpt-4o has a large context window (e.g. 128k tokens) but we should be mindful of costs.
        # For summarization, we might not need the full text if it's extremely long.
        # However, for this first version, we'll send the whole text.
        # Consider truncation/chunking strategies for very long texts in future iterations.

        prompt_template = (
            "You are an expert research assistant. Please summarize the following academic paper text. "
            "Focus on the most interesting findings, key contributions, and methodologies, "
            "especially those relevant to the fields of: {interests_str}. "
            "The summary should be concise, clear, and suitable for someone wanting to stay up-to-date on these topics. "
            "Do not include any prefatory phrases like 'This paper discusses...' or 'The authors investigate...'. "
                "Just provide the summary directly. Limit the summary to approximately {max_tokens_summary} tokens.\n\n"
                "--- Paper Text ---\n"
                "{text_content}\n\n"
                "--- Summary ---"
        )

        interests_str = ", ".join(user_interests)
        prompt = prompt_template.format(
            interests_str=interests_str,
            text_content=text_content[:40000], # Truncate input text to avoid excessive token usage for now
            max_tokens_summary=max_tokens_summary
        )

        try:
            # Using the chat completions endpoint with gpt-4o
            response = await self.client.chat.completions.create(
                model="gpt-4o", # Explicitly use gpt-4o
                messages=[
                    {"role": "system", "content": "You are a helpful research assistant specialized in summarizing academic papers."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens_summary, # Max tokens for the generated summary
                temperature=0.5, # Lower temperature for more factual summaries
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )

            summary = response.choices[0].message.content.strip()

            if not summary:
                logger.warning("SummarizeAgent: LLM returned an empty summary.")
                return AgentOutput(success=True, data={"summary": "", "message": "LLM returned an empty summary."})

            logger.info("SummarizeAgent: Successfully generated summary.")
            return AgentOutput(success=True, data={"summary": summary})

        except openai.APIError as e: # Catch OpenAI specific API errors
            logger.error(f"SummarizeAgent: OpenAI API error: {e}")
            return AgentOutput(success=False, error_message=f"OpenAI API error: {str(e)}")
        except httpx.RequestError as e: # Catch network errors related to the API call
            logger.error(f"SummarizeAgent: Network error calling OpenAI API: {e}")
            return AgentOutput(success=False, error_message=f"Network error calling OpenAI API: {str(e)}")
        except Exception as e:
            logger.exception(f"SummarizeAgent: An unexpected error occurred during summarization: {e}")
            return AgentOutput(success=False, error_message=f"An unexpected error occurred during summarization: {str(e)}")

# Example Usage (for testing purposes, requires a valid OpenAI API Key in .env)
# if __name__ == "__main__":
#     import asyncio
#
#     async def test_summarize_agent():
#         # Ensure OPENAI_API_KEY is set in your .env file and loaded by settings
#         if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
#             print("OpenAI API key not found or is a placeholder. Please set it in .env to run this test.")
#             return
#
#         agent = SummarizeAgent()
#
#         sample_text = (
#             "Large Language Models (LLMs) have demonstrated remarkable capabilities in natural language understanding and generation. "
#             "This paper introduces a novel technique called 'Reflective Summarization' which prompts the LLM to first identify "
#             "key sentences and then iteratively refine a summary based on them. Experiments on a diverse set of academic articles "
#             "show that Reflective Summarization achieves state-of-the-art results in terms of ROUGE scores and human evaluations. "
#             "The core idea is to mimic the human process of highlighting important parts before writing a summary. "
#             "Furthermore, we explore the impact of different base LLMs, including GPT-4 and Llama 2, on the final summary quality. "
#             "Our findings indicate that larger models benefit more from this technique. We also release a new benchmark dataset for summarization."
#         )
#
#         # Test case 1: Valid text
#         output_valid = await agent.execute_task({"text_content": sample_text})
#         print("\n--- Test Case 1: Valid Text ---")
#         if output_valid.success:
#             print(f"Successfully generated summary:")
#             print(output_valid.data.get('summary'))
#         else:
#             print(f"Error: {output_valid.error_message}")
#
#         # Test case 2: Empty text
#         output_empty_text = await agent.execute_task({"text_content": ""})
#         print("\n--- Test Case 2: Empty Text ---")
#         if not output_empty_text.success:
#             print(f"Correctly failed with error: {output_empty_text.error_message}")
#         else:
#             print("Test failed: Should have reported an error for empty text.")
#
#         # Test case 3: Missing text_content
#         output_missing_text = await agent.execute_task({})
#         print("\n--- Test Case 3: Missing text_content ---")
#         if not output_missing_text.success:
#             print(f"Correctly failed with error: {output_missing_text.error_message}")
#         else:
#             print("Test failed: Should have reported an error for missing text_content.")
#
#     asyncio.run(test_summarize_agent())
