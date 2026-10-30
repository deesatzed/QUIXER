"""Minimal local command-line entry point."""
import argparse
import json
from .store import open_catalog
from .ingest import ingest
from .retrieve import search

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    ingest_parser = sub.add_parser('ingest')
    ingest_parser.add_argument('path')
    search_parser = sub.add_parser('search')
    search_parser.add_argument('query')
    search_parser.add_argument('--variant', choices=('baseline','topic','decision','role'), default='baseline')
    search_parser.add_argument('--role')
    search_parser.add_argument('--role-version')
    search_parser.add_argument('--env-file')
    search_parser.add_argument('--model-slot', type=int, choices=(1,2,3,4))
    args = parser.parse_args()
    if args.command == 'search' and bool(args.env_file) != bool(args.model_slot):
        parser.error('--env-file and --model-slot must be provided together')
    if args.command == 'search' and args.env_file and args.variant not in ('decision','role'):
        parser.error('a model requires the decision or role variant')
    db = open_catalog(args.db)
    try:
        if args.command == 'ingest':
            source_id = ingest(db,args.path)
            print(json.dumps({'source_id':source_id}))
            return 0 if source_id else 1
        provider = None
        if args.env_file:
            from .openrouter import load_settings, OpenRouterDecision
            provider = OpenRouterDecision(load_settings(args.env_file,args.model_slot))
        print(json.dumps(search(db,args.query,variant=args.variant,role=args.role,role_version=args.role_version,provider=provider)))
        return 0
    finally:
        db.close()

if __name__ == '__main__':
    raise SystemExit(main())
