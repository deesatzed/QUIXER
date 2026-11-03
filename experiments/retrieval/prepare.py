"""Create a fresh local blind-review catalog from the preregistered manifest."""
import argparse
import json
from pathlib import Path

from quix_knowledge.retrieval_study import prepare_study

parser=argparse.ArgumentParser()
parser.add_argument('output',help='new output directory; existing directories are never overwritten')
args=parser.parse_args()
root=Path(__file__).resolve().parents[2]
print(json.dumps(prepare_study(root,root/'experiments/retrieval/manifest.json',args.output)))
