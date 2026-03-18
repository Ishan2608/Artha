from utils.rag_engine import query_documents

def search_uploaded_documents(query: str) -> dict:
    """
    Search through the text and tables of files the user has uploaded.

    Use this tool when the user asks a question about a document they provided 
    (like a PDF, Word document, CSV, or Excel file). The tool performs a semantic 
    search over the document contents and returns the most relevant paragraphs or rows.

    Args:
        query: The specific question or keywords to search for within the documents.
               Be as descriptive as possible to improve search accuracy.

    Returns:
        A dictionary containing a list of relevant text snippets, or an error message.
    """
    try:
        results = query_documents(query, n_results=5)
        
        if not results:
            return {
                "status": "no_results",
                "message": "No relevant information found in the uploaded documents."
            }
            
        return {
            "status": "success",
            "query": query,
            "results": results
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"An error occurred while searching documents: {str(e)}"
        }
