"""Test suite. Importing this package puts the repository root on sys.path."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
