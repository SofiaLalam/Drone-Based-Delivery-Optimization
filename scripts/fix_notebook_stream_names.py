import json
import sys
from pathlib import Path


def fix_notebook(path: Path) -> int:
    raw = path.read_text(encoding="utf-8")
    nb = json.loads(raw)

    changed = 0
    for cell in nb.get("cells", []):
        outputs = cell.get("outputs")
        if not isinstance(outputs, list):
            continue
        for out in outputs:
            if not isinstance(out, dict):
                continue
            if out.get("output_type") == "stream" and "name" not in out:
                out["name"] = "stdout"
                changed += 1

    if changed:
        path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    return changed


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python scripts/fix_notebook_stream_names.py <path-to-ipynb>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    changed = fix_notebook(path)
    print(f"Fixed {changed} stream outputs missing 'name' in {path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

