import os
import google.generativeai as genai
from dotenv import load_dotenv

from calendar_functions import (
    create_event,
    find_and_delete_events_by_summary,
    get_current_datetime,
)

def run_chat_agent():
    """Initializes the chat loop and handles tool execution."""
    
    try:
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
    except KeyError:
        print("FATAL ERROR: GOOGLE_API_KEY environment variable not set.")
        print("Please set it before running the agent.")
        return

    system_instruction = (
        "You are an intelligent, helpful, and concise Calendar Agent specializing in assisting a Cambridge student with their university schedule. "
        "Your goal is to translate requests (like creating or deleting events) into precise function calls. "
        "You MUST parse all necessary date/time/location data from the user's input before calling 'create_event'. "
        f"Current date is {get_current_datetime()}, use this as a reference point when resolving the date from user input 'today', 'tomorrow', etc."
        "When calculating dates, assume the current date and time are used as the reference point. "
        "End time for event creation is optional"
        "At the end of each operation, get back to the user with confirmation or error message"
        f"At all costs try to create events with as little information as possible (for example, don't ask for the end time if not provided, don't ask for the year because you already have it ({get_current_datetime()}))"
    )

    model = genai.GenerativeModel('gemini-2.5-flash-lite',
    system_instruction=system_instruction,
    tools=[create_event, find_and_delete_events_by_summary])

    chat = model.start_chat(enable_automatic_function_calling=True)

    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ['quit', 'exit']:
                print("\nAgent: Goodbye!")
                break
            
            response = chat.send_message(user_input)
            
            print(f"Agent: {response.text if hasattr(response, 'text') else ""}")
            
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            break

if __name__ == "__main__":
    run_chat_agent()