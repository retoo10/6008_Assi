# 1. ROOMS
# Each room is a dictionary (a set of labelled facts).
# zone = distance from the lift: "near" (1-2 doors),
#        "mid" (3-6 doors), "far" (7+ doors)

ROOMS = [
    {"id": "101", "type": "Accessible King", "max_adults": 2, "max_children": 1,
     "bed": "king", "price": 115, "floor": 1, "zone": "mid",
     "features": ["walk-in shower", "step-free access"],
     "accessible": True, "connecting": False, "available": True},

    {"id": "201", "type": "Standard Twin", "max_adults": 2, "max_children": 0,
     "bed": "2 singles", "price": 95, "floor": 2, "zone": "mid",
     "features": ["desk"],
     "accessible": False, "connecting": False, "available": True},

    {"id": "202", "type": "Standard Twin", "max_adults": 2, "max_children": 0,
     "bed": "2 singles", "price": 95, "floor": 2, "zone": "far",
     "features": ["desk"],
     "accessible": False, "connecting": False, "available": True},

    {"id": "203", "type": "Standard King", "max_adults": 2, "max_children": 1,
     "bed": "king", "price": 115, "floor": 2, "zone": "near",
     "features": ["desk"],
     "accessible": False, "connecting": False, "available": True},

    {"id": "204", "type": "Standard King", "max_adults": 2, "max_children": 1,
     "bed": "king", "price": 115, "floor": 2, "zone": "mid",
     "features": ["desk", "quiet side"],
     "accessible": False, "connecting": False, "available": True},

    {"id": "205", "type": "Family Room", "max_adults": 2, "max_children": 2,
     "bed": "queen + sofa bed", "price": 165, "floor": 2, "zone": "near",
     "features": ["low floor"],
     "accessible": False, "connecting": False, "available": True},

    {"id": "307", "type": "Connecting Queen", "max_adults": 2, "max_children": 1,
     "bed": "queen", "price": 110, "floor": 3, "zone": "mid",
     "features": ["connecting door"],
     "accessible": False, "connecting": True, "connects_to": "308",
     "available": True},

    {"id": "308", "type": "Connecting Queen", "max_adults": 2, "max_children": 1,
     "bed": "queen", "price": 110, "floor": 3, "zone": "mid",
     "features": ["connecting door"],
     "accessible": False, "connecting": True, "connects_to": "307",
     "available": True},

    {"id": "401", "type": "Deluxe King", "max_adults": 2, "max_children": 1,
     "bed": "king", "price": 145, "floor": 4, "zone": "mid",
     "features": ["city view", "bath"],
     "accessible": False, "connecting": False, "available": True},

    {"id": "402", "type": "Deluxe King", "max_adults": 2, "max_children": 1,
     "bed": "king", "price": 145, "floor": 4, "zone": "far",
     "features": ["city view", "bath"],
     "accessible": False, "connecting": False, "available": True},

    {"id": "601", "type": "Deluxe King", "max_adults": 2, "max_children": 1,
     "bed": "king", "price": 145, "floor": 6, "zone": "mid",
     "features": ["city view", "bath", "high floor"],
     "accessible": False, "connecting": False, "available": True},

    {"id": "501", "type": "Executive King", "max_adults": 2, "max_children": 0,
     "bed": "king", "price": 185, "floor": 5, "zone": "mid",
     "features": ["lounge access", "workspace"],
     "accessible": False, "connecting": False, "available": True},

    {"id": "701", "type": "Junior Suite", "max_adults": 2, "max_children": 2,
     "bed": "king", "price": 210, "floor": 7, "zone": "mid",
     "features": ["lounge area", "high floor"],
     "accessible": False, "connecting": False, "available": True},

    {"id": "702", "type": "Junior Suite", "max_adults": 2, "max_children": 2,
     "bed": "king", "price": 210, "floor": 7, "zone": "far",
     "features": ["lounge area", "high floor"],
     "accessible": False, "connecting": False, "available": True},
]

# 2. MUQADDAS HONOURS LOYALTY TIERS
# A higher "rank" means higher priority when upgrade rooms are scarce.
# (Used by the conflict-resolution rule: Diamond beats Gold.)

LOYALTY_TIERS = {
    "Member":  {"rank": 0},
    "Silver":  {"rank": 1},
    "Gold":    {"rank": 2},
    "Diamond": {"rank": 3},
}

# 3. UPGRADE LADDER
# Maps a room type to the next room type up. None = top of the ladder.

UPGRADE_LADDER = {
    "Standard Twin":    "Deluxe King",
    "Standard King":    "Deluxe King",
    "Accessible King":  None,            # never upgraded out of accessible
    "Connecting Queen": "Junior Suite",
    "Family Room":      "Junior Suite",
    "Deluxe King":      "Junior Suite",
    "Executive King":   "Junior Suite",
    "Junior Suite":     None,
}

# 4. HOTEL SETTINGS (thresholds used by the rules later)
# Keeping them here means you change a number in ONE place.

GROUP_BOOKING_MIN_ROOMS = 5      # 5+ rooms -> refer to reservations team
LONG_STAY_MIN_NIGHTS = 4         # 4+ nights -> restock service applies
RESTOCK_EVERY_DAYS = 3           # sheets and amenities restocked every 3 days

# Occupancy-based pricing: (min %, max %, discount)
OCCUPANCY_DISCOUNTS = [
    (0, 50, 0.10),     # below 50% full -> 10% off
    (50, 70, 0.05),    # 50-70% full   -> 5% off
    (70, 101, 0.00),   # above 70%     -> standard price
]


if __name__ == "__main__":
    # Quick check: print every room when you run this file.
    print(f"{'ID':<5}{'Type':<18}{'Floor':<7}{'Zone':<6}{'Price':<7}Features")
    print("-" * 70)
    for room in ROOMS:
        print(f"{room['id']:<5}{room['type']:<18}{room['floor']:<7}"
              f"{room['zone']:<6}£{room['price']:<6}{', '.join(room['features'])}")
    print(f"\nTotal rooms: {len(ROOMS)}")