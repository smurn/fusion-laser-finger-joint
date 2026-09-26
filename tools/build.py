"""
Builds the distributable packages of the add-in into dist/:

- LaserFingerJoint-<version>.bundle.zip
    "Laser Finger Joint.bundle" in the Autodesk App Store format:
        Laser Finger Joint.bundle/
            PackageContents.xml
            Contents/
                Laser Finger Joint.manifest, Laser Finger Joint.py, ... (the add-in)
                Help.html
    Fusion loads bundles from
        Windows: %APPDATA%\\Autodesk\\ApplicationPlugins
        macOS:   ~/Library/Application Support/Autodesk/ApplicationPlugins

- LaserFingerJoint-<version>.zip
    "Laser Finger Joint/" for manual installation into Fusion's API/AddIns folder.

The version is taken from the add-in manifest. Only the Python standard library is used.

Usage: python tools/build.py
"""

import json
import pathlib
import shutil
import uuid
import zipfile
from xml.sax.saxutils import quoteattr

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

ADDIN_NAME = "Laser Finger Joint"
FILE_STEM = "LaserFingerJoint"
MANIFEST = f"{ADDIN_NAME}.manifest"

#: Files and folders that make up the add-in, relative to the repository root.
ADDIN_FILES = [
    f"{ADDIN_NAME}.py",
    MANIFEST,
    "laser_finger_joint_feature.py",
    "laserfingerjoint.svg",
    "resources",
    "sane",
    "LICENSE",
]

AUTHOR = "Stefan C. Mueller"
REPOSITORY_URL = "https://github.com/smurn/fusion-laser-finger-joint"

#: Identifies the app across all versions. Never change.
UPGRADE_CODE = "{BF8F4EFB-FE39-4075-98B0-F97D267B7ECD}"

#: Namespace for deriving a per-version ProductCode, so every version gets its own stable GUID.
PRODUCT_CODE_NAMESPACE = uuid.UUID("9b8e5280-dfeb-4730-8831-6d3b1280fbcf")

#: Fixed timestamp for zip entries so that builds are reproducible.
ZIP_DATE_TIME = (2025, 1, 1, 0, 0, 0)


def read_manifest() -> dict:
    text = (ROOT / MANIFEST).read_text(encoding="utf-8-sig")
    return json.loads(text)


def package_contents_xml(version: str, description: str) -> str:
    product_code = "{" + str(uuid.uuid5(PRODUCT_CODE_NAMESPACE, version)).upper() + "}"
    return f"""<?xml version="1.0" encoding="utf-8"?>
<ApplicationPackage
    SchemaVersion="1.0"
    AutodeskProduct="Fusion360"
    ProductType="Application"
    Name={quoteattr(ADDIN_NAME)}
    Description={quoteattr(description)}
    AppVersion={quoteattr(version)}
    Author={quoteattr(AUTHOR)}
    ProductCode="{product_code}"
    UpgradeCode="{UPGRADE_CODE}"
    Icon="./Contents/resources/32x32.png"
    HelpFile="./Contents/Help.html">
  <CompanyDetails Name={quoteattr(AUTHOR)} Url={quoteattr(REPOSITORY_URL)} />
  <Components>
    <RuntimeRequirements OS="Win64|MacOS" Platform="Fusion360" />
    <ComponentEntry AppName={quoteattr(ADDIN_NAME)} Version={quoteattr(version)} ModuleName={quoteattr(f"./Contents/{MANIFEST}")} />
  </Components>
</ApplicationPackage>
"""


def copy_addin(destination: pathlib.Path):
    destination.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for name in ADDIN_FILES:
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(source, destination / name, ignore=ignore)
        else:
            shutil.copy2(source, destination / name)


def make_zip(source_dir: pathlib.Path, zip_path: pathlib.Path):
    """Zips source_dir so that the archive contains the folder itself at its root."""
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            arcname = path.relative_to(source_dir.parent).as_posix()
            if path.is_dir():
                info = zipfile.ZipInfo(arcname + "/", ZIP_DATE_TIME)
                info.external_attr = 0o40755 << 16
                archive.writestr(info, "")
            else:
                info = zipfile.ZipInfo(arcname, ZIP_DATE_TIME)
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())


def main():
    manifest = read_manifest()
    version = manifest["version"]
    description = manifest["description"][""]
    if not version:
        raise SystemExit(f"No version set in {MANIFEST}")

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    # Plain add-in folder for manual installation
    addin_dir = DIST / "addin" / ADDIN_NAME
    copy_addin(addin_dir)
    addin_zip = DIST / f"{FILE_STEM}-{version}.zip"
    make_zip(addin_dir, addin_zip)

    # App Store bundle
    bundle_dir = DIST / "bundle" / f"{ADDIN_NAME}.bundle"
    copy_addin(bundle_dir / "Contents")
    shutil.copy2(ROOT / "docs" / "help.html", bundle_dir / "Contents" / "Help.html")
    (bundle_dir / "PackageContents.xml").write_text(package_contents_xml(version, description), encoding="utf-8")
    bundle_zip = DIST / f"{FILE_STEM}-{version}.bundle.zip"
    make_zip(bundle_dir, bundle_zip)

    print(f"Built version {version}:")
    print(f"  {addin_zip.relative_to(ROOT)}")
    print(f"  {bundle_zip.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
