"""FINDING's training procedure (Yu et al., CIKM '23), over the user tower.

Re-implemented from the paper and the reference code (resources/FINDING,
`model/general/trainer/federated_group.py`), mechanism for mechanism:

- **Groups.** One global model and `groups` group models. Readers are
  clustered by the global model's user vectors (KMeans, n_init=10).
- **A round.** Each group samples its share of `users_per_round` readers
  (proportional to its size), takes every training sample of those readers
  as one batch, and steps its own model. The global model then steps on
  the sample-weighted average of the groups' gradients. Clients are
  *simulated*: this is a replay of logs on one machine, not federation.
- **Fine-grained interpolation.** Every `interpolate_every` rounds each
  group model is pulled toward the global one, layer by layer, with
  personalisation coefficient p(r, i) = (1 - alpha^-r) * ((i + 1) / n)^beta: little
  personal early in training and in shallow layers, more later and deeper.
  Adam's moment estimates are interpolated the same way, as the paper's
  code does.
- **Dynamic clustering.** Every `cluster_every` rounds readers are
  re-clustered. New labels are matched to old ones by a Hungarian
  assignment on the old→new transfer counts, then each new group model
  becomes the mix of old group models its readers came from (the transfer
  matrix, column-normalised) - so a group's model moves with its readers.
- **Evaluation.** A reader is assigned a group by the global model's vector
  and scored by that group's model.

Serving is centralised (JustNews computes every reader's vector offline and
ranks by a dot product); nothing here describes, or makes, a federated
production system.
"""

from __future__ import annotations

import copy
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt
import torch
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from torch import nn

from jnfinding import metrics
from jnfinding.data import Behaviours, Samples
from jnfinding.model import UserTower


@dataclass(frozen=True, slots=True)
class Config:
    """The paper's defaults (fednewsrec/parameters.py)."""

    groups: int = 8
    rounds: int = 12000
    users_per_round: int = 50
    interpolate_every: int = 10
    cluster_every: int = 100
    alpha: float = 1.0003
    beta: float = 0.5
    learning_rate: float = 1e-4
    validate_every: int = 600
    patience: int = 3
    seed: int = 0
    history: int = 50


def personalisation(round_: int, depth: int, depths: int, *, alpha: float, beta: float) -> float:
    """p(r, i) = (1 - alpha^-r) * ((i + 1) / n)^beta."""
    return (1.0 - alpha ** (-round_)) * ((depth + 1) / depths) ** beta


def maximise_diagonal(transfer: npt.NDArray[np.int64]) -> dict[int, int]:
    """Relabels new clusters to keep as many readers in "the same" group as
    possible: a map from each new label to the old label it takes over."""
    rows, columns = transfer.shape
    if rows > columns:
        transfer = transfer[:columns]
    elif rows < columns:
        transfer = np.pad(transfer, [(0, columns - rows), (0, 0)])
    _, assigned = linear_sum_assignment(transfer, maximize=True)
    return {int(new): old for old, new in enumerate(assigned)}


def _batch(
    news: torch.Tensor, history: npt.NDArray[np.int64], device: torch.device
) -> tuple[torch.Tensor, torch.Tensor]:
    ids = torch.as_tensor(history, device=device)
    return news[ids], ids != 0


@torch.no_grad()
def user_vectors(
    model: UserTower, news: torch.Tensor, behaviours: Behaviours, device: torch.device
) -> torch.Tensor:
    model.eval()
    out = []
    for start in range(0, len(behaviours), 4096):
        history, mask = _batch(news, behaviours.history[start : start + 4096], device)
        out.append(model.user(history, mask))
    model.train()
    return torch.cat(out)


@torch.no_grad()
def score_impressions(
    models: dict[int, UserTower],
    groups: npt.NDArray[np.int64],
    news: torch.Tensor,
    behaviours: Behaviours,
    device: torch.device,
) -> metrics.Report:
    """Every reader-day scored by the model of its group: its day's clicked
    candidates against the not-clicked ones, as FINDING's evaluation does."""
    impressions: list[tuple[list[int], list[float]]] = []
    for group_index in np.unique(groups).tolist():
        model = models[group_index]
        model.eval()
        rows = np.flatnonzero(groups == group_index)
        adapted = model.news(news)
        for start in range(0, len(rows), 4096):
            chunk = rows[start : start + 4096]
            history, mask = _batch(news, behaviours.history[chunk], device)
            users = model.user(history, mask)
            for row, user in zip(chunk.tolist(), users, strict=True):
                positives, negatives = behaviours.positives[row], behaviours.negatives[row]
                ids = torch.as_tensor(positives + negatives, device=device)
                impressions.append(
                    ([1] * len(positives) + [0] * len(negatives), (adapted[ids] @ user).tolist())
                )
        model.train()
    return metrics.evaluate(impressions)


@dataclass
class _Group:
    model: UserTower
    optimiser: torch.optim.Adam


@dataclass
class Finding:
    config: Config
    news: torch.Tensor  # (N, D), frozen
    train: Behaviours
    samples: Samples
    device: torch.device
    global_model: UserTower = field(init=False)
    global_optimiser: torch.optim.Adam = field(init=False)
    groups: list[_Group] = field(init=False)
    kmeans: KMeans = field(init=False)
    relabel: dict[int, int] = field(init=False, default_factory=dict)
    assignment: npt.NDArray[np.int64] = field(init=False)
    log: list[str] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        torch.manual_seed(self.config.seed)
        self.rng = random.Random(self.config.seed)
        self.global_model = UserTower().to(self.device)
        self.global_optimiser = torch.optim.Adam(
            self.global_model.parameters(), lr=self.config.learning_rate
        )
        self.groups = []
        for _ in range(self.config.groups):
            model = copy.deepcopy(self.global_model)
            self.groups.append(
                _Group(model, torch.optim.Adam(model.parameters(), lr=self.config.learning_rate))
            )
        self.samples_by_row: dict[int, list[int]] = defaultdict(list)
        for index, row in enumerate(self.samples.row.tolist()):
            self.samples_by_row[row].append(index)
        self.rows_with_samples = sorted(self.samples_by_row)
        self.criterion = nn.CrossEntropyLoss()
        self.cluster(initial=True)

    # --- clustering ---------------------------------------------------------

    def _groups_of(self, vectors: npt.NDArray[np.float32]) -> npt.NDArray[np.int64]:
        labels = self.kmeans.predict(vectors)
        if not self.relabel:
            return labels.astype(np.int64)
        return np.array([self.relabel[int(label)] for label in labels], dtype=np.int64)

    @torch.no_grad()
    def cluster(self, *, initial: bool = False) -> None:
        vectors = user_vectors(self.global_model, self.news, self.train, self.device).cpu().numpy()
        kmeans = KMeans(n_clusters=self.config.groups, n_init=10, random_state=self.config.seed)
        labels = kmeans.fit_predict(vectors).astype(np.int64)
        self.kmeans = kmeans
        if initial:
            self.relabel = {}
            self.assignment = labels
            return
        k = self.config.groups
        transfer = np.zeros((k, k), dtype=np.int64)
        np.add.at(transfer, (self.assignment, labels), 1)
        self.relabel = maximise_diagonal(transfer)
        relabelled = np.array([self.relabel[int(label)] for label in labels], dtype=np.int64)
        transfer = np.zeros((k, k), dtype=np.float64)
        np.add.at(transfer, (self.assignment, relabelled), 1)
        totals = transfer.sum(axis=0)
        # mix[new, old]: the share of the new group's readers from each old one.
        mix = np.where(totals > 0, transfer / np.maximum(totals, 1), 0).T
        self._remix(mix, keep=totals == 0)
        self.assignment = relabelled

    def _remix(self, mix: npt.NDArray[np.float64], keep: npt.NDArray[np.bool_]) -> None:
        """Each new group's parameters and Adam moments become the mix of the
        old groups' - a group with no readers keeps its own."""
        old = [[p.detach().clone() for p in group.model.parameters()] for group in self.groups]
        old_state = [self._moments(group) for group in self.groups]
        for new, group in enumerate(self.groups):
            if keep[new]:
                continue
            weights = mix[new]
            for index, parameter in enumerate(group.model.parameters()):
                parameter.data.copy_(sum(float(w) * old[g][index] for g, w in enumerate(weights)))
            for index, parameter in enumerate(group.model.parameters()):
                state = group.optimiser.state.get(parameter)
                if not state or any(moments[index] is None for moments in old_state):
                    continue
                for key in ("exp_avg", "exp_avg_sq"):
                    state[key].copy_(
                        sum(float(w) * old_state[g][index][key] for g, w in enumerate(weights))
                    )

    @staticmethod
    def _moments(group: _Group) -> list[dict[str, torch.Tensor] | None]:
        out: list[dict[str, torch.Tensor] | None] = []
        for parameter in group.model.parameters():
            state = group.optimiser.state.get(parameter)
            out.append(
                {key: state[key].clone() for key in ("exp_avg", "exp_avg_sq")} if state else None
            )
        return out

    # --- interpolation ------------------------------------------------------

    @torch.no_grad()
    def interpolate(self, round_: int) -> dict[str, float]:
        depths = len(UserTower.LAYERS)
        coefficients: dict[str, float] = {}
        global_named = dict(self.global_model.named_parameters())
        for group in self.groups:
            for name, parameter in group.model.named_parameters():
                depth = group.model.layer_of(name)
                p = personalisation(
                    round_, depth, depths, alpha=self.config.alpha, beta=self.config.beta
                )
                coefficients[UserTower.LAYERS[depth]] = p
                shared = global_named[name]
                parameter.mul_(p).add_(shared, alpha=1.0 - p)
                local_state = group.optimiser.state.get(parameter)
                global_state = self.global_optimiser.state.get(shared)
                if local_state and global_state:
                    for key in ("exp_avg", "exp_avg_sq"):
                        local_state[key].mul_(p).add_(global_state[key], alpha=1.0 - p)
        return coefficients

    # --- training -----------------------------------------------------------

    def _loss(self, model: UserTower, sample_indexes: list[int]) -> torch.Tensor:
        rows = self.samples.row[sample_indexes]
        history, mask = _batch(self.news, self.train.history[rows], self.device)
        candidates = self.news[
            torch.as_tensor(self.samples.candidates[sample_indexes], device=self.device)
        ]
        logits = model(history, mask, candidates)
        target = torch.zeros(len(sample_indexes), dtype=torch.long, device=self.device)
        return self.criterion(logits, target)

    def round(self, round_: int) -> float:
        if round_ and round_ % self.config.interpolate_every == 0:
            self.interpolate(round_)
        if round_ and round_ % self.config.cluster_every == 0:
            self.cluster()

        by_group: dict[int, list[int]] = defaultdict(list)
        for row in self.rows_with_samples:
            by_group[int(self.assignment[row])].append(row)
        total_rows = len(self.rows_with_samples)

        gradients: list[tuple[int, list[torch.Tensor]]] = []
        loss_sum, sample_sum = 0.0, 0
        for group_index, rows in by_group.items():
            group = self.groups[group_index]
            take = math.ceil(self.config.users_per_round * len(rows) / total_rows)
            chosen = self.rng.sample(rows, min(take, len(rows)))
            sample_indexes = [i for row in chosen for i in self.samples_by_row[row]]
            loss = self._loss(group.model, sample_indexes)
            group.optimiser.zero_grad()
            loss.backward()
            group.optimiser.step()
            gradients.append(
                (len(sample_indexes), [p.grad.detach().clone() for p in group.model.parameters()])  # type: ignore[union-attr]
            )
            loss_sum += float(loss) * len(sample_indexes)
            sample_sum += len(sample_indexes)

        weight_total = sum(n for n, _ in gradients)
        for index, parameter in enumerate(self.global_model.parameters()):
            parameter.grad = sum((n / weight_total) * grads[index] for n, grads in gradients)  # type: ignore[assignment]
        self.global_optimiser.step()
        self.global_optimiser.zero_grad()
        return loss_sum / max(sample_sum, 1)

    # --- evaluation ---------------------------------------------------------

    @torch.no_grad()
    def evaluate(self, behaviours: Behaviours, *, personal: bool = True) -> metrics.Report:
        """Each reader scored by their group's model (`personal`), or every
        reader by the global model."""
        if not personal:
            groups = np.zeros(len(behaviours), dtype=np.int64)
            return score_impressions(
                {0: self.global_model}, groups, self.news, behaviours, self.device
            )
        vectors = user_vectors(self.global_model, self.news, behaviours, self.device)
        groups = self._groups_of(vectors.cpu().numpy())
        models = {index: group.model for index, group in enumerate(self.groups)}
        return score_impressions(models, groups, self.news, behaviours, self.device)

    def state(self) -> dict[str, Any]:
        return {
            "global": copy.deepcopy(self.global_model.state_dict()),
            "groups": [copy.deepcopy(group.model.state_dict()) for group in self.groups],
            "centroids": self.kmeans.cluster_centers_.copy(),
            "relabel": dict(self.relabel),
            "config": self.config,
        }


def train_centralised(
    news: torch.Tensor,
    train: Behaviours,
    samples: Samples,
    val: Behaviours,
    device: torch.device,
    *,
    epochs: int = 15,
    batch_size: int = 128,
    learning_rate: float = 1e-4,
    patience: int = 3,
    seed: int = 0,
) -> tuple[UserTower, metrics.Report, list[str]]:
    """The same tower trained the ordinary way - FINDING's CentralizedModel
    path, the paper's non-federated baseline: minibatches over every
    sample, validated each epoch, stopped early on validation AUC."""
    torch.manual_seed(seed)
    model = UserTower().to(device)
    optimiser = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.CrossEntropyLoss()
    best: tuple[float, dict[str, Any], metrics.Report] | None = None
    waited = 0
    log: list[str] = []
    order = np.random.default_rng(seed)
    everyone = np.zeros(len(val), dtype=np.int64)
    for epoch in range(epochs):
        permutation = order.permutation(len(samples))
        total = 0.0
        for start in range(0, len(permutation), batch_size):
            batch = permutation[start : start + batch_size]
            history, mask = _batch(news, train.history[samples.row[batch]], device)
            candidates = news[torch.as_tensor(samples.candidates[batch], device=device)]
            logits = model(history, mask, candidates)
            loss = criterion(logits, torch.zeros(len(batch), dtype=torch.long, device=device))
            optimiser.zero_grad()
            loss.backward()
            optimiser.step()
            total += float(loss) * len(batch)
        report = score_impressions({0: model}, everyone, news, val, device)
        log.append(f"epoch {epoch} loss {total / len(samples):.4f} val {report.as_dict()}")
        if best is None or report.auc > best[0]:
            best = (report.auc, copy.deepcopy(model.state_dict()), report)
            waited = 0
        else:
            waited += 1
            if waited >= patience:
                break
    assert best is not None
    model.load_state_dict(best[1])
    return model, best[2], log
