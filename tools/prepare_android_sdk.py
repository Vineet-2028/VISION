"""Install Google's Windows command-line tools into ignored workspace tooling."""
import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / ".tools/android-sdk"
metadata = urllib.request.urlopen("https://dl.google.com/android/repository/repository2-1.xml", timeout=60).read()
tree = ET.fromstring(metadata)
packages = [p for p in tree if p.tag.endswith("remotePackage") and p.attrib.get("path") == "cmdline-tools;latest"]
if len(packages) != 1:
    raise RuntimeError("Official command-line-tools metadata unavailable")
archive = next(a for a in packages[0].iter("archive") if a.findtext("host-os") == "windows")
complete = archive.find("complete")
assert complete is not None
name = complete.findtext("url")
checksum = complete.find("checksum")
assert name and checksum is not None and checksum.text
url = "https://dl.google.com/android/repository/" + name
data = urllib.request.urlopen(url, timeout=120).read()
algorithm = checksum.attrib.get("type", "sha1")
if hashlib.new(algorithm, data).hexdigest() != checksum.text:
    raise RuntimeError("Official SDK archive checksum mismatch")
destination = target / "cmdline-tools/latest"
if destination.exists():
    raise RuntimeError("SDK command-line-tools already exist; refusing overwrite")
with zipfile.ZipFile(io.BytesIO(data)) as bundle:
    for member in bundle.infolist():
        relative = Path(member.filename).relative_to("cmdline-tools")
        path = (destination / relative).resolve()
        if not path.is_relative_to(destination.resolve()):
            raise RuntimeError("Unsafe archive path")
        if member.is_dir():
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bundle.read(member))
print("Official SDK command-line tools installed; checksum verified:", destination)
