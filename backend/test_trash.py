import re
line = "12 questions in total"
match_answer = re.search(r"^\s*(?:\|\s*)?(?:(?:Q|Question)\s*)?(?:\*\*)?\s*(\d+)\s*(?:\*\*)?[\s:\|\.\-\)]*(.*?)\s*(?:\|\s*)?(?:\*)?$", line, flags=re.IGNORECASE)
print(f"Group 1: '{match_answer.group(1)}', Group 2: '{match_answer.group(2)}'") if match_answer else print("No match")
