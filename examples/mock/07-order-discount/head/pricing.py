"""Intentionally faulty synthetic pricing fixture."""


def payable(subtotal, shipping):
    total = subtotal + shipping
    if subtotal > 100_000:
        total -= total // 10
    return total
