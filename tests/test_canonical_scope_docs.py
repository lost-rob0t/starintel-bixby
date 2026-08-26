import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CanonicalScopeDocsTests(unittest.TestCase):
    def test_repository_does_not_reintroduce_obsolete_target_write_scope(self):
        stale_scope = "starintel.targets.write"
        offenders = []

        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
                continue
            if path.suffix.lower() not in {
                ".md",
                ".json",
                ".bxb",
                ".js",
                ".py",
                ".txt",
                ".yaml",
                ".yml",
            }:
                continue
            if path == Path(__file__):
                continue

            text = path.read_text(encoding="utf-8", errors="ignore")
            if stale_scope in text:
                offenders.append(str(path.relative_to(ROOT)))

        self.assertEqual([], offenders, f"obsolete target scope found in: {offenders}")


if __name__ == "__main__":
    unittest.main()
