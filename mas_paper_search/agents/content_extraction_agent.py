import httpx
import fitz # PyMuPDF
from mas_paper_search.core.base_agent import BaseAgent, AgentOutput
import logging
import io

# Configure logging for the agent
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentExtractionAgent(BaseAgent):
    '''
    An agent responsible for downloading a PDF from a URL
    and extracting its text content.
    '''

    async def execute_task(self, task_input: dict) -> AgentOutput:
        '''
        Executes the PDF content extraction task.

        Args:
            task_input (dict): A dictionary containing:
                - 'pdf_url' (str): The URL of the PDF to process.

        Returns:
            AgentOutput: An object containing the extracted text or an error message.
        '''
        pdf_url = task_input.get('pdf_url')
        if not pdf_url:
            logger.error("ContentExtractionAgent: 'pdf_url' not provided in task_input.")
            return AgentOutput(success=False, error_message="'pdf_url' is required for content extraction.")

        logger.info(f"ContentExtractionAgent: Attempting to download and extract text from {pdf_url}")

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client: # Increased timeout and allow redirects
                response = await client.get(pdf_url)
                response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

            pdf_bytes = response.content
            logger.info(f"ContentExtractionAgent: Successfully downloaded PDF from {pdf_url} ({len(pdf_bytes)} bytes).")

            # Extract text using PyMuPDF (fitz)
            text_content = ""
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    text_content += page.get_text()

            if not text_content.strip():
                logger.warning(f"ContentExtractionAgent: No text extracted from PDF {pdf_url}. It might be an image-based PDF or empty.")
                # Still success, but with a message.
                return AgentOutput(success=True, data={"extracted_text": "", "message": "No text content found in PDF."})

            logger.info(f"ContentExtractionAgent: Successfully extracted text from {pdf_url} (approx {len(text_content)} chars).")
            return AgentOutput(success=True, data={"extracted_text": text_content, "pdf_url": pdf_url})

        except httpx.HTTPStatusError as e:
            logger.error(f"ContentExtractionAgent: HTTP error {e.response.status_code} while downloading {pdf_url}: {e}")
            return AgentOutput(success=False, error_message=f"HTTP error {e.response.status_code} downloading PDF: {e.request.url}")
        except httpx.RequestError as e:
            logger.error(f"ContentExtractionAgent: Network error downloading {pdf_url}: {e}")
            return AgentOutput(success=False, error_message=f"Network error downloading PDF: {str(e)}")
        except fitz.fitz.PyMuPDFError as e: # More specific PyMuPDF exception
             logger.error(f"ContentExtractionAgent: PyMuPDF error processing PDF from {pdf_url}: {e}")
             return AgentOutput(success=False, error_message=f"Error processing PDF content: {str(e)}")
        except Exception as e:
            logger.exception(f"ContentExtractionAgent: An unexpected error occurred while processing {pdf_url}: {e}")
            return AgentOutput(success=False, error_message=f"An unexpected error occurred: {str(e)}")

# Example Usage (for testing purposes, can be removed or commented out later)
# if __name__ == "__main__":
#     import asyncio
#
#     async def test_content_extraction():
#         agent = ContentExtractionAgent()
#
#         # Test case 1: Valid Arxiv PDF URL
#         # (Using a known paper, replace with a current one if this link breaks)
#         # Example: "Attention Is All You Need"
#         valid_pdf_url = "https://arxiv.org/pdf/1706.03762.pdf"
#         output_valid = await agent.execute_task({"pdf_url": valid_pdf_url})
#
#         print("\n--- Test Case 1: Valid PDF URL ---")
#         if output_valid.success:
#             print(f"Successfully extracted text from {output_valid.data.get('pdf_url')}.")
#             print(f"Extracted text length: {len(output_valid.data.get('extracted_text', ''))} characters.")
#             # print(f"Sample text: {output_valid.data.get('extracted_text', '')[:500]}...") # Uncomment to see sample
#         else:
#             print(f"Error: {output_valid.error_message}")
#
#         # Test case 2: Invalid URL (non-PDF)
#         invalid_url_not_pdf = "https://arxiv.org/abs/1706.03762" # This is an abstract page, not a PDF
#         output_invalid_not_pdf = await agent.execute_task({"pdf_url": invalid_url_not_pdf})
#         print("\n--- Test Case 2: Invalid URL (Not a PDF) ---")
#         if not output_invalid_not_pdf.success:
#             print(f"Correctly failed with error: {output_invalid_not_pdf.error_message}")
#         else:
#             # This might succeed if the content type isn't strictly checked by PyMuPDF and it tries to parse HTML
#             # or if the server returns a PDF anyway (unlikely for abstract pages)
#             print(f"Test might not be as expected. Success: {output_invalid_not_pdf.success}, Message: {output_invalid_not_pdf.data.get('message','')}")
#             print(f"Extracted text length: {len(output_invalid_not_pdf.data.get('extracted_text', ''))} characters.")
#
#         # Test case 3: URL that might result in 404
#         url_404 = "https://arxiv.org/pdf/nonexistentpaper12345.pdf"
#         output_404 = await agent.execute_task({"pdf_url": url_404})
#         print("\n--- Test Case 3: PDF URL resulting in 404 ---")
#         if not output_404.success:
#             print(f"Correctly failed with error: {output_404.error_message}")
#         else:
#             print(f"Test failed or URL was unexpectedly valid: {output_404.data}")
#
#         # Test case 4: Missing pdf_url
#         output_missing_url = await agent.execute_task({})
#         print("\n--- Test Case 4: Missing pdf_url ---")
#         if not output_missing_url.success:
#             print(f"Correctly failed with error: {output_missing_url.error_message}")
#         else:
#             print("Test failed: Should have reported an error for missing pdf_url.")
#
#     asyncio.run(test_content_extraction())
