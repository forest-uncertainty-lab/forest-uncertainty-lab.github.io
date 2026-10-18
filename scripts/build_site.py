"""Build the static site into _site/."""

from sulteng.config import ROOT
from sulteng.sitebuild import build, find_chrome


def main() -> None:
    for note in build(ROOT, ROOT / "_site", chrome=find_chrome()):
        print(f"note: {note}")
    print(f"site written to {ROOT / '_site'}")


if __name__ == "__main__":
    main()
