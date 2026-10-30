"""Named unittest parameterization; every row is independently discoverable."""
from copy import deepcopy


def cases(rows):
    def decorate(check):
        check.case_rows = rows
        return check
    return decorate


def expand_cases(cls):
    for name, check in list(vars(cls).items()):
        if not hasattr(check, 'case_rows'):
            continue
        delattr(cls, name)
        for label, *values in check.case_rows:
            test_name = f'{name}_{label}'
            if hasattr(cls, test_name):
                raise ValueError(f'Duplicate test: {test_name}')
            def test(self, _check=check, _values=values):
                _check(self, *deepcopy(_values))
            test.__name__ = test_name
            test.__doc__ = f'{check.__doc__ or name}: {label}'
            setattr(cls, test_name, test)
    return cls
