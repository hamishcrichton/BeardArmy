from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Dict, Iterable, List

from loguru import logger

from .models import Artifact


def write_json(path: str, data: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Wrote {path}")


def publish_artifacts(base_out: str, datasets: Dict[str, Dict]) -> List[Artifact]:
    artifacts: List[Artifact] = []
    for name, payload in datasets.items():
        rel = f"{name}.json" if not name.endswith(".json") else name
        out = os.path.join(base_out, rel)
        write_json(out, payload)
        artifacts.append(Artifact(name=name, content=payload, path=out))
    return artifacts

