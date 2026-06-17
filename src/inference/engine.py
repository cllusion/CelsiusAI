"""
CelsiusAI Inference Engine
============================
Loads a trained CelsiusLM and generates responses.
Automatically falls back to the keyword router if no trained model exists.

Model files expected at:
  models/best_model.pt   - trained weights
  models/tokenizer.json  - trained vocabulary

Run 'python train.py' to produce these files.
"""

import torch
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = PROJECT_ROOT / 'models' / 'best_model.pt'
DEFAULT_TOKENIZER = PROJECT_ROOT / 'models' / 'tokenizer.json'

SYSTEM_PROMPT = "You are CelsiusAI, the CLLUSION Investments assistant. Answer clearly and helpfully."


class CelsiusInferenceEngine:
    """Wraps the trained CelsiusLM for real-time inference."""

    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL,
        tokenizer_path: Path = DEFAULT_TOKENIZER,
        device: Optional[str] = None,
        max_new_tokens: int = 300,
        temperature: float = 0.75,
        top_k: int = 50,
    ):
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_k = top_k
        self.ready = False
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')

        if model_path.exists() and tokenizer_path.exists():
            self._load(model_path, tokenizer_path)
        else:
            logger.info(
                "No trained model found at %s — falling back to keyword router. "
                "Run 'python train.py' to train CelsiusAI.",
                model_path,
            )

    def _load(self, model_path: Path, tokenizer_path: Path) -> None:
        from src.training.model import CelsiusLM
        from src.training.tokenizer import CelsiusTokenizer

        logger.info("Loading CelsiusAI model from %s ...", model_path)
        self.model = CelsiusLM.load(model_path, device=self.device)
        self.model.eval()
        self.tokenizer = CelsiusTokenizer.load(tokenizer_path)
        self.ready = True
        logger.info("CelsiusAI model loaded on %s", self.device)

    def generate(self, prompt: str) -> Optional[str]:
        """Return a response string, or None if the engine is not ready."""
        if not self.ready:
            return None

        from src.training.tokenizer import SPECIAL_TOKENS

        tok = self.tokenizer
        sys_ids = tok.encode(SYSTEM_PROMPT, add_special_tokens=False)
        prompt_ids = tok.encode(prompt, add_special_tokens=False)

        input_ids = (
            [tok.bos_token_id]
            + [SPECIAL_TOKENS['<SYS>']]
            + sys_ids
            + [tok.sep_token_id]
            + [SPECIAL_TOKENS['<USR>']]
            + prompt_ids
            + [tok.sep_token_id]
            + [SPECIAL_TOKENS['<AST>']]
        )

        tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)

        with torch.no_grad():
            out = self.model.generate(
                tensor,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                top_k=self.top_k,
                eos_token_id=tok.eos_token_id,
            )

        new_ids = out[0, len(input_ids):].tolist()
        return tok.decode(new_ids, skip_special_tokens=True).strip()
