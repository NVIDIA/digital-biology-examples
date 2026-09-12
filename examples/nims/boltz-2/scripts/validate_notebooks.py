"""Execute notebooks in real kernels and retain outputs and failure details."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

import nbformat
from nbclient import NotebookClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results/notebooks"))
    parser.add_argument("--notebook", action="append", help="Run only these notebook filenames")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    notebooks = sorted((root / "examples/notebooks").glob("*.ipynb"))
    if args.notebook:
        unknown = set(args.notebook) - {path.name for path in notebooks}
        if unknown:
            parser.error("Unknown notebook(s): " + ", ".join(sorted(unknown)))
        notebooks = [path for path in notebooks if path.name in args.notebook]
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # A private kernel specification ensures the installed client under test is used.
    jupyter = output / "jupyter"
    kernel = jupyter / "kernels/boltz2-validation"
    kernel.mkdir(parents=True, exist_ok=True)
    (kernel / "kernel.json").write_text(json.dumps({
        "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "Boltz2 validation", "language": "python",
    }))
    os.environ["JUPYTER_PATH"] = str(jupyter) + os.pathsep + os.environ.get("JUPYTER_PATH", "")
    report = []
    for path in notebooks:
        row = {"notebook": path.name}
        notebook = nbformat.read(path, as_version=4)
        work = output / "work" / path.stem
        work.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        print("Running", path.name, flush=True)
        try:
            NotebookClient(notebook, kernel_name="boltz2-validation", timeout=1200,
                           resources={"metadata": {"path": str(work)}}).execute()
            structures = list(work.rglob("*.cif"))
            if not structures:
                raise AssertionError("Notebook did not save any mmCIF structures")
            from Bio.PDB import MMCIFParser
            import numpy as np
            for file in structures:
                structure = MMCIFParser(QUIET=True).get_structure(file.stem, str(file))
                coords = np.asarray([atom.coord for atom in structure.get_atoms()])
                assert coords.size and np.isfinite(coords).all(), str(file)
            row.update(status="passed", structures=len(structures))
            for cell in notebook.cells:
                for item in cell.get("outputs", []):
                    html = item.get("data", {}).get("text/html", "")
                    if "3Dmol" in html:
                        viewers = output / "viewers"
                        viewers.mkdir(exist_ok=True)
                        (viewers / (path.stem + ".html")).write_text(html)
        except Exception as error:
            row.update(status="failed", error=str(error))
        row["seconds"] = round(time.monotonic() - start, 2)
        nbformat.write(notebook, output / path.name)
        report.append(row)
        (output / "validation.json").write_text(json.dumps(report, indent=2))
        print(row["status"], path.name, row["seconds"], flush=True)
    (output / "validation.json").write_text(json.dumps(report, indent=2))
    return int(any(row["status"] == "failed" for row in report))


if __name__ == "__main__":
    raise SystemExit(main())
