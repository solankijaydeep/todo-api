import os
import logging
from openai import OpenAI

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("todo_api.openai")

def categorize_todo(title: str) -> str:
    """
    Sends the task title to the OpenAI API to automatically classify it.
    Defaults to 'Uncategorized' if the API key is not configured or in case of errors.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY environment variable is not set. Defaulting to 'Uncategorized'.")
        return "Uncategorized"
    
    try:
        # Initialize OpenAI client with the provided API key
        client = OpenAI(api_key=api_key)
        
        system_prompt = (
            "You are a task categorization assistant. Classify the given task title into a single, "
            "concise category (1-2 words maximum) e.g., 'Buy milk' -> 'Groceries', 'Fix sink' -> 'Home Maintenance', "
            "'Write report' -> 'Work', 'Cardio workout' -> 'Fitness'. "
            "Respond ONLY with the category name, with no punctuation or additional text."
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": title}
            ],
            max_tokens=10,
            temperature=0.3
        )
        
        category = response.choices[0].message.content.strip()
        # Strip generic enclosing characters
        category = category.strip('\'".')
        
        if not category:
            return "Uncategorized"
            
        logger.info(f"Successfully categorized task '{title}' as '{category}' via OpenAI.")
        return category
        
    except Exception as e:
        logger.error(f"Error calling OpenAI API for categorization: {e}. Defaulting to 'Uncategorized'.")
        return "Uncategorized"
