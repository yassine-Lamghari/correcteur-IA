import re

tests = [
    "1 A",
    "1A",
    "28",
    "3C",
    "14D",
    "Q14 D"
]

ocr_map = {'8': 'B', '0': 'D', '4': 'A', '1': 'I', '5': 'S', '6': 'G', '2': 'Z'}

for line in tests:
    match_answer = re.search(r"^\s*(?:\|\s*)?(?:(?:Q|Question)\s*)?(?:\*\*)?\s*(\d+)\s*(?:\*\*)?[\s:\|\.\-\)]*(.*?)\s*(?:\|\s*)?(?:\*)?$", line, flags=re.IGNORECASE)
    if match_answer:
        q_num_raw = match_answer.group(1)
        ans_raw = match_answer.group(2).strip().upper()
        
        # If there's no space and it's something like "28", group(1) might be "28" and group(2) empty.
        if not ans_raw and len(q_num_raw) > 1:
             # Try to split last char as answer
             ans_raw = q_num_raw[-1]
             q_num_raw = q_num_raw[:-1]
             
        if ans_raw:
             q_num = str(int(q_num_raw)) # Normalize number, e.g. '01' to '1'
             # Apply OCR corrections
             if ans_raw in ocr_map:
                 ans_raw = ocr_map[ans_raw]
             print(f"'{line}' -> {q_num} | {ans_raw}")
        else:
             print(f"'{line}' -> None")

