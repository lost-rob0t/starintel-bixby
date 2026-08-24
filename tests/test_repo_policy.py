import tempfile
import unittest
from pathlib import Path

from tools.repo_policy import PolicyError, validate_tree


class RepoPolicyTests(unittest.TestCase):
    def make_tree(self, files):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.addCleanup(temp.cleanup)
        return root

    def test_rejects_private_star_intel_host_in_capsule_source(self):
        root = self.make_tree({
            "capsules/starintel-intelligence/code/endpoint.js":
                "const endpoint = 'https://ingest.star.intel/search';\n"
        })
        with self.assertRaisesRegex(PolicyError, r"private/internal endpoint"):
            validate_tree(root)

    def test_rejects_private_ip_in_capsule_source(self):
        root = self.make_tree({
            "capsules/starintel-intelligence/code/endpoint.js":
                "const endpoint = 'http://10.50.50.5:5984';\n"
        })
        with self.assertRaisesRegex(PolicyError, r"private/internal endpoint"):
            validate_tree(root)

    def test_rejects_committed_secret_like_assignment(self):
        root = self.make_tree({
            "capsules/starintel-operations/code/auth.js":
                "const client_secret = 'super-secret-value';\n"
        })
        with self.assertRaisesRegex(PolicyError, r"secret-like credential"):
            validate_tree(root)

    def test_allows_developer_center_secret_key_reference(self):
        root = self.make_tree({
            "capsules/starintel-operations/authorization.bxb":
                "client-secret-key (starintel_operations_oauth)\n"
        })
        validate_tree(root)

    def test_allows_public_document_url_fixture(self):
        root = self.make_tree({
            "fixtures/document-success.json":
                '{"url":"https://docs.starintel.actor/document/abc%2F123"}\n'
        })
        validate_tree(root)


if __name__ == "__main__":
    unittest.main()
