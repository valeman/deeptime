import functools

import sktime
from sktime.markov import TransitionCountEstimator

from sktime.markov.msm import MarkovStateModel, MaximumLikelihoodMSM
from sktime.markov.msm.augmented_msm import AugmentedMSM, AugmentedMSMEstimator
import numpy as np


class DoubleWellScenario(object):

    def __init__(self, sparse: bool, statdist_constraint: bool, count_mode: str):
        self._data = sktime.data.double_well_discrete()
        self._statdist = 1. * np.bincount(self.data.dtraj)
        self._statdist /= self._statdist.sum()
        count_model = TransitionCountEstimator(lagtime=self.lagtime, count_mode=count_mode, sparse=sparse) \
            .fit(self.data.dtraj).fetch_model()
        if statdist_constraint:
            count_model = count_model.submodel_largest(probability_constraint=self.stationary_distribution)
        else:
            count_model = count_model.submodel_largest()
        self._counts = count_model

    @property
    def counts(self):
        return self._counts

    @property
    def data(self):
        return self._data

    @property
    def stationary_distribution(self):
        return self._statdist

    @property
    def lagtime(self):
        return 10

    @property
    def n_states(self) -> int:
        """ Not actual number of states but number of connected ones. """
        return 66

    @property
    def selected_count_fraction(self) -> float:
        return 1.0


class DoubleWellScenarioMLMSM(DoubleWellScenario):

    def __init__(self, reversible, statdist_constraint, sparse, count_mode="sliding"):
        super().__init__(statdist_constraint=statdist_constraint, sparse=sparse, count_mode=count_mode)
        maxerr = 1e-12
        if statdist_constraint:
            est = MaximumLikelihoodMSM(reversible=reversible, maxerr=maxerr,
                                       stationary_distribution_constraint=self.stationary_distribution, sparse=sparse)
        else:
            est = MaximumLikelihoodMSM(reversible=reversible, maxerr=maxerr, sparse=sparse)
        est.fit(self.counts)
        self._msm = est.fetch_model()
        self._msm_estimator = est
        if not reversible:
            self._timescales = np.array([310.49376926, 8.48302712, 5.02649564])
        else:
            self._timescales = np.array([310.87, 8.5, 5.09])

    @property
    def msm(self) -> MarkovStateModel:
        return self._msm

    @property
    def msm_estimator(self) -> MaximumLikelihoodMSM:
        return self._msm_estimator

    @property
    def timescales(self):
        return self._timescales


class DoubleWellScenarioAMM(DoubleWellScenario):
    def __init__(self, sparse, count_mode="sliding"):
        super().__init__(statdist_constraint=False, sparse=sparse, count_mode=count_mode)
        amm_expectations = np.linspace(0.01, 2. * np.pi, 66).reshape(-1, 1) ** 0.5
        amm_m = np.array([1.9])
        amm_w = np.array([2.0])
        amm_sigmas = 1. / np.sqrt(2) / np.sqrt(amm_w)
        amm_sd = list(set(self.data.dtraj))
        amm_ftraj = amm_expectations[[amm_sd.index(d) for d in self.data.dtraj], :]
        est_amm = AugmentedMSMEstimator.estimator_from_feature_trajectories(self.data.dtraj, amm_ftraj,
                                                                            n_states=self.counts.n_states_full,
                                                                            m=amm_m, sigmas=amm_sigmas)
        amm = est_amm.fit(self.counts).fetch_model()
        self._msm = amm
        self._msm_estimator = est_amm
        self._timescales = np.array([364.])  # reference?

    @property
    def msm(self) -> AugmentedMSM:
        return self._msm

    @property
    def msm_estimator(self) -> AugmentedMSMEstimator:
        return self._msm_estimator

    @property
    def timescales(self):
        return self._timescales


@functools.lru_cache(maxsize=None)
def _make_reference_data(dataset: str, msm_type: str, reversible: bool, statdist_constraint: bool, sparse: bool,
                         count_mode: str):
    if dataset == "doublewell":
        if msm_type == "MLMSM":
            return DoubleWellScenarioMLMSM(reversible=reversible, statdist_constraint=statdist_constraint,
                                           sparse=sparse, count_mode=count_mode)
        elif msm_type == "AMM":
            return DoubleWellScenarioAMM(sparse=sparse, count_mode=count_mode)
