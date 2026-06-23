from app.analysis.rate_tests import (
    DecisionClass,
    benjamini_hochberg,
    classify_pairwise_result,
    compare_incident_rates,
    dispersion_status,
)


def test_compare_incident_rates_finds_lower_rate_with_exact_method():
    result = compare_incident_rates(
        count_a=8,
        exposure_a=30.0,
        count_b=28,
        exposure_b=30.0,
    )

    assert result.method == "exact_conditional_poisson"
    assert result.rate_a == 8 / 30.0
    assert result.rate_b == 28 / 30.0
    assert round(result.rate_ratio, 3) == 0.286
    assert result.p_value < 0.05
    assert result.ci_lower < result.rate_ratio < result.ci_upper


def test_compare_incident_rates_handles_zero_count_with_continuity_correction():
    result = compare_incident_rates(
        count_a=0,
        exposure_a=30.0,
        count_b=12,
        exposure_b=30.0,
    )

    assert result.used_continuity_correction is True
    assert result.rate_ratio < 0.1
    assert result.p_value < 0.05
    assert "continuity correction" in result.caveat_text


def test_dispersion_status_marks_high_variance_periods_as_overdispersed():
    status = dispersion_status([0, 0, 0, 12, 0, 12])

    assert status.status == "overdispersed"
    assert status.phi > 1.2


def test_dispersion_status_marks_short_series_as_insufficient_periods():
    status = dispersion_status([2])

    assert status.status == "insufficient_periods"
    assert status.phi is None


def test_quasi_poisson_adjustment_weakens_high_dispersion_significance():
    poisson = compare_incident_rates(
        count_a=8,
        exposure_a=30.0,
        count_b=28,
        exposure_b=30.0,
        overdispersion_phi=1.0,
    )
    adjusted = compare_incident_rates(
        count_a=8,
        exposure_a=30.0,
        count_b=28,
        exposure_b=30.0,
        overdispersion_phi=4.0,
    )

    assert poisson.method == "exact_conditional_poisson"
    assert adjusted.method == "quasi_poisson_log_rate_ratio"
    assert adjusted.p_value > poisson.p_value
    assert adjusted.ci_lower < poisson.ci_lower
    assert adjusted.ci_upper > poisson.ci_upper


def test_benjamini_hochberg_adjusts_p_values_monotonically():
    adjusted = benjamini_hochberg([0.01, 0.04, 0.03])

    assert adjusted == [0.03, 0.04, 0.04]


def test_classify_requires_statistical_and_practical_thresholds():
    statistically_lower = classify_pairwise_result(
        rate_ratio=0.5,
        adjusted_p_value=0.01,
        minimum_data_met=True,
        model_warning=False,
    )
    weak_practical_difference = classify_pairwise_result(
        rate_ratio=0.9,
        adjusted_p_value=0.01,
        minimum_data_met=True,
        model_warning=False,
    )
    weak_statistical_difference = classify_pairwise_result(
        rate_ratio=0.5,
        adjusted_p_value=0.20,
        minimum_data_met=True,
        model_warning=False,
    )

    assert statistically_lower == DecisionClass.STATISTICALLY_LOWER
    assert weak_practical_difference == DecisionClass.NOT_STATISTICALLY_CLEAR
    assert weak_statistical_difference == DecisionClass.NOT_STATISTICALLY_CLEAR
