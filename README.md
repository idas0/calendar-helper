# Calendar Helper

A small CLI interface that converts natural-language text into Google Calendar operations using the Gemini API with function calling.

Key points
- **What it does:** Parse user text (e.g., "Supervision with John tomorrow 1pm, repeats weekly", "Delete all events on Wednesday") and turn it into precise function calls to create or delete events.
- **How it works:** Uses Google Gemini (via the `google.generativeai` client) configured for automatic function calling to invoke helper functions such as `create_event` and `find_and_delete_events_by_summary`.
- **Interactive:** Runs as a simple REPL (`main.py`) that sends user messages to the model and asks for confirmation before creating/deleting events.