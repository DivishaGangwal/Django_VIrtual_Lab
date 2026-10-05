"""
Statistics & Type-Inference Engine (pure Python, standard library only).

Infers a data type for every column (int / float / date / str) and computes
descriptive statistics with Python's `statistics` module.
"""

import statistics
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

from .csv_parser import is_missing

DATE_FORMATS = ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d.%m.%Y')


def to_number(value: str) -> Optional[float]:
    """Converts '1,234.5' / ' 42 ' to a float; returns None if not numeric."""
    if is_missing(value):
        return None
    try:
        return float(str(value).replace(',', '').strip())
    except ValueError:
        return None


def to_date(value: str) -> Optional[datetime]:
    if is_missing(value):
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def _is_int_like(value: str) -> bool:
    text = str(value).replace(',', '').strip()
    if text.startswith(('+', '-')):
        text = text[1:]
    return text.isdigit()


def infer_column_type(values: List[str]) -> str:
    """
    Returns 'int', 'float', 'date' or 'str'.
    A column gets a numeric/date type only if EVERY non-missing value fits it.
    """
    present = [v for v in values if not is_missing(v)]
    if not present:
        return 'str'
    if all(to_number(v) is not None for v in present):
        return 'int' if all(_is_int_like(v) for v in present) else 'float'
    if all(to_date(v) is not None for v in present):
        return 'date'
    return 'str'


def _round(x: Optional[float], digits: int = 3) -> Optional[float]:
    return None if x is None else round(x, digits)


def describe_column(name: str, values: List[str]) -> Dict[str, Any]:
    col_type = infer_column_type(values)
    missing = sum(1 for v in values if is_missing(v))
    info: Dict[str, Any] = {
        'name': name,
        'type': col_type,
        'count': len(values) - missing,
        'missing': missing,
        'unique': len({v for v in values if not is_missing(v)}),
    }

    if col_type in ('int', 'float'):
        nums = [n for n in (to_number(v) for v in values) if n is not None]
        info.update({
            'kind': 'numeric',
            'sum': _round(sum(nums)),
            'mean': _round(statistics.fmean(nums)),
            'median': _round(statistics.median(nums)),
            'min': _round(min(nums)),
            'max': _round(max(nums)),
            'range': _round(max(nums) - min(nums)),
            'std_dev': _round(statistics.stdev(nums)) if len(nums) > 1 else 0.0,
            'variance': _round(statistics.variance(nums)) if len(nums) > 1 else 0.0,
        })
        if len(nums) >= 4:
            q1, _, q3 = statistics.quantiles(nums, n=4)
            info.update({'q1': _round(q1), 'q3': _round(q3)})
        # Identifier columns (e.g. Student_ID: unique integers, named *id*) are
        # numbers but not measurements, so charts should not plot them by default.
        lowered = name.lower().replace(' ', '_')
        info['is_identifier'] = (
            col_type == 'int' and missing == 0 and info['unique'] == len(values)
            and (lowered == 'id' or lowered.endswith('_id') or lowered.startswith('id_') or lowered in ('roll_no', 'rollno', 'sr_no', 'serial_no'))
        )
    elif col_type == 'date':
        dates = [d for d in (to_date(v) for v in values) if d is not None]
        info.update({
            'kind': 'date',
            'min': min(dates).strftime('%Y-%m-%d'),
            'max': max(dates).strftime('%Y-%m-%d'),
            'span_days': (max(dates) - min(dates)).days,
        })
    else:
        counts = Counter(v for v in values if not is_missing(v))
        top = counts.most_common(5)
        info.update({
            'kind': 'categorical',
            'mode': top[0][0] if top else None,
            'top_values': [{'value': v, 'count': c} for v, c in top],
        })
    return info


def describe_dataset(headers: List[str], rows: List[Dict[str, str]]) -> Dict[str, Any]:
    columns = [describe_column(h, [r.get(h, '') for r in rows]) for h in headers]
    numeric = [c['name'] for c in columns if c.get('kind') == 'numeric']
    categorical = [c['name'] for c in columns if c.get('kind') == 'categorical']
    dates = [c['name'] for c in columns if c.get('kind') == 'date']
    total_cells = len(rows) * len(headers)
    total_missing = sum(c['missing'] for c in columns)
    return {
        'columns': columns,
        'numeric_columns': numeric,
        'categorical_columns': categorical,
        'date_columns': dates,
        'total_cells': total_cells,
        'total_missing': total_missing,
        'completeness_pct': round(100 * (total_cells - total_missing) / total_cells, 2) if total_cells else 0,
    }
