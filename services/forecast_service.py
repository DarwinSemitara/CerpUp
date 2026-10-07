"""Yearly ARIMA forecasts for research, extension, and admin work volume."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import logging
import math

logger = logging.getLogger(__name__)

PAPER_TYPES = {
    'oral_poster', 'proceedings', 'monographs', 'monograph',
    'journals', 'journal_article', 'chapters', 'book_chapter',
    'books', 'book', 'others_creative',
}
PROJECT_TYPES = {'proposal', 'implementation', 'research'}
HORIZON = 3
# Sample yearly counts with trendy spikes and lows for realistic visualization
USE_SAMPLE_SERIES = True
SAMPLE_SERIES = {
    # Upward trend with fluctuations
    'research': [12, 15, 18, 14, 22, 19, 25, 28, 24, 30],
    'extensions': [20, 18, 25, 22, 28, 24, 32, 30, 35, 38],  # Strong growth
    'admin': [8, 6, 10, 12, 9, 15, 13, 18, 16, 20],  # Growth with dips
}


def _parse_year(value) -> int | None:
    if not value:
        return None
    text = str(value).strip()
    if len(text) >= 9 and text[4] == '-':
        try:
            return int(text[:4])
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
        return dt.year
    except (ValueError, TypeError):
        return None


def _safe_rows(execute_fn):
    try:
        result = execute_fn()
        return result.data or []
    except Exception as e:
        logger.warning('Forecast query failed: %s', e)
        return []


def _row_matches_member(row, member_id, uid) -> bool:
    if not member_id and not uid:
        return True
    row_member = row.get('member_id')
    row_uid = row.get('uid')
    if member_id and row_member == member_id:
        return True
    if uid and row_uid == uid:
        return True
    return False


def _firestore_rows(stream_fn):
    rows = []
    try:
        for doc in stream_fn():
            item = doc.to_dict() or {}
            item['id'] = getattr(doc, 'id', None)
            rows.append(item)
    except Exception as e:
        logger.warning('Forecast Firestore query failed: %s', e)
    return rows


def collect_yearly_volume(supabase, db, member_id=None, uid=None) -> dict:
    """Count research papers, extensions, and admin works per calendar/academic year."""
    research = defaultdict(int)
    extensions = defaultdict(int)
    admin = defaultdict(int)
    seen_research = set()
    seen_ext = set()

    def add_research(rows):
        for row in rows:
            rid = row.get('id')
            if rid and rid in seen_research:
                continue
            if rid:
                seen_research.add(rid)
            if not _row_matches_member(row, member_id, uid):
                continue
            year = (
                _parse_year(row.get('date_completion'))
                or _parse_year(row.get('end_date'))
                or _parse_year(row.get('start_date'))
                or _parse_year(row.get('created_at'))
            )
            if not year:
                continue
            rtype = (row.get('research_type')
                     or 'implementation').strip().lower()
            if rtype in PAPER_TYPES:
                research[year] += 1
            elif rtype in PROJECT_TYPES:
                research[year] += 1
            else:
                research[year] += 1

    def add_extensions(rows):
        for row in rows:
            eid = row.get('id')
            if eid and eid in seen_ext:
                continue
            if eid:
                seen_ext.add(eid)
            if not _row_matches_member(row, member_id, uid):
                continue
            year = (
                _parse_year(row.get('start_date'))
                or _parse_year(row.get('created_at'))
                or _parse_year(row.get('date_submitted'))
            )
            if year:
                extensions[year] += 1

    research_query = supabase.table('research').select(
        'id, member_id, uid, research_type, created_at, start_date, end_date, date_completion')
    if member_id:
        research_query = research_query.eq('member_id', member_id)
    add_research(_safe_rows(lambda: research_query.execute()))
    add_research(_firestore_rows(lambda: db.collection('research').stream()))

    ext_query = supabase.table('extensions').select(
        'id, member_id, uid, created_at, start_date')
    if member_id:
        ext_query = ext_query.eq('member_id', member_id)
    add_extensions(_safe_rows(lambda: ext_query.execute()))
    add_extensions(_firestore_rows(
        lambda: db.collection('extensions').stream()))

    fsr_query = supabase.table('fsr_files').select(
        'id, member_id, academic_year, semester, deleted_at')
    if member_id:
        fsr_query = fsr_query.eq('member_id', member_id)
    for row in _safe_rows(lambda: fsr_query.execute()):
        if row.get('deleted_at'):
            continue
        year = _parse_year(row.get('academic_year'))
        if year:
            admin[year] += 1

    current = datetime.now(timezone.utc).year
    years_present = set(research) | set(extensions) | set(admin)
    start = current - 4
    if years_present:
        start = min(start, max(min(years_present), current - 11))
    if USE_SAMPLE_SERIES:
        start = current - (len(SAMPLE_SERIES['research']) - 1)
    years = list(range(start, current + 1))

    def series(bucket):
        return [int(bucket.get(year, 0)) for year in years]

    volume = {
        'years': years,
        'research': series(research),
        'extensions': series(extensions),
        'admin': series(admin),
        'current_year': current,
        'demo': False,
    }
    if USE_SAMPLE_SERIES:
        n = len(years)
        for key, sample in SAMPLE_SERIES.items():
            if n <= len(sample):
                volume[key] = list(sample[-n:])
            else:
                volume[key] = [0] * (n - len(sample)) + list(sample)
        volume['demo'] = True
    return volume


def _naive_forecast(values, horizon):
    last = float(values[-1]) if values else 0.0
    slope = 0.0
    if len(values) >= 2:
        slope = (float(values[-1]) - float(values[0])) / \
            max(len(values) - 1, 1)
    mean = [max(0.0, last + slope * (i + 1)) for i in range(horizon)]
    lower = [max(0.0, v * 0.6) for v in mean]
    upper = [v * 1.4 + 1 for v in mean]
    return mean, lower, upper, 'naive-trend'


def forecast_series(values, horizon=HORIZON):
    """Fit a small ARIMA grid; fall back to a trend if the series is too short."""
    y = [max(0.0, float(v)) for v in values]
    if len(y) < 4 or sum(y) == 0:
        return _naive_forecast(y, horizon)

    try:
        from statsmodels.tsa.arima.model import ARIMA
        import warnings
        warnings.filterwarnings('ignore')
    except Exception as e:
        logger.warning('statsmodels unavailable (%s); using trend forecast', e)
        return _naive_forecast(y, horizon)

    estimators = ('innovations_mle', 'hannan_rissanen')
    candidates = (
        ((0, 1, 0), 't'),
        ((1, 1, 0), 't'),
        ((1, 0, 0), 't'),
        ((0, 1, 1), 't'),
        ((1, 1, 0), None),
        ((0, 1, 0), None),
        ((1, 0, 0), None),
    )
    best = None
    best_aic = math.inf
    best_order = (1, 1, 0)
    best_trend = None
    for order, trend in candidates:
        for method in estimators:
            try:
                kwargs = {'order': order}
                if trend:
                    kwargs['trend'] = trend
                fitted = ARIMA(y, **kwargs).fit(method=method)
                if fitted.aic < best_aic:
                    best = fitted
                    best_aic = fitted.aic
                    best_order = order
                    best_trend = trend
                break
            except Exception:
                continue

    if best is None:
        return _naive_forecast(y, horizon)

    try:
        fc = best.get_forecast(horizon)
        mean = [max(0.0, float(v)) for v in fc.predicted_mean]
        ci = fc.conf_int(alpha=0.2)
        lower = []
        upper = []
        for i in range(horizon):
            if hasattr(ci, 'iloc'):
                lo, hi = float(ci.iloc[i, 0]), float(ci.iloc[i, 1])
            else:
                lo, hi = float(ci[i][0]), float(ci[i][1])
            lower.append(max(0.0, lo))
            upper.append(max(mean[i], hi))
        tag = f'ARIMA{best_order}'
        if best_trend:
            tag += f'+{best_trend}'
        return mean, lower, upper, tag
    except Exception:
        return _naive_forecast(y, horizon)


def build_forecast_payload(supabase, db, member_id=None, uid=None) -> dict:
    volume = collect_yearly_volume(supabase, db, member_id=member_id, uid=uid)
    years = volume['years']
    current = volume['current_year']
    future_years = [current + i for i in range(1, HORIZON + 1)]
    series_keys = ('research', 'extensions', 'admin')
    forecasts = {}
    models = {}
    mix = {}
    prev_mix = {}  # Previous year values

    # When using sample data, use fast naive forecasts instead of ARIMA
    use_fast_forecast = volume.get('demo', False)

    for key in series_keys:
        hist = volume[key]
        mix[key] = hist[-1] if hist else 0  # Current year (last value)
        # Previous year (second-to-last)
        prev_mix[key] = hist[-2] if len(hist) >= 2 else 0

        if use_fast_forecast:
            # Fast trend-based forecast for sample data
            mean, lower, upper, model = _naive_forecast(hist, HORIZON)
        else:
            # Full ARIMA forecast for real data
            mean, lower, upper, model = forecast_series(hist)

        forecasts[key] = {
            'mean': [round(v, 1) for v in mean],
            'lower': [round(v, 1) for v in lower],
            'upper': [round(v, 1) for v in upper],
        }
        models[key] = model

    return {
        'years': years,
        'future_years': future_years,
        'historical': {key: volume[key] for key in series_keys},
        'forecast': forecasts,
        'models': models,
        'horizon': HORIZON,
        'current_year': current,
        'previous_year': current - 1,  # Add previous year
        'mix': mix,
        'prev_mix': prev_mix,  # Add previous year values
        'demo': bool(volume.get('demo')),
        'next_year': {
            key: forecasts[key]['mean'][0] if forecasts[key]['mean'] else 0
            for key in series_keys
        },
    }
