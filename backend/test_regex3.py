import re

tests = [
    "1 A",
    "1A",
    "28",
    "3  C",
    "4.",
    "5",
    "28"
]

def parse_line(line):
    # try letters first
    match_answer = re.search(r"^\s*(?:\|\s*)?(?:(?:Q|Question)\s*)?(?:\*\*)?\s*(\d+)\s*(?:\*\*)?[\s:\|\.\-\)]*([A-Za-z])\s*(?:\|\s*)?(?:\*)?$", line, flags=re.IGNORECASE)
    if match_answer:
        return match_answer.group(1), match_answer.group(2).upper()
    
    # fallback for OCR misreads like 28 -> 2 B, 40 -> 4 D, 14 -> 1 A
    ocr_map = {'8': 'B', '0': 'D', '4': 'A', '1': 'I', '5': 'S', '6': 'G', '2': 'Z'}
    match_number = re.search(r"^\s*(?:\|\s*)?(?:(?:Q|Question)\s*)?(?:\*\*)?\s*(\d+)\s*(?:\*\*)?[\s:\|\.\-\)]*([0-9])\s*(?:\|\s*)?(?:\*)?$", line)
    if match_number:
        q_num, ans_digit = match_number.group(1), match_number.group(2)
        if ans_digit in ocr_map:
            return q_num, ocr_map[ans_digit]
            
    # what if there's no space and it's a double digit question? e.g. 10A
    # If it is like "108" -> Q 10, Ans 8 (B)
    match_no_space = re.search(r"^(\d+)([A-Za-z0-9])$", line.replace(" ", ""))
    if match_no_space:
        q_num, ans_char = match_no_space.group(1), match_no_space.group(2)
        ans_char = ans_char.upper()
        if ans_char in ocr_map:
             ans_char = ocr_map[ans_char]
        return q_num, ans_char

    return None, None

for t in tests:
    print(f"'{t}' -> {parse_line(t)}")

