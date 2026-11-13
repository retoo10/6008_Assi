"""
test_cases.py - Test suite for the Muqaddas Tower Hotel recommender.

Run with:  python3 test_cases.py
It prints PASS/FAIL for each test and saves test_results.csv, which you can
open in Excel and paste into the testing section of your report.

IMPORTANT: the "expect" values below come from hotel knowledge (the rules
agreed with the domain expert), NOT from the program's own output. A test
that simply copied the output could never fail and would prove nothing.
If a test FAILS, that is a finding: log it, fix the rule, re-run.
"""

import csv

from hotel_data import ROOMS, GROUP_BOOKING_MIN_ROOMS
from engine import run_engine, decide_upgrade, SERVICE_RULES

BASE = {"needs_access": False, "wants_twin": False}


# THE TEST CASES
# "unavailable" temporarily marks rooms as booked for that test only.

TESTS = [
    {"id": "T01", "rules": "R4",
     "scenario": "Couple, GBP 120 budget, no requests",
     "guest": {"adults": 2, "children": 0, "budget": 120},
     "expect": {"top_type": "Standard King"}},

    {"id": "T02", "rules": "R4",
     "scenario": "Couple, GBP 120 budget, wants separate beds",
     "guest": {"adults": 2, "children": 0, "budget": 120, "wants_twin": True},
     "expect": {"top_type": "Standard Twin"}},

    {"id": "T03", "rules": "R8, R25",
     "scenario": "Couple wants a quiet room, GBP 130 (king should beat twin)",
     "guest": {"adults": 2, "children": 0, "budget": 130, "wants_quiet": True},
     "expect": {"top_type": "Standard King", "top_zone": "mid"}},

    {"id": "T04", "rules": "R8, R9, R10",
     "scenario": "Quiet + short walk to lift + view, GBP 160",
     "guest": {"adults": 2, "children": 0, "budget": 160, "wants_quiet": True,
               "limited_mobility": True, "wants_view": True},
     "expect": {"top_type": "Deluxe King", "top_zone": "mid"}},

    {"id": "T05", "rules": "R5",
     "scenario": "Family of 4 (2 adults, 2 children), GBP 250",
     "guest": {"adults": 2, "children": 2, "budget": 250},
     "expect": {"top_type": "Junior Suite", "rooms_needed": 1}},

    {"id": "T06", "rules": "R6",
     "scenario": "Family of 4, GBP 180 (suite is over budget)",
     "guest": {"adults": 2, "children": 2, "budget": 180},
     "expect": {"top_type": "Family Room"}},

    {"id": "T07", "rules": "R1",
     "scenario": "Guest needs an accessible room, GBP 130",
     "guest": {"adults": 1, "children": 0, "budget": 130, "needs_access": True},
     "expect": {"top_type": "Accessible King"}},

    {"id": "T08", "rules": "R2",
     "scenario": "Couple with no access needs, GBP 300 (accessible room must never be offered)",
     "guest": {"adults": 2, "children": 0, "budget": 300},
     "expect": {"not_offered": "Accessible King"}},

    {"id": "T09", "rules": "R7",
     "scenario": "Couple with GBP 50 budget (nothing fits)",
     "guest": {"adults": 2, "children": 0, "budget": 50},
     "expect": {"result": "over_budget"}},

    {"id": "T10", "rules": "R14",
     "scenario": "Member on an anniversary, GBP 120",
     "guest": {"adults": 2, "children": 0, "budget": 120, "occasion": "anniversary"},
     "expect": {"upgrade_status": "granted", "upgrade_type": "Deluxe King",
                "extras_include": ["room set-up with rose petals", "anniversary card"]}},

    {"id": "T11", "rules": "R16",
     "scenario": "Diamond member, GBP 120",
     "guest": {"adults": 2, "children": 0, "budget": 120, "loyalty_tier": "Diamond"},
     "expect": {"upgrade_status": "granted",
                "extras_include": ["treat", "welcome card from the hotel"]}},

    {"id": "T12", "rules": "R18",
     "scenario": "Silver member, no occasion (no free upgrade, paid offer)",
     "guest": {"adults": 2, "children": 0, "budget": 120, "loyalty_tier": "Silver"},
     "expect": {"upgrade_status": "paid_offer", "paid_cost": 24.0}},

    {"id": "T13", "rules": "R17, R24",
     "scenario": "Gold member, ONE upgrade room left, a Diamond member also arriving",
     "guest": {"adults": 2, "children": 0, "budget": 120, "loyalty_tier": "Gold",
               "diamond_also_arriving": True},
     "unavailable": ["402", "601"],
     "expect": {"upgrade_status": "conflict"}},

    {"id": "T14", "rules": "R19",
     "scenario": "Diamond member, no Deluxe rooms free at all",
     "guest": {"adults": 2, "children": 0, "budget": 120, "loyalty_tier": "Diamond"},
     "unavailable": ["401", "402", "601"],
     "expect": {"upgrade_status": "unavailable"}},

    {"id": "T15", "rules": "R20",
     "scenario": "Hotel only 45% full: Standard King should be 10% cheaper",
     "guest": {"adults": 2, "children": 0, "budget": 120, "occupancy": 45},
     "expect": {"top_type": "Standard King", "top_price": 103.5}},

    {"id": "T16", "rules": "R11",
     "scenario": "Business traveller, GBP 200",
     "guest": {"adults": 1, "children": 0, "budget": 200, "business_traveller": True},
     "expect": {"top_type": "Executive King", "notes_include": ["R11"]}},

    {"id": "T17", "rules": "R12",
     "scenario": "12 adults (needs 6 rooms): group handoff",
     "guest": {"adults": 12, "children": 0, "budget": 150},
     "expect": {"rooms_needed": 6, "plan_size": 6, "notes_include": ["R12"]}},

    {"id": "T18", "rules": "R13",
     "scenario": "6 adults (needs 3 rooms): standard pricing, no group handoff",
     "guest": {"adults": 6, "children": 0, "budget": 130},
     "expect": {"rooms_needed": 3, "notes_include": ["R13"], "notes_exclude": ["R12"]}},

    {"id": "T19", "rules": "R23",
     "scenario": "7-night stay: restock every 3 days",
     "guest": {"adults": 2, "children": 0, "budget": 120, "nights": 7},
     "expect": {"notes_include": ["R23"], "restock_contains": "day 3, day 6"}},
]



# Run the engine the same way recommend() does, but return data

def get_outcome(guest):
    facts, affordable, suitable = run_engine(guest)
    n = facts["rooms_needed"]
    out = {"facts": facts, "affordable": affordable, "rooms_needed": n,
           "top": None, "plan": [], "upgrade": None, "result": "recommended"}

    out["notes"] = [r["id"] for r in SERVICE_RULES if r["condition"](facts)]
    out["restock"] = next((r["message"](facts) for r in SERVICE_RULES
                           if r["id"] == "R23" and r["condition"](facts)), "")

    if not affordable:
        out["result"] = "over_budget" if suitable else "no_room"
        return out

    if n == 1:
        out["plan"] = [affordable[0]]
    else:
        singles = [r for r in affordable if r["type"] != "Connecting Rooms"]
        out["plan"] = singles[:n]
    out["top"] = out["plan"][0] if out["plan"] else None

    if out["top"] and n < GROUP_BOOKING_MIN_ROOMS:
        out["upgrade"] = decide_upgrade(facts, out["top"],
                                        [r["id"] for r in out["plan"]])
    return out


def measure(out):
    top, up = out["top"], out["upgrade"]
    return {
        "result": out["result"],
        "top_type": top["type"] if top else None,
        "top_zone": top["zone"] if top else None,
        "top_price": top["price"] if top else None,
        "upgrade_status": up["status"] if up else None,
        "upgrade_type": up["room"]["type"] if up and up["room"] else None,
        "paid_cost": up["paid_cost"] if up else None,
        "extras": up["extras"] if up else [],
        "notes": out["notes"],
        "rooms_needed": out["rooms_needed"],
        "plan_size": len(out["plan"]),
        "offered_types": sorted({r["type"] for r in out["affordable"]}),
        "restock": out["restock"],
    }


def check(expect, actual):
    """Returns (passed, expected_text, actual_text)."""
    passed = True
    exp_parts, act_parts = [], []
    for key, want in expect.items():
        if key == "extras_include":
            ok = all(x in actual["extras"] for x in want)
            exp_parts.append("extras include " + " + ".join(want))
            act_parts.append("extras: " + (", ".join(actual["extras"]) or "none"))
        elif key == "notes_include":
            ok = all(x in actual["notes"] for x in want)
            exp_parts.append("notes include " + ", ".join(want))
            act_parts.append("notes: " + (", ".join(actual["notes"]) or "none"))
        elif key == "notes_exclude":
            ok = not any(x in actual["notes"] for x in want)
            exp_parts.append("notes exclude " + ", ".join(want))
            act_parts.append("notes: " + (", ".join(actual["notes"]) or "none"))
        elif key == "not_offered":
            ok = want not in actual["offered_types"]
            exp_parts.append(f"{want} never offered")
            act_parts.append("offered: " + ", ".join(actual["offered_types"]))
        elif key == "restock_contains":
            ok = want in actual["restock"]
            exp_parts.append(f"restock message contains '{want}'")
            act_parts.append(actual["restock"] or "no restock message")
        else:
            got = actual[key]
            ok = (got == want)
            exp_parts.append(f"{key} = {want}")
            act_parts.append(f"{key} = {got}")
        passed = passed and ok
    return passed, "; ".join(exp_parts), "; ".join(act_parts)


def run_test(case):
    saved = {r["id"]: r["available"] for r in ROOMS}
    for r in ROOMS:
        if r["id"] in case.get("unavailable", []):
            r["available"] = False
    try:
        actual = measure(get_outcome({**BASE, **case["guest"]}))
    finally:
        for r in ROOMS:                        # always restore availability
            r["available"] = saved[r["id"]]
    return check(case["expect"], actual)


def main():
    rows, failures = [], 0
    print(f"Running {len(TESTS)} tests...\n")
    for case in TESTS:
        passed, expected, actual = run_test(case)
        status = "PASS" if passed else "FAIL"
        failures += (not passed)
        print(f"{case['id']}  {status}  [{case['rules']}]  {case['scenario']}")
        if not passed:
            print(f"        expected: {expected}")
            print(f"        actual:   {actual}")
        rows.append([case["id"], case["rules"], case["scenario"],
                     expected, actual, status])

    with open("test_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Test", "Rules", "Scenario", "Expected", "Actual", "Result"])
        writer.writerows(rows)

    print(f"\n{len(TESTS) - failures}/{len(TESTS)} passed, {failures} failed.")
    print("Saved test_results.csv (open it in Excel for your report).")


if __name__ == "__main__":
    main()
