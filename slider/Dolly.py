class Dolly:
    """
    Dolly knows:
     # its own position
    """

    """ Actual dolly position """
    current_position = 0

    """ Change
    """
    def change_position(self, value, direction):
        self.current_position += direction * value

    """ Set current position for dolly
    """
    def set_position(self, position: int):
        self.current_position = position

    """ Get current dolly position
    """
    def get_position(self) -> int:
        return self.current_position
