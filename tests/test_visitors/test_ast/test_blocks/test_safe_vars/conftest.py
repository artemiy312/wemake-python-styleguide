# -*- coding: utf-8 -*-

from string import Formatter

import pytest


class _DefaultFormatter(Formatter):

    def __init__(self, subs: str):
        self._default = subs

    def get_value(self, key, args, kwargs):
        if not isinstance(key, str):
            return super().get_value(key, args, kwargs)

        if key in kwargs:
            return kwargs[key]
        return self._default

    def check_unused_args(self, used_args, args, kwargs):
        for key in kwargs:
            if key not in used_args:
                raise ValueError('{0} is not in format string.'.format(key))
        if len(used_args) < len(args) + len(kwargs):
            raise ValueError('Too many args are passed.')


@pytest.fixture()
def default_formatter(request):
    """Get formatter which substitute missed keys with default value."""
    return _DefaultFormatter(getattr(request, 'param', '...'))
