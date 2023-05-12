# django-filter-autotools

## Installation

Either using pip

```bash
python -m pip install django-filter-autotools
```

or directly copying the file `django_filters_autotools/mixins.py` into your project.


## DefaultLookupsMixin

By default django-filter FilterSet class will only generate `exact` lookups if given a list of fields. This mixin can be used to customize this behaviour:
```python
class MyFilterSet(DefaultLookupsMixin, FilterSet):

    DEFAULT_LOOKUPS = {
        models.CharField:      [ 'exact', 'icontains' ],
        models.IntegerField:   [ 'exact', 'lt', 'lte', 'gt', 'gte', 'range' ]
    }
```

`MyFilterSet` will automatically generate filters for all these lookups for any field included in `fields` if `fields` is an array. In the case that `fields` is a dictionary, defaults will be generated for any key having `None` as value.


## PseudoLookupsMixin

We can use this mixin to patch the FilterSet filter creation algorithm to understand some lookups which are not registered into Django. Two common scenarios are checking whether a string is empty, adding "exclusion" filters (not) and adding "conjoined" filters (and for m2m):

```python
class EmptyStringFilter(filters.BooleanFilter):
    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        exclude = self.exclude ^ (value is False)
        method = qs.exclude if exclude else qs.filter

        return method(**{self.field_name: ""})


class MyFilterSet(PseudoLookupsMixin, FilterSet):

    PSEUDO_LOOKUPS = { 
        'isempty': {
            'behaves_like': 'isnull',
            'filter_class': EmptyStringFilter,
        },
        'not_icontains': {
            'behaves_like': 'icontains',
            'filter_class': None,
            'replace_with': 'icontains',
            'extra': lambda f: {'exclude': True}
        },
        'exact_all': {
            'behaves_like': 'exact',
            'filter_class': None,
            'replace_with': 'exact',
            'extra': lambda f: {'conjoined': True}
        }
    }
```

Under the hood this works by replacing the lookup with the one specified in the `behaves_like` key, running the filter creation algorithm and then patching the filters if necessary. This way any transformer or any extra lookups registered into Django will also be available.

`PSEUDO_LOOKUPS` is a dictionary whose keys are the new lookups to be supported and the values are dictionary with the following keys:

* `behaves_like`: should be a lookup registered in Django with similar semantics.
* `filter_class`: filter class to be used for this lookup. If not specified or set to None, the one chosen django-filter for the `behaves_like` lookup will be used. Note that these may be fine-tuned by overriding the `FILTER_FOR_DBFIELD_DEFAULTS` dictionary.
* `replace_with`: if present the filter class is patched so that its `__init__` method replaces the new lookup with this value.
* `extra`: if present the object returned from applying this function to the field will be merged into the filter class kwargs.

Override the `filter_for_pseudolookup` class method on the FilterSet if you need to choose different filter classes depending on both the field type and the lookup.


## Integrating everything into DRF by default

Complete example making available several lookups by default for all fields of type `CharField`, and conjoined filters for all fields of type `ManyToManyField`:

filters.py:
```python
from django_filters import rest_framework as filters
from django.db import models
from django.core.validators import EMPTY_VALUES
from django_filters_autotools.mixins import *


class EmptyStringFilter(filters.BooleanFilter):
    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        exclude = self.exclude ^ (value is False)
        method = qs.exclude if exclude else qs.filter

        return method(**{self.field_name: ""})


class MyFilterSet(DefaultLookupsMixin, PseudoLookupsMixin, filters.FilterSet):

    PSEUDO_LOOKUPS = { 
        'isempty': {
            'behaves_like': 'isnull',
            'filter_class': EmptyStringFilter,
        },
        'not_icontains': {
            'behaves_like': 'icontains',
            'filter_class': None,
            'replace_with': 'icontains',
            'extra': lambda f: {'exclude': True}
        },
        'exact_all': {
            'behaves_like': 'exact',
            'filter_class': None,
            'replace_with': 'exact',
            'extra': lambda f: {'conjoined': True}
        }
    }

    DEFAULT_LOOKUPS = {
        models.CharField:        [ 'exact', 'icontains', 'isempty', 'not_icontains' ],
        models.ManyToManyField:  [ 'exact', 'exact_all' ],
    }

    
class MyFilterBackend(filters.DjangoFilterBackend):
    filterset_base = MyFilterSet
```

settings.py:
```python
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'path.to.filters.MyFilterBackend',
    ],
}
```

## More info

[PyPI project](https://pypi.org/project/django-filter-autotools/)

[Github page](https://github.com/WhiteSage/django-filter-autotools)