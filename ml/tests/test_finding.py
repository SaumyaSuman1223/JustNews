"""FINDING's mechanisms, re-implemented (jnfinding/trainer.py), against
values worked out by hand and the properties the paper states."""

from __future__ import annotations

import numpy as np
import pytest
import torch
from jnfinding import trainer
from jnfinding.data import Behaviours, training_samples
from jnfinding.model import UserTower


class TestPersonalisation:
    def test_starts_at_zero(self) -> None:
        assert trainer.personalisation(0, 2, 3, alpha=1.0003, beta=0.5) == 0.0

    def test_matches_the_formula(self) -> None:
        # (1 - 1.0003^-3000) * ((1 + 1) / 3)^0.5
        expected = (1 - 1.0003**-3000) * (2 / 3) ** 0.5
        assert trainer.personalisation(3000, 1, 3, alpha=1.0003, beta=0.5) == pytest.approx(
            expected
        )

    def test_deeper_layers_and_later_rounds_stay_more_personal(self) -> None:
        early = trainer.personalisation(100, 2, 3, alpha=1.0003, beta=0.5)
        late = trainer.personalisation(5000, 2, 3, alpha=1.0003, beta=0.5)
        shallow = trainer.personalisation(5000, 0, 3, alpha=1.0003, beta=0.5)
        assert early < late
        assert shallow < late


class TestMaximiseDiagonal:
    def test_relabels_to_keep_readers_in_place(self) -> None:
        # Old group 0's readers all went to new label 1, and old 1's to new 0.
        transfer = np.array([[0, 5], [4, 0]])
        assert trainer.maximise_diagonal(transfer) == {1: 0, 0: 1}

    def test_identity_when_nothing_moved(self) -> None:
        transfer = np.diag([3, 2, 7])
        assert trainer.maximise_diagonal(transfer) == {0: 0, 1: 1, 2: 2}


class TestUserTower:
    def test_padding_does_not_change_the_user_vector(self) -> None:
        torch.manual_seed(0)
        tower = UserTower(dim=24, heads=4, query_dim=8, dropout=0.0).eval()
        history = torch.randn(1, 3, 24)
        mask = torch.tensor([[True, True, True]])
        padded = torch.cat([torch.zeros(1, 2, 24), history], dim=1)
        padded_mask = torch.tensor([[False, False, True, True, True]])
        assert torch.allclose(tower.user(history, mask), tower.user(padded, padded_mask), atol=1e-5)

    def test_an_empty_history_is_finite(self) -> None:
        tower = UserTower(dim=24, heads=4, query_dim=8, dropout=0.0).eval()
        vector = tower.user(torch.zeros(1, 4, 24), torch.zeros(1, 4, dtype=torch.bool))
        assert torch.isfinite(vector).all()

    def test_serving_vector_ranks_raw_vectors_as_the_model_does(self) -> None:
        """u · (W c + b) and (Wᵀ u) · c differ by u · b, the same for every
        candidate - so the order is the same."""
        torch.manual_seed(1)
        tower = UserTower(dim=24, heads=4, query_dim=8, dropout=0.0).eval()
        with torch.no_grad():
            tower.news_adapter.weight.add_(0.1 * torch.randn(24, 24))
            tower.news_adapter.bias.add_(0.1 * torch.randn(24))
        history, mask = torch.randn(1, 5, 24), torch.ones(1, 5, dtype=torch.bool)
        candidates = torch.randn(1, 30, 24)
        model_scores = tower(history, mask, candidates)[0]
        served = candidates[0] @ tower.serving_vector(history, mask)[0]
        assert torch.equal(torch.argsort(model_scores), torch.argsort(served))


def _toy(readers: int = 40, news: int = 60) -> tuple[Behaviours, torch.Tensor]:
    rng = np.random.default_rng(0)
    history = rng.integers(1, news, size=(readers, 6))
    history[:, :2] = 0  # left padding
    positives = [[int(rng.integers(1, news))] for _ in range(readers)]
    negatives = [[int(x) for x in rng.integers(1, news, size=8)] for _ in range(readers)]
    behaviours = Behaviours(
        user=np.arange(readers), history=history, positives=positives, negatives=negatives
    )
    vectors = torch.nn.functional.normalize(torch.randn(news, 384), dim=1)
    vectors[0] = 0
    return behaviours, vectors


class TestTrainer:
    def test_rounds_train_every_group_and_the_global_model(self) -> None:
        behaviours, news = _toy()
        samples = training_samples(behaviours, len(news), k=4)
        config = trainer.Config(groups=3, users_per_round=12, interpolate_every=2, cluster_every=3)
        finding = trainer.Finding(config, news, behaviours, samples, torch.device("cpu"))
        before = [p.clone() for p in finding.global_model.parameters()]
        for round_ in range(7):
            loss = finding.round(round_)
            assert np.isfinite(loss)
        after = list(finding.global_model.parameters())
        assert any(not torch.equal(a, b) for a, b in zip(before, after, strict=True))
        report = finding.evaluate(behaviours)
        assert 0.0 <= report.auc <= 1.0 and report.impressions == len(behaviours)

    def test_interpolation_at_p_zero_is_the_global_model(self) -> None:
        behaviours, news = _toy()
        samples = training_samples(behaviours, len(news), k=4)
        finding = trainer.Finding(
            trainer.Config(groups=2), news, behaviours, samples, torch.device("cpu")
        )
        finding.round(1)
        finding.interpolate(0)  # p(0, i) = 0 for every layer
        for group in finding.groups:
            for mine, shared in zip(
                group.model.parameters(), finding.global_model.parameters(), strict=True
            ):
                assert torch.allclose(mine, shared)


class TestExport:
    def test_onnx_matches_pytorch_for_every_history_length(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        from jnfinding.export import TOLERANCE, export_tower

        torch.manual_seed(2)
        tower = UserTower().eval()
        with torch.no_grad():
            tower.news_adapter.weight.add_(0.05 * torch.randn(384, 384))
        for output in ("user", "serving"):
            worst = export_tower(tower, tmp_path / f"{output}.onnx", output, history=50)
            assert worst < TOLERANCE, (output, worst)
