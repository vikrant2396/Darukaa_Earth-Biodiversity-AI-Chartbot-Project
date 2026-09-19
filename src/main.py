"""
CLI demo of the Darukaa.Earth Biodiversity Intelligence system.

Run:
    python -m src.main

Supports plain text turns, e.g.:
    "Biodiversity is declining on my land"
    "Soil organic carbon is 0.3%, rainfall is low, monoculture wheat, semi-arid region"

Or structured JSON turns by prefixing with 'json:':
    json:{"soil_organic_carbon": 0.3, "rainfall": "low", "land_use": "monoculture_wheat", "region": "semi-arid"}
"""
import json
import sys
import uuid

from src.conversation_manager import ConversationManager


def main():
    print("=" * 70)
    print("Darukaa.Earth — AI Biodiversity Intelligence (CLI demo)")
    print("Type 'exit' to quit. Prefix a message with 'json:' to send structured input.")
    print("=" * 70)

    manager = ConversationManager()
    session_id = str(uuid.uuid4())

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Session ended.")
            break
        if not user_input:
            continue

        text, structured = None, None
        if user_input.startswith("json:"):
            try:
                structured = json.loads(user_input[len("json:"):])
            except json.JSONDecodeError as e:
                print(f"Invalid JSON: {e}")
                continue
        else:
            text = user_input

        result = manager.handle_message(session_id, text=text, structured=structured)
        print(f"\nSystem [{result['type']}]:\n{result['message']}")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
