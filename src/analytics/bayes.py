"""Empirical-Bayes "true talent" estimates for rate statistics.

Each rate (on-base, strikeout, walk, home-run rate) is modelled as a
binomial outcome with a Beta prior fitted to the league by the method of
moments. The posterior shrinks small samples toward the league mean, which
is what separates a hot 40-plate-appearance streak from a real skill.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

MIN_CONCENTRATION = 2.0
MAX_CONCENTRATION = 5000.0
CREDIBLE_LEVEL = 0.80


@dataclass(frozen=True)
class BetaPrior:
    alpha: float
    beta: float

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def concentration(self) -> float:
        """Prior strength expressed as an equivalent number of trials."""
        return self.alpha + self.beta


@dataclass(frozen=True)
class Posterior:
    mean: float
    low: float
    high: float
    raw: float | None
    trials: float


def fit_beta_prior(
    successes: Sequence[float],
    trials: Sequence[float],
    min_trials: float = 1.0,
) -> BetaPrior:
    """Fit a Beta prior to observed rates, removing binomial sampling noise.

    The observed variance of rates is the true talent variance plus the
    average binomial noise mu(1-mu)/n. Subtracting the noise term keeps the
    prior from being too wide when most players have few trials.
    """
    pairs = [(float(s), float(n)) for s, n in zip(successes, trials) if float(n) >= min_trials]
    if not pairs:
        raise ValueError("at least one player with enough trials is required to fit a prior")
    total_s = sum(s for s, _ in pairs)
    total_n = sum(n for _, n in pairs)
    mu = min(max(total_s / total_n, 1e-6), 1 - 1e-6)
    if len(pairs) == 1:
        concentration = MIN_CONCENTRATION
    else:
        rates = [s / n for s, n in pairs]
        mean_rate = sum(rates) / len(rates)
        observed_var = sum((r - mean_rate) ** 2 for r in rates) / (len(rates) - 1)
        noise_var = mu * (1 - mu) * sum(1.0 / n for _, n in pairs) / len(pairs)
        talent_var = observed_var - noise_var
        if talent_var <= 0:
            concentration = MAX_CONCENTRATION
        else:
            concentration = mu * (1 - mu) / talent_var - 1.0
    concentration = min(max(concentration, MIN_CONCENTRATION), MAX_CONCENTRATION)
    return BetaPrior(alpha=mu * concentration, beta=(1 - mu) * concentration)


def posterior(successes: float, trials: float, prior: BetaPrior, level: float = CREDIBLE_LEVEL) -> Posterior:
    """Return the posterior mean and equal-tailed credible interval."""
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("successes must lie between 0 and trials")
    a = prior.alpha + successes
    b = prior.beta + (trials - successes)
    tail = (1 - level) / 2
    return Posterior(
        mean=a / (a + b),
        low=beta_ppf(tail, a, b),
        high=beta_ppf(1 - tail, a, b),
        raw=successes / trials if trials > 0 else None,
        trials=trials,
    )


def shrink_all(
    successes: Iterable[float],
    trials: Iterable[float],
    min_trials_for_prior: float,
) -> tuple[BetaPrior, list[Posterior]]:
    s_list = [float(s) for s in successes]
    n_list = [float(n) for n in trials]
    prior = fit_beta_prior(s_list, n_list, min_trials=min_trials_for_prior)
    return prior, [posterior(s, n, prior) for s, n in zip(s_list, n_list)]


def _beta_continued_fraction(x: float, a: float, b: float) -> float:
    """Lentz's continued fraction for the incomplete beta function."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 500):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h


def beta_cdf(x: float, a: float, b: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if a <= 0 or b <= 0:
        raise ValueError("beta parameters must be positive")
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    log_front = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    front = math.exp(log_front)
    if x < (a + 1) / (a + b + 2):
        return front * _beta_continued_fraction(x, a, b) / a
    return 1.0 - front * _beta_continued_fraction(1.0 - x, b, a) / b


def beta_ppf(p: float, a: float, b: float) -> float:
    """Inverse of :func:`beta_cdf` by bisection (monotone, so always converges)."""
    if not 0 <= p <= 1:
        raise ValueError("p must be a probability")
    if p == 0:
        return 0.0
    if p == 1:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if beta_cdf(mid, a, b) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12:
            break
    return (lo + hi) / 2
