from datetime import datetime
import jdatetime

def is_valid_persian_name(name: str) -> bool:
    if not name or not (2 <= len(name) <= 50):
        return False
    for char in name:
        if not ('\u0600' <= char <= '\u06FF' or char == ' '):
            return False
    return True

def is_valid_national_code(code: str) -> bool:
    if not code.isdigit() or len(code) != 10:
        return False

    s = 0
    for i in range(9):
        s += int(code[i]) * (10 - i)
    
    remainder = s % 11
    
    control_digit = int(code[9])

    if remainder < 2:
        return control_digit == remainder
    else:
        return control_digit == 11 - remainder

def is_valid_birth_date(date_str: str) -> bool:

    try:
        parts = date_str.split('/')
        if len(parts) != 3:
            return False
        
        year, month, day = map(int, parts)

        jdatetime.date(year, month, day)

        today = jdatetime.date.today()
        age = today.year - year - ((today.month, today.day) < (month, day))
        
        if not 10 <= age <= 100:
            return False
            
        return True
    except (ValueError, IndexError):
        return False