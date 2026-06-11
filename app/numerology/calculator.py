from datetime import datetime


def parse_birth_date(date_text: str) -> tuple[int, int, int]:
    try:
        dt = datetime.strptime(date_text.strip(), "%d.%m.%Y")
        return dt.day, dt.month, dt.year
    except ValueError:
        raise ValueError("Дата должна быть в формате ДД.ММ.ГГГГ")


def digit_sum(value: int) -> int:
    return sum(int(d) for d in str(value))


def reduce_to_digit(value: int) -> int:
    while value > 9 and value not in (11, 22, 33):
        value = digit_sum(value)
    return value


def calculate_life_path_number(date_text: str) -> dict:
    day, month, year = parse_birth_date(date_text)
    raw = digit_sum(day) + digit_sum(month) + digit_sum(year)
    number = reduce_to_digit(raw)

    return {
        "birth_date": date_text.strip(),
        "number": number,
        "raw": raw,
        "type": "life_path",
    }


def calculate_destiny_number(date_text: str) -> dict:
    day, month, year = parse_birth_date(date_text)
    raw = day + month + digit_sum(year)
    number = reduce_to_digit(raw)

    return {
        "birth_date": date_text.strip(),
        "number": number,
        "raw": raw,
        "type": "destiny",
    }


def calculate_personal_qualities(date_text: str) -> dict:
    day, month, year = parse_birth_date(date_text)

    life_path = calculate_life_path_number(date_text)
    destiny = calculate_destiny_number(date_text)

    return {
        "birth_date": date_text.strip(),
        "day_number": reduce_to_digit(day),
        "month_number": reduce_to_digit(month),
        "year_number": reduce_to_digit(digit_sum(year)),
        "life_path_number": life_path["number"],
        "destiny_number": destiny["number"],
        "type": "qualities",
    }


def calculate_purpose(date_text: str) -> dict:
    life_path = calculate_life_path_number(date_text)
    destiny = calculate_destiny_number(date_text)

    raw = life_path["number"] + destiny["number"]
    number = reduce_to_digit(raw)

    return {
        "birth_date": date_text.strip(),
        "number": number,
        "life_path_number": life_path["number"],
        "destiny_number": destiny["number"],
        "type": "purpose",
    }


def calculate_compatibility(date1: str, date2: str) -> dict:
    p1 = calculate_life_path_number(date1)
    p2 = calculate_life_path_number(date2)

    raw = p1["number"] + p2["number"]
    pair_number = reduce_to_digit(raw)

    return {
        "date1": date1.strip(),
        "date2": date2.strip(),
        "person1_number": p1["number"],
        "person2_number": p2["number"],
        "pair_number": pair_number,
        "type": "compatibility",
    }


def calculate_personal_numerology(date_text: str) -> dict:
    return calculate_personal_qualities(date_text)


def calculate_compatibility_numerology(date1: str, date2: str) -> dict:
    return calculate_compatibility(date1, date2)
