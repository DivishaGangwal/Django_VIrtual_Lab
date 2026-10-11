"""
Educational trace builder (pure Python).

Re-creates, for teaching purposes, the intermediate values of each stage that
the real services (csv_parser, stats_engine, chart_builder) go through, so the
Simulation page can show students HOW Django reads and visualizes a CSV.
It never changes the real results; it only describes them.
"""

import csv
import io
import json
import statistics
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from .csv_parser import MISSING_TOKENS, is_missing
from .stats_engine import to_number

BOM = b'\xef\xbb\xbf'
SNIFF_CANDIDATES = [(',', 'comma'), (';', 'semicolon'), ('\t', 'tab'), ('|', 'pipe')]
IN_MEMORY_LIMIT = 2_621_440  # Django FILE_UPLOAD_MAX_MEMORY_SIZE (2.5 MB)


def _detect_encoding(raw: bytes) -> str:
    for enc in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return 'utf-8'


def _fmt_num(v: float) -> Any:
    return round(v, 3) if isinstance(v, float) else v


def build_ingest_trace(
    raw: bytes,
    filename: str,
    content_type: str,
    source: str,
    text: str,
    parse_result: Dict[str, Any],
    stats: Dict[str, Any],
    session_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Describes the 6 ingestion stages for the stepper."""
    size = len(raw)
    has_bom = raw.startswith(BOM)
    encoding = _detect_encoding(raw)
    delimiter = parse_result['delimiter']

    # Stage 3: how often each candidate delimiter appears per line in the sample.
    lines = text.strip('\r\n').splitlines()
    sample_lines = lines[:10]
    candidates = []
    for ch, name in SNIFF_CANDIDATES:
        counts = [ln.count(ch) for ln in sample_lines]
        consistent = bool(counts) and counts[0] > 0 and len(set(counts)) == 1
        candidates.append({'char': ch, 'name': name, 'per_line': counts,
                           'total': sum(counts), 'consistent': consistent,
                           'chosen': ch == delimiter})

    # Stage 4: raw line -> tokens -> dict, for the first rows.
    headers_clean = parse_result['headers']
    raw_headers = next(csv.reader(io.StringIO(lines[0]), delimiter=delimiter), []) if lines else []
    row_steps = []
    for i, ln in enumerate(lines[1:8]):
        tokens = next(csv.reader(io.StringIO(ln), delimiter=delimiter), [])
        cells = (tokens + [''] * len(headers_clean))[:len(headers_clean)]
        row_steps.append({
            'line_no': i + 2,
            'raw_line': ln,
            'naive_split': ln.split(delimiter),
            'tokens': tokens,
            'row': {h: c.strip() for h, c in zip(headers_clean, cells)},
            'missing': [h for h, c in zip(headers_clean, cells) if is_missing(c)],
        })

    # Stage 5: type inference + one worked statistics example.
    columns = stats.get('columns', [])
    type_rows = [{'name': c['name'], 'type': c['type'], 'kind': c['kind'],
                  'missing': c.get('missing', 0)} for c in columns]
    example = None
    for c in columns:
        if c['kind'] == 'numeric' and not c.get('is_identifier'):
            nums = [n for n in (to_number(r.get(c['name'], '')) for r in parse_result['rows']) if n is not None]
            if nums:
                example = {
                    'column': c['name'], 'n': len(nums),
                    'first_values': nums[:8],
                    'sum': _fmt_num(sum(nums)),
                    'mean': _fmt_num(statistics.fmean(nums)),
                    'median': _fmt_num(statistics.median(nums)),
                    'min': min(nums), 'max': max(nums),
                    'std_dev': _fmt_num(statistics.stdev(nums)) if len(nums) > 1 else None,
                }
                break

    # Stage 6: what ends up in the session.
    session_payload = {
        'filename': filename, 'headers': headers_clean,
        'row_count': parse_result['row_count'], 'col_count': parse_result['col_count'],
        'delimiter': delimiter, 'rows': f"[{parse_result['row_count']} dicts]", 'stats': '{...}',
    }
    try:
        session_bytes = len(json.dumps({'rows': parse_result['rows'], 'stats': stats}).encode())
    except (TypeError, ValueError):
        session_bytes = None

    return {
        'upload': {
            'filename': filename, 'size': size, 'content_type': content_type, 'source': source,
            'class_name': 'InMemoryUploadedFile' if size <= IN_MEMORY_LIMIT else 'TemporaryUploadedFile',
            'in_memory_limit': IN_MEMORY_LIMIT,
            'method': 'POST' if source == 'upload' else 'GET',
        },
        'bytes': {
            'hex': ' '.join(f'{b:02x}' for b in raw[:48]),
            'repr': repr(raw[:48]),
            'has_bom': has_bom, 'encoding_used': encoding,
            'total': size,
            'decoded_preview': text[:120],
            'first_header_utf8': repr(raw.decode('utf-8', errors='replace').split(delimiter)[0][:20]),
            'first_header_utf8sig': repr(raw.decode('utf-8-sig', errors='replace').split(delimiter)[0][:20]),
        },
        'sniff': {
            'delimiter': delimiter, 'candidates': candidates,
            'sample': '\n'.join(sample_lines[:3]),
            'stringio_chars': len(text),
        },
        'tokenize': {
            'raw_headers': raw_headers, 'clean_headers': headers_clean,
            'rows': row_steps, 'missing_tokens': sorted(MISSING_TOKENS),
            'ragged_rows_count': parse_result.get('ragged_rows_count', 0),
        },
        'types': {'columns': type_rows, 'example': example},
        'session': {
            'key': session_key, 'payload': session_payload, 'approx_bytes': session_bytes,
        },
    }


def build_chart_trace(
    rows: List[Dict[str, str]],
    payload: Dict[str, Any],
    chart_type: str,
    x: str,
    y_columns: List[str],
    agg: str,
    bins: int,
) -> Dict[str, Any]:
    """Describes how the server turned rows into the chart payload."""
    params = {'type': chart_type, 'x': x, 'y': y_columns, 'agg': agg}
    if chart_type == 'histogram':
        params = {'type': chart_type, 'x': x, 'bins': bins}
    trace: Dict[str, Any] = {'params': params, 'mode': 'raw', 'groups': []}

    if chart_type == 'histogram':
        nums = [n for n in (to_number(r.get(x, '')) for r in rows) if n is not None]
        b = max(1, min(int(bins), 50))
        lo, hi = min(nums), max(nums)
        width = (hi - lo) / b or 1
        trace.update(mode='histogram', lo=lo, hi=hi, bins=b, width=round(width, 4), n=len(nums),
                     groups=[{'key': lbl, 'values': [], 'result': c, 'count': c}
                             for lbl, c in zip(payload['labels'], payload['datasets'][0]['data'])])
        return trace

    if chart_type == 'scatter':
        pts = payload['datasets'][0]['data'] if payload['datasets'] else []
        trace.update(mode='scatter', total_points=len(pts), points=pts[:8],
                     skipped=len(rows) - len(pts))
        return trace

    effective_agg = agg
    ycols = y_columns[:1] if chart_type in ('pie', 'doughnut') else y_columns
    if chart_type in ('pie', 'doughnut') and not ycols:
        counts = payload['datasets'][0]['data']
        trace.update(mode='category_count', agg='count',
                     groups=[{'key': k, 'values': [], 'result': v, 'count': v}
                             for k, v in zip(payload['labels'], counts)])
        return trace
    if not ycols:
        effective_agg = 'count'

    if effective_agg == 'none':
        trace.update(mode='raw', agg='none', total_rows=len(rows),
                     groups=[{'key': lab, 'values': [v], 'result': v, 'count': 1}
                             for lab, v in zip(payload['labels'][:6], payload['datasets'][0]['data'][:6])]
                     if payload['datasets'] else [])
        return trace

    groups: 'OrderedDict[str, List[Dict[str, str]]]' = OrderedDict()
    for r in rows:
        key = r.get(x, '')
        if is_missing(key):
            continue
        groups.setdefault(key, []).append(r)
    y = ycols[0] if ycols else None
    out = []
    results = payload['datasets'][0]['data'] if payload['datasets'] else []
    for i, (key, grp) in enumerate(list(groups.items())[:12]):
        nums = [n for n in (to_number(r.get(y, '')) for r in grp) if n is not None] if y else []
        out.append({'key': key, 'values': nums[:8], 'n_values': len(nums),
                    'count': len(grp), 'result': results[i] if i < len(results) else None})
    trace.update(mode='grouped', agg=effective_agg, y=y, n_groups=len(groups), groups=out)
    return trace
