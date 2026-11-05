"""Sampling weights always define a finite probability distribution."""

import math

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from src.modules.behavior.engine import softmax_probabilities


@given(
    st.dictionaries(
        st.sampled_from(["text", "voice", "ignore"]),
        st.floats(min_value=-1e308, max_value=1e308, allow_nan=False),
        min_size=1,
    ),
    st.floats(min_value=0.1, max_value=10, allow_nan=False),
)
@example({"text": 1e-216}, 0.5)
@example({"text": 1e308, "voice": 1e308}, 0.1)
def test_probabilities_are_normalized_and_negative_weights_cannot_win(weights, temperature):
    probabilities = softmax_probabilities(weights, temperature)
    assert probabilities.keys() == weights.keys()
    assert all(math.isfinite(value) and 0 <= value <= 1 for value in probabilities.values())
    if any(value > 0 for value in weights.values()):
        assert sum(probabilities.values()) == pytest.approx(1.0)
    else:
        assert not any(probabilities.values())
    assert all(probabilities[key] == 0 for key, value in weights.items() if value <= 0)
