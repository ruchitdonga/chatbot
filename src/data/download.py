"""Download the MASSIVE archive named in the config, verify its checksum, and extract it.

Run from the repo root: python -m src.data.download
"""
import hashlib
import tarfile
import urllib.request

from src.data.load import ROOT, load_config


def main():
    ds = load_config()["dataset"]
    raw_dir = ROOT / ds["raw_dir"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    archive = raw_dir / ds["url"].rsplit("/", 1)[1]

    if not archive.exists():
        print(f"Downloading {ds['url']}")
        urllib.request.urlretrieve(ds["url"], archive)

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != ds["sha256"]:
        raise SystemExit(f"Checksum mismatch for {archive.name}: got {digest}, expected {ds['sha256']}")

    # The "data" filter refuses absolute paths, links and anything escaping raw_dir.
    with tarfile.open(archive) as tar:
        tar.extractall(raw_dir, filter="data")
    print(f"Verified and extracted to {raw_dir / ds['version']}")


if __name__ == "__main__":
    main()
