"""
CelsiusAI Trainer
==================
Full training loop with:
  - Mixed precision (fp16) for RTX 4070 Ti SUPER
  - Gradient accumulation (effective batch = batch_size x grad_accum_steps)
  - Cosine LR schedule with linear warmup
  - Automatic checkpointing (best + periodic)
  - Train/validation split
"""

import json
import math
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torch.amp import GradScaler, autocast
from pathlib import Path
from typing import Optional

from .model import CelsiusLM
from .tokenizer import CelsiusTokenizer
from .dataset import ConversationDataset


class CelsiusTrainer:

    def __init__(
        self,
        model: CelsiusLM,
        tokenizer: CelsiusTokenizer,
        data_path: Path,
        output_dir: Path,
        batch_size: int = 16,
        grad_accum_steps: int = 4,
        learning_rate: float = 3e-4,
        weight_decay: float = 0.1,
        max_epochs: int = 50,
        warmup_steps: int = 100,
        max_length: int = 512,
        val_split: float = 0.1,
        save_every: int = 5,
        eval_every: int = 1,
    ):
        self.model = model
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_epochs = max_epochs
        self.grad_accum_steps = grad_accum_steps
        self.learning_rate = learning_rate
        self.warmup_steps = warmup_steps
        self.save_every = save_every
        self.eval_every = eval_every

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"\nDevice: {self.device}")
        if self.device == 'cuda':
            props = torch.cuda.get_device_properties(0)
            print(f"GPU   : {props.name}")
            print(f"VRAM  : {props.total_memory / 1e9:.1f} GB")

        self.model = self.model.to(self.device)

        full = ConversationDataset(data_path, tokenizer, max_length)
        val_n = max(1, int(len(full) * val_split))
        train_n = len(full) - val_n
        train_ds, val_ds = random_split(full, [train_n, val_n])

        self.train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=2, pin_memory=True)
        self.val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=2, pin_memory=True)
        print(f"Train : {train_n} | Val: {val_n}")

        decay = [p for n, p in model.named_parameters() if p.dim() >= 2]
        no_decay = [p for n, p in model.named_parameters() if p.dim() < 2]
        self.optimizer = torch.optim.AdamW(
            [{'params': decay, 'weight_decay': weight_decay}, {'params': no_decay, 'weight_decay': 0.0}],
            lr=learning_rate, betas=(0.9, 0.95), eps=1e-8,
        )

        self.scaler = GradScaler('cuda', enabled=(self.device == 'cuda'))
        self.global_step = 0
        self.best_val_loss = float('inf')
        self.log = []

    def _lr(self, step: int, total: int) -> float:
        if step < self.warmup_steps:
            return step / max(1, self.warmup_steps)
        progress = (step - self.warmup_steps) / max(1, total - self.warmup_steps)
        return max(0.1, 0.5 * (1.0 + math.cos(math.pi * progress)))

    @torch.no_grad()
    def _evaluate(self) -> float:
        self.model.eval()
        total, n = 0.0, 0
        for batch in self.val_loader:
            ids = batch['input_ids'].to(self.device)
            lbl = batch['labels'].to(self.device)
            with autocast('cuda', enabled=(self.device == 'cuda')):
                loss, _ = self.model(ids, lbl)
            total += loss.item()
            n += 1
        self.model.train()
        return total / max(1, n)

    def train(self) -> None:
        total_steps = len(self.train_loader) * self.max_epochs // self.grad_accum_steps
        print(f"\nStarting: {self.max_epochs} epochs | {total_steps} optimizer steps")
        print('=' * 60)

        self.model.train()
        self.optimizer.zero_grad()

        for epoch in range(1, self.max_epochs + 1):
            epoch_loss, t0 = 0.0, time.time()

            for step, batch in enumerate(self.train_loader):
                ids = batch['input_ids'].to(self.device)
                lbl = batch['labels'].to(self.device)

                lr = self.learning_rate * self._lr(self.global_step, total_steps)
                for pg in self.optimizer.param_groups:
                    pg['lr'] = lr

                with autocast('cuda', enabled=(self.device == 'cuda')):
                    loss, _ = self.model(ids, lbl)
                    loss = loss / self.grad_accum_steps

                self.scaler.scale(loss).backward()
                epoch_loss += loss.item() * self.grad_accum_steps

                if (step + 1) % self.grad_accum_steps == 0:
                    self.scaler.unscale_(self.optimizer)
                    nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                    self.optimizer.zero_grad()
                    self.global_step += 1

            avg = epoch_loss / len(self.train_loader)
            elapsed = time.time() - t0
            entry = {'epoch': epoch, 'train_loss': round(avg, 4), 'lr': round(lr, 8), 'time_s': round(elapsed, 1)}

            if epoch % self.eval_every == 0:
                val_loss = self._evaluate()
                entry['val_loss'] = round(val_loss, 4)
                if val_loss < self.best_val_loss:
                    self.best_val_loss = val_loss
                    self.model.save(self.output_dir / 'best_model.pt')
                    print(f"  ★ New best  val_loss={val_loss:.4f}")

            self.log.append(entry)
            print(f"Epoch {epoch:3d}/{self.max_epochs}  loss={avg:.4f}  {elapsed:.0f}s  lr={lr:.2e}")

            if epoch % self.save_every == 0:
                self.model.save(self.output_dir / f'ckpt_epoch{epoch:04d}.pt')

        self.model.save(self.output_dir / 'final_model.pt')
        with open(self.output_dir / 'training_log.json', 'w') as f:
            json.dump(self.log, f, indent=2)
        print(f"\nDone. Best val loss: {self.best_val_loss:.4f}")
        print(f"Models saved to: {self.output_dir}")
