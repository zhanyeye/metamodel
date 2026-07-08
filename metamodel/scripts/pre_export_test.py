import os
import sys
import base64
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pre_export import process_zip_from_b64


class TestPreExport(unittest.TestCase):
    def test_process_zip(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        zip_path = os.path.join(project_root, "model.zip")
        with open(zip_path, "rb") as f:
            zip_content_b64 = base64.b64encode(f.read()).decode("utf-8")

        new_zip_content_b64, error_detail = process_zip_from_b64(zip_content_b64)

        self.assertIsNotNone(new_zip_content_b64)
        self.assertEqual(error_detail, "")

        output_path = os.path.join(script_dir, "pre_export_test_output.zip")
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(new_zip_content_b64))


if __name__ == "__main__":
    unittest.main()