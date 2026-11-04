"""Repaired synthetic pricing fixture; no payment integration."""


def payable(subtotal, shipping):
    discount = subtotal // 10 if subtotal >= 100_000 else 0
    return subtotal - discount + shipping
