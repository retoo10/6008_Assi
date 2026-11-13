"""
engine.py - Rules and inference engine for the Muqaddas Tower Hotel
recommendation system.  Needs hotel_data.py in the same folder.

Rule groups:
  RULES          R1-R10, R25   room selection and preferences (scored)
  PRICE_RULES    R20-R22  occupancy-based pricing
  UPGRADE_RULES  R14-R17  who is eligible for a complimentary upgrade
  decide_upgrade R18,R19,R24  what actually happens (paid offer, room
                              full, Diamond-over-Gold conflict)
  SERVICE_RULES  R11-R13, R23  handoffs to reservations and long-stay
                              housekeeping (R11 also has a scoring part
                              in RULES: prefer rooms with a workspace)
"""

import math

from hotel_data import (ROOMS, UPGRADE_LADDER, OCCUPANCY_DISCOUNTS,
                        GROUP_BOOKING_MIN_ROOMS, LONG_STAY_MIN_NIGHTS,
                        RESTOCK_EVERY_DAYS)


# Settings used by the rules

LOW_BUDGET_LIMIT = 130        # per night; below this = budget-conscious guest
PAID_UPGRADE_DISCOUNT = 0.20  # 20% off the price DIFFERENCE for a paid upgrade
SUITE_PRICE = min(r["price"] for r in ROOMS if r["type"] == "Junior Suite")


def fmt_price(p):
    """Show £115 for whole numbers and £103.50 otherwise."""
    return f"£{p:.0f}" if float(p).is_integer() else f"£{p:.2f}"



# 1. DERIVING NEW FACTS (forward chaining)

def derive_facts(guest):
    facts = dict(guest)
    # Anything the guest didn't mention gets a sensible default
    for key in ("needs_access", "wants_twin", "wants_quiet",
                "limited_mobility", "wants_view", "diamond_also_arriving"):
        facts.setdefault(key, False)
    facts.setdefault("loyalty_tier", "Member")
    facts.setdefault("occasion", None)     # None, "anniversary", "honeymoon", "birthday"
    facts.setdefault("occupancy", 100)     # hotel % full tonight (100 = standard rate)
    facts.setdefault("business_traveller", False)
    facts.setdefault("rooms_requested", 0) # 0 = let the system decide
    facts.setdefault("nights", 1)          # length of stay
    # Derived facts. The guest gives TOTAL adults and children. We work out
    # how many rooms are needed (a standard room holds 2 adults; a room
    # holds about 2 children at most), then plan for the largest room.
    total_adults, total_children = guest["adults"], guest["children"]
    min_rooms = max(1, math.ceil(total_adults / 2), math.ceil(total_children / 2))
    requested = max(1, min(facts["rooms_requested"], total_adults))
    facts["rooms_needed"] = max(min_rooms, requested)
    facts["total_adults"], facts["total_children"] = total_adults, total_children
    facts["adults"] = math.ceil(total_adults / facts["rooms_needed"])      # per room
    facts["children"] = math.ceil(total_children / facts["rooms_needed"])  # per room
    facts["party_size"] = total_adults + total_children
    facts["has_children"] = total_children > 0
    facts["low_budget"] = guest["budget"] < LOW_BUDGET_LIMIT
    return facts



# 2a. ROOM-SELECTION RULES (R1-R10)
#   kind "exclude" -> if condition is true, remove this room
#   kind "score"   -> if condition is true, add points + give a reason
#   f = the guest's facts, c = the candidate room (or room pair)
#   "points"/"reason" can be fixed values or functions of the room.

RULES = [
    {"id": "R1", "kind": "exclude",
     "description": "Guest needs accessibility -> only accessible rooms",
     "condition": lambda f, c: f["needs_access"] and not c["accessible"]},

    {"id": "R2", "kind": "exclude",
     "description": "Guest does not need accessibility -> exclude accessible rooms",
     "condition": lambda f, c: (not f["needs_access"]) and c["accessible"]},

    {"id": "R3", "kind": "exclude",
     "description": "Party is larger than the room's capacity -> exclude",
     "condition": lambda f, c: f["adults"] > c["max_adults"]
                               or f["children"] > c["max_children"]},

    {"id": "R4", "kind": "score", "points": 3,
     "description": "Low budget, 1-2 adults, no children -> Standard King "
                    "(or Standard Twin if they want separate beds)",
     "condition": lambda f, c: f["low_budget"] and f["adults"] <= 2
                               and not f["has_children"]
                               and c["type"] == ("Standard Twin" if f["wants_twin"]
                                                 else "Standard King"),
     "reason": "best-value basic room for your budget"},

    {"id": "R5", "kind": "score", "points": 3,
     "description": "Children in party -> recommend a suite or connecting rooms",
     "condition": lambda f, c: f["has_children"]
                               and c["type"] in ("Junior Suite", "Connecting Rooms"),
     "reason": "suite or connecting rooms give a family more space and privacy"},

    {"id": "R6", "kind": "score", "points": 2,
     "description": "Children AND budget below suite price -> offer Family Room",
     "condition": lambda f, c: f["has_children"] and f["budget"] < SUITE_PRICE
                               and c["type"] == "Family Room",
     "reason": "a suite is above your budget, so this is the best family option"},

    {"id": "R8", "kind": "score",
     "description": "Wants quiet -> prefer mid zone (+3), avoid near-lift (-3), "
                    "slight penalty for far (-1)",
     "condition": lambda f, c: f["wants_quiet"],
     "points": lambda c: {"mid": 3, "near": -3, "far": -1}[c["zone"]],
     "reason": lambda c: {
         "mid": "mid-corridor position is away from lift noise but a short walk",
         "near": "it is close to the lift, which can be noisy",
         "far": "it is quiet but a long walk from the lift"}[c["zone"]]},

    {"id": "R9", "kind": "score",
     "description": "Wants quiet AND cannot walk far -> avoid far zone (-3 extra)",
     "condition": lambda f, c: f["wants_quiet"] and f["limited_mobility"]
                               and c["zone"] == "far",
     "points": lambda c: -3,
     "reason": lambda c: "it is a long walk from the lift and you prefer a short one"},

    {"id": "R10", "kind": "score",
     "description": "Wants a view or high floor -> prefer rooms with those features (+2)",
     "condition": lambda f, c: f["wants_view"]
                               and ("city view" in c["features"]
                                    or "high floor" in c["features"]),
     "points": lambda c: 2,
     "reason": lambda c: "it has " + " and ".join(
         x for x in ("city view", "high floor") if x in c["features"])},

    {"id": "R11", "kind": "score",
     "description": "Business traveller -> prefer a room with a workspace "
                    "(the reservations handoff half of R11 is in SERVICE_RULES)",
     "condition": lambda f, c: f["business_traveller"]
                               and ("workspace" in c["features"]
                                    or "desk" in c["features"]),
     "points": lambda c: 3 if "workspace" in c["features"] else 2,
     "reason": lambda c: "it has a " + ("workspace" if "workspace" in c["features"]
                                        else "desk") + " for work"},

    # Added after testing: a tie between Standard Twin and Standard King was
    # being broken by price alone, which put the Twin first.
    {"id": "R25", "kind": "score",
     "description": "Bed preference (no children, 1-2 adults per room): king bed "
                    "by default, separate beds only if the guest asks (+1)",
     "condition": lambda f, c: (not f["has_children"]) and f["adults"] <= 2
                               and c.get("bed") == ("2 singles" if f["wants_twin"]
                                                    else "king"),
     "points": lambda c: 1,
     "reason": lambda c: ("separate beds, as you prefer" if c["bed"] == "2 singles"
                          else "a king bed is our default for 1-2 guests")},
]



# 2b. PRICING RULES (R20-R22): quieter hotel -> small discount.
# The bands come from OCCUPANCY_DISCOUNTS in hotel_data.py.

def make_price_rule(rule_id, low, high, discount):
    return {"id": rule_id, "kind": "price", "discount": discount,
            "description": f"Occupancy {low}-{high}% -> {int(discount * 100)}% off",
            "condition": lambda f, c: low <= f["occupancy"] < high}


PRICE_RULES = [make_price_rule(f"R{20 + i}", *band)
               for i, band in enumerate(OCCUPANCY_DISCOUNTS)]


def apply_price_rules(facts, room):
    """Set room['price'] after any occupancy discount (first matching rule wins)."""
    room["list_price"] = room["price"]
    room["price_note"] = None
    for rule in PRICE_RULES:
        if rule["condition"](facts, room):
            if rule["discount"] > 0:
                room["price"] = round(room["list_price"] * (1 - rule["discount"]), 2)
                room["price_note"] = (
                    f"{rule['id']}: hotel is {facts['occupancy']}% full tonight, "
                    f"so {int(rule['discount'] * 100)}% off the standard rate "
                    f"({fmt_price(room['list_price'])} -> {fmt_price(room['price'])})")
            break



# 2c. UPGRADE ELIGIBILITY RULES (R14-R17)
# If a rule's condition is true the guest is ELIGIBLE for a free upgrade
# and gets the listed extras (set-up, card, treat).

UPGRADE_RULES = [
    {"id": "R14", "condition": lambda f: f["occasion"] in ("anniversary", "honeymoon"),
     "reason": "special occasion (anniversary/honeymoon)",
     "extras": ["room set-up with rose petals", "anniversary card"]},

    {"id": "R15", "condition": lambda f: f["occasion"] == "birthday",
     "reason": "special occasion (birthday)",
     "extras": ["birthday card", "treat"]},

    {"id": "R16", "condition": lambda f: f["loyalty_tier"] == "Diamond",
     "reason": "Diamond member of Muqaddas Honours",
     "extras": ["treat", "welcome card from the hotel"]},

    {"id": "R17", "condition": lambda f: f["loyalty_tier"] == "Gold",
     "reason": "Gold member of Muqaddas Honours",
     "extras": ["treat", "welcome card from the hotel"]},
]


def find_upgrade_rooms(facts, room, taken_ids=()):
    """Free rooms in the next category up that fit the party."""
    ladder_type = "Connecting Queen" if room["type"] == "Connecting Rooms" else room["type"]
    next_type = UPGRADE_LADDER.get(ladder_type)
    if next_type is None:
        return []
    own_ids = room["id"].split("+") + list(taken_ids)
    options = []
    for r in ROOMS:
        if (r["available"] and r["type"] == next_type and r["id"] not in own_ids
                and facts["adults"] <= r["max_adults"]
                and facts["children"] <= r["max_children"]):
            up = dict(r)
            apply_price_rules(facts, up)
            options.append(up)
    # Keep the guest's preference: mid zone if they want quiet, else same zone
    preferred_zone = "mid" if facts["wants_quiet"] else room["zone"]
    options.sort(key=lambda r: (r["zone"] != preferred_zone, r["price"], r["id"]))
    return options


def decide_upgrade(facts, room, taken_ids=()):
    """Applies R14-R19 and R24 to the top recommended room."""
    result = {"status": "none", "room": None, "extras": [], "log": [],
              "paid_cost": None, "message": ""}
    options = find_upgrade_rooms(facts, room, taken_ids)
    ladder_type = "Connecting Queen" if room["type"] == "Connecting Rooms" else room["type"]
    has_next_category = UPGRADE_LADDER.get(ladder_type) is not None

    # Which eligibility rules fire?
    eligible = False
    for rule in UPGRADE_RULES:
        if rule["condition"](facts):
            eligible = True
            result["log"].append(f"{rule['id']}: {rule['reason']}")
            for item in rule["extras"]:
                if item not in result["extras"]:
                    result["extras"].append(item)

    def paid_offer():
        diff = options[0]["price"] - room["price"]
        result["paid_cost"] = round(max(diff, 0) * (1 - PAID_UPGRADE_DISCOUNT), 2)
        result["room"] = options[0]

    if not eligible:
        if options:                                          # R18
            result["status"] = "paid_offer"
            result["log"].append("R18: no occasion and not a Gold/Diamond member, "
                                 "so no complimentary upgrade")
            paid_offer()
    elif not options:                                        # R19
        result["status"] = "unavailable"
        if room["accessible"]:
            result["message"] = "Accessible rooms are not part of the upgrade ladder."
            result["log"].append("R19: you qualify, but accessible rooms "
                                 "are not upgraded")
        elif not has_next_category:
            result["message"] = "You are already in our top room category."
            result["log"].append("R19: you qualify, but there is no higher "
                                 "room category")
        else:
            result["message"] = ("No upgrade room is free tonight. We will move "
                                 "you if one becomes available before arrival.")
            result["log"].append("R19: you qualify, but the next room category "
                                 "is fully booked tonight")
    elif (facts["loyalty_tier"] == "Gold" and len(options) == 1
          and facts["diamond_also_arriving"]):               # R24 (conflict)
        result["status"] = "conflict"
        result["log"].append("R24: only one upgrade room is left and a Diamond "
                             "member has priority over Gold")
        paid_offer()
    else:                                                    # R14-R17 succeed
        result["status"] = "granted"
        result["room"] = options[0]
    return result



# 2d. SERVICE RULES (R11, R12, R13, R23)
# These do not rank rooms. They produce notes for the staff member:
# who to hand the guest to, and what housekeeping to schedule.

def restock_message(nights):
    days = list(range(RESTOCK_EVERY_DAYS, nights, RESTOCK_EVERY_DAYS))
    when = ", ".join(f"day {d}" for d in days)
    return (f"long stay ({nights} nights): housekeeping restocks sheets and "
            f"amenities every {RESTOCK_EVERY_DAYS} days ({when})")


SERVICE_RULES = [
    {"id": "R11",
     "condition": lambda f: f["business_traveller"],
     "message": lambda f: "business traveller: connect them with the reservations "
                          "team, who can offer a better corporate rate for "
                          "frequent stays"},

    {"id": "R12",
     "condition": lambda f: f["rooms_needed"] >= GROUP_BOOKING_MIN_ROOMS,
     "message": lambda f: f"{f['rooms_needed']} rooms booked "
                          f"({GROUP_BOOKING_MIN_ROOMS}+): connect them with the "
                          f"reservations team for a group deal"},

    {"id": "R13",
     "condition": lambda f: 2 <= f["rooms_needed"] < GROUP_BOOKING_MIN_ROOMS,
     "message": lambda f: f"{f['rooms_needed']} rooms is under "
                          f"{GROUP_BOOKING_MIN_ROOMS}, so standard pricing applies "
                          f"and no group handoff is needed"},

    {"id": "R23",
     "condition": lambda f: f["nights"] >= LONG_STAY_MIN_NIGHTS,
     "message": lambda f: restock_message(f["nights"])},
]



# Candidates: single rooms, plus connecting rooms treated as one PAIR

def build_candidates():
    candidates = []
    by_id = {r["id"]: r for r in ROOMS}
    for r in ROOMS:
        if not r["available"]:
            continue
        if r["connecting"]:
            partner = by_id[r["connects_to"]]
            if r["id"] < partner["id"] and partner["available"]:
                candidates.append({
                    "id": f"{r['id']}+{partner['id']}",
                    "type": "Connecting Rooms",
                    "price": r["price"] + partner["price"],
                    "max_adults": r["max_adults"] + partner["max_adults"],
                    "max_children": r["max_children"] + partner["max_children"],
                    "accessible": False,
                    "zone": r["zone"],
                    "features": ["two rooms with connecting door"],
                })
        else:
            candidates.append(dict(r))
    return candidates



# 3. THE INFERENCE ENGINE

def run_engine(guest):
    facts = derive_facts(guest)
    suitable = []

    for room in build_candidates():
        apply_price_rules(facts, room)        # R20-R22 first, so budget uses real price
        room["score"] = 0
        room["reasons"] = []
        excluded = False

        for rule in RULES:
            if not rule["condition"](facts, room):
                continue
            if rule["kind"] == "exclude":
                excluded = True
                break
            points = rule["points"](room) if callable(rule["points"]) else rule["points"]
            reason = rule["reason"](room) if callable(rule["reason"]) else rule["reason"]
            room["score"] += points
            room["reasons"].append(f"{rule['id']} ({points:+d}): {reason}")

        if not excluded:
            suitable.append(room)

    affordable = [r for r in suitable if r["price"] <= facts["budget"]]
    affordable.sort(key=lambda r: (-r["score"], r["price"], r["id"]))
    suitable.sort(key=lambda r: (r["price"], r["id"]))
    return facts, affordable, suitable



# 4. SHOW THE RESULT WITH EXPLANATIONS

def print_upgrade(top, decision):
    status = decision["status"]
    if status == "none" and not decision["extras"]:
        return
    print("  Upgrade and welcome:")
    if status == "granted":
        up = decision["room"]
        print(f"    COMPLIMENTARY UPGRADE: Room {up['id']} ({up['type']}) "
              f"instead of Room {top['id']} ({top['type']}), "
              f"at the price of the room you booked ({fmt_price(top['price'])}).")
    elif status == "paid_offer" or status == "conflict":
        up = decision["room"]
        print(f"    No complimentary upgrade, but you can move to Room {up['id']} "
              f"({up['type']}) for {fmt_price(decision['paid_cost'])} extra per night "
              f"({int(PAID_UPGRADE_DISCOUNT * 100)}% off the price difference).")
    elif status == "unavailable":
        print(f"    {decision['message']}")
    for line in decision["log"]:
        print(f"      because {line}")
    if decision["extras"]:
        print(f"    We will arrange: {', '.join(decision['extras'])}.")


def recommend(guest, top_n=3):
    facts, affordable, suitable = run_engine(guest)
    rooms_needed = facts["rooms_needed"]
    print(f"\nGuest: {facts['total_adults']} adult(s), {facts['total_children']} "
          f"child(ren) in total, budget {fmt_price(facts['budget'])}/night per room, "
          f"accessibility: {'yes' if facts['needs_access'] else 'no'}")
    print(f"       loyalty: {facts['loyalty_tier']}, "
          f"occasion: {facts['occasion'] or 'none'}, "
          f"hotel occupancy: {facts['occupancy']}%")
    print(f"       stay: {facts['nights']} night(s), "
          f"business traveller: {'yes' if facts['business_traveller'] else 'no'}")
    if rooms_needed > 1:
        print(f"       plan: {rooms_needed} rooms, up to {facts['adults']} adult(s) "
              f"and {facts['children']} child(ren) per room")

    if affordable and rooms_needed == 1:
        print("Recommended rooms:")
        for room in affordable[:top_n]:
            print(f"  Room {room['id']} - {room['type']} - "
                  f"{fmt_price(room['price'])}/night (score {room['score']})")
            for reason in room["reasons"]:
                print(f"      because {reason}")
            if room["price_note"]:
                print(f"      price: {room['price_note']}")
        top = affordable[0]
        print_upgrade(top, decide_upgrade(facts, top))
        if facts["nights"] > 1:
            print(f"  Total for {facts['nights']} nights (top choice): "
                  f"{fmt_price(top['price'] * facts['nights'])}")

    elif affordable:
        # Several rooms: take the best-ranked single rooms (connecting pairs
        # are for one family, so they are not used here).
        plan = [r for r in affordable if r["type"] != "Connecting Rooms"][:rooms_needed]
        print(f"Suggested allocation ({rooms_needed} rooms):")
        for room in plan:
            rules = ", ".join(x.split(" ")[0] for x in room["reasons"]) or "no preference rules"
            print(f"  Room {room['id']} - {room['type']} - "
                  f"{fmt_price(room['price'])}/night per room (matched: {rules})")
        if plan:
            if plan[0]["price_note"]:
                print(f"  price: {plan[0]['price_note']}")
            per_night = sum(r["price"] for r in plan)
            print(f"  Rate: {fmt_price(per_night)} per night for {len(plan)} room(s) "
                  f"(average {fmt_price(per_night / len(plan))} per room)")
            if facts["nights"] > 1:
                print(f"  Total for {facts['nights']} nights: "
                      f"{fmt_price(per_night * facts['nights'])}")
        if len(plan) < rooms_needed:
            print(f"  Note: only {len(plan)} suitable room(s) within budget are free "
                  f"tonight but {rooms_needed} are needed, so the reservations team "
                  f"will arrange the rest.")
        if rooms_needed >= GROUP_BOOKING_MIN_ROOMS:
            print("  Upgrades and final rates for group bookings are agreed "
                  "by the reservations team.")
        elif plan:
            print_upgrade(plan[0], decide_upgrade(facts, plan[0],
                                                  [r["id"] for r in plan]))

    elif suitable:
        print("R7: No suitable room fits your budget. Closest options:")
        for room in suitable[:2]:
            over = room["price"] - facts["budget"]
            print(f"  Room {room['id']} - {room['type']} - "
                  f"{fmt_price(room['price'])}/night ({fmt_price(over)} over budget)")
        print("  Tip: try different dates, or a smaller room type.")
    else:
        print("No room can accommodate this party. Please contact reservations.")

    notes = [f"{r['id']}: {r['message'](facts)}"
             for r in SERVICE_RULES if r["condition"](facts)]
    if notes:
        print("  Reservations and housekeeping notes:")
        for note in notes:
            print(f"    {note}")



# Demo: run `python3 engine.py`

if __name__ == "__main__":
    base = {"needs_access": False, "wants_twin": False}

    print("=== Steps 2-3 scenarios (standard rates, no loyalty) ===")
    recommend({**base, "adults": 2, "children": 0, "budget": 120})
    recommend({**base, "adults": 2, "children": 2, "budget": 180})
    recommend({**base, "adults": 2, "children": 0, "budget": 50})

    print("\n=== Step 4: pricing and upgrades ===")
    # Quiet night: 10% off (R20). Diamond -> upgrade + treat (R16)
    recommend({**base, "adults": 2, "children": 0, "budget": 120,
               "loyalty_tier": "Diamond", "occupancy": 45})
    # Honeymoon -> upgrade + rose petals (R14); 5% off (R21)
    recommend({**base, "adults": 2, "children": 0, "budget": 120,
               "occasion": "honeymoon", "occupancy": 60})
    # Silver, no occasion -> paid upgrade offer (R18)
    recommend({**base, "adults": 2, "children": 0, "budget": 120,
               "loyalty_tier": "Silver"})

    print("\n=== Step 5: business, group and long-stay ===")
    # Business traveller: workspace room (R11) + corporate-rate handoff
    recommend({**base, "adults": 1, "children": 0, "budget": 200,
               "business_traveller": True, "nights": 2})
    # 10 adults -> 5 rooms: group handoff (R12)
    recommend({**base, "adults": 10, "children": 0, "budget": 130, "nights": 3})
    # 6 adults -> 3 rooms: standard pricing (R13)
    recommend({**base, "adults": 6, "children": 0, "budget": 130})
    # 7 nights: restock schedule (R23)
    recommend({**base, "adults": 2, "children": 0, "budget": 120, "nights": 7,
               "loyalty_tier": "Gold"})

    # The case from testing: 12 adults must be split across 6 rooms
    recommend({**base, "adults": 12, "children": 0, "budget": 150, "nights": 5,
               "wants_view": True, "business_traveller": True,
               "loyalty_tier": "Diamond", "occupancy": 50})
    # Colleagues who each want their own room: 3 adults, 3 rooms requested
    recommend({**base, "adults": 3, "children": 0, "budget": 130,
               "rooms_requested": 3, "business_traveller": True})

    print("\n=== Testing fix: king bed is the default (R25) ===")
    # Previously the cheaper Standard Twin ranked first here
    recommend({**base, "adults": 2, "children": 0, "budget": 130, "wants_quiet": True})
    # Guest asks for separate beds: the Twin should now win
    recommend({**base, "adults": 2, "children": 0, "budget": 130, "wants_quiet": True,
               "wants_twin": True})

    print("\n=== Step 4: scarce upgrade rooms (only Deluxe 401 left) ===")
    for r in ROOMS:
        if r["id"] in ("402", "601"):
            r["available"] = False
    gold = {**base, "adults": 2, "children": 0, "budget": 120,
            "loyalty_tier": "Gold", "diamond_also_arriving": True}
    recommend(gold)                                  # R24: Diamond has priority
    recommend({**gold, "loyalty_tier": "Diamond"})   # Diamond gets the last room

    print("\n=== Step 4: no upgrade rooms left at all ===")
    for r in ROOMS:
        if r["id"] == "401":
            r["available"] = False
    recommend({**gold, "loyalty_tier": "Diamond"})   # R19