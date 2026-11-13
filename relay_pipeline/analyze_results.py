"""
Analyze results and generate summary statistics for writeup.
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


def load_measurements():
    """Load Groq API measurements."""
    path = "results/groq_measurements.json"
    if not os.path.exists(path):
        print(f"⚠ {path} not found")
        return None
    
    with open(path) as f:
        return json.load(f)


def load_quality_results():
    """Load quality test results."""
    path = "results/quality_test_results.json"
    if not os.path.exists(path):
        print(f"⚠ {path} not found")
        return None
    
    with open(path) as f:
        return json.load(f)


def load_load_test_results():
    """Load most recent load test CSV."""
    results_dir = Path("results")
    csv_files = list(results_dir.glob("load_test_*.csv"))
    
    if not csv_files:
        print("⚠ No load test CSV files found")
        return None
    
    # Get most recent
    latest = max(csv_files, key=lambda p: p.stat().st_mtime)
    print(f"Loading: {latest}")
    
    return pd.read_csv(latest)


def analyze_measurements(measurements):
    """Analyze API measurements."""
    if not measurements:
        return
    
    print("\n" + "="*80)
    print("GROQ API MEASUREMENTS")
    print("="*80)
    
    if "latency_distribution" in measurements:
        lat = measurements["latency_distribution"]
        print("\nLatency Distribution:")
        print(f"  Mean: {lat['mean']:.0f} ms (±{lat['std']:.0f} ms)")
        print(f"  Range: {lat['min']:.0f} - {lat['max']:.0f} ms")
        print(f"  Percentiles:")
        print(f"    P50: {lat['p50']:.0f} ms")
        print(f"    P95: {lat['p95']:.0f} ms")
        print(f"    P99: {lat['p99']:.0f} ms")
        if lat.get('ttft_avg'):
            print(f"  TTFT (streaming): {lat['ttft_avg']:.0f} ms")
    
    if "rate_limits" in measurements:
        limits = measurements["rate_limits"]
        print("\nRate Limits:")
        print(f"  RPM: {limits['rpm_observed']}")
        print(f"  TPM: {limits['tpm_observed']}")
        print(f"  Daily: {limits['daily_limit_tokens']} tokens")
    
    if "token_usage" in measurements:
        tokens = measurements["token_usage"]
        print("\nToken Usage:")
        print(f"  Tokens per word: {tokens['token_per_word_ratio']:.2f}")
        print(f"  Avg prompt tokens: {tokens['avg_prompt_tokens']:.1f}")
        print(f"  Avg completion tokens: {tokens['avg_completion_tokens']:.1f}")
    
    if "error_rates" in measurements:
        errors = measurements["error_rates"]
        print("\nError Rates:")
        print(f"  Success rate: {(1-errors['error_rate'])*100:.1f}%")
        print(f"  Failures: {errors['failed']}/{errors['total_requests']}")


def analyze_quality(quality_results):
    """Analyze quality test results."""
    if not quality_results:
        return
    
    print("\n" + "="*80)
    print("QUALITY TEST RESULTS")
    print("="*80)
    
    results = quality_results.get("results", [])
    if not results:
        return
    
    successful = [r for r in results if r.get("success")]
    verified = [r for r in successful if r.get("verified")]
    
    print(f"\nOverall:")
    print(f"  Questions answered: {len(successful)}/{len(results)}")
    print(f"  Success rate: {len(successful)/len(results)*100:.1f}%")
    print(f"  Verification rate: {len(verified)/len(successful)*100:.1f}%")
    
    if successful:
        # Quality scores
        quality_scores = [r["quality_eval"]["quality_score"] for r in successful if "quality_eval" in r]
        if quality_scores:
            print(f"\nQuality Scores:")
            print(f"  Mean: {np.mean(quality_scores):.2f}")
            print(f"  Median: {np.median(quality_scores):.2f}")
            print(f"  Range: {np.min(quality_scores):.2f} - {np.max(quality_scores):.2f}")
        
        # Topic coverage
        topic_coverage = [r["quality_eval"]["topic_coverage"] for r in successful if "quality_eval" in r]
        if topic_coverage:
            print(f"\nTopic Coverage:")
            print(f"  Mean: {np.mean(topic_coverage)*100:.1f}%")
            print(f"  Median: {np.median(topic_coverage)*100:.1f}%")
        
        # Timings
        latencies = [r["timings"]["total"] for r in successful if "timings" in r]
        if latencies:
            print(f"\nLatencies:")
            print(f"  Mean: {np.mean(latencies):.2f}s")
            print(f"  P95: {np.percentile(latencies, 95):.2f}s")
        
        # Tokens
        tokens = [r["tokens_used"] for r in successful if "tokens_used" in r]
        if tokens:
            print(f"\nToken Usage:")
            print(f"  Mean: {np.mean(tokens):.0f} tokens/query")
            print(f"  Total: {sum(tokens)} tokens")


def analyze_load_tests(df):
    """Analyze load test results."""
    if df is None or df.empty:
        return
    
    print("\n" + "="*80)
    print("LOAD TEST RESULTS")
    print("="*80)
    
    # Overall statistics
    print(f"\nOverall:")
    print(f"  Total requests: {len(df)}")
    print(f"  Success rate: {df['success'].mean()*100:.1f}%")
    print(f"  Verification rate: {df[df['success']]['verified'].mean()*100:.1f}%")
    print(f"  Avg latency: {df[df['success']]['total_latency'].mean():.2f}s")
    print(f"  Avg tokens: {df[df['success']]['tokens_used'].mean():.0f}")
    
    # By scenario
    print("\nBy Scenario:")
    for scenario in df['scenario'].unique():
        scenario_df = df[df['scenario'] == scenario]
        success_rate = scenario_df['success'].mean()
        
        print(f"\n  {scenario}:")
        print(f"    Requests: {len(scenario_df)}")
        print(f"    Success rate: {success_rate*100:.1f}%")
        
        if success_rate > 0:
            successful = scenario_df[scenario_df['success']]
            print(f"    Avg latency: {successful['total_latency'].mean():.2f}s")
            print(f"    P95 latency: {successful['total_latency'].quantile(0.95):.2f}s")
            print(f"    Avg tokens: {successful['tokens_used'].mean():.0f}")
            print(f"    Budget refusals: {(scenario_df['error'].str.contains('udget', case=False, na=False)).sum()}")
    
    # Stage breakdown
    if df[df['success']]['intent_latency'].notna().any():
        print("\nStage Latency Breakdown (successful requests):")
        successful = df[df['success']]
        stages = ['intent', 'retrieval', 'generation', 'verification']
        
        for stage in stages:
            col = f"{stage}_latency"
            if col in successful.columns and successful[col].notna().any():
                print(f"  {stage.capitalize()}: {successful[col].mean():.3f}s (±{successful[col].std():.3f}s)")


def create_summary_table(measurements, quality_results, df):
    """Create a summary table for writeup."""
    print("\n" + "="*80)
    print("SUMMARY TABLE FOR WRITEUP")
    print("="*80)
    
    summary = {}
    
    # API characteristics
    if measurements and "latency_distribution" in measurements:
        lat = measurements["latency_distribution"]
        summary["API Latency (mean)"] = f"{lat['mean']:.0f} ms"
        summary["API Latency (P95)"] = f"{lat['p95']:.0f} ms"
    
    if measurements and "rate_limits" in measurements:
        limits = measurements["rate_limits"]
        summary["RPM Limit"] = limits["rpm_observed"]
        summary["TPM Limit"] = limits["tpm_observed"]
    
    # Quality metrics
    if quality_results:
        results = quality_results.get("results", [])
        successful = [r for r in results if r.get("success")]
        verified = [r for r in successful if r.get("verified")]
        
        summary["Questions Answered"] = f"{len(successful)}/{len(results)}"
        summary["Verification Rate"] = f"{len(verified)/len(successful)*100:.1f}%"
        
        quality_scores = [r["quality_eval"]["quality_score"] for r in successful if "quality_eval" in r]
        if quality_scores:
            summary["Avg Quality Score"] = f"{np.mean(quality_scores):.2f}"
    
    # Load test metrics
    if df is not None and not df.empty:
        summary["Total Load Test Requests"] = len(df)
        summary["Load Test Success Rate"] = f"{df['success'].mean()*100:.1f}%"
        
        successful = df[df['success']]
        if len(successful) > 0:
            summary["Avg End-to-End Latency"] = f"{successful['total_latency'].mean():.2f}s"
            summary["Avg Tokens/Query"] = f"{successful['tokens_used'].mean():.0f}"
    
    # Print table
    print("\n" + "-"*60)
    for key, value in summary.items():
        print(f"{key:.<40} {value}")
    print("-"*60)
    
    return summary


def create_plots(measurements, quality_results, df):
    """Create plots for writeup."""
    print("\n" + "="*80)
    print("GENERATING PLOTS")
    print("="*80)
    
    sns.set_style("whitegrid")
    
    # Plot 1: Latency distribution
    if df is not None and not df.empty and df[df['success']]['total_latency'].notna().any():
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        successful = df[df['success']]
        
        # Total latency histogram
        axes[0, 0].hist(successful['total_latency'], bins=30, edgecolor='black', alpha=0.7)
        axes[0, 0].set_xlabel('Total Latency (s)')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('End-to-End Latency Distribution')
        
        # Stage breakdown
        stages = ['intent_latency', 'retrieval_latency', 'generation_latency', 'verification_latency']
        stage_names = ['Intent', 'Retrieval', 'Generation', 'Verification']
        stage_means = [successful[s].mean() for s in stages if s in successful.columns]
        valid_names = [n for i, n in enumerate(stage_names) if stages[i] in successful.columns]
        
        axes[0, 1].bar(valid_names, stage_means, edgecolor='black', alpha=0.7)
        axes[0, 1].set_ylabel('Mean Latency (s)')
        axes[0, 1].set_title('Pipeline Stage Latencies')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # Success rate by scenario
        scenario_success = df.groupby('scenario')['success'].mean()
        axes[1, 0].bar(range(len(scenario_success)), scenario_success.values, edgecolor='black', alpha=0.7)
        axes[1, 0].set_xticks(range(len(scenario_success)))
        axes[1, 0].set_xticklabels(scenario_success.index, rotation=45, ha='right')
        axes[1, 0].set_ylabel('Success Rate')
        axes[1, 0].set_title('Success Rate by Load Scenario')
        axes[1, 0].set_ylim([0, 1.1])
        
        # Token usage
        axes[1, 1].hist(successful['tokens_used'], bins=30, edgecolor='black', alpha=0.7)
        axes[1, 1].set_xlabel('Tokens Used')
        axes[1, 1].set_ylabel('Frequency')
        axes[1, 1].set_title('Token Usage Distribution')
        
        plt.tight_layout()
        plt.savefig('results/analysis_plots.png', dpi=150, bbox_inches='tight')
        print("  ✓ Saved: results/analysis_plots.png")
        plt.close()
    
    # Plot 2: Quality metrics
    if quality_results:
        results = quality_results.get("results", [])
        successful = [r for r in results if r.get("success") and "quality_eval" in r]
        
        if successful:
            fig, axes = plt.subplots(1, 2, figsize=(12, 4))
            
            quality_scores = [r["quality_eval"]["quality_score"] for r in successful]
            topic_coverage = [r["quality_eval"]["topic_coverage"] for r in successful]
            
            axes[0].hist(quality_scores, bins=20, edgecolor='black', alpha=0.7)
            axes[0].set_xlabel('Quality Score')
            axes[0].set_ylabel('Frequency')
            axes[0].set_title('Answer Quality Score Distribution')
            axes[0].axvline(np.mean(quality_scores), color='red', linestyle='--', label=f'Mean: {np.mean(quality_scores):.2f}')
            axes[0].legend()
            
            axes[1].hist(topic_coverage, bins=20, edgecolor='black', alpha=0.7)
            axes[1].set_xlabel('Topic Coverage')
            axes[1].set_ylabel('Frequency')
            axes[1].set_title('Topic Coverage Distribution')
            axes[1].axvline(np.mean(topic_coverage), color='red', linestyle='--', label=f'Mean: {np.mean(topic_coverage):.2f}')
            axes[1].legend()
            
            plt.tight_layout()
            plt.savefig('results/quality_plots.png', dpi=150, bbox_inches='tight')
            print("  ✓ Saved: results/quality_plots.png")
            plt.close()


def main():
    print("\n" + "="*80)
    print("RELAY PIPELINE RESULTS ANALYSIS")
    print("="*80)
    
    # Load all results
    measurements = load_measurements()
    quality_results = load_quality_results()
    df = load_load_test_results()
    
    # Analyze each component
    analyze_measurements(measurements)
    analyze_quality(quality_results)
    analyze_load_tests(df)
    
    # Create summary
    summary = create_summary_table(measurements, quality_results, df)
    
    # Save summary
    with open("results/analysis_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    print("\n✓ Saved: results/analysis_summary.json")
    
    # Create plots
    try:
        create_plots(measurements, quality_results, df)
    except Exception as e:
        print(f"⚠ Could not create plots: {e}")
    
    print("\n" + "="*80)
    print("Analysis complete! Check results/ directory for outputs.")
    print("="*80)


if __name__ == "__main__":
    main()
