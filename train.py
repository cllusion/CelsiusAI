#!/usr/bin/env python3
"""
CelsiusAI Training Script
==========================
Train CelsiusAI's language model from scratch on your own data.

Quick start:
    # 1. Install PyTorch with CUDA (RTX 4070 Ti SUPER)
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

    # 2. Train on the seed data
    python train.py

    # 3. Train longer with more epochs
    python train.py --epochs 200

    # 4. Resume from a checkpoint
    python train.py --resume models/ckpt_epoch0050.pt

    # 5. Train on a specific data file
    python train.py --data data/training/curated_qa.jsonl

Outputs (saved to models/):
    best_model.pt      - best checkpoint by validation loss
    final_model.pt     - model after all epochs
    tokenizer.json     - trained vocabulary
    config.json        - model hyperparameters
    training_log.json  - loss curve

Once training completes, CelsiusAI will automatically use the trained model
the next time it starts (falls back to keyword router if model is missing).
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description='Train CelsiusAI from scratch')
    parser.add_argument('--data', type=Path, default=None)
    parser.add_argument('--output', type=Path, default=ROOT / 'models')
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--batch_size', type=int, default=16)
    parser.add_argument('--lr', type=float, default=3e-4)
    parser.add_argument('--resume', type=Path, default=None)
    parser.add_argument('--vocab_size', type=int, default=8192)
    parser.add_argument('--n_layer', type=int, default=6)
    parser.add_argument('--n_embd', type=int, default=256)
    parser.add_argument('--n_head', type=int, default=8)
    parser.add_argument('--max_length', type=int, default=512)
    args = parser.parse_args()

    from src.training.data_collector import merge_training_data
    from src.training.tokenizer import CelsiusTokenizer
    from src.training.model import CelsiusLM, CelsiusConfig
    from src.training.trainer import CelsiusTrainer

    # ── Resolve data ──────────────────────────────────────────────────
    if args.data is None:
        print('Merging all available training data...')
        data_path = merge_training_data()
    else:
        data_path = args.data

    if not data_path.exists():
        print(f'ERROR: No training data at {data_path}')
        print('Add data first:')
        print('  python -c "from src.training.data_collector import add_curated_qa; add_curated_qa(\'Q\', \'A\')", ')
        sys.exit(1)

    # ── Tokenizer ─────────────────────────────────────────────────────
    tok_path = args.output / 'tokenizer.json'
    if tok_path.exists():
        print(f'Loading tokenizer from {tok_path}')
        tokenizer = CelsiusTokenizer.load(tok_path)
    else:
        print('Building tokenizer from training data...')
        tokenizer = CelsiusTokenizer(vocab_size=args.vocab_size)
        corpus = []
        with open(data_path, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    corpus.append(obj.get('prompt', '') + ' ' + obj.get('response', ''))
        tokenizer.train(corpus)
        args.output.mkdir(parents=True, exist_ok=True)
        tokenizer.save(tok_path)

    # ── Model ─────────────────────────────────────────────────────────
    if args.resume and args.resume.exists():
        print(f'Resuming from {args.resume}')
        model = CelsiusLM.load(args.resume)
    else:
        config = CelsiusConfig(
            vocab_size=len(tokenizer),
            n_layer=args.n_layer,
            n_embd=args.n_embd,
            n_head=args.n_head,
            n_inner=args.n_embd * 4,
        )
        model = CelsiusLM(config)

    args.output.mkdir(parents=True, exist_ok=True)
    model.config.save(args.output / 'config.json')

    # ── Train ─────────────────────────────────────────────────────────
    trainer = CelsiusTrainer(
        model=model,
        tokenizer=tokenizer,
        data_path=data_path,
        output_dir=args.output,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        max_epochs=args.epochs,
        max_length=args.max_length,
    )
    trainer.train()


if __name__ == '__main__':
    main()
