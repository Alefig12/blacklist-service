"""Empaqueta el código para subirlo a Elastic Beanstalk: dist/blacklist-service-v<VERSION>.zip


Uso:
    python scripts/build_zip.py
"""
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INCLUDE = ["application.py", "requirements.txt", "Procfile", "app", ".ebextensions", ".platform"]


def read_version():
    text = (ROOT / "app" / "version.py").read_text(encoding="utf-8")
    return re.search(r'VERSION\s*=\s*"([^"]+)"', text).group(1)


def files_to_package():
    for name in INCLUDE:
        path = ROOT / name
        if path.is_file():
            yield path
        elif path.is_dir():
            for file in sorted(path.rglob("*")):
                if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc":
                    yield file


def main():
    version = read_version()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    target = dist / f"blacklist-service-v{version}.zip"

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle:
        for file in files_to_package():
            arcname = file.relative_to(ROOT).as_posix()
            bundle.write(file, arcname)
            print(f"  + {arcname}")

    print(f"\nPaquete generado: {target}")
    print(f"Etiqueta sugerida para la version en Beanstalk: v{version}")


if __name__ == "__main__":
    main()
