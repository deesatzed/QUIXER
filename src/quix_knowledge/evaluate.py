"""Small evaluation primitives; labels must be independently prepared for claims."""
def evaluate(labels, results):
    if set(labels) != set(results):
        raise ValueError('query IDs differ')
    recalls=[]
    unsupported=0
    for query, relevant in labels.items():
        rows=results[query]
        unsupported += sum(bool(row.get('unsupported')) for row in rows)
        if relevant:
            recalls.append(len(set(relevant) & {row['id'] for row in rows}) / len(set(relevant)))
    return {'answerable':len(recalls),'unanswerable':len(labels)-len(recalls),'mean_recall':sum(recalls)/len(recalls) if recalls else None,'unsupported_returned':unsupported}
