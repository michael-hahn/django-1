"""Splice database modification."""

from django.db import models
from django.db.models.fields import reverse_related, related
from django.splice.splice import SpliceMixin
from django.splice.identity import to_int, to_bitarray, empty_taint, union_to_int


class SpliceDB(models.Model):
    """Model's abstract base class. All existing models should inherit this class to be Splice-aware."""
    synthesized = models.BooleanField(default=False)
    trusted = models.BooleanField(default=True)
    taints = models.BigIntegerField(default=0)

    # FIXME: For ModelForm that inherits SpliceDB, e.g., InvoiceAddressForm and ShippingAddressForm,
    #  the form will require input from the new fields above, which is not what we want. Reference:
    #  https://stackoverflow.com/questions/1134667/django-required-field-in-model-form. For now, we
    #  manually set .required to False in the __init__ of those classes (e.g., check the __init__
    #  of InvoiceAddressForm at lfs.addresses.forms).

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Before saving the model instance to the database, compute the taints."""
        taints = empty_taint()
        for field in self.__class__._meta.get_fields():
            # We do not want to inspect reverse relationships
            if isinstance(field, reverse_related.ManyToOneRel) or isinstance(field, reverse_related.OneToOneRel):
                continue

            # It is possible that at time of save(), getattr() will fail for some
            # relational fields (perhaps because more information is needed later)
            # e.g., when saving a User instance object.
            try:
                field_value = getattr(self, field.name, None)
                # FIXME: For relational fields, do we get their taints from
                #  their model instances (i.e., propagate taints) or not? For
                #  now, we ignore their taints (i.e., taints from their
                #  referenced row in perhaps another table).
                if isinstance(field, related.ForeignKey) \
                   or isinstance(field, related.OneToOneField) \
                   or isinstance(field, related.ManyToManyField):
                    # # Note: field.remote_field.model returns the model of the ForeignKey/OneToOneField
                    # key_taint = field_value.taints   # field_value.taints is the foreign instance's taint, i.e., int
                    # # Convert from integer into bitarray for bit operation
                    # kba = to_bitarray(key_taint)
                    # taints |= kba
                    pass

                # For non-relational fields, check if field value is tainted
                if isinstance(field_value, SpliceMixin):
                    # field_value.taints is the object's taint stored in that field
                    # The taints should already be in bitarray format
                    taints |= field_value.taints
            except Exception as e:
                pass

        # Update the taint with the existing taint from self.taints and
        # set the taint properly by convert the bitarray into integer
        self.taints = union_to_int(self.taints, taints)
        # Call the "real" save() method (save to DB).
        super().save(*args, **kwargs)
