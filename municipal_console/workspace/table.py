from urllib.parse import urlencode
from django.urls import reverse
from .models import ASSESSMENTS, STATUSES


def control_table(params, audit, role, all_rows, it_label):
    """Filter only the data already projected for the viewer's permissions."""
    show_response = role != 'intern'
    show_evaluation = role in ('admin', 'auditor', 'executive')
    risk_choices = [('high', 'Yüksek'), ('medium', 'Orta'), ('low', 'Düşük')]
    filters = [
        ('framework', 'Referans', [(v, v) for v in sorted({r['framework'] for r in all_rows})]),
        ('theme', 'Tema', [(v, v) for v in sorted({r['theme'] for r in all_rows})]),
        ('risk', 'Risk', risk_choices),
    ]
    if show_response:
        filters.append(('status', 'BT yanıtı', STATUSES))
    if show_evaluation:
        filters.extend([
            ('assessment', 'Denetçi görüşü', ASSESSMENTS),
            ('verified', 'Son test onayı', [('yes', 'Onaylandı'), ('no', 'Onay bekliyor')]),
        ])
    selected = {key: params.get(key, '') if params.get(key, '') in dict(choices) else ''
                for key, label, choices in filters}
    q = params.get('q', '').strip()[:100]
    rows = []
    for row in all_rows:
        ev = row.get('evaluation') or {}
        values = {**row, 'assessment': ev.get('assessment', 'pending'), 'verified': 'yes' if ev.get('verified') else 'no'}
        if q and q.casefold() not in ' '.join(row[k] for k in ('code', 'title', 'framework', 'theme')).casefold():
            continue
        if any(value and values.get(key) != value for key, value in selected.items()):
            continue
        rows.append(row)

    sort_fields = [('code', 'Kontrol kodu'), ('title', 'Kontrol adı'), ('framework', 'Referans'), ('risk', 'Risk (yüksek → düşük)')]
    if show_response: sort_fields.append(('status', 'BT yanıtı'))
    if show_evaluation: sort_fields.append(('assessment', 'Denetçi görüşü'))
    sort_choices = [(prefix+key, label+(' · ters sıra' if prefix else '')) for key, label in sort_fields for prefix in ('', '-')]
    sort = params.get('sort', 'code')
    if sort not in dict(sort_choices): sort = 'code'
    key = sort.lstrip('-')
    ranks = {
        'risk': {'high': 0, 'medium': 1, 'low': 2},
        'status': {value: i for i, value in enumerate(('unanswered', 'missing', 'partial', 'implemented', 'na'))},
        'assessment': {value: i for i, value in enumerate(('pending', 'noncompliant', 'partial', 'compliant'))},
    }

    def sort_key(row):
        value = (row.get('evaluation') or {}).get('assessment', 'pending') if key == 'assessment' else row[key]
        return (ranks[key][value] if key in ranks else value.casefold(), row['code'].casefold(), row['id'])

    rows.sort(key=sort_key, reverse=sort.startswith('-'))
    query = {'audit': audit.pk, **{k: v for k, v in selected.items() if v}}
    if q: query['q'] = q
    headers = [('code', 'Kontrol / Referans'), ('risk', 'Risk')]
    if show_response: headers.append(('status', it_label+' yanıtı'))
    if show_evaluation: headers.append(('assessment', 'Denetçi görüşü'))
    sort_headers = []
    for field, label in headers:
        active = key == field or (field == 'code' and key in ('title', 'framework'))
        descending = sort.startswith('-')
        next_sort = ('-' if not descending else '')+key if active else field
        sort_headers.append({
            'label': label,
            'url': reverse('console')+'?'+urlencode({**query, 'sort': next_sort})+'#controls',
            'aria': ('descending' if descending else 'ascending') if active else 'none',
            'arrow': ('↓' if descending else '↑') if active else '↕',
        })
    return rows, {
        'q': q, 'sort': sort, 'sort_choices': sort_choices, 'sort_headers': sort_headers,
        'control_filters': [{'name': k, 'label': label, 'choices': choices, 'value': selected[k]} for k, label, choices in filters],
        'filtered_count': len(rows), 'filters_active': bool(q or any(selected.values()) or sort != 'code'),
        'clear_filters_url': reverse('console')+'?'+urlencode({'audit': audit.pk})+'#controls',
    }
