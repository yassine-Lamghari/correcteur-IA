import re

tests = [
    "1 A",
    "1A",
    "Q1 B",
    "2  C",
    "3  D"
]

regex = r"^\s*(?:\|\s*)?(?:(?:Q|Question)\s*)?(?:\*\*)?\s*(\d+)\s*(?:\*\*)?[\s:\|\.\-\)]+(.*?)\s*(?:\|\s*)?(?:\*)?$"
for t in tests:
    m = re.search(regex, t, flags=re.IGNORECASE)
    print(f"'{t}' -> {m.groups() if m else None}")
