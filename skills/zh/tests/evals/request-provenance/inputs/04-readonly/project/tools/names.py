def clean_names(values):
    result = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result
