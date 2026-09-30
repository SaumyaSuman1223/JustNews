"""The user tower, over frozen news vectors (ROADMAP §3.2, ADR 0005).

FINDING's news tower is NRMS over GloVe, which cannot read Hindi or Spanish.
Here the news tower is the frozen multilingual sentence encoder JustNews
already stores a vector from for every article; what trains is NRMS's user
encoder on top of it - multi-head self-attention over the reader's history,
then additive attention down to one vector - plus one linear adapter on the
news side, NRMS's trainable news encoder reduced to the one layer a frozen
encoder leaves room for.

The adapter is what keeps serving free of inference (ADR 0004): a click
score is u · (W c + b), and for one reader u · b is a constant that cannot
change their ranking, so u · W c = (Wᵀ u) · c. `serving_vector` returns
Wᵀ u - a vector that ranks by a plain dot product with the article vectors
already in Postgres, which therefore never need recomputing per model.

Differences from FINDING's NRMS user encoder, each for a stated reason:
- the history is masked: FINDING attends over left-padding (zero vectors),
  harmless with 50-item MIND histories and not with a news reader's five;
- torch's MultiheadAttention (with its output projection) instead of the
  paper's hand-rolled one, which exports to ONNX without custom ops;
- 12 heads, since 384 is not divisible by the paper's 15.
"""

from __future__ import annotations

import torch
from torch import nn


class AdditiveAttention(nn.Module):
    """NRMS's additive attention: weights from a learned query against
    tanh(W h + b), softmaxed over the unmasked positions."""

    def __init__(self, dim: int, query_dim: int) -> None:
        super().__init__()
        self.projection = nn.Linear(dim, query_dim)
        self.query = nn.Parameter(torch.empty(query_dim).uniform_(-0.1, 0.1))

    def forward(self, values: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        # values: (B, H, D); mask: (B, H), True where there is an item.
        logits = torch.tanh(self.projection(values)) @ self.query
        logits = logits.masked_fill(~mask, float("-inf"))
        weights = torch.softmax(logits, dim=-1)
        return (weights.unsqueeze(-1) * values).sum(dim=1)


class UserTower(nn.Module):
    #: Parameter groups, shallowest first - FINDING's "layers" for the
    #: depth-dependent interpolation coefficient (see trainer.py).
    LAYERS = ("news_adapter", "self_attention", "additive_attention")

    def __init__(
        self, dim: int = 384, heads: int = 12, query_dim: int = 200, dropout: float = 0.2
    ) -> None:
        super().__init__()
        self.news_adapter = nn.Linear(dim, dim)
        with torch.no_grad():
            self.news_adapter.weight.copy_(torch.eye(dim))
            self.news_adapter.bias.zero_()
        self.self_attention = nn.MultiheadAttention(dim, heads, batch_first=True)
        self.additive_attention = AdditiveAttention(dim, query_dim)
        self.dropout = nn.Dropout(dropout)

    def news(self, vectors: torch.Tensor) -> torch.Tensor:
        return self.news_adapter(vectors)

    def user(self, history: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """history: (B, H, D) raw news vectors; mask: (B, H) bool."""
        # A reader with no history at all would softmax over nothing; let
        # them attend to the (zero) first slot instead of producing NaN.
        # Written without in-place indexing so it exports to ONNX.
        first = (torch.arange(mask.shape[1], device=mask.device) == 0).unsqueeze(0)
        mask = mask | (first & ~mask.any(dim=1, keepdim=True))
        news = self.dropout(self.news(history))
        attended, _ = self.self_attention(
            news, news, news, key_padding_mask=~mask, need_weights=False
        )
        return self.additive_attention(self.dropout(attended), mask)

    def forward(
        self, history: torch.Tensor, mask: torch.Tensor, candidates: torch.Tensor
    ) -> torch.Tensor:
        """Click logits, (B, C), for candidates (B, C, D)."""
        user = self.user(history, mask)
        return torch.einsum("bd,bcd->bc", user, self.news(candidates))

    def serving_vector(self, history: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Wᵀ u: the vector a reader is ranked by with raw article vectors."""
        return self.user(history, mask) @ self.news_adapter.weight

    def layer_of(self, name: str) -> int:
        return self.LAYERS.index(name.split(".")[0])
