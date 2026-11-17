"""Report writers. Each one renders the same Review; none of them re-runs checks."""

from ato_readiness_checker.reports.brief import brief_html, brief_markdown
from ato_readiness_checker.reports.html import report_html
from ato_readiness_checker.reports.json_out import report_json
from ato_readiness_checker.reports.markdown import report_markdown
from ato_readiness_checker.reports.oscal_out import review_to_oscal

__all__ = ["brief_html", "brief_markdown", "report_html", "report_json", "report_markdown", "review_to_oscal"]
