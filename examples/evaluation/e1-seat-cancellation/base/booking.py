class Booking:
    def __init__(self, available, quantity):
        self.available = available - quantity
        self.quantity = quantity
        self.status = 'active'
