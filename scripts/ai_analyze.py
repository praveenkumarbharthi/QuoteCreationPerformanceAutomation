#!/usr/bin/env python3
"""
AI Performance Analysis Script
Reads JMeter result.jtl, sends metrics to Google Gemini,
and generates an AI_Performance_Report.html for Jenkins publishing.
"""

import csv
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

    summary = f"""
You are an expert performance engineering analyst. Analyze the following JMeter load test results
and provide a detailed, professional performance report.

Build Information:
- Build Number: {build_number}
- Environment: {environment}
- Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- Total Requests: {total_samples}
- Total Failures: {total_failures}
- Overall Error Rate: {error_rate}%

Endpoint Statistics:
"""

    for label, s in stats.items():
        summary += f"""
Endpoint: {label}
  Samples     : {s['samples']}
  Failures    : {s['failures']}
  Error %     : {s['error_pct']}%
  Avg (ms)    : {s['avg_ms']}
  Min (ms)    : {s['min_ms']}
  Max (ms)    : {s['max_ms']}
  90th pct    : {s['p90_ms']} ms
  95th pct    : {s['p95_ms']} ms
  99th pct    : {s['p99_ms']} ms
"""

    summary += """
Please provide your analysis in the following exact structure:

1. EXECUTIVE SUMMARY (2-3 sentences overall health assessment)
2. APDEX ASSESSMENT (rate each endpoint as Excellent/Good/Fair/Poor based on response times)
3. BOTTLENECKS (list slowest endpoints with specific observations)
4. BEST PERFORMING APIs (highlight fast, reliable endpoints)
5. RECOMMENDATIONS (specific, actionable technical improvements for each bottleneck)
6. OVERALL HEALTH SCORE (score out of 100 with brief justification)
7. RISK LEVEL (Low/Medium/High with reasoning)

Be specific, technical, and concise. Use bullet points where appropriate.
"""
    return summary


def call_gemini(api_key, prompt):
    # Use the google.generativeai package if available, but access attributes
    # dynamically to avoid static import/export warnings from type checkers
    try:
        configure = getattr(genai, "configure", None)
        if callable(configure):
            configure(api_key=api_key)
        else:
            # Some distributions read the API key from env var
            os.environ.setdefault("GOOGLE_API_KEY", api_key)

        # Try the newer/high-level model object if present
        GenerativeModel = getattr(genai, "GenerativeModel", None)
        if GenerativeModel is not None:
            model = GenerativeModel("gemini-flash-latest")
            # Prefer a generate_content-like method if present
            gen_fn = getattr(model, "generate_content", None) or getattr(model, "generate", None)
            if callable(gen_fn):
                resp = gen_fn(prompt)
                # response may be object-like or dict-like
                text = getattr(resp, "text", None) or (resp.get("text") if isinstance(resp, dict) else None)
                if text:
                    return text

        # Fallback: try module-level convenience functions
        gen_fn = getattr(genai, "generate_text", None) or getattr(genai, "generate", None)
        if callable(gen_fn):
            # different versions return different shapes; try to extract a reasonable string
            resp = gen_fn(prompt=prompt) if 'prompt' in gen_fn.__code__.co_varnames else gen_fn(prompt)
            if isinstance(resp, dict):
                # common fields: 'candidates', 'outputs', 'text'
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
        # Handle quota or API errors gracefully and return a helpful fallback
        print("WARNING: Gemini API call failed:", str(e))
        fallback = (
            "AI analysis unavailable due to Gemini API error.\n"
            "Error: " + str(e) + "\n\n"
            "Original prompt (truncated):\n" + (prompt[:3000] + '\n...')
        )
        return fallback


def generate_html_report(ai_analysis, stats, total_samples, total_failures, environment, build_number, output_path):
    """Generate a styled HTML report from the AI analysis."""
    error_rate = round((total_failures / total_samples) * 100, 2) if total_samples > 0 else 0
    status_color = '#2ecc71' if error_rate == 0 else '#e74c3c'
    status_text = 'PASS' if error_rate == 0 else 'FAIL'

    rows = ''
    for label, s in stats.items():
        health = ''
        avg = s['avg_ms']
        if avg < 500:
            health = '<span style="color:#2ecc71">Excellent</span>'
        elif avg < 1500:
            health = '<span style="color:#f39c12">Good</span>'
        elif avg < 3000:
            health = '<span style="color:#e67e22">Fair</span>'
        else:
            health = '<span style="color:#e74c3c">Poor</span>'

        rows += f"""
        <tr>
          <td>{label}</td>
          <td>{s['samples']}</td>
          <td>{s['error_pct']}%</td>
          <td>{s['avg_ms']} ms</td>
          <td>{s['min_ms']} ms</td>
          <td>{s['max_ms']} ms</td>
          <td>{s['p95_ms']} ms</td>
          <td>{health}</td>
        </tr>"""

    # Convert AI markdown-style text to HTML
    ai_html = ai_analysis.replace('\n', '<br>').replace('**', '').replace('##', '<h3>').replace('# ', '<h2>')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AI Performance Analysis - Build #{build_number}</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
  h1 {{ color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 10px; }}
  h2 {{ color: #79c0ff; margin-top: 30px; }}
  h3 {{ color: #d2a8ff; }}
  .badge {{ display:inline-block; padding:6px 16px; border-radius:20px; font-weight:bold; font-size:18px; }}
  .summary-grid {{ display:grid; grid-template-columns: repeat(4,1fr); gap:15px; margin:20px 0; }}
  .card {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:15px; text-align:center; }}
  .card .value {{ font-size:28px; font-weight:bold; color:#58a6ff; }}
  .card .label {{ font-size:12px; color:#8b949e; margin-top:5px; }}
  table {{ width:100%; border-collapse:collapse; margin:20px 0; }}
  th {{ background:#161b22; color:#8b949e; padding:10px; text-align:left; border-bottom:2px solid #30363d; }}
  td {{ padding:10px; border-bottom:1px solid #21262d; }}
  tr:hover td {{ background:#161b22; }}
  .ai-section {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:20px; margin:20px 0; line-height:1.8; }}
  .footer {{ text-align:center; color:#8b949e; font-size:12px; margin-top:40px; padding-top:20px; border-top:1px solid #30363d; }}
  .gemini-badge {{ background: linear-gradient(135deg, #4285f4, #34a853); color:white; padding:4px 12px; border-radius:12px; font-size:12px; }}
</style>
</head>
<body>
<h1>&#129302; AI Performance Analysis Report
  <span class="gemini-badge">Powered by Google Gemini</span>
</h1>

<div class="summary-grid">
  <div class="card"><div class="value" style="color:{status_color}">{status_text}</div><div class="label">Build Status</div></div>
  <div class="card"><div class="value">{total_samples}</div><div class="label">Total Requests</div></div>
  <div class="card"><div class="value" style="color:{status_color}">{error_rate}%</div><div class="label">Error Rate</div></div>
  <div class="card"><div class="value">{environment.upper()}</div><div class="label">Environment</div></div>
</div>

<h2>&#128202; Endpoint Statistics</h2>
<table>
  <tr>
    <th>Endpoint</th><th>Samples</th><th>Error %</th>
    <th>Avg</th><th>Min</th><th>Max</th><th>95th pct</th><th>Health</th>
  </tr>
  {rows}
</table>

<h2>&#129302; AI Analysis by Google Gemini</h2>
<div class="ai-section">
  {ai_html}
</div>

<div class="footer">
  Generated by AI Performance Analyzer | Build #{build_number} | {datetime.now().strftime('%Y-%m-%d %H:%M IST')}<br>
  Powered by Google Gemini AI (Free Tier) | Apache JMeter + Jenkins CI/CD
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
