from bitarray import bitarray


class TaintSource(object):
    """Track everything about user taints."""
    MAX_USERS = 64  # Maximum number of user allowed
    current_user_id = None
    current_user_taint = None


def set_current_user_id(uid):
    TaintSource.current_user_id = uid
    set_taint_from_id(uid)


def set_current_user_taint(taint):
    TaintSource.current_user_taint = taint


def set_taint_from_id(uid):
    pos = uid % TaintSource.MAX_USERS
    taint = bitarray(TaintSource.MAX_USERS, endian='big')
    taint.setall(False)
    taint[pos] = True
    set_current_user_taint(taint)
