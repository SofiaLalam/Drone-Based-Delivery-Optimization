import json
import sys
from pathlib import Path


def strip_outputs(path: Path) -> int:
    nb = json.loads(path.read_text(encoding="utf-8"))
    changed_cells = 0
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        if cell.get("outputs"):
            cell["outputs"] = []
            changed_cells += 1
        if cell.get("execution_count") is not None:
            cell["execution_count"] = None
            changed_cells += 1
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    return changed_cells


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python scripts/strip_notebook_outputs.py <path-to-ipynb>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    n = strip_outputs(path)
    print(f"Stripped outputs/execution counts in {n} cells: {path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

