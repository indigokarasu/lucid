"""Smoke tests for ocas-lucid skill."""
import os
import unittest
import yaml

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")


class TestSkillFrontmatter(unittest.TestCase):
    def test_frontmatter_parses(self):
        with open(SKILL_MD) as f:
            text = f.read()
        import re
        m = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        self.assertIsNotNone(m, "SKILL.md must have YAML frontmatter")
        fm = yaml.safe_load(m.group(1))
        self.assertIsNotNone(fm)
        self.assertEqual(fm.get("name"), "ocas-lucid")
        self.assertTrue(fm.get("description"))
        self.assertEqual(fm.get("license"), "MIT")
        self.assertIn("references/**", fm.get("includes", []))

    def test_metadata_hermes(self):
        with open(SKILL_MD) as f:
            text = f.read()
        import re
        m = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        fm = yaml.safe_load(m.group(1))
        hermes = fm.get("metadata", {}).get("hermes", {})
        self.assertTrue(hermes.get("tags"))
        self.assertTrue(hermes.get("category"))

    def test_triggers_present(self):
        with open(SKILL_MD) as f:
            text = f.read()
        import re
        m = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        fm = yaml.safe_load(m.group(1))
        self.assertTrue(fm.get("triggers"))


class TestSkillSections(unittest.TestCase):
    def test_required_sections(self):
        with open(SKILL_MD) as f:
            text = f.read()
        required = [
            "## When to Use",
            "## When NOT to Use",
            "## Error Handling",
            "## Gotchas",
            "## Support Files",
        ]
        for section in required:
            self.assertIn(section, text, f"Missing section: {section}")


class TestReferencedFiles(unittest.TestCase):
    def test_references_exist(self):
        with open(SKILL_MD) as f:
            text = f.read()
        import re
        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text)
        for label, url in links:
            if url.startswith("references/"):
                path = os.path.join(SKILL_DIR, url)
                self.assertTrue(os.path.exists(path), f"Dead reference: {url}")
            elif url.startswith("CHANGELOG") or url.startswith("config.json") or url.startswith("data/"):
                path = os.path.join(SKILL_DIR, url)
                self.assertTrue(os.path.exists(path), f"Dead reference: {url}")


if __name__ == "__main__":
    unittest.main()
