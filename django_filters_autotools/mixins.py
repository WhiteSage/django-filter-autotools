from django_filters.conf import settings as django_filter_settings
from django_filters.utils import resolve_field as django_filter_resolve_field
from django_filters.utils import get_model_field, try_dbfield
from django.db import models
from django.db.models.fields.related import (ManyToManyRel, ManyToOneRel, OneToOneRel)
from django.core.validators import EMPTY_VALUES



class DefaultLookupsMixin():
    DEFAULT_LOOKUPS = {
        models.AutoField:                   None,
        models.CharField:                   None,
        models.TextField:                   None,
        models.BooleanField:                None,
        models.DateField:                   None,
        models.DateTimeField:               None,
        models.TimeField:                   None,
        models.DurationField:               None,
        models.DecimalField:                None,
        models.SmallIntegerField:           None,
        models.IntegerField:                None,
        models.PositiveIntegerField:        None,
        models.PositiveSmallIntegerField:   None,
        models.FloatField:                  None,
        models.NullBooleanField:            None,
        models.SlugField:                   None,
        models.EmailField:                  None,
        models.FilePathField:               None,
        models.URLField:                    None,
        models.GenericIPAddressField:       None,
        models.CommaSeparatedIntegerField:  None,
        models.UUIDField:                   None,

        # Forward relationships
        models.OneToOneField:               None,
        models.ForeignKey:                  None,
        models.ManyToManyField:             None,

        # Reverse relationships
        OneToOneRel:                        None,
        ManyToOneRel:                       None,
        ManyToManyRel:                      None,
    }


    @classmethod
    def get_fields(cls):
        fields = super().get_fields()
        user_fields = cls._meta.fields

        for field_name in fields:
            # Compute traversed field (if it includes relations)
            field = get_model_field(cls._meta.model, field_name)

            # Get data associated with the field class
            data = try_dbfield(cls.DEFAULT_LOOKUPS.get, field.__class__)

            # Patch them up if they were not provided
            if data is not None and \
              (not isinstance(user_fields, dict) or not user_fields[field_name]):
                fields[field_name] = data

        return fields


class PseudoLookupsMixin():
    PSEUDO_LOOKUPS = {}

    @classmethod
    def patch_filter_class(cls, filter_class, old_lookup, new_lookup):
        """
        Patches filter_class __init__ method to replace old_lookup with the new_lookup.
        """

        class PseudoLookupsFilterMetaclass(type):
            def __str__(self):
                return '<' + str(filter_class) + ' wrapped by ' + str(self) + '>'

        class PseudoLookupsFilter(filter_class, metaclass=PseudoLookupsFilterMetaclass):
            def __init__(self, *args, **kwargs):
                if 'lookup_expr' in kwargs:
                    kwargs['lookup_expr'] = kwargs['lookup_expr'][:-len(old_lookup)] + new_lookup
                super().__init__(*args, **kwargs)

        return PseudoLookupsFilter


    @classmethod
    def filter_for_pseudolookup(cls, field, lookup_type):
        """
        Override this method to provide custom lookups.
        By default it returns the class specified in 'filter_class' if not None.
        If None was specified, it returns the class django-filters' would use.
        If 'replace_lookup' is set, patches the class to receive this lookup 
        instead of the actual one.

        Args:
            field: resulting field from applying all transforms to the LHS
            lookup_type: lookup excluding any transforms

        Return value:
            Tuple (filterset_class, kwargs)
        """
        params = cls.PSEUDO_LOOKUPS[lookup_type].get('extra', lambda f: {})(field)
        behaves_like = cls.PSEUDO_LOOKUPS[lookup_type]['behaves_like']

        if cls.PSEUDO_LOOKUPS[lookup_type].get('filter_class', None) is not None:
            filter_class = cls.PSEUDO_LOOKUPS[lookup_type]['filter_class']
        else:
            filter_class, df_params = super().filter_for_lookup(field, behaves_like)

            df_params.update(params)
            params = df_params

        # Patch the class if we have to so that it receives the new lookup
        if cls.PSEUDO_LOOKUPS[lookup_type].get('replace_lookup', None):
            filter_class = cls.patch_filter_class(filter_class, lookup_type, cls.PSEUDO_LOOKUPS[lookup_type]['replace_lookup'])

        return filter_class, params

                

    @classmethod
    def filter_for_lookup(cls, field, lookup_type):
        """
        Support for pseudo-lookups
        """
        PSEUDO_LOOKUPS = getattr(cls, 'PSEUDO_LOOKUPS', {})

        if lookup_type in PSEUDO_LOOKUPS:
            filter, params = cls.filter_for_pseudolookup(field, lookup_type)
        else:
            filter, params = super().filter_for_lookup(field, lookup_type)

        return filter, params
    

    @classmethod
    def resolve_field(cls, field, lookup_expr):
        """
        This function attempts to resolve lookup_expr into transforms
        and a final lookup. At the same time it computes the field type
        resulting from applying the transforms.

        For pseudo-lookups the underlying Django machinery will fail,
        therefore we will swap them for a Django-compliant one with the
        same semantics, and then swap it back
        """
        PSEUDO_LOOKUPS = getattr(cls, 'PSEUDO_LOOKUPS', [])

        pseudo = None
        lookup_expr_parts = lookup_expr.split('__')
        for lookup in PSEUDO_LOOKUPS:
            if lookup_expr_parts[-1] == lookup:
                pseudo = lookup
                lookup_expr = lookup_expr[:-len(lookup)] + PSEUDO_LOOKUPS[lookup]['behaves_like']
                break

        field, lookup_type = django_filter_resolve_field(field, lookup_expr)

        if pseudo:
            lookup_type = pseudo

        return (field, lookup_type)


    @classmethod
    def filter_for_field(cls, field, field_name, lookup_expr=None):
        """
        This is exactly the same function copied from the BaseFilterSet class,
        except that it calls the class function resolve_field.
        See https://github.com/carltongibson/django-filter/issues/1575
        """
        if lookup_expr is None:
            lookup_expr = django_filter_settings.DEFAULT_LOOKUP_EXPR
        field, lookup_type = cls.resolve_field(field, lookup_expr)

        default = {
            "field_name": field_name,
            "lookup_expr": lookup_expr,
        }

        filter_class, params = cls.filter_for_lookup(field, lookup_type)
        default.update(params)

        assert filter_class is not None, (
            "%s resolved field '%s' with '%s' lookup to an unrecognized field "
            "type %s. Try adding an override to 'Meta.filter_overrides'. See: "
            "https://django-filter.readthedocs.io/en/main/ref/filterset.html"
            "#customise-filter-generation-with-filter-overrides"
        ) % (cls.__name__, field_name, lookup_expr, field.__class__.__name__)

        return filter_class(**default)