from __future__ import annotations

import json

from ato_readiness_checker.review import Review


def report_json(review: Review) -> str:
    return json.dumps(review.to_dict(), indent=2, ensure_ascii=False) + "\n"
