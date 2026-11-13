"""
main.py - Interactive front end for the Muqaddas Tower Hotel
room recommendation system.

Run with:  python3 main.py
Needs hotel_data.py and engine.py in the same folder.
"""

from engine import recommend


def ask_int(question, minimum=0, maximum=None):
    """Keep asking until the user types a whole number in range."""
    while True:
        answer = input(question).strip()
        if answer.isdigit():
            value = int(answer)
            if value >= minimum and (maximum is None or value <= maximum):
                return value
        limit = f" and {maximum}" if maximum is not None else " or more"
        print(f"  Please enter a whole number ({minimum}{limit}).")


def ask_yes_no(question):
    """Keep asking until the user types y or n."""
    while True:
        answer = input(question + " (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please type y or n.")


def ask_choice(question, options):
    """Show a numbered menu and return the chosen option."""
    print(question)
    for number, option in enumerate(options, start=1):
        print(f"  {number}. {option}")
    while True:
        answer = input("Choose a number: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        print(f"  Please enter a number from 1 to {len(options)}.")


def collect_guest_facts():
    print("\nPlease answer a few questions about the stay.\n")
    guest = {}
    guest["adults"] = ask_int("How many adults in total? ", minimum=1)
    guest["children"] = ask_int("How many children in total? ")
    guest["rooms_requested"] = ask_int(
        "Preferred number of rooms (0 = let the system decide)? ")
    guest["nights"] = ask_int("How many nights? ", minimum=1)
    guest["budget"] = ask_int("Maximum budget per night, per room, in £? ", minimum=1)
    guest["needs_access"] = ask_yes_no("Does anyone need an accessible room?")
    guest["wants_twin"] = ask_yes_no("Do you prefer two separate beds?")
    guest["wants_quiet"] = ask_yes_no("Do you want a quiet room?")
    if guest["wants_quiet"]:
        guest["limited_mobility"] = ask_yes_no(
            "Is it important to be a short walk from the lift?")
    guest["wants_view"] = ask_yes_no("Would you like a city view or high floor?")
    guest["business_traveller"] = ask_yes_no("Is this a business trip?")

    print()
    guest["loyalty_tier"] = ask_choice(
        "Muqaddas Honours membership:", ["Member", "Silver", "Gold", "Diamond"])
    occasion = ask_choice(
        "Special occasion:", ["None", "Anniversary", "Honeymoon", "Birthday"])
    guest["occasion"] = None if occasion == "None" else occasion.lower()
    guest["occupancy"] = ask_int(
        "How full is the hotel tonight, in % (0-100)? ", minimum=0, maximum=100)
    if guest["loyalty_tier"] == "Gold":
        guest["diamond_also_arriving"] = ask_yes_no(
            "Is a Diamond member also arriving tonight?")
    return guest


def main():
    print("=" * 50)
    print("  Muqaddas Tower Hotel - Room Recommendation")
    print("=" * 50)
    while True:
        recommend(collect_guest_facts())
        print("\n(This is an educational tool. Final availability is "
              "confirmed by our reservations team.)")
        if not ask_yes_no("\nTry another guest?"):
            print("Thank you. Goodbye!")
            break


if __name__ == "__main__":
    main()