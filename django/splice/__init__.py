"""Globally override function imports."""

import sys

from django.splice.untrustedtypes import is_synthesized, to_untrusted


#  Override built-in functions by modifying Python's builtins module
#  This type of module level override is risky since other modules
#  that use those built-in functions may not be aware of this override.
module = sys.modules['builtins']
#  len(): we override this function because CPython performs a type
#  validation on the return type of the builtin len() to ensure that
#  the value is always of int type, even if we override __len__. To
#  circumvent this check, we have to directly override len().
module.len = lambda obj: obj.__len__()
sys.modules['builtins'] = module
