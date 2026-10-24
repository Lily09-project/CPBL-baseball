from __future__ import annotations

import math

import pytest

from src.analytics import bayes


def test_beta_cdf_matches_closed_forms() -> None:
    for x in (0.1, 0.25, 0.5, 0.9):
        assert bayes.beta_cdf(x, 1, 1) == pytest.approx(x, abs=1e-10)
        assert bayes.beta_cdf(x, 2, 2) == pytest.approx(3 * x**2 - 2 * x**3, abs=1e-10)
        assert bayes.beta_cdf(x, 1, 3) == pytest.approx(1 - (1 - x) ** 3, abs=1e-10)


def test_beta_cdf_edges_and_validation() -> None:
    assert bayes.beta_cdf(0, 2, 3) == 0.0
    assert bayes.beta_cdf(1, 2, 3) == 1.0
    with pytest.raises(ValueError):
        bayes.beta_cdf(0.5, 0, 1)


def test_beta_ppf_inverts_cdf() -> None:
    for a, b in ((2.5, 7.0), (48.7, 102.6), (0.8, 0.8)):
        for p in (0.1, 0.5, 0.9):
            x = bayes.beta_ppf(p, a, b)
            assert bayes.beta_cdf(x, a, b) == pytest.approx(p, abs=1e-8)
    assert bayes.beta_ppf(0, 2, 2) == 0.0
    assert bayes.beta_ppf(1, 2, 2) == 1.0
    with pytest.raises(ValueError):
        bayes.beta_ppf(1.5, 2, 2)


def test_prior_is_finite_and_centred_on_league_rate() -> None:
    successes = [30, 45, 60, 25, 80, 33]
    trials = [100, 150, 180, 90, 220, 110]
    prior = bayes.fit_beta_prior(successes, trials, min_trials=50)
    assert prior.alpha > 0 and prior.beta > 0
    assert math.isfinite(prior.alpha) and math.isfinite(prior.beta)
    assert prior.mean == pytest.approx(sum(successes) / sum(trials), rel=1e-9)


def test_prior_falls_back_to_strong_prior_when_no_talent_spread() -> None:
    # Every player has exactly the league rate: all variance is noise.
    prior = bayes.fit_beta_prior([30, 60, 90], [100, 200, 300], min_trials=1)
    assert prior.concentration == bayes.MAX_CONCENTRATION


def test_prior_with_single_player_and_without_players() -> None:
    prior = bayes.fit_beta_prior([10], [40], min_trials=1)
    assert prior.concentration == bayes.MIN_CONCENTRATION
    with pytest.raises(ValueError):
        bayes.fit_beta_prior([1], [5], min_trials=50)


def test_posterior_mean_lies_between_raw_rate_and_league_mean() -> None:
    prior = bayes.BetaPrior(alpha=32.0, beta=68.0)  # league mean 0.32
    for successes, trials in ((9, 15), (2, 15), (150, 400), (100, 400)):
        post = bayes.posterior(successes, trials, prior)
        raw = successes / trials
        assert min(raw, prior.mean) <= post.mean <= max(raw, prior.mean)
        assert post.low <= post.mean <= post.high


def test_interval_narrows_with_more_trials() -> None:
    prior = bayes.BetaPrior(alpha=32.0, beta=68.0)
    widths = [
        bayes.posterior(round(0.35 * n), n, prior).high - bayes.posterior(round(0.35 * n), n, prior).low
        for n in (10, 50, 200, 600)
    ]
    assert widths == sorted(widths, reverse=True)


def test_zero_trials_returns_the_prior() -> None:
    prior = bayes.BetaPrior(alpha=32.0, beta=68.0)
    post = bayes.posterior(0, 0, prior)
    assert post.mean == pytest.approx(prior.mean)
    assert post.raw is None


def test_posterior_rejects_impossible_counts() -> None:
    prior = bayes.BetaPrior(alpha=2.0, beta=2.0)
    with pytest.raises(ValueError):
        bayes.posterior(5, 3, prior)


def test_shrink_all_returns_one_posterior_per_player() -> None:
    prior, posts = bayes.shrink_all([30, 3, 70], [100, 10, 200], min_trials_for_prior=50)
    assert len(posts) == 3
    assert prior.alpha > 0
