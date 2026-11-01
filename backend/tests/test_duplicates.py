import math
from datetime import UTC, datetime, timedelta

import numpy as np

from moneyplease.duplicates import duplicate_groups

T0 = datetime(2026, 10, 1, tzinfo=UTC)


def pair(s: float, base=None) -> tuple[list[float], list[float]]:
    a = np.zeros(8)
    a[0] = 1.0
    b = np.zeros(8)
    b[0], b[1] = s, math.sqrt(1 - s * s)
    return list(a), list(b)


def groups(items, score=None, seen=None):
    return duplicate_groups(items, score or {}, seen or {i: T0 for i, _, _ in items})


def test_misma_empresa_casi_igual_se_agrupa():
    a, b = pair(0.995)
    assert groups([(1, "HPE", a), (2, "hpe ", b)]) == {1: [2]}


def test_empresa_distinta_no():
    a, b = pair(0.999)
    assert groups([(1, "HPE", a), (2, "Abbott", b)]) == {}


def test_bajo_el_umbral_no():
    a, b = pair(0.98)
    assert groups([(1, "HPE", a), (2, "HPE", b)]) == {}


def test_cadena_se_une_en_un_grupo():
    # A~B y B~C, pero A y C quedan a 0.985: igual son un solo grupo.
    ang = math.acos(0.9925)
    vec = lambda t: [math.cos(t), math.sin(t)] + [0.0] * 6  # noqa: E731
    out = groups([(1, "X", vec(0)), (2, "X", vec(ang)), (3, "X", vec(2 * ang))])
    assert out == {1: [2, 3]}


def test_representante_por_puntaje_fecha_e_id():
    a, b = pair(0.999)
    assert groups([(1, "X", a), (2, "X", b)], score={1: 70, 2: 90}) == {2: [1]}
    seen = {1: T0, 2: T0 - timedelta(days=1)}
    assert groups([(1, "X", a), (2, "X", b)], score={1: 80, 2: 80}, seen=seen) == {2: [1]}
    assert groups([(5, "X", a), (3, "X", b)]) == {3: [5]}
