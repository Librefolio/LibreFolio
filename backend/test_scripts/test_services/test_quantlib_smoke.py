"""Smoke tests for the adopted QuantLib runtime dependency."""

from __future__ import annotations

import QuantLib as ql


def _seeded_path(seed: int) -> tuple[float, ...]:
    evaluation_date = ql.Date(27, 7, 2026)
    day_counter = ql.Actual365Fixed()
    ql.Settings.instance().evaluationDate = evaluation_date
    spot = ql.QuoteHandle(ql.SimpleQuote(100.0))
    risk_free_curve = ql.YieldTermStructureHandle(ql.FlatForward(evaluation_date, 0.03, day_counter))
    dividend_curve = ql.YieldTermStructureHandle(ql.FlatForward(evaluation_date, 0.0, day_counter))
    volatility = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(
            evaluation_date,
            ql.NullCalendar(),
            0.2,
            day_counter,
        )
    )
    process = ql.BlackScholesMertonProcess(
        spot,
        dividend_curve,
        risk_free_curve,
        volatility,
    )
    uniform = ql.UniformRandomSequenceGenerator(
        30,
        ql.UniformRandomGenerator(seed),
    )
    gaussian = ql.GaussianRandomSequenceGenerator(uniform)
    generator = ql.GaussianPathGenerator(
        process,
        30 / 365,
        30,
        gaussian,
        False,
    )

    sample = generator.next()
    path = sample.value()
    return tuple(float(path[index]) for index in range(len(path)))


def test_quantlib_required_capabilities_are_available():
    required = {
        "BlackScholesMertonProcess",
        "Burley2020SobolRsg",
        "GaussianMultiPathGenerator",
        "GaussianSobolMultiPathGenerator",
        "FixedRateBond",
        "BondFunctions",
    }

    assert ql.__version__ == "1.43"
    assert {name for name in required if not hasattr(ql, name)} == set()


def test_quantlib_seeded_path_is_reproducible():
    first = _seeded_path(123456)
    second = _seeded_path(123456)

    assert len(first) == 31
    assert first == second
    assert first[0] == 100.0
