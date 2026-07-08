import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calc_sql import get_io_fields_from_content, append_io_fields_to_sql
from lib.file_util import find_file


class TestFlinkFields(unittest.TestCase):
    def setUp(self):
        base_folder = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        job_file = "FlinkSQLJob.flinkJob1.yaml"
        job_path = find_file(base_folder, job_file)
        with open(job_path, 'r', encoding='utf-8') as f:
            self.file_content = f.read()
        self.base_folder = base_folder

    def test_append_io_fields_to_sql(self):
        success, error_detail, new_content = append_io_fields_to_sql(self.file_content)
        self.assertTrue(success)
        self.assertEqual(error_detail, "")
        self.assertIn("-- input:", new_content)
        self.assertIn("-- output:", new_content)
        self.assertIn("/*", new_content)
        self.assertIn("*/", new_content)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "test_output.yaml")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

    def test_get_io_fields_from_content(self):
        inputs_str, outputs_str = get_io_fields_from_content(self.base_folder, self.file_content)
        self.assertIn("-- input:", inputs_str)
        self.assertIn("Message.msg1.yaml", inputs_str)
        self.assertIn("-- output:", outputs_str)
        self.assertIn("msgid,", inputs_str)


if __name__ == "__main__":
    unittest.main()