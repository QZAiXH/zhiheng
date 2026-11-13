from decimal import Decimal


def subtotal(lines):
    """Return the sum of quantity * unit price for each line."""
    return sum((Decimal(str(qty)) * Decimal(str(price)) for qty, price in lines), Decimal("0"))
