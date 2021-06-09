##########################################
# SPLICE_DEBUG is used internally to debug
# splice-related code in Django's core
# framework, including additional modules
# introduced by the Splice framework.
# Turn it off during evaluation since it
# affects performance.
##########################################
SPLICE_DEBUG = False
##########################################################
# TAINT_OPTIMIZATION, if set, allows Splice to "turn off"
# taint propagation at certain places and resume at a
# later place. For example, for a function call that takes
# a tainted input and produces an output value, if we know
# that 1) operations in the function does not persist any
# data that might be tainted, and 2) the output inherits
# the taint from the input, we can simply taint the output
# using input's taint and does not track taint during the
# function call.
##########################################################
TAINT_OPTIMIZATION = False
##########################################################
# We can opt to drop taint early at the end of the Django
# pipeline where HttpResponse is being rendered from a
# template and context. If TAINT_DROP is set, we can check
# taint in the context to determine early if the Http
# response would contain synthesized data, so that taint
# does not need to be propagated to the HttpResponse bytes
# This is an aggressive taint optimization and it requires
# that we clear any cache that might store HttpResponse
# for future requests because those cached HttpResponses
# no longer contain taints (meaning that they might
# contain user data that should be deleted but Splice will
# not be able to identify without taints). This
# optimization is specific to HttpResponse.
##########################################################
TAINT_DROP = False
