#!/usr/bin/env python3
"""Dry-run analyzer: generates the HTML report without calling Gemini API."""
import os
import importlib.util
import sys

HERE = os.path.dirname(__file__)
ai_path = os.path.join(HERE, 'ai_analyze.py')

spec = importlib.util.spec_from_file_location('ai_analyze', ai_path)
ai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai)

jtl_path     = os.environ.get('JTL_PATH', 'results/result.jtl')
output_path  = os.environ.get('AI_REPORT_PATH', 'reports/ai/index.html')
environment  = os.environ.get('ENVIRONMENT', 'dev')
build_number = os.environ.get('BUILD_NUMBER', 'dry-run')

print(f"Dry-run: parsing JTL file: {jtl_path}")
stats, total_samples, total_failures = ai.parse_jtl(jtl_path)
print(f"Parsed {total_samples} samples across {len(stats)} endpoints.")

print("Building prompt (not sent to API)...")
prompt = ai.build_prompt(stats, total_samples, total_failures, environment, build_number)

# Mocked AI analysis for dry-run
ai_analysis = (
    "DRY-RUN AI ANALYSIS\n"
    "-------------------\n"
    "This is a mocked analysis generated locally for testing purposes.\n\n"
    "SUMMARY:\n- Dry-run completed; no external API called.\n"
)

print("Generating HTML report (dry-run)...")
ai.generate_html_report(ai_analysis, stats, total_samples, total_failures, environment, build_number, output_path)
print(f"Dry-run report generated: {output_path}")
