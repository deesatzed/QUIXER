"""Build a small, source-anchored packet for HITMCockpit's bounded planner."""
from .context import build_context_packet, serialize_packet


def make_agent_packet(task, rows, *, fingerprint, body_characters=300, result_limit=1):
    if type(body_characters) is not int or body_characters < 1 or type(result_limit) is not int or not 1 <= result_limit <= 100:
        raise ValueError('invalid body budget or result limit')
    selected=[]
    for original in rows[:result_limit]:
        row=dict(original)
        text=row.get('body','')
        if not isinstance(text,str):
            raise ValueError('invalid evidence body')
        row['body']=text[:body_characters]
        row['context_truncated']=bool(row.get('context_truncated') or row.get('body_truncated')) or len(text)>body_characters
        selected.append(row)
    packet=build_context_packet(task['query'],task['role'],task['role_version'],selected,budget=10000,
        count_tokens=len,tokenizer_name='json-characters',catalog_fingerprint=fingerprint)
    packet['omitted_count']+=max(0,len(rows)-len(selected))
    if len(serialize_packet(packet))>10000:
        raise ValueError('packet exceeded budget after omitted results')
    return packet
