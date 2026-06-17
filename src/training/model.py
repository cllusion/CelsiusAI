"""
CelsiusAI Language Model
=========================
GPT-2 style decoder-only transformer built from scratch in pure PyTorch.
No pretrained weights — trained entirely on CelsiusAI's own data.

Default config (~7M parameters, fast to train on RTX 4070 Ti SUPER):
  n_layer=6, n_embd=256, n_head=8  →  ~7M params

Larger config (~85M parameters, higher quality):
  n_layer=12, n_embd=512, n_head=8  →  ~85M params
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Tuple


@dataclass
class CelsiusConfig:
    vocab_size: int = 8192
    n_positions: int = 512
    n_embd: int = 256
    n_layer: int = 6
    n_head: int = 8
    n_inner: int = 1024
    dropout: float = 0.1
    bias: bool = True

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> 'CelsiusConfig':
        with open(path) as f:
            return cls(**json.load(f))


class CausalSelfAttention(nn.Module):
    def __init__(self, config: CelsiusConfig):
        super().__init__()
        assert config.n_embd % config.n_head == 0
        self.n_head = config.n_head
        self.n_embd = config.n_embd
        self.head_dim = config.n_embd // config.n_head

        self.c_attn = nn.Linear(config.n_embd, 3 * config.n_embd, bias=config.bias)
        self.c_proj = nn.Linear(config.n_embd, config.n_embd, bias=config.bias)
        self.attn_drop = nn.Dropout(config.dropout)
        self.resid_drop = nn.Dropout(config.dropout)

        self.register_buffer(
            'mask',
            torch.tril(torch.ones(config.n_positions, config.n_positions))
            .view(1, 1, config.n_positions, config.n_positions)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        q, k, v = self.c_attn(x).split(self.n_embd, dim=2)
        q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = k.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_head, self.head_dim).transpose(1, 2)

        scale = 1.0 / math.sqrt(self.head_dim)
        attn = (q @ k.transpose(-2, -1)) * scale
        attn = attn.masked_fill(self.mask[:, :, :T, :T] == 0, float('-inf'))
        attn = F.softmax(attn, dim=-1)
        attn = self.attn_drop(attn)

        y = (attn @ v).transpose(1, 2).contiguous().view(B, T, C)
        return self.resid_drop(self.c_proj(y))


class MLP(nn.Module):
    def __init__(self, config: CelsiusConfig):
        super().__init__()
        self.fc = nn.Linear(config.n_embd, config.n_inner, bias=config.bias)
        self.proj = nn.Linear(config.n_inner, config.n_embd, bias=config.bias)
        self.drop = nn.Dropout(config.dropout)
        self.act = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.drop(self.proj(self.act(self.fc(x))))


class Block(nn.Module):
    def __init__(self, config: CelsiusConfig):
        super().__init__()
        self.ln1 = nn.LayerNorm(config.n_embd)
        self.attn = CausalSelfAttention(config)
        self.ln2 = nn.LayerNorm(config.n_embd)
        self.mlp = MLP(config)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        x = x + self.mlp(self.ln2(x))
        return x


class CelsiusLM(nn.Module):
    """
    CelsiusAI Language Model.
    Decoder-only transformer trained from scratch — no pretrained weights.
    """

    def __init__(self, config: CelsiusConfig):
        super().__init__()
        self.config = config

        self.wte = nn.Embedding(config.vocab_size, config.n_embd)
        self.wpe = nn.Embedding(config.n_positions, config.n_embd)
        self.drop = nn.Dropout(config.dropout)
        self.blocks = nn.ModuleList([Block(config) for _ in range(config.n_layer)])
        self.ln_f = nn.LayerNorm(config.n_embd)
        self.lm_head = nn.Linear(config.n_embd, config.vocab_size, bias=False)

        # Weight tying
        self.lm_head.weight = self.wte.weight

        self.apply(self._init_weights)
        n = sum(p.numel() for p in self.parameters())
        print(f"CelsiusLM initialised: {n/1e6:.1f}M parameters")

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(
        self,
        input_ids: torch.Tensor,
        labels: Optional[torch.Tensor] = None,
    ) -> Tuple[Optional[torch.Tensor], torch.Tensor]:
        B, T = input_ids.shape
        assert T <= self.config.n_positions

        pos = torch.arange(T, device=input_ids.device)
        x = self.drop(self.wte(input_ids) + self.wpe(pos))
        for block in self.blocks:
            x = block(x)
        x = self.ln_f(x)
        logits = self.lm_head(x)

        loss = None
        if labels is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)),
                labels.view(-1),
                ignore_index=-100,
            )
        return loss, logits

    @torch.no_grad()
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int = 256,
        temperature: float = 0.8,
        top_k: int = 50,
        eos_token_id: Optional[int] = None,
    ) -> torch.Tensor:
        self.eval()
        for _ in range(max_new_tokens):
            ctx = input_ids[:, -self.config.n_positions:]
            _, logits = self(ctx)
            logits = logits[:, -1, :] / temperature
            if top_k:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = float('-inf')
            probs = F.softmax(logits, dim=-1)
            next_tok = torch.multinomial(probs, num_samples=1)
            input_ids = torch.cat([input_ids, next_tok], dim=1)
            if eos_token_id is not None and next_tok.item() == eos_token_id:
                break
        return input_ids

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({'config': asdict(self.config), 'state_dict': self.state_dict()}, path)

    @classmethod
    def load(cls, path: Path, device: str = 'cpu') -> 'CelsiusLM':
        ckpt = torch.load(path, map_location=device)
        model = cls(CelsiusConfig(**ckpt['config']))
        model.load_state_dict(ckpt['state_dict'])
        return model
