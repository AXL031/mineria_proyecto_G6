"""DAG y recibos con scripts mínimos; nunca entrenar los modelos de la demo."""

from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bankshield.preparation import Preparation, Stage, dependency_order
from scripts.prepare_demo import stages_for, write_demo_configs


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "source.txt").write_text("entrada", encoding="utf-8")
        (self.root / "config.json").write_text('{"seed":42}', encoding="utf-8")
        (self.root / "build.py").write_text(
            "from pathlib import Path\nimport json,sys\n"
            "Path(sys.argv[1]).write_text(json.dumps({'schema_version':1,'data':Path(sys.argv[2]).read_text()}))\n",
            encoding="utf-8",
        )
        self.first = Stage("silver", "build.py", ("silver.json", "source.txt"),
                           inputs=("source.txt",), outputs=("silver.json",), configs=("config.json",),
                           json_versions={"silver.json": 1})
        self.second = Stage("gold", "build.py", ("gold.json", "silver.json"), dependencies=("silver",),
                            inputs=("silver.json",), outputs=("gold.json",), json_versions={"gold.json": 1})

    def engine(self):
        return Preparation(self.root, "reports", environment={"fixture": 1})

    def run_pipeline(self, **kwargs):
        return self.engine().run([self.second, self.first], ["gold"], **kwargs)

    def test_dependency_order_and_verified_reuse(self):
        first = self.run_pipeline()
        self.assertEqual([(s["stage"], s["status"]) for s in first["stages"]], [("silver", "built"), ("gold", "built")])
        second = self.run_pipeline()
        self.assertEqual([s["status"] for s in second["stages"]], ["reused", "reused"])
        self.assertTrue(all(s["inputs"] and s["outputs"] and s["duration_seconds"] >= 0 for s in second["stages"]))

    def test_input_and_configuration_changes_invalidate_receipt(self):
        self.run_pipeline()
        (self.root / "source.txt").write_text("otra entrada", encoding="utf-8")
        changed = self.run_pipeline()
        self.assertEqual([s["status"] for s in changed["stages"]], ["built", "built"])
        (self.root / "config.json").write_text('{"seed":43}', encoding="utf-8")
        changed = self.run_pipeline()
        self.assertEqual(changed["stages"][0]["status"], "built")

    def test_missing_and_modified_outputs_are_rebuilt(self):
        self.run_pipeline()
        (self.root / "gold.json").unlink()
        self.assertEqual([s["status"] for s in self.run_pipeline()["stages"]], ["reused", "built"])
        (self.root / "gold.json").write_text('{"schema_version":9}', encoding="utf-8")
        self.assertEqual(self.run_pipeline()["stages"][-1]["status"], "built")

    def test_force_rebuilds_selected_dependency_closure(self):
        self.run_pipeline()
        self.assertEqual([s["status"] for s in self.run_pipeline(force=True)["stages"]], ["built", "built"])

    def test_failure_publishes_manifest_and_does_not_run_dependent(self):
        (self.root / "fail.py").write_text("raise SystemExit(7)", encoding="utf-8")
        broken = replace(self.first, script="fail.py")
        with self.assertRaisesRegex(RuntimeError, "código 7"):
            self.engine().run([broken, self.second], ["gold"])
        manifest = json.loads((self.root / "reports/preparation-manifest.json").read_text())
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["stages"][0]["returncode"], 7)
        self.assertFalse((self.root / "gold.json").exists())
        self.assertIn("finished_at_utc", manifest)

    def test_success_without_complete_outputs_is_rejected(self):
        (self.root / "empty.py").write_text("pass", encoding="utf-8")
        stage = replace(self.first, script="empty.py")
        with self.assertRaises((OSError, ValueError)):
            self.engine().run([stage, self.second], ["gold"])
        self.assertFalse((self.root / "gold.json").exists())
        # Tampoco aceptar una salida antigua si el comando no vuelve a escribirla.
        self.run_pipeline()
        with self.assertRaisesRegex(ValueError, "restos antiguos"):
            self.engine().run([stage], ["silver"], force=True)

    def test_legacy_existence_is_not_a_receipt(self):
        (self.root / "silver.json").write_text('{"schema_version":1}', encoding="utf-8")
        result = self.engine().run([self.first], ["silver"])
        self.assertEqual(result["stages"][0]["status"], "built")

    def test_optional_stage_is_explicit_but_required_missing_delivery_fails(self):
        pending = replace(self.second, optional=True, unavailable_reason="Entrega pendiente")
        result = self.engine().run([self.first, pending], ["gold"])
        self.assertEqual(result["stages"][-1]["status"], "skipped_optional")
        with self.assertRaisesRegex(RuntimeError, "Entrega pendiente"):
            self.engine().run([self.first, replace(pending, optional=False)], ["gold"])
        manifest = json.loads((self.root / "reports/preparation-manifest.json").read_text())
        self.assertEqual(manifest["stages"][0]["stage"], "gold")
        self.assertEqual(manifest["stages"][0]["status"], "failed")

    def test_cycles_and_unknown_selection_publish_failure(self):
        cycle = replace(self.first, dependencies=("gold",))
        with self.assertRaisesRegex(ValueError, "circular"):
            self.engine().run([cycle, self.second], ["gold"])
        with self.assertRaisesRegex(ValueError, "desconocida"):
            self.engine().run([self.first], ["other"])
        self.assertEqual(json.loads((self.root / "reports/preparation-manifest.json").read_text())["status"], "failed")

    def test_paths_outside_project_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "sale del proyecto"):
            self.engine().path("../outside")

    def test_source_code_and_environment_changes_invalidate_receipt(self):
        self.run_pipeline()
        script = self.root / "build.py"
        script.write_text(script.read_text() + "\n# nueva versión\n", encoding="utf-8")
        self.assertEqual(self.run_pipeline()["stages"][0]["status"], "built")
        engine = Preparation(self.root, "reports", environment={"fixture": 2})
        self.assertEqual(engine.run([self.first], ["silver"])["stages"][0]["status"], "built")

    def test_incompatible_source_identity_is_rejected(self):
        (self.root / "bad.py").write_text(
            "from pathlib import Path\nimport json\nPath('silver.json').write_text(json.dumps({'schema_version':1,'source':{'sha256':'0'*64}}))",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "Identidad source"):
            self.engine().run([replace(self.first, script="bad.py")], ["silver"])

    def test_bronze_and_versioned_documentation_are_protected_outputs(self):
        for path in ("data/bronze/original.csv", "docs/report.md"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "Salida protegida"):
                self.engine().run([replace(self.first, outputs=(path,))], ["silver"])

    def test_registry_contains_new_dependencies_and_bounded_graph_comparison(self):
        registry = {s.name: s for s in stages_for()}
        self.assertEqual(registry["analytics-d1"].dependencies, ("transactions-silver",))
        for name in ("associations", "regression"):
            self.assertEqual(registry[name].dependencies, ("analytics-d1",))
            self.assertTrue(registry[name].unavailable_reason)
        self.assertIn("10000", registry["graph-comparison"].arguments)
        self.assertEqual(registry["model-monitoring"].dependencies, ("regression",))

    def test_demo_configuration_redirects_markdown_without_changing_source(self):
        (self.root / "configs").mkdir()
        path = self.root / "configs/segments.json"
        original = '{"report_markdown":"docs/segmentacion.md","seed":42}'
        path.write_text(original, encoding="utf-8")
        write_demo_configs(self.root)
        self.assertEqual(path.read_text(), original)
        generated = json.loads((self.root / "artifacts/reports/demo/segments-config.json").read_text())
        self.assertTrue(generated["report_markdown"].startswith("artifacts/reports/demo/"))


if __name__ == "__main__":
    unittest.main()
