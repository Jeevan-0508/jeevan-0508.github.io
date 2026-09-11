#!/usr/bin/env python3
"""Keep the portfolio page true and current.

Two jobs, no dependencies, no model:

  figures   recount every quoted number from the source data of the repository
            it describes, and rewrite the page if the truth has moved
  activity  regenerate the "Latest" section from real push events and the
            newest FOMO signals

Deliberately writes no timestamp anywhere: the page changes only when the
underlying facts change, so a run with nothing to say produces no commit.
"""
import io, json, os, re, sys, urllib.request
from collections import Counter

RAW = 'https://raw.githubusercontent.com/Jeevan-0508'
API = 'https://api.github.com'
USER = 'Jeevan-0508'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'index.html')

# One li per entry; the template owns the wording so the number can never
# drift out of step with the sentence around it.
TEMPLATES = {
    'patterns':          '{v} patterns',
    'categories':        '{v} categories',
    'indicators':        '{v} indicators',
    'false_positives':   '{v} documented false positives',
    'countermeasures':   '{v} countermeasures',
    'sources':           '{v} public sources',
    'indicators_scored': '{v} indicators scored',
    'post_event_pct':    '{v}% of detection weight lands after the loss',
    'frameworks':        '{v} frameworks',
    'requirements':      '{v} cited requirements',
    'controls':          '{v} controls',
    'evidence':          '{v} evidence artefacts',
    'req_links':         '{v} requirement links',
}

# The 9 repos carrying the daily inspect_site / check_figures bots. Only
# these are polled for open findings -- adding a repo to the site elsewhere
# doesn't put it on this list.
MONITORED_REPOS = [
    'dora-compliance-scanner', 'freight-fraud-taxonomy', 'freight-risk-atlas',
    'ai-governance-control-room', 'gdpr-compliance-scanner', 'eu-ai-act-scanner',
    'risk-os', 'FOMO', 'shrink-signal',
]


def get(url, accept='application/json'):
    req = urllib.request.Request(url, headers={
        'Accept': accept,
        'User-Agent': 'jeevan-0508-portfolio-refresh',
    })
    token = os.environ.get('GITHUB_TOKEN')
    if token and url.startswith(API):
        req.add_header('Authorization', 'Bearer ' + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def count_figures():
    # The atlas ships a byte-identical copy of the taxonomy model, so one
    # fetch covers every taxonomy figure.
    tax = get(RAW + '/freight-risk-atlas/main/docs/taxonomy.json')['patterns']
    fw = get(RAW + '/ai-governance-control-room/main/data/frameworks.json')['frameworks']
    ctl = get(RAW + '/ai-governance-control-room/main/data/controls.json')['controls']

    counter = lambda key: sum(len(p.get(key) or []) for p in tax)
    cms = sum(len(v) for p in tax for v in (p.get('countermeasures') or {}).values())
    refs = {r if isinstance(r, str) else (r.get('url') or r.get('title'))
            for p in tax for r in (p.get('references') or [])}

    weight = Counter()
    for p in tax:
        for i in p['indicators']:
            weight[i['phase']] += i['weight']
    total = sum(weight.values())

    reqs = [r for f in fw for r in f['requirements']]
    return {
        'patterns': len(tax),
        'categories': len({p['category'] for p in tax}),
        'indicators': counter('indicators'),
        'false_positives': counter('false_positives'),
        'countermeasures': cms,
        'sources': len(refs),
        'indicators_scored': counter('indicators'),
        'post_event_pct': round(weight['post_event'] / total * 100),
        'frameworks': len(fw),
        'requirements': len(reqs),
        'controls': len(ctl),
        'evidence': sum(len(c.get('evidence') or []) for c in ctl),
        'req_links': sum(len(c.get('satisfies') or []) for c in ctl),
    }


def apply_figures(html, figures):
    changed = []

    def repl(m):
        key, current = m.group(1), m.group(2)
        if key not in TEMPLATES:
            print('WARN unknown data-fig on the page: ' + key, file=sys.stderr)
            return m.group(0)
        wanted = TEMPLATES[key].format(v=figures[key])
        if wanted != current:
            changed.append((key, current, wanted))
        return '<li data-fig="%s">%s</li>' % (key, wanted)

    html = re.sub(r'<li data-fig="([a-z_]+)">(.*?)</li>', repl, html)
    unused = set(TEMPLATES) - set(re.findall(r'data-fig="([a-z_]+)"', html))
    for key in sorted(unused):
        print('WARN template %s is never used on the page' % key, file=sys.stderr)
    return html, changed


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def recent_commits(limit=5):
    """Latest commit per repository, most recently pushed first.

    The public events feed no longer carries commit messages, so ask each
    repository directly.
    """
    repos = get('%s/users/%s/repos?per_page=100&sort=pushed' % (API, USER))
    out = []
    for r in repos:
        if r['fork'] or r['archived'] or r['private']:
            continue
        try:
            commits = get('%s/repos/%s/commits?per_page=1' % (API, r['full_name']))
        except Exception as e:                     # a repo with no commits yet
            print('WARN %s: %s' % (r['name'], e), file=sys.stderr)
            continue
        if not commits:
            continue
        c = commits[0]['commit']
        out.append({'repo': r['name'],
                    'subject': c['message'].split('\n')[0].strip(),
                    'date': (c['author'] or c['committer'])['date'][:10]})
        if len(out) >= limit:
            break
    return out


def recent_signals(limit=5):
    data = get(RAW + '/FOMO/main/data/signals.json')['signals']
    data.sort(key=lambda s: s.get('found_at') or '', reverse=True)
    out, seen, cats = [], set(), set()
    for s in data:
        # Google News titles carry a trailing " - Publisher"; the publisher is
        # already a field, so drop the duplicate.
        title = re.sub(r'\s+-\s+[^-]{2,40}$', '', s['title']).strip()
        cat = s.get('category') or ''
        # one headline per risk category, so the strip shows the breadth of
        # what FOMO watches rather than five variations of the same story
        if title in seen or cat in cats:
            continue
        seen.add(title)
        cats.add(cat)
        out.append({'title': title, 'source': s.get('source') or '',
                    'category': s.get('category') or '', 'link': s['link']})
        if len(out) >= limit:
            break
    return out


def bot_reports(limit=8):
    """Open inspect_site / check_figures findings across the monitored repos.

    Each bot closes its own issue on the next clean run, so 'open' is the
    whole signal -- nothing here is ever stale by more than a day.
    """
    out = []
    for repo in MONITORED_REPOS:
        try:
            issues = get('%s/repos/%s/%s/issues?labels=inspection,figures&state=open'
                          % (API, USER, repo))
        except Exception as e:
            print('WARN %s: %s' % (repo, e), file=sys.stderr)
            continue
        for i in issues:
            if 'pull_request' in i:
                continue
            label = next((l['name'] for l in i['labels']
                          if l['name'] in ('inspection', 'figures')), 'bot')
            out.append({'repo': repo, 'title': i['title'], 'url': i['html_url'],
                        'label': label, 'date': i['updated_at'][:10]})
    out.sort(key=lambda x: x['date'], reverse=True)
    return out[:limit]


def render_activity(pushes, signals):
    rows = ''.join(
        '<li><b>%s</b> <span>%s</span><i>%s</i></li>' % (esc(p['repo']), esc(p['subject']), esc(p['date']))
        for p in pushes) or '<li><span>No recent public pushes.</span></li>'
    news = ''.join(
        '<li><a href="%s" rel="nofollow noopener">%s</a><i>%s%s</i></li>' % (
            esc(s['link']), esc(s['title']), esc(s['category']),
            ' &middot; ' + esc(s['source']) if s['source'] else '')
        for s in signals) or '<li><span>No signals yet.</span></li>'
    return (
        '<div class="inner two">\n'
        '      <div><h4>Latest commits</h4><ul class="feed">%s</ul></div>\n'
        '      <div><h4>Freight risk signals <em>from FOMO</em></h4><ul class="feed">%s</ul></div>\n'
        '    </div>' % (rows, news))


def render_bots(reports):
    rows = ''.join(
        '<li><b>%s</b> <a href="%s" rel="nofollow noopener">%s</a><i>%s &middot; %s</i></li>' % (
            esc(r['repo']), esc(r['url']), esc(r['title']), esc(r['label']), esc(r['date']))
        for r in reports) or (
        '<li><span>No open findings across the 9 monitored repos &mdash; all clean.</span></li>')
    return '<div class="inner"><ul class="feed">%s</ul></div>' % rows


def splice(html, block, name='activity'):
    a, b = '<!-- %s:start -->' % name, '<!-- %s:end -->' % name
    i, j = html.index(a) + len(a), html.index(b)
    new = '\n    ' + block + '\n    '
    return html[:i] + new + html[j:], html[i:j] != new


def main():
    html = original = io.open(PAGE, encoding='utf-8').read()

    figures = count_figures()
    html, changed = apply_figures(html, figures)
    for key, was, now in changed:
        print('FIGURE %-18s %r -> %r' % (key, was, now))
    if not changed:
        print('figures: all %d already correct' % len(TEMPLATES))

    html, moved = splice(html, render_activity(recent_commits(), recent_signals()))
    print('activity: %s' % ('updated' if moved else 'unchanged'))

    html, bots_moved = splice(html, render_bots(bot_reports()), name='bots')
    print('bots: %s' % ('updated' if bots_moved else 'unchanged'))

    if html == original:
        print('nothing to commit')
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
    print('index.html rewritten')
    return 0


if __name__ == '__main__':
    sys.exit(main())
