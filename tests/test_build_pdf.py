import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_pdf.py"
SPEC = importlib.util.spec_from_file_location("build_pdf", MODULE_PATH)
build_pdf = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(build_pdf)


class BuildPdfUnitTests(unittest.TestCase):
    def test_placeholder_detection_ignores_latex_grouping(self):
        source = r"\newcommand{\x}{{\color{green}X}} Name: {{FULL NAME}}"
        self.assertEqual(build_pdf.placeholder_labels(source), ["{{FULL NAME}}"])

    def test_log_page_count(self):
        log = "Output written on cv.pdf (2 pages, 12345 bytes)."
        self.assertEqual(build_pdf.log_page_count(log), 2)
        self.assertIsNone(build_pdf.log_page_count("No page count here"))

    def test_text_qa_checks_presence_and_order(self):
        extracted = "Candidate Name\nTarget Role\nRecent Company\nOlder Company"
        self.assertEqual(
            build_pdf.text_qa(
                extracted,
                expect_text=["Candidate Name", "Target Role"],
                expect_order=["Recent Company", "Older Company"],
                min_text_chars=10,
            ),
            [],
        )
        failures = build_pdf.text_qa(
            extracted,
            expect_text=["Missing Skill"],
            expect_order=["Older Company", "Recent Company"],
            min_text_chars=10,
        )
        self.assertEqual(len(failures), 2)

    @unittest.skipUnless(shutil.which("pdflatex"), "pdflatex is not installed")
    def test_end_to_end_build_with_text_qa(self):
        with tempfile.TemporaryDirectory() as temp_name:
            temp = Path(temp_name)
            tex = temp / "cv_test.tex"
            tex.write_text(
                r"""
\documentclass[10pt]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\begin{document}
Candidate Name\par
Target Role\par
Recent Company\par
Delivered a verified application improvement for users.\par
Older Company\par
Maintained a production service and documented operational decisions.
\end{document}
""",
                encoding="utf-8",
            )
            out = temp / "out"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--tex",
                    str(tex),
                    "--out",
                    str(out),
                    "--check-text",
                    "--min-text-chars",
                    "40",
                    "--expect-text",
                    "Candidate Name",
                    "--expect-order",
                    "Recent Company",
                    "--expect-order",
                    "Older Company",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue((out / "cv_test.pdf").is_file())


if __name__ == "__main__":
    unittest.main()
