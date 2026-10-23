import pytest

import tridi  # noqa: F401
from projects.shelf.body import build_body
from projects.shelf.layout import plan
from projects.shelf.params import ShelfParams, effective


def _build(**kw):
    p = effective(ShelfParams(**kw))[0]
    return build_body(p, plan(p))


@pytest.fixture
def build():
    return _build
