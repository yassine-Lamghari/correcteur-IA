import re
tests = ["1 A.", "1A)", "28..", "Page 1 of 2", "1 ABCD."]
for line in tests:
    m = re.search(r"^\s*(?:\|\s*)?(?:(?:Q|Question)\s*)?(?:\*\*)?\s*(\d+)\s*(?:\*\*)?[\s:\|\.\-\)]*([A-Za-z]{1,5}|[0-9])[\s:\|\.\-\)]*(?:\*)?$", line, flags=re.IGNORECASE)
    print(f"'{line}' -> {(m.group(1), m.group(2)) if m else 'None'}")
