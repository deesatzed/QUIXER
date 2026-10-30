"""Minimal local command-line entry point."""
import argparse
import json
from pathlib import Path
from .store import open_catalog
from .ingest import ingest
from .retrieve import search

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    ingest_parser = sub.add_parser('ingest')
    ingest_parser.add_argument('path')
    index_parser = sub.add_parser('index')
    index_parser.add_argument('path')
    index_parser.add_argument('--env-file')
    index_parser.add_argument('--model-slot', type=int, choices=(1,2,3,4))
    index_parser.add_argument('--max-decisions', type=int, default=10)
    list_index = sub.add_parser('list-index')
    list_index.add_argument('--status',choices=('proposed','accepted','rejected','stale'))
    review_index = sub.add_parser('review-index')
    review_index.add_argument('entry_id')
    review_index.add_argument('decision',choices=('accepted','rejected'))
    review_index.add_argument('--reviewer',required=True)
    role_parser = sub.add_parser('assess-role')
    role_parser.add_argument('section_id')
    role_parser.add_argument('--role',required=True)
    role_parser.add_argument('--role-version',required=True)
    role_parser.add_argument('--role-purpose',required=True)
    role_parser.add_argument('--env-file',required=True)
    role_parser.add_argument('--model-slot',type=int,choices=(1,2,3,4),required=True)
    experiment_parser = sub.add_parser('experiment')
    experiment_parser.add_argument('tasks', help='JSON array of task records')
    exp_budget = experiment_parser.add_mutually_exclusive_group()
    exp_budget.add_argument('--context-chars', type=int)
    exp_budget.add_argument('--context-tokens', type=int)
    experiment_parser.add_argument('--tokenizer')
    experiment_parser.add_argument('--include-proposed', action='store_true')
    experiment_parser.add_argument('--indexing-receipts', help='JSON array of indexing receipt IDs from this catalog')
    experiment_parser.add_argument('--limit', type=int, default=10)
    experiment_parser.add_argument('--label-provenance')
    experiment_parser.add_argument('--env-file')
    experiment_parser.add_argument('--model-slot', type=int, choices=(1,2,3,4))
    search_parser = sub.add_parser('search')
    search_parser.add_argument('query')
    search_parser.add_argument('--variant', choices=('baseline','topic','decision','role'), default='baseline')
    search_parser.add_argument('--role')
    search_parser.add_argument('--role-version')
    budget = search_parser.add_mutually_exclusive_group()
    budget.add_argument('--context-chars', type=int)
    budget.add_argument('--context-tokens', type=int)
    search_parser.add_argument('--tokenizer')
    search_parser.add_argument('--include-proposed', action='store_true')
    search_parser.add_argument('--env-file')
    search_parser.add_argument('--model-slot', type=int, choices=(1,2,3,4))
    args = parser.parse_args()
    if args.command == 'index' and bool(args.env_file) != bool(args.model_slot):
        parser.error('--env-file and --model-slot must be provided together')
    if args.command == 'experiment' and bool(args.env_file) != bool(args.model_slot):
        parser.error('--env-file and --model-slot must be provided together')
    if args.command == 'experiment' and bool(args.tokenizer) != (args.context_tokens is not None):
        parser.error('--context-tokens and --tokenizer must be provided together')
    if args.command == 'search' and bool(args.env_file) != bool(args.model_slot):
        parser.error('--env-file and --model-slot must be provided together')
    if args.command == 'search' and args.env_file and args.variant not in ('decision','role'):
        parser.error('a model requires the decision or role variant')
    if args.command == 'search' and bool(args.tokenizer) != (args.context_tokens is not None):
        parser.error('--context-tokens and --tokenizer must be provided together')
    db = open_catalog(args.db)
    try:
        if args.command == 'assess-role':
            from .decisions import assess_role
            from .openrouter import load_settings, OpenRouterDecision
            provider = OpenRouterDecision(load_settings(args.env_file,args.model_slot))
            result = assess_role(db,args.section_id,args.role,args.role_version,args.role_purpose,provider)
            print(json.dumps(result))
            return 0 if result['outcome'] != 'unknown' else 1
        if args.command == 'list-index':
            query = 'SELECT g.*,s.path,s.revision,p.page_start,p.page_end FROM generated_index g JOIN sections x ON x.id=g.section_id JOIN sources s ON s.id=x.source_id LEFT JOIN section_pages p ON p.section_id=x.id'
            params = ()
            if args.status:
                query += ' WHERE g.status=?'
                params = (args.status,)
            print(json.dumps([dict(row) for row in db.execute(query+' ORDER BY s.path,g.start_offset',params)]))
            return 0
        if args.command == 'review-index':
            from .indexing import review_generated_entry
            review_generated_entry(db,args.entry_id,args.decision,args.reviewer)
            print(json.dumps({'entry_id':args.entry_id,'decision':args.decision,'reviewer':args.reviewer}))
            return 0
        if args.command == 'ingest':
            source_id = ingest(db,args.path)
            print(json.dumps({'source_id':source_id}))
            return 0 if source_id else 1
        if args.command == 'index':
            from .indexing import index_source
            provider = None
            if args.env_file:
                from .openrouter import load_settings, OpenRouterDecision
                provider = OpenRouterDecision(load_settings(args.env_file,args.model_slot))
            result = index_source(db,args.path,provider=provider,max_decisions=args.max_decisions)
            print(json.dumps(result))
            return 0 if result['source_id'] else 1
        if args.command == 'experiment':
            from .experiment import run_experiment
            provider = None
            if args.env_file:
                from .openrouter import load_settings, OpenRouterDecision
                provider = OpenRouterDecision(load_settings(args.env_file,args.model_slot))
            tasks = json.loads(Path(args.tasks).read_text(encoding='utf-8'))
            indexing_receipts = json.loads(Path(args.indexing_receipts).read_text(encoding='utf-8')) if args.indexing_receipts else None
            count_tokens = None
            if args.tokenizer:
                import tiktoken
                encoding = tiktoken.get_encoding(args.tokenizer)
                count_tokens = lambda text: len(encoding.encode_ordinary(text))
            context_chars = args.context_chars if args.context_chars is not None else (None if args.context_tokens is not None else 4000)
            print(json.dumps(run_experiment(db,tasks,provider=provider,context_chars=context_chars,context_tokens=args.context_tokens,count_tokens=count_tokens,tokenizer_name=args.tokenizer,limit=args.limit,label_provenance=args.label_provenance,include_proposed=args.include_proposed,indexing_receipt_ids=indexing_receipts)))
            return 0
        provider = None
        if args.env_file:
            from .openrouter import load_settings, OpenRouterDecision
            provider = OpenRouterDecision(load_settings(args.env_file,args.model_slot))
        count_tokens = None
        if args.tokenizer:
            import tiktoken
            encoding = tiktoken.get_encoding(args.tokenizer)
            count_tokens = lambda text: len(encoding.encode_ordinary(text))
        print(json.dumps(search(db,args.query,variant=args.variant,role=args.role,role_version=args.role_version,provider=provider,context_chars=args.context_chars,include_proposed=args.include_proposed,context_tokens=args.context_tokens,count_tokens=count_tokens)))
        return 0
    finally:
        db.close()

if __name__ == '__main__':
    raise SystemExit(main())
