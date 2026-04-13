import re

tests = [
    "1 A",
    "1A",
    "28",
    "2  8",
    "Page 1 of 2",
    "1 ABCD",
    "MATRICULE 12345",
    "1 A 2 B 3C",
    "Q1 B Q2 8 Q3: C"
]

ocr_map = {'8': 'B', '0': 'D', '4': 'A', '1': 'I', '5': 'S', '6': 'G', '2': 'Z'}
valid_answers = {'A', 'B', 'C', 'D'}

for text in tests:
    print(f"\n--- Testing: '{text}'")
    
    # regex pour trouver N'IMPORTE OÙ dans le texte un chiffre (question) suivi d'une lettre (réponse)
    # \b(\d+)\s*[:.\-\)]?\s*([A-Za-z]|[0-9])\b  <-- too broad?
    # let's be specific for answers: A, B, C, D or their OCR equivalents 8, 0, 4
    
    # We want to capture the number, and the immediate next token if it looks like an answer.
    # pattern: group 1 = question number, group 2 = potential answer.
    # Look for digits, optional separator, then 1 character (letter or mapped digit).
    # Ignore standalone numbers that aren't followed by something answer-like?
    
    matches = re.finditer(r"(?:^|\s|Q|Question)(?:\*\*)?(\d+)(?:\*\*)?[\s:\|\.\-\)]*([A-Za-z]|[0-9])(?=\s|$|\|)", text, re.IGNORECASE)
    
    for m in matches:
        q_num = m.group(1)
        ans_raw = m.group(2).upper()
        
        # Apply mapping
        if ans_raw in ocr_map:
            ans_raw = ocr_map[ans_raw]
            
        if ans_raw in valid_answers:
            print(f"  -> Q{q_num}: {ans_raw}")
        else:
            print(f"  -> Q{q_num}: Rejected ({ans_raw})")

