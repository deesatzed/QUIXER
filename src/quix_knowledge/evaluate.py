"""Small evaluation primitives; labels must be independently prepared for claims."""
def evaluate(labels, results):
    if set(labels) != set(results):
        raise ValueError('query IDs differ')
    recalls=[]
    unsupported=0
    unlabeled=0
    unanswerable=0
    for query, relevant in labels.items():
        rows=results[query]
        unsupported += sum(bool(row.get('unsupported')) for row in rows)
        if relevant is None:
            unlabeled += 1
        elif not relevant:
            unanswerable += 1
        else:
            recalls.append(len(set(relevant) & {row['id'] for row in rows}) / len(set(relevant)))
    return {'answerable':len(recalls),'unanswerable':unanswerable,'unlabeled':unlabeled,'mean_recall':sum(recalls)/len(recalls) if recalls else None,'unsupported_returned':unsupported}

def compare_runs(labels, runs):
    if not runs:
        raise ValueError('no runs')
    revisions = {run['corpus_revision'] for run in runs.values()}
    if len(revisions) != 1:
        raise ValueError('corpus revisions differ')
    return {'corpus_revision':revisions.pop(),'variants':{name:evaluate(labels,run['results']) for name,run in runs.items()}}
