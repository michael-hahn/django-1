from bitarray import bitarray
from bitarray.util import int2ba, ba2int

MAX_USERS = 64


def empty_taint():
    taint = bitarray(MAX_USERS, endian='big')
    taint.setall(False)
    return taint


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
    taint = empty_taint()
    taint[pos] = True
    set_current_user_taint(taint)


def to_int(taint):
    """Convert a bitarray taint to its corresponding integer."""
    return ba2int(taint, signed=True)


def to_bitarray(taint):
    """Convert an integer taint to its corresponding bitarray."""
    return int2ba(taint, length=TaintSource.MAX_USERS, endian='big', signed=True)


def union(taint_1, taint_2):
    """
    Union two taints and return a union-ed bit array.
    The two taints can either be an integer or a bit array.
    """
    if not isinstance(taint_1, bitarray):
        taint_1 = to_bitarray(taint_1)
    if not isinstance(taint_2, bitarray):
        taint_2 = to_bitarray(taint_2)
    return taint_1 | taint_2


def union_to_int(taint_1, taint_2):
    """Similar to union but return a union-ed integer."""
    return to_int(union(taint_1, taint_2))


if __name__ == "__main__":
    pass
