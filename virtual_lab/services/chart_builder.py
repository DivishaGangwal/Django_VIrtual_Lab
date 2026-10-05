"""
Chart Data Builder (pure Python).

Turns the active dataset into ready-to-plot {labels, datasets} payloads for
Chart.js. All grouping/aggregation happens here on the server so students can
see how Python prepares data for visualisation.
"""

from collections import Counter, OrderedDict
from typing import Any, Dict, List, Optional

from .csv_parser import is_missing
from .stats_engine import to_number

CHART_TYPES = ('bar', 'line', 'pie', 'doughnut', 'scatter', 'histogram')
AGGREGATIONS = ('none', 'sum', 'mean', 'count', 'min', 'max')
MAX_CATEGORIES = 30


class ChartBuildError(ValueError):
    pass


def _aggregate(values: List[float], agg: str) -> Optional[float]:
    if agg == 'count':
        return float(len(values))
    if not values:
        return None
    if agg == 'sum':
        return round(sum(values), 3)
    if agg == 'mean':
        return round(sum(values) / len(values), 3)
    if agg == 'min':
        return min(values)
    if agg == 'max':
        return max(values)
    raise ChartBuildError(f'Unknown aggregation: {agg}')


def build_chart_data(
    headers: List[str],
    rows: List[Dict[str, str]],
    chart_type: str,
    x: str,
    y_columns: List[str],
    agg: str = 'none',
    bins: int = 8,
) -> Dict[str, Any]:
    if chart_type not in CHART_TYPES:
        raise ChartBuildError(f'Unsupported chart type: {chart_type}')
    if agg not in AGGREGATIONS:
        raise ChartBuildError(f'Unsupported aggregation: {agg}')
    for col in [x, *y_columns]:
        if col and col not in headers:
            raise ChartBuildError(f"Column '{col}' does not exist in the dataset.")

    # Histogram: distribution of ONE numeric column (x).
    if chart_type == 'histogram':
        nums = [n for n in (to_number(r.get(x, '')) for r in rows) if n is not None]
        if not nums:
            raise ChartBuildError(f"Column '{x}' has no numeric values to bin.")
        bins = max(1, min(int(bins), 50))
        lo, hi = min(nums), max(nums)
        width = (hi - lo) / bins or 1
        counts = [0] * bins
        for n in nums:
            counts[min(int((n - lo) / width), bins - 1)] += 1
        labels = [f'{round(lo + i * width, 2)}–{round(lo + (i + 1) * width, 2)}' for i in range(bins)]
        return {'chart_type': 'bar', 'labels': labels, 'is_histogram': True,
                'datasets': [{'label': f'Frequency of {x}', 'data': counts}],
                'x_label': x, 'y_label': 'Frequency'}

    # Scatter: numeric x vs numeric y (first y column).
    if chart_type == 'scatter':
        if not y_columns:
            raise ChartBuildError('Scatter plots need a Y column.')
        datasets = []
        for y in y_columns:
            points = []
            for r in rows:
                xv, yv = to_number(r.get(x, '')), to_number(r.get(y, ''))
                if xv is not None and yv is not None:
                    points.append({'x': xv, 'y': yv})
            if not points:
                raise ChartBuildError(f"'{x}' and '{y}' must both be numeric for a scatter plot.")
            datasets.append({'label': f'{y} vs {x}', 'data': points})
        return {'chart_type': 'scatter', 'labels': [], 'datasets': datasets,
                'x_label': x, 'y_label': ', '.join(y_columns)}

    # Pie / doughnut with no Y: frequency of each category in X.
    if chart_type in ('pie', 'doughnut') and not y_columns:
        counts = Counter(r.get(x, '') for r in rows if not is_missing(r.get(x, '')))
        top = counts.most_common(MAX_CATEGORIES)
        return {'chart_type': chart_type, 'labels': [k for k, _ in top],
                'datasets': [{'label': f'Count of {x}', 'data': [v for _, v in top]}],
                'x_label': x, 'y_label': 'Count'}

    if not y_columns:
        y_columns = []
        agg = 'count'

    if chart_type in ('pie', 'doughnut'):
        y_columns = y_columns[:1]  # one series only

    # Bar / line / pie with Y columns.
    if agg == 'none':
        labels = [r.get(x, '') for r in rows][:500]
        datasets = [{'label': y, 'data': [to_number(r.get(y, '')) for r in rows][:500]} for y in y_columns]
    else:
        groups: 'OrderedDict[str, List[Dict[str, str]]]' = OrderedDict()
        for r in rows:
            key = r.get(x, '')
            if is_missing(key):
                continue
            groups.setdefault(key, []).append(r)
        if len(groups) > MAX_CATEGORIES * 4:
            raise ChartBuildError(
                f"'{x}' has {len(groups)} distinct values — too many groups. "
                "Pick a categorical column or use aggregation 'none'.")
        labels = list(groups.keys())
        if agg == 'count' and not y_columns:
            datasets = [{'label': f'Count of {x}', 'data': [len(g) for g in groups.values()]}]
        else:
            datasets = []
            for y in y_columns:
                data = []
                for g in groups.values():
                    nums = [n for n in (to_number(r.get(y, '')) for r in g) if n is not None]
                    data.append(_aggregate(nums, agg) if agg != 'count' else len(nums))
                datasets.append({'label': f'{agg}({y})', 'data': data})

    return {'chart_type': chart_type, 'labels': labels, 'datasets': datasets,
            'x_label': x, 'y_label': ', '.join(y_columns) or 'Count'}
