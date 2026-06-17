"""
CelsiusAI Training Dataset
===========================
Loads Q&A pairs from JSONL and formats them for causal language modelling.

Each sequence:
  <BOS> <SYS> system <SEP> <USR> prompt <SEP> <AST> response <EOS>

Labels are -100 (ignored) over the prompt portion; only the response
tokens contribute to the loss, so the model learns to answer, not repeat.

JSONL format (one object per line):
  {"prompt": "How do I add a seller?", "response": "Go to /admin/sellers..."}
"""

import json
import torch
from pathlib import Path
from torch.utils.data import Dataset
from typing import List, Dict
from .tokenizer import CelsiusTokenizer, SPECIAL_TOKENS


SYSTEM_PROMPT = "You are CelsiusAI, the CLLUSION Investments assistant. Answer clearly and helpfully."


class ConversationDataset(Dataset):
    SYSTEM_PROMPT = SYSTEM_PROMPT

    def __init__(self, data_path: Path, tokenizer: CelsiusTokenizer, max_length: int = 512):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.examples: List[Dict] = []
        self._load(data_path)
        print(f"Dataset: {len(self.examples)} examples from {data_path.name}")

    def _load(self, path: Path) -> None:
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    obj = json.loads(line)
                    if 'prompt' in obj and 'response' in obj:
                        self.examples.append(obj)

    def _build(self, prompt: str, response: str):
        tok = self.tokenizer
        sys_ids = tok.encode(SYSTEM_PROMPT, add_special_tokens=False)
        prompt_ids = tok.encode(prompt, add_special_tokens=False)
        resp_ids = tok.encode(response, add_special_tokens=False)

        input_ids = (
            [tok.bos_token_id]
            + [SPECIAL_TOKENS['<SYS>']]
            + sys_ids
            + [tok.sep_token_id]
            + [SPECIAL_TOKENS['<USR>']]
            + prompt_ids
            + [tok.sep_token_id]
            + [SPECIAL_TOKENS['<AST>']]
            + resp_ids
            + [tok.eos_token_id]
        )

        prompt_len = 1 + 1 + len(sys_ids) + 1 + 1 + len(prompt_ids) + 1 + 1
        labels = [-100] * prompt_len + resp_ids + [tok.eos_token_id]
        return input_ids, labels

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        ex = self.examples[idx]
        ids, labels = self._build(ex['prompt'], ex['response'])

        ids = ids[:self.max_length]
        labels = labels[:self.max_length]

        pad = self.max_length - len(ids)
        ids += [self.tokenizer.pad_token_id] * pad
        labels += [-100] * pad

        return {
            'input_ids': torch.tensor(ids, dtype=torch.long),
            'labels': torch.tensor(labels, dtype=torch.long),
        }
