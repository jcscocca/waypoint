# Statistical Route And Place Comparison

## What The App Can Claim

The app can say that one route or site has a statistically lower reported-incident rate
than another route or site for the selected date range, geography, radius, offense filter,
and method. This claim is scoped to the public SPD incident records and the exact analysis
inputs used for the comparison.

The app cannot say that a route is safe, unsafe, dangerous, risk-free, or that a route prevents crime.

## Why Raw Counts Are Not Enough

Raw incident counts do not account for route length, buffer size, or analysis period. A
longer route corridor or larger place buffer can include more incidents simply because it
covers more area. A longer analysis period can include more incidents simply because it has
more days. The app compares exposure-adjusted rates so that each option is evaluated against
the amount of area and time included in that option's analysis.

## Exposure

Place exposure is the selected place buffer area in square kilometers multiplied by the
number of analysis days. Route exposure is the selected route corridor area in square
kilometers multiplied by the number of analysis days.

For route comparisons, the corridor area is calculated as:

```text
route_corridor_area_square_km = (route_length_km * 2 * radius_km) + pi * radius_km^2
```

The exposure unit for both place and route comparisons is square-kilometer-days.

## Incident Inclusion

An incident is included only when it has coordinates, falls within the selected date range,
matches the selected offense filters, and falls inside the selected place buffer or route
corridor. Incidents outside the selected geography, dates, or offense filters are excluded
from the count and rate calculation.

## Statistical Test

The default test is an exact conditional Poisson comparison of exposure-adjusted incident
rates. If period counts are overdispersed, the app uses a quasi-Poisson log-rate-ratio
adjustment so the uncertainty estimate reflects extra variation in the observed counts.

For the exact conditional Poisson test, the two incident counts are conditioned on their
combined total. The expected share for option A is:

```text
expected_share_a = exposure_a / (exposure_a + exposure_b)
```

The p-value is two-sided. It sums binomial outcomes whose probability is less than or equal
to the probability of the observed count for option A. Direction is not chosen after seeing
the p-value; direction comes from the exposure-adjusted rate ratio.

The reported rate ratio is:

```text
rate_ratio = (count_a / exposure_a) / (count_b / exposure_b)
```

When either count is zero, the app uses a 0.5 continuity correction for the log-rate-ratio
and confidence interval calculation. The exact conditional Poisson p-value still uses the
original observed counts. The result includes a caveat saying the correction was used.

## Overdispersion Guard

The app estimates overdispersion from monthly incident-count bins. For each pairwise
comparison, it combines the candidate option's monthly counts with the other option's
monthly counts, then calculates:

```text
phi = observed_variance / observed_mean
```

The overdispersion status is:

- `poisson_ok` when `phi <= 1.2`
- `overdispersed` when `phi > 1.2`
- `insufficient_periods` when fewer than two aligned monthly bins are available

When `phi <= 1.2`, the exact conditional Poisson p-value is used as the primary pairwise
p-value. When `phi > 1.2`, the app does not rely on the unadjusted Poisson p-value. It uses
a quasi-Poisson log-rate-ratio adjustment:

```text
se_log_rr = sqrt(phi * (1 / safe_count_a + 1 / safe_count_b))
z = abs(log(rate_ratio)) / se_log_rr
```

The quasi-Poisson p-value is calculated from that z statistic, and the confidence interval
is widened by the same adjusted standard error.

This guard can make a large raw-count difference fail the recommendation threshold when the
observed incidents are clustered in only one or two monthly bins. For example, `1` incident
near one place and `33` near another place can be statistically clear when counts are spread
across the analysis window, but not statistically clear when the same counts are temporally
lumpy enough to produce high `phi`.

## Multiple Comparisons

When more than two options are compared, the app applies a Benjamini-Hochberg adjustment to
control the false discovery rate across pairwise comparisons. An option is recommended only
when it passes the conservative threshold against every relevant alternative.

The candidate option is the option with the lowest exposure-adjusted incident rate. The app
compares that candidate against every other option. If any pair fails the recommendation
threshold, the overall comparison is not a lower-incident recommendation.

## Recommendation Threshold

- adjusted p-value below 0.05
- rate ratio less than or equal to 0.80
- at least 30 analysis days
- positive exposure for every compared option
- combined incident count of at least 10
- no unhandled model warning

## Operational Decision Rules

The app applies the following gates before it allows lower-incident recommendation wording:

1. At least two options must be present.
2. All compared options must use positive exposure.
3. The analysis window must contain at least 30 days.
4. Each pairwise comparison must have at least 10 combined incidents.
5. The candidate must have the lowest exposure-adjusted incident rate.
6. Pairwise p-values are adjusted with Benjamini-Hochberg when more than one pair is tested.
7. Every pair involving the candidate must have adjusted p-value below `0.05`.
8. Every pair involving the candidate must have rate ratio less than or equal to `0.80`.
9. Any `insufficient_periods` overdispersion status prevents a recommendation and returns a
   model-warning decision.

Minimum-data failures return `insufficient_data`. A valid test that does not clear the
statistical and practical thresholds returns `not_statistically_clear`. A comparison with
an unhandled model warning returns `model_warning`.

## Dashboard Modes

Overview is the public summary view. It shows the reader-facing summary text, the decision
class, exposure-adjusted rates, and a short caveat that keeps the claim tied to reported
incidents and the selected inputs.

Analytical is the audit view. It shows the supporting counts, exposure, rate ratio,
confidence interval, p-values, method, overdispersion status, minimum-data status, filters,
and full caveats.

Both modes read the same backend result. They differ only in how much of the result they
show.

## Decision Classes

`statistically_lower` means one compared option has a statistically lower reported-incident
rate under the selected filters and threshold.

`not_statistically_clear` means the comparison does not identify a statistically clear
lower reported-incident rate.

`insufficient_data` means the selected inputs do not meet the minimum data requirements.

`model_warning` means the model produced a warning that should prevent a recommendation
claim.

## Analytical Output Fields

The analytical response and Tableau statistical-comparison export include the fields needed
to audit the decision:

- `method`: `exact_conditional_poisson`, `quasi_poisson_log_rate_ratio`, or
  `not_tested_minimum_data`
- `incident_count_a` and `incident_count_b`
- `exposure_a` and `exposure_b`
- `rate_a`, `rate_b`, and `rate_ratio`
- `ci_lower` and `ci_upper`
- `p_value` and `adjusted_p_value`
- `overdispersion_phi` and `overdispersion_status`
- `minimum_data_status`
- `decision_class`, `winner_option_id`, and `winner_label`
- `caveat_text`

These fields are intended to make the public summary traceable without requiring a code
review.

## Automated Test Coverage

The statistical implementation is covered by focused unit, service, API, persistence, and
export tests.

`tests/test_analysis_rate_tests.py` covers the statistical core:

- exact conditional Poisson comparisons
- zero-count continuity correction
- invalid count, exposure, and overdispersion inputs
- overdispersion detection
- quasi-Poisson adjustment widening uncertainty and weakening significance
- Benjamini-Hochberg p-value adjustment
- decision classification thresholds

`tests/test_statistical_comparison_service.py` covers comparison assembly:

- recommending only when all candidate pairwise comparisons pass
- preserving alternatives when evidence is not statistically clear
- blocking short date ranges
- handling non-positive exposure without raising
- counting incidents for site options and returning/persisting the analytical payload
- monthly period-count alignment, including zero-count months

API, migration, route, and export tests cover response shape and downstream auditability:

- `tests/test_statistical_comparison_api.py`
- `tests/test_route_alternatives_api.py`
- `tests/test_route_models_migration.py`
- `tests/test_statistical_comparison_exports.py`

The tests intentionally avoid live Socrata network access. Live-data ingestion is validated
separately from the statistical decision rules so that statistical tests remain deterministic.
