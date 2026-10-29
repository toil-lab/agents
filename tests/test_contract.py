"""Tests for contract/service.schema.json, contract/toil.schema.json, and contract/validate.py."""
import copy, glob, json, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT = os.path.join(ROOT, "contract")
sys.path.insert(0, CONTRACT)

try:
    import yaml
    from jsonschema import Draft202012Validator
    import validate
    HAVE_LIBS = True
except (ImportError, SystemExit):
    HAVE_LIBS = False


def load_json(name):
    with open(os.path.join(CONTRACT, name), encoding="utf-8") as f:
        return json.load(f)


@unittest.skipUnless(HAVE_LIBS, "needs pyyaml and jsonschema")
class ServiceSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_json("service.schema.json")
        Draft202012Validator.check_schema(cls.schema)
        with open(os.path.join(CONTRACT, "examples", "checks", "probe-worker.yaml"), encoding="utf-8") as f:
            cls.base = yaml.safe_load(f)

    def errors(self, doc):
        return validate.validate(doc, self.schema)

    def test_examples_are_valid(self):
        files = sorted(glob.glob(os.path.join(CONTRACT, "examples", "*", "*.yaml")))
        self.assertGreaterEqual(len(files), 6)
        for path in files:
            with self.subTest(file=os.path.relpath(path, CONTRACT)):
                with open(path, encoding="utf-8") as f:
                    self.assertEqual(self.errors(yaml.safe_load(f)), [])

    def test_invalid_specs(self):
        def changed(**patch):
            doc = copy.deepcopy(self.base)
            for k, v in patch.items():
                if v is None:
                    doc.pop(k, None)
                else:
                    doc[k] = v
            return doc

        cases = {
            "missing resources": changed(resources=None),
            "unknown field": changed(replicas=3),
            "image with a tag": changed(image="ghcr.io/toil-lab/probe-worker:latest"),
            "cpu in cores": changed(resources={"cpu": "0.5", "memory": "32Mi"}),
            "lowercase env name": changed(config=["probe_timeout"]),
            "queue scaling without source": changed(scaling={"min": 1, "max": 6, "metric": "queue", "target": 20}),
            "cpu scaling without target": changed(scaling={"min": 1, "max": 4, "metric": "cpu"}),
            "min above max": changed(scaling={"min": 5, "max": 2, "metric": "none"}),
            "deployment without health": changed(health=None),
            "deployment with schedule": changed(schedule="* * * * *"),
            "cronjob without schedule": changed(kind="cronjob", health=None, scaling=None, port=None),
            "cronjob with scaling": changed(kind="cronjob", schedule="5 * * * *", health=None, port=None),
            "bad egress": changed(egress=["anything"]),
            "bad dependency": changed(depends_on=["Status/API"]),
            "wrong schema version": changed(schema_version=2),
            "backing store named like the service": changed(backing=[{"type": "redis", "name": "probe-worker"}]),
        }
        for label, doc in cases.items():
            with self.subTest(case=label):
                self.assertNotEqual(self.errors(doc), [], f"{label} should be rejected")


@unittest.skipUnless(HAVE_LIBS, "needs pyyaml and jsonschema")
class ToilSchemaTest(unittest.TestCase):
    def test_toil_json(self):
        schema = load_json("toil.schema.json")
        Draft202012Validator.check_schema(schema)
        v = Draft202012Validator(schema)
        self.assertTrue(v.is_valid({"kind": "app", "team": "checks"}))
        self.assertTrue(v.is_valid({"kind": "platform"}))
        self.assertFalse(v.is_valid({"kind": "app"}))
        self.assertFalse(v.is_valid({"kind": "service"}))
        with open(os.path.join(ROOT, "toil.json"), encoding="utf-8") as f:
            self.assertTrue(v.is_valid(json.load(f)))


if __name__ == "__main__":
    unittest.main()
