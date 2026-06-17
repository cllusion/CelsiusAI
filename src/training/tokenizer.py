"""
CelsiusAI Tokenizer
===================
A word-level tokenizer trained entirely on CelsiusAI's own data.
No external dependencies beyond Python stdlib.

Special tokens:
  <PAD> 0  - padding
  <BOS> 1  - beginning of sequence
  <EOS> 2  - end of sequence
  <UNK> 3  - unknown token
  <SEP> 4  - separator
  <SYS> 5  - system prompt marker
  <USR> 6  - user turn marker
  <AST> 7  - assistant turn marker
"""

import json
import re
from pathlib import Path
from typing import List, Dict
from collections import Counter


SPECIAL_TOKENS: Dict[str, int] = {
    '<PAD>': 0,
    '<BOS>': 1,
    '<EOS>': 2,
    '<UNK>': 3,
    '<SEP>': 4,
    '<SYS>': 5,
    '<USR>': 6,
    '<AST>': 7,
}


class CelsiusTokenizer:
    """Word-level tokenizer for CelsiusAI."""

    def __init__(self, vocab_size: int = 8192):
        self.vocab_size = vocab_size
        self.token_to_id: Dict[str, int] = dict(SPECIAL_TOKENS)
        self.id_to_token: Dict[int, str] = {v: k for k, v in self.token_to_id.items()}
        self.trained = False

    # ------------------------------------------------------------------
    # Text splitting
    # ------------------------------------------------------------------

    def _split(self, text: str) -> List[str]:
        """Split text into word + punctuation tokens."""
        return re.findall(r"\w+|[^\w\s]", text.lower())

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, corpus: List[str]) -> None:
        """Build vocabulary from a list of strings."""
        counts: Counter = Counter()
        for text in corpus:
            counts.update(self._split(text))

        slots = self.vocab_size - len(SPECIAL_TOKENS)
        next_id = len(SPECIAL_TOKENS)
        for word, _ in counts.most_common(slots):
            if word not in self.token_to_id:
                self.token_to_id[word] = next_id
                self.id_to_token[next_id] = word
                next_id += 1

        self.trained = True
        print(f"Tokenizer trained: {len(self.token_to_id):,} tokens")

    # ------------------------------------------------------------------
    # Encode / decode
    # ------------------------------------------------------------------

    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        tokens = self._split(text)
        ids = []
        if add_special_tokens:
            ids.append(SPECIAL_TOKENS['<BOS>'])
        for t in tokens:
            ids.append(self.token_to_id.get(t, SPECIAL_TOKENS['<UNK>']))
        if add_special_tokens:
            ids.append(SPECIAL_TOKENS['<EOS>'])
        return ids

    def decode(self, ids: List[int], skip_special_tokens: bool = True) -> str:
        tokens = []
        for id_ in ids:
            tok = self.id_to_token.get(id_, '<UNK>')
            if skip_special_tokens and tok in SPECIAL_TOKENS:
                continue
            tokens.append(tok)

        result = ''
        for i, tok in enumerate(tokens):
            if i > 0 and tok not in '.,!?;:\'")]-' and tokens[i - 1] not in '([{-\'"':
                result += ' '
            result += tok
        return result.strip()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'vocab_size': self.vocab_size, 'token_to_id': self.token_to_id, 'trained': self.trained}, f, indent=2)

    @classmethod
    def load(cls, path: Path) -> 'CelsiusTokenizer':
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        tok = cls(vocab_size=data['vocab_size'])
        tok.token_to_id = {k: int(v) for k, v in data['token_to_id'].items()}
        tok.id_to_token = {int(v): k for k, v in data['token_to_id'].items()}
        tok.trained = data['trained']
        return tok

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def pad_token_id(self) -> int:
        return SPECIAL_TOKENS['<PAD>']

    @property
    def bos_token_id(self) -> int:
        return SPECIAL_TOKENS['<BOS>']

    @property
    def eos_token_id(self) -> int:
        return SPECIAL_TOKENS['<EOS>']

    @property
    def sep_token_id(self) -> int:
        return SPECIAL_TOKENS['<SEP>']

    def __len__(self) -> int:
        return len(self.token_to_id)
