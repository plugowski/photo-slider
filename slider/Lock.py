class Lock:
    """ Locker to avoid race condition in access to motor
    """

    is_lock = False
    locked_by = None

    def lock(self, process: str = None):
        if self.is_lock and self.locked_by != process:
            raise LockedProcessException('Motor is working!')

        self.is_lock = True
        self.locked_by = process

    def unlock(self, process: str = None):
        if self.locked_by == process:
            self.is_lock = False

    def is_locked(self):
        return self.is_lock


class LockedProcessException(Exception):
    pass
