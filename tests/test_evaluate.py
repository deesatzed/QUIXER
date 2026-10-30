from quix_knowledge.evaluate import evaluate

def test_evaluation_excludes_unanswerable_and_counts_unsupported():
    labels = {'q1':['a','b'], 'q2':[]}
    results = {'q1':[{'id':'a','unsupported':True}], 'q2':[]}
    report = evaluate(labels,results)
    assert report['answerable'] == 1
    assert report['unanswerable'] == 1
    assert report['mean_recall'] == 0.5
    assert report['unsupported_returned'] == 1
