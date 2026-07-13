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


# Ordered keyword -> cuisine bucket; first match wins. Buckets are the axis for
# the analytics "by cuisine" charts, so keep the set small (~12 + other).
_CUISINE_RULES = [
    ("breakfast", ["breakfast", "fry up", "pancake", "waffle", "french toast"]),
    ("burger", ["burger"]),
    ("pizza", ["pizza", "calzone"]),
    ("mexican", ["burrito", "taco", "nacho", "quesadilla", "enchilada", "mexican"]),
    ("wings & chicken", ["wing", "chicken", "nando"]),
    ("bbq & ribs", ["bbq", "barbecue", "rib", "brisket", "pulled pork", "smokehouse"]),
    ("hot dog", ["hot dog", "hotdog"]),
    ("sandwich & sub", ["sandwich", "sub", "blt", "toastie", "panini", "wrap", "kebab", "gyro"]),
    ("fish & chips", ["fish and chip", "fish & chip", "fish n chip", "seafood", "fish"]),
    ("steak & grill", ["steak", "mixed grill", "grill", "parmo", "schnitzel"]),
    ("curry & asian", ["curry", "asian", "chinese", "thai", "ramen", "noodle", "sushi", "pho", "rice"]),
    ("pasta & italian", ["pasta", "spaghetti", "lasagn", "italian", "carbonara"]),
    ("dessert & sweet", ["dessert", "cake", "ice cream", "sundae", "donut", "doughnut", "chocolate",
                          "eclair", "pudding", "sweet", "milkshake", "cookie", "brownie", "pie"]),
    ("roast dinner", ["roast", "carvery", "christmas dinner", "thanksgiving"]),
]


def cuisine_bucket(food_type: str | None) -> str:
    if not food_type:
        return "other"
    ft = food_type.lower()
    for bucket, needles in _CUISINE_RULES:
        if any(n in ft for n in needles):
            return bucket
    return "other"


def publish_artifacts(base_out: str, datasets: Dict[str, Dict]) -> List[Artifact]:
    artifacts: List[Artifact] = []
    for name, payload in datasets.items():
        rel = f"{name}.json" if not name.endswith(".json") else name
        out = os.path.join(base_out, rel)
        write_json(out, payload)
        artifacts.append(Artifact(name=name, content=payload, path=out))
    return artifacts

