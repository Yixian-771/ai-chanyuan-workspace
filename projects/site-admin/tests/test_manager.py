import argparse
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("site_admin_manager", ROOT / "manager.py")
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)


class ManagerOfflineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_state, self.old_task_dir, self.old_audit = manager.STATE, manager.TASK_DIR, manager.AUDIT
        manager.STATE = Path(self.temp.name)
        manager.TASK_DIR = manager.STATE / "tasks"
        manager.AUDIT = manager.STATE / "audit.jsonl"

    def tearDown(self):
        manager.STATE, manager.TASK_DIR, manager.AUDIT = self.old_state, self.old_task_dir, self.old_audit
        self.temp.cleanup()

    def test_forum_ids_are_known(self):
        site = manager.get_site("lifecosmos-bbs")
        self.assertEqual(site["forums"]["八仙过海各显神通"], 426)
        self.assertEqual(site["forums"]["专题事件"], 427)

    def test_digest_changes_with_body(self):
        t = dict(site="lifecosmos-bbs", forum="专题事件",
                 title="测试", body="甲", source="公开资料")
        first = manager.digest(t)
        t["body"] = "乙"
        self.assertNotEqual(first, manager.digest(t))

    def test_draft_approve_and_duplicate_guard(self):
        text_file = manager.STATE / "post.txt"
        text_file.write_text("这是一篇测试正文。", encoding="utf-8")
        manager.new_task(argparse.Namespace(site="lifecosmos-bbs", forum="八仙过海各显神通",
            title="测试", source="公开资料", body_file=str(text_file),
            ai=False, brief_file=None))
        paths = list(manager.TASK_DIR.glob("*.json"))
        self.assertEqual(len(paths), 1)
        task = json.loads(paths[0].read_text(encoding="utf-8"))
        self.assertEqual(task["status"], "draft")
        manager.approve_task(argparse.Namespace(task_id=task["id"], approved_by="人工测试员", yes=True))
        approved = manager.load_task(task["id"])
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["approval_hash"], manager.digest(approved))
        approved["body"] = "事后修改"
        self.assertNotEqual(approved["approval_hash"], manager.digest(approved))

    def test_bad_task_ids_rejected(self):
        with self.assertRaises(ValueError):
            manager.task_path("../../secret")


if __name__ == "__main__":
    unittest.main()
