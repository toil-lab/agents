"""Validate service.yaml files against service.schema.json, plus the rules JSON Schema can't express.

Usage: python validate.py FILE...            (schema next to this script)
       python validate.py --schema PATH FILE...
Exit 0 if every file is valid, 1 if any is not, 2 if PyYAML or jsonschema is missing.
CI installs both: pip install pyyaml jsonschema
"""
import json, os, sys

try:
    import yaml
    from jsonschema import Draft202012Validator
except ImportError as e:
    sys.stderr.write(f"validate.py needs PyYAML and jsonschema: {e}\n")
    sys.exit(2)


def extra_errors(doc):
    """Rules beyond the schema."""
    errs = []
    s = doc.get("scaling") or {}
    if "min" in s and "max" in s and s["min"] > s["max"]:
        errs.append(f"scaling: min ({s['min']}) is greater than max ({s['max']})")
    names = [b.get("name") for b in doc.get("backing") or []]
    if len(names) != len(set(names)):
        errs.append("backing: two stores have the same name")
    if doc.get("name") in names:
        errs.append("backing: a store has the same name as the service")
    return errs


def validate(doc, schema):
    """List of error strings for one parsed service.yaml; empty when valid."""
    v = Draft202012Validator(schema)
    errs = [f"{'/'.join(str(p) for p in e.absolute_path) or '(top)'}: {e.message}"
            for e in sorted(v.iter_errors(doc), key=lambda e: list(e.absolute_path))]
    return errs + (extra_errors(doc) if isinstance(doc, dict) else [])


def main(argv):
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "service.schema.json")
    if argv[:1] == ["--schema"]:
        schema_path, argv = argv[1], argv[2:]
    if not argv:
        sys.stderr.write(__doc__)
        return 2
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    failed = 0
    for path in argv:
        with open(path, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        errs = validate(doc, schema)
        if errs:
            failed += 1
            print(f"FAIL {path}")
            for e in errs:
                print(f"  {e}")
        else:
            print(f"ok   {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
