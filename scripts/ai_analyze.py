#!/usr/bin/env python3
"""
AI Performance Analysis Script
Reads JMeter result.jtl, sends metrics to Google Gemini,
and generates an AI_Performance_Report.html for Jenkins publishing.
"""

import csv
import inspect
import os
import sys
import json
from datetime import datetime

try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai not installed. Run: pip install google-generativeai")
    sys.exit(1)


def parse_jtl(jtl_path):
    """Parse JMeter JTL CSV file and extract key metrics per endpoint."""
    if not os.path.exists(jtl_path):
        print(f"ERROR: JTL file not found at {jtl_path}")
        sys.exit(1)

    endpoints = {}
    total_samples = 0
    total_failures = 0

    with open(jtl_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = row.get('label', row.get('Label', 'Unknown'))
            elapsed = int(row.get('elapsed', row.get('Elapsed', 0)))
            success = row.get('success', row.get('Success', 'true')).strip().lower()
            response_code = row.get('responseCode', row.get('ResponseCode', ''))

            if label not in endpoints:
                endpoints[label] = {
                    'samples': 0, 'failures': 0,
                    'times': [], 'response_codes': []
                }

            endpoints[label]['samples'] += 1
            endpoints[label]['times'].append(elapsed)
            endpoints[label]['response_codes'].append(response_code)
            if success != 'true':
                endpoints[label]['failures'] += 1

            total_samples += 1
            if success != 'true':
                total_failures += 1

    # Calculate stats per endpoint
    stats = {}
    for label, data in endpoints.items():
        times = sorted(data['times'])
        n = len(times)
        if n == 0:
            continue
        avg = sum(times) / n
        p90 = times[int(n * 0.90) - 1] if n >= 10 else times[-1]
        p95 = times[int(n * 0.95) - 1] if n >= 10 else times[-1]
        p99 = times[int(n * 0.99) - 1] if n >= 10 else times[-1]
        error_pct = (data['failures'] / n) * 100

        stats[label] = {
            'samples': n,
            'failures': data['failures'],
            'error_pct': round(error_pct, 2),
            'avg_ms': round(avg, 2),
            'min_ms': times[0],
            'max_ms': times[-1],
            'p90_ms': p90,
            'p95_ms': p95,
            'p99_ms': p99
        }

    return stats, total_samples, total_failures


def build_prompt(stats, total_samples, total_failures, environment, build_number):
    """Build the prompt to send to Gemini."""
    error_rate = round((total_failures / total_samples) * 100, 2) if total_samples > 0 else 0

    important = sorted(
        stats.items(),
        key=lambda item: (item[1]["failures"], item[1]["samples"]),
        reverse=True
    )[:8]

    lines = [
        "You are an expert performance engineering analyst."
        " Analyze these JMeter results and return one concise report.",
        f"Build: {build_number}",
        f"Environment: {environment}",
        f"Requests: {total_samples}",
        f"Failures: {total_failures}",
        f"Error Rate: {error_rate}%",
        "Endpoint statistics (top 8 by failures/samples):"
    ]

    for label, s in important:
        lines.append(
            f"{label}: samples={s['samples']}, failures={s['failures']}, "
            f"avg={s['avg_ms']}ms, p95={s['p95_ms']}ms, error={s['error_pct']}%"
        )

    lines.extend([
        "Respond in concise technical bullet points.",
        "Provide only the requested sections and avoid unnecessary explanation.",
        "Limit the response to approximately 250 words.",
        "Sections: EXECUTIVE SUMMARY, APDEX, BOTTLENECKS, BEST PERFORMING APIS, RECOMMENDATIONS, HEALTH SCORE, RISK LEVEL."
    ])

    return "\n".join(lines)


def _invoke_with_args(fn, prompt):
    try:
        sig = inspect.signature(fn)
        kwargs = {}
        if "prompt" in sig.parameters:
            kwargs["prompt"] = prompt
        elif "input" in sig.parameters:
            kwargs["input"] = prompt
        if "max_output_tokens" in sig.parameters:
            kwargs["max_output_tokens"] = 300
        if "temperature" in sig.parameters:
            kwargs["temperature"] = 0.2
        return fn(**kwargs)
    except Exception:
        try:
            return fn(prompt)
        except Exception:
            return fn(prompt, 300)


def call_gemini(api_key, prompt):
    # Use the google.generativeai package if available, but access attributes
    # dynamically to avoid static import/export warnings from type checkers
    try:
        configure = getattr(genai, "configure", None)
        if callable(configure):
            configure(api_key=api_key)
        else:
            os.environ.setdefault("GOOGLE_API_KEY", api_key)

        GenerativeModel = getattr(genai, "GenerativeModel", None)
        model_names = [
            "gemini-3.1-flash-lite",
            "gemini-3.5-lite",
            "gemini-3.0-flash",
            "gemini-flash-latest"
        ]

        if GenerativeModel is not None:
            for model_name in model_names:
                try:
                    model = GenerativeModel(model_name)
                    gen_fn = getattr(model, "generate_content", None) or getattr(model, "generate", None)
                    if not callable(gen_fn):
                        continue
                    resp = _invoke_with_args(gen_fn, prompt)
                    text = getattr(resp, "text", None) or (resp.get("text") if isinstance(resp, dict) else None)
                    if text:
                        return text
                except Exception:
                    continue

        gen_fn = getattr(genai, "generate_text", None) or getattr(genai, "generate", None)
        if callable(gen_fn):
            try:
                resp = _invoke_with_args(gen_fn, prompt)
            except Exception:
                resp = gen_fn(prompt)
            if isinstance(resp, dict):
                if "candidates" in resp and isinstance(resp["candidates"], list) and resp["candidates"]:
                    cand = resp["candidates"][0]
                    return cand.get("output") or cand.get("content") or str(cand)
                if "outputs" in resp and isinstance(resp["outputs"], list) and resp["outputs"]:
                    out = resp["outputs"][0]
                    return out.get("content") or str(out)
                return resp.get("text") or json.dumps(resp)
            return str(resp)

        raise RuntimeError("No supported google.generativeai API found in the installed package")
    except Exception as e:
        print("WARNING: Gemini API call failed:", str(e))
        fallback = (
            "AI analysis unavailable due to Gemini API error.\n"
            "Error: " + str(e) + "\n\n"
            "Original prompt (truncated):\n" + (prompt[:3000] + '\n...')
        )
        return fallback


def generate_html_report(ai_analysis, stats, total_samples, total_failures, environment, build_number, output_path):
    """Generate a modern dashboard-style HTML report from the AI analysis."""
    error_rate = round((total_failures / total_samples) * 100, 2) if total_samples > 0 else 0
    overall_avg = round(
        sum(s['avg_ms'] * s['samples'] for s in stats.values()) / total_samples,
        2
    ) if total_samples > 0 else 0
    total_endpoints = len(stats)

    if overall_avg < 500 and error_rate < 1:
        status_text = 'PASS'
        status_color = '#22c55e'
        status_emoji = '🟢'
    elif overall_avg < 1500 and error_rate < 5:
        status_text = 'PASS'
        status_color = '#38bdf8'
        status_emoji = '🟡'
    else:
        status_text = 'FAIL'
        status_color = '#f97316'
        status_emoji = '🔴'

    health_score = max(0, min(10, round(10 - error_rate * 0.08 - overall_avg / 1200)))
    health_grade = 'A' if health_score >= 9 else 'B' if health_score >= 7 else 'C' if health_score >= 5 else 'D'
    progress_pct = int((health_score / 10) * 100)

    top_endpoints = sorted(stats.items(), key=lambda item: item[1]['avg_ms'], reverse=True)[:5]
    chart_bars = ''
    max_avg = max((s['avg_ms'] for _, s in top_endpoints), default=1)
    for label, s in top_endpoints:
        width = int((s['avg_ms'] / max_avg) * 100)
        chart_bars += f"""
          <div class='chart-row'>
            <span class='chart-label'>{label}</span>
            <div class='chart-bar' style='width:{max(4, width)}%'></div>
            <span class='chart-value'>{s['avg_ms']} ms</span>
          </div>
        """

    rows = ''
    for label, s in stats.items():
        avg = s['avg_ms']
        if avg < 500:
            health_badge = '<span class="badge badge-good">Excellent</span>'
        elif avg < 1500:
            health_badge = '<span class="badge badge-warning">Good</span>'
        elif avg < 3000:
            health_badge = '<span class="badge badge-alert">Fair</span>'
        else:
            health_badge = '<span class="badge badge-bad">Poor</span>'

        rows += f"""
        <tr>
          <td>{label}</td>
          <td>{s['samples']}</td>
          <td>{s['error_pct']}%</td>
          <td>{avg} ms</td>
          <td>{s['p95_ms']} ms</td>
          <td>{health_badge}</td>
        </tr>
        """

    ai_html = ai_analysis.replace('\n', '<br>').replace('**', '').replace('##', '<h3>').replace('# ', '<h2>')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Performance Analysis - Build #{build_number}</title>
<style>
  :root {{
    color-scheme: dark;
    --bg: #0f172a;
    --panel: #111827;
    --panel-strong: #1f2937;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --blue: #38bdf8;
    --green: #22c55e;
    --yellow: #facc15;
    --orange: #fb923c;
    --red: #f97316;
    --border: rgba(148, 163, 184, 0.16);
  }}

  * {{ box-sizing: border-box; }}
  body {{ margin: 0; min-height: 100vh; background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.1), transparent 28%), var(--bg); color: var(--text); font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif; }}
  body::before {{ content: ''; position: fixed; inset: 0; background: linear-gradient(135deg, rgba(56,189,248,.06), transparent 45%), linear-gradient(225deg, rgba(34,197,94,.06), transparent 40%); pointer-events: none; }}
  .page {{ width: min(1200px, 100%); margin: 0 auto; padding: 24px; }}
  .header {{ display: grid; gap: 20px; margin-bottom: 24px; }}
  .hero {{ background: var(--panel); border: 1px solid var(--border); border-radius: 24px; padding: 26px; display: flex; justify-content: space-between; align-items: center; gap: 20px; }}
  .hero-title {{ display: flex; flex-direction: column; gap: 10px; }}
  .hero-title h1 {{ margin: 0; font-size: clamp(1.8rem, 2.2vw, 2.6rem); letter-spacing: -0.03em; }}
  .hero-meta {{ color: var(--muted); display: flex; flex-wrap: wrap; gap: 12px; font-size: 0.95rem; }}
  .hero-status {{ font-size: 1.25rem; font-weight: 700; color: {status_color}; }}
  .grid-4 {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 20px; padding: 20px; }}
  .metric-title {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 14px; text-transform: uppercase; letter-spacing: .11em; }}
  .metric-value {{ font-size: 2rem; font-weight: 700; line-height: 1; }}
  .metric-note {{ color: var(--blue); margin-top: 6px; font-size: 0.95rem; }}
  .progress-card {{ display: grid; gap: 12px; }}
  .progress-label {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; color: var(--muted); }}
  .progress-bar {{ height: 14px; width: 100%; border-radius: 999px; background: rgba(148, 163, 184, 0.12); overflow: hidden; }}
  .progress-fill {{ height: 100%; width: {progress_pct}%; background: linear-gradient(90deg, #38bdf8, #22c55e); border-radius: 999px; }}
  .section {{ margin-bottom: 26px; }}
  .section-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }}
  .section-title {{ font-size: 1.1rem; margin: 0; }}
  .section-pill {{ padding: 6px 12px; border-radius: 999px; background: rgba(56, 189, 248, 0.16); color: var(--blue); font-size: 0.9rem; }}
  .panel {{ background: var(--panel); border: 1px solid var(--border); border-radius: 22px; padding: 22px; }}
  .table-wrap {{ overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; min-width: 720px; }}
  th, td {{ padding: 16px; text-align: left; }}
  th {{ color: var(--muted); font-size: 0.95rem; border-bottom: 1px solid rgba(148,163,184,.12); }}
  tr:nth-child(even) {{ background: rgba(148,163,184,.03); }}
  td {{ border-bottom: 1px solid rgba(148,163,184,.08); }}
  .badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 8px 12px; border-radius: 999px; font-size: 0.9rem; font-weight: 600; }}
  .badge-good {{ background: rgba(34,197,94,.15); color: #22c55e; }}
  .badge-warning {{ background: rgba(251, 199, 70, .15); color: #facc15; }}
  .badge-alert {{ background: rgba(251, 146, 60, .15); color: #fb923c; }}
  .badge-bad {{ background: rgba(249,115,22,.15); color: #f97316; }}
  .chart-row {{ display: grid; grid-template-columns: 1.4fr 3fr 0.8fr; gap: 12px; align-items: center; margin-bottom: 12px; }}
  .chart-label {{ color: var(--text); font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .chart-bar {{ height: 14px; border-radius: 999px; background: linear-gradient(90deg, #38bdf8, #22c55e); }}
  .chart-value {{ color: var(--muted); font-size: 0.92rem; text-align: right; }}
  .ai-section {{ background: var(--panel); border: 1px solid var(--border); border-radius: 22px; padding: 24px; line-height: 1.8; }}
  .ai-section h2 {{ margin-top: 0; color: #8b95a5; }}
  .ai-section p, .ai-section br {{ color: var(--text); }}
  .footer {{ text-align:center; font-size: 0.9rem; color: var(--muted); margin-top: 30px; }}
  @media (max-width: 900px) {{
    .grid-4 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  }}
  @media (max-width: 640px) {{
    .grid-4 {{ grid-template-columns: 1fr; }}
    .hero {{ flex-direction: column; align-items: flex-start; }}
  }}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div class="hero">
      <div class="hero-title">
        <h1>🤖 AI Performance Analysis Report</h1>
        <div class="hero-meta">
          <span>Build #{build_number}</span>
          <span>•</span>
          <span>{environment.upper()}</span>
          <span>•</span>
          <span>{datetime.now().strftime('%b %d, %Y')}</span>
          <span>•</span>
          <span>{total_samples} requests</span>
          <span>•</span>
          <span>{total_endpoints} endpoints</span>
        </div>
      </div>
      <div class="hero-status">{status_emoji} {status_text}</div>
    </div>

    <div class="grid-4">
      <div class="card">
        <div class="metric-title">Build Status</div>
        <div class="metric-value">{status_emoji} {status_text}</div>
      </div>
      <div class="card">
        <div class="metric-title">Requests</div>
        <div class="metric-value">{total_samples}</div>
        <div class="metric-note">Total requests analyzed</div>
      </div>
      <div class="card">
        <div class="metric-title">Error Rate</div>
        <div class="metric-value">{error_rate}%</div>
        <div class="metric-note">Overall failure percentage</div>
      </div>
      <div class="card">
        <div class="metric-title">Average Response</div>
        <div class="metric-value">{overall_avg} ms</div>
        <div class="metric-note">Weighted average across endpoints</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <h2 class="section-title">📊 Health Score</h2>
      <span class="section-pill">Grade {health_grade}</span>
    </div>
    <div class="card progress-card">
      <div class="progress-label">
        <span>Overall system health</span>
        <strong>{health_score} / 10</strong>
      </div>
      <div class="progress-bar"><div class="progress-fill"></div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <h2 class="section-title">📈 Top Slow Endpoints</h2>
    </div>
    <div class="panel">
      {chart_bars}
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <h2 class="section-title">📊 Endpoint Summary</h2>
    </div>
    <div class="panel table-wrap">
      <table>
        <thead>
          <tr>
            <th>Endpoint</th>
            <th>Samples</th>
            <th>Error %</th>
            <th>Avg</th>
            <th>P95</th>
            <th>Health</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <h2 class="section-title">💡 AI Recommendations</h2>
    </div>
    <div class="ai-section">
      {ai_html}
    </div>
  </div>

  <div class="footer">
    Generated by AI Performance Analyzer | Build #{build_number} | {datetime.now().strftime('%Y-%m-%d %H:%M IST')}<br>
    Powered by Google Gemini AI | Apache JMeter + Jenkins CI/CD
  </div>
</div>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"AI Report generated: {output_path}")


if __name__ == '__main__':
    # Inputs from environment or arguments
    jtl_path     = os.environ.get('JTL_PATH', 'results/result.jtl')
    output_path  = os.environ.get('AI_REPORT_PATH', 'reports/ai/index.html')
    environment  = os.environ.get('ENVIRONMENT', 'dev')
    build_number = os.environ.get('BUILD_NUMBER', '0')
    api_key      = os.environ.get('GEMINI_API_KEY', '')

    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    print(f"Parsing JTL file: {jtl_path}")
    stats, total_samples, total_failures = parse_jtl(jtl_path)
    print(f"Parsed {total_samples} samples across {len(stats)} endpoints.")

    print("Building prompt for Gemini...")
    prompt = build_prompt(stats, total_samples, total_failures, environment, build_number)

    print("Calling Google Gemini API...")
    ai_analysis = call_gemini(api_key, prompt)
    print("Gemini response received.")

    print(f"Generating HTML report at: {output_path}")
    generate_html_report(ai_analysis, stats, total_samples, total_failures, environment, build_number, output_path)
    print("AI Performance Analysis complete!")
