import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ROOTS = (ROOT / "capsules", ROOT / "tools")


class CanonicalScopeDocsTests(unittest.TestCase):
    def test_production_sources_do_not_use_obsolete_target_write_scope(self):
        stale_scope = "starintel.targets.write"
        offenders = []

        for root in PRODUCTION_ROOTS:
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix.lower() not in {".json", ".bxb", ".js", ".py", ".txt"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                if stale_scope in text:
                    offenders.append(str(path.relative_to(ROOT)))

        self.assertEqual([], offenders, f"obsolete target scope found in production sources: {offenders}")


if __name__ == "__main__":
    unittest.main()
