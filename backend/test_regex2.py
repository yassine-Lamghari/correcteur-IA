import re

tests = [
    "1 A",
    "1A",
    "2B",
    "3  C",
    "4.",
    "5",
    "28"
]

regex = r"^\s*(?:\|\s*)?(?:(?:Q|Question)\s*)?(?:\*\*)?\s*(\d+)\s*(?:\*\*)?[\s:\|\.\-\)]*(.*?)\s*(?:\|\s*)?(?:\*)?$"
for t in tests:
    m = re.search(regex, t, flags=re.IGNORECASE)
    ans = m.group(2).strip() if m else None
    if m and ans:
        print(f"'{t}' -> {m.group(1)} | {ans}")
    else:
        print(f"'{t}' -> None")
