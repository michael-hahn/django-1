from django.splice.settings import BITARRAY

if BITARRAY:
    from bitarray import bitarray
    from bitarray.util import int2ba, ba2int

MAX_USERS = 63


def empty_taint():
    if BITARRAY:
        taint = bitarray(MAX_USERS, endian='big')
        taint.setall(False)
        return taint
    return 0


class TaintSource(object):
    """Track everything about user taints."""
    MAX_USERS = MAX_USERS  # Maximum number of user allowed
    current_user_id = None
    current_user_taint = empty_taint()


def set_current_user_id(uid):
    TaintSource.current_user_id = uid
    set_taint_from_id(uid)


def set_current_user_taint(taint):
    TaintSource.current_user_taint = taint


def set_taint_from_id(uid):
    pos = uid % TaintSource.MAX_USERS
    if BITARRAY:
        taint = empty_taint()
        taint[pos] = True
    else:
        taint = 1 << pos
    set_current_user_taint(taint)


# For int taint only
def get_taint_from_id(uid):
    pos = uid % TaintSource.MAX_USERS
    return 1 << pos


def to_int(taint):
    """Convert a bitarray taint to its corresponding integer."""
    if BITARRAY:
        return ba2int(taint, signed=True)
    return taint


def to_bitarray(taint):
    """Convert an integer taint to its corresponding bitarray."""
    if BITARRAY:
        return int2ba(taint, length=TaintSource.MAX_USERS, endian='big', signed=True)
    return taint


def union(taint_1, taint_2):
    """
    Union two taints and return a union-ed bit array.
    The two taints can either be an integer or a bit array.
    """
    if BITARRAY:
        if not isinstance(taint_1, bitarray):
            taint_1 = to_bitarray(taint_1)
        if not isinstance(taint_2, bitarray):
            taint_2 = to_bitarray(taint_2)
        return taint_1 | taint_2
    return taint_1 | taint_2


def union_to_int(taint_1, taint_2):
    """Similar to union but return a union-ed integer."""
    if BITARRAY:
        return to_int(union(taint_1, taint_2))
    return union(taint_1, taint_2)


if __name__ == "__main__":
    pass
