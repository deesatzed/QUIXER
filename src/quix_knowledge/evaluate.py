"""Small evaluation primitives; labels must be independently prepared for claims."""
def evaluate(labels, results):
    if set(labels) != set(results):
        raise ValueError('query IDs differ')
    recalls=[]
    precisions=[]
    unsupported=0
    stale=0
    unlabeled=0
    unanswerable=0
    for query, relevant in labels.items():
        rows=results[query]
        unsupported += sum(bool(row.get('unsupported')) for row in rows)
        stale += sum(row.get('evidence_status') == 'stale' or row.get('source_status') in ('superseded','invalidated') for row in rows)
        if relevant is None:
            unlabeled += 1
        elif not relevant:
            unanswerable += 1
            if rows:
                precisions.append(0.0)
        else:
            matched = len(set(relevant) & {row['id'] for row in rows})
            recalls.append(matched / len(set(relevant)))
            precisions.append(matched / len(rows) if rows else 0.0)
    return {'answerable':len(recalls),'unanswerable':unanswerable,'unlabeled':unlabeled,'mean_recall':sum(recalls)/len(recalls) if recalls else None,'mean_precision':sum(precisions)/len(precisions) if precisions else None,'unsupported_returned':unsupported,'stale_returned':stale}

def compare_runs(labels, runs):
    if not runs:
        raise ValueError('no runs')
    revisions = {run['corpus_revision'] for run in runs.values()}
    if len(revisions) != 1:
        raise ValueError('corpus revisions differ')
    return {'corpus_revision':revisions.pop(),'variants':{name:evaluate(labels,run['results']) for name,run in runs.items()}}
