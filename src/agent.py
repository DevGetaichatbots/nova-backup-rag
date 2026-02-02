from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam
from src.config import settings
from src.vector_store import vector_store_manager
from src.database import save_chat_message, get_chat_history
from typing import List
import json


SYSTEM_PROMPT_BASE = """INSTRUCTIONS

CORE RULES (APPLY TO ALL RESPONSES)
- ALWAYS return responses in a structured table format whenever comparison data is present.
- Every comparison result (Added / Removed / Moved / Delayed / Earlier / Critical Path / Risks) MUST be displayed as a table.
- Column names must be clear, consistent, and aligned.

Example columns:
Task Name | Week A | Week B | Shift | Earlier/Later | Days | Notes

After the table(s), you MAY include a brief summary of key findings.

You have access to two vector stores containing document data. When the user asks about comparisons or analysis:
1. Retrieve relevant content from both vector stores
2. Compare the information
3. Present findings in structured table format
4. Provide insights based on the comparison

Be thorough in your analysis and always cite which document the information came from."""


LANGUAGE_INSTRUCTIONS = {
    "da": "IMPORTANT: You MUST respond in Danish (Dansk). All your responses, tables, summaries, and analysis must be written in Danish language.",
    "en": "Respond in English."
}


class RAGAgent:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
    
    def _retrieve_context(self, query: str, table_names: list[str], top_k: int = 10) -> str:
        all_results = vector_store_manager.search_multiple_stores(table_names, query, top_k)
        
        context_parts = []
        for table_name, results in all_results.items():
            if isinstance(results, dict) and "error" in results:
                context_parts.append(f"\n[Document: {table_name}]\nError retrieving: {results['error']}\n")
            else:
                context_parts.append(f"\n[Document: {table_name}]")
                for i, result in enumerate(results, 1):
                    context_parts.append(f"Chunk {i} (similarity: {result['similarity']:.3f}):")
                    context_parts.append(result["content"])
                    context_parts.append("")
        
        return "\n".join(context_parts)
    
    def query(
        self, 
        user_query: str, 
        table_names: list[str], 
        session_id: str,
        language: str = "en",
        top_k: int = 10
    ) -> dict:
        context = self._retrieve_context(user_query, table_names, top_k)
        
        chat_history = get_chat_history(session_id, limit=10)
        
        lang_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
        system_prompt = f"{SYSTEM_PROMPT_BASE}\n\n{lang_instruction}"
        
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt}
        ]
        
        for msg in chat_history:
            role = msg["role"]
            if role == "user":
                messages.append({"role": "user", "content": str(msg["content"])})
            elif role == "assistant":
                messages.append({"role": "assistant", "content": str(msg["content"])})
        
        user_message = f"""Based on the following retrieved document context, please answer the user's question.

RETRIEVED CONTEXT:
{context}

USER QUESTION: {user_query}

Please analyze the content from both documents and provide a structured comparison if applicable."""

        messages.append({"role": "user", "content": user_message})
        
        response = self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=messages,
            temperature=0.7,
            max_tokens=4000
        )
        
        assistant_response = response.choices[0].message.content or ""
        
        save_chat_message(session_id, "user", user_query)
        save_chat_message(session_id, "assistant", assistant_response)
        
        return {
            "response": assistant_response,
            "sources": list(table_names),
            "context_chunks": len(context.split("Chunk"))
        }


rag_agent = RAGAgent()
