import os
from openai import OpenAI
from dotenv import load_dotenv
import json

# ==============================================================================
# PART 1: CONFIGURATION (The Settings)
# All our main settings are here. Easy to change!
# ==============================================================================

# The personality you want the AI to adopt. Be as detailed as possible!
PERSONA_PROMPT = """
You are [Performer's Name], a flirty, charming, and charismatic man.
Your personality is confident but not arrogant, playful, and a great listener.
You make witty jokes and give genuine compliments.
You are here to have engaging, fun, and lighthearted conversations.

RULES:
- NEVER mention you are an AI, a language model, or a bot. You are [Performer's Name].
- NEVER be explicit, vulgar, or overly sexual. Keep it charming and suggestive, not graphic.
- NEVER break character.
- If the user gets aggressive or asks for inappropriate things, playfully deflect and change the subject.
- Your goal is to make the user feel special and entertained.
"""

# The prompt for the summarizer AI
SUMMARY_PROMPT = """
Concisely summarize the key points, user interests, and emotional tone of the following conversation.
This summary will be used to provide context for a future conversation.
Do not include any personally identifiable information.
Focus on what was discussed (e.g., "user is interested in travel, mentioned liking dogs") and the overall vibe (e.g., "playful, getting to know each other").

Conversation to summarize:
{conversation_history}
"""

# Freemium Tier Message Limits
TIER_LIMITS = {
    "Free": 10,
    "Basic": 500,
    "Premium": 2000,
    "VIP": float('inf')  # 'inf' means infinity (unlimited)
}

# ==============================================================================
# PART 2: FAKE DATABASE (The Memory)
# This pretends to be our database. It's just a Python dictionary.
# When the backend team takes over, they will replace this with a real database.
# ==============================================================================

# We will store our "database" in a file to remember things between runs.
DB_FILE = "fake_database.json"

def load_database():
    """Loads the user and chat data from a file."""
    if not os.path.exists(DB_FILE):
        # If the file doesn't exist, create it with default data
        return {
            "users": {
                "user_free_1": {"tier": "Free", "message_count": 0},
                "user_at_limit": {"tier": "Free", "message_count": 10},
                "user_basic_1": {"tier": "Basic", "message_count": 498},
                "user_vip_1": {"tier": "VIP", "message_count": 12345},
            },
            "chats": {
                "user_free_1": {"summary": "No summary yet.", "history": [], "session_message_count": 0},
                "user_at_limit": {"summary": "No summary yet.", "history": [], "session_message_count": 0},
                "user_basic_1": {"summary": "User seems interested in music.", "history": [], "session_message_count": 9},
                "user_vip_1": {"summary": "User is a long-time chatter.", "history": [], "session_message_count": 0},
            }
        }
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def save_database(data):
    """Saves the current data back to the file."""
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ==============================================================================
# PART 3: AI SERVICE (The Brain)
# This part connects to the AI model and does the "thinking".
# ==============================================================================

# Load the secret API key from the .env file
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("Error: OPENROUTER_API_KEY not found in .env file! Please create one.")

# Set up the OpenRouter client
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENROUTER_API_KEY,
)

def get_new_summary(conversation_history: list) -> str:
    """Calls the AI to generate a new summary."""
    print("\ntyping")
    
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
    prompt = SUMMARY_PROMPT.format(conversation_history=history_text)
    
    try:
        response = client.chat.completions.create(
            model="google/gemini-flash-1.5",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        summary = response.choices[0].message.content
        print("[SYSTEM] Summary generated successfully.")
        return summary
    except Exception as e:
        print(f"[SYSTEM] Error generating summary: {e}")
        return "Could not generate a new summary."

def generate_ai_response(summary: str, history: list, new_message: str) -> str:
    """Generates the main chat response from the AI."""
    print("typing..")
    
    system_prompt = {"role": "system", "content": f"{PERSONA_PROMPT}\n\nPREVIOUS CONVERSATION SUMMARY:\n{summary}"}
    recent_history = history[-12:]
    messages_for_api = [system_prompt] + recent_history + [{"role": "user", "content": new_message}]
    
    try:
        response = client.chat.completions.create(
            model="google/gemini-flash-1.5",
            messages=messages_for_api,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[SYSTEM] Error generating chat response: {e}")
        return "I'm sorry, I'm having a little trouble thinking right now. Ask me something else?"

# ==============================================================================
# PART 4: MAIN CHAT LOOP (The Program)
# This is what runs when you start the script.
# ==============================================================================

def main():
    """The main function to run the chatbot in the terminal."""
    
    db_data = load_database()
    
    print("--- Terminal Chatbot MVP ---")
    print("Available test users:", list(db_data["users"].keys()))
    user_id = input("Enter the user_id you want to chat as: ")

    if user_id not in db_data["users"]:
        print(f"User '{user_id}' not found. Please choose from the list.")
        return

    print(f"\n--- Starting chat session for '{user_id}' (Tier: {db_data['users'][user_id]['tier']}) ---")
    print("Type 'quit' to exit.")

    while True:
        # Load the latest data for the user for this turn
        user_data = db_data["users"][user_id]
        chat_data = db_data["chats"].setdefault(user_id, {"summary": "No summary yet.", "history": [], "session_message_count": 0})
        
        # 1. FREEMIUM LOGIC: Check message limits before asking for input
        limit = TIER_LIMITS.get(user_data["tier"], 0)
        if user_data["message_count"] >= limit:
            print(f"\nYou have reached your message limit of {limit} for the '{user_data['tier']}' tier.")
            print("In a real app, you would be asked to upgrade.")
            break # Exit the chat loop

        # Get user input
        user_message = input("\nYou: ")
        if user_message.lower() == 'quit':
            break

        # 2. GENERATE AI RESPONSE
        ai_message = generate_ai_response(chat_data["summary"], chat_data["history"], user_message)
        print(f"\nDaddy John: {ai_message}")

        # 3. UPDATE HISTORY AND COUNTS
        chat_data["history"].append({"role": "user", "content": user_message})
        chat_data["history"].append({"role": "model", "content": ai_message})
        user_data["message_count"] += 1
        chat_data["session_message_count"] += 1

        # 4. CONTEXT SUMMARIZATION LOGIC
        if chat_data["session_message_count"] >= 10:
            history_for_summary = chat_data["history"][-20:]
            new_summary = get_new_summary(history_for_summary)
            chat_data["summary"] = new_summary
            chat_data["session_message_count"] = 0 # Reset counter
        
        # 5. SAVE EVERYTHING BACK TO THE "DATABASE"
        save_database(db_data)

    print("\n--- Chat session ended. ---")


if __name__ == "__main__":
    main()
