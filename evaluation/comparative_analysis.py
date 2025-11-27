"""
Comparative Analysis Module
Objective 3: Quantify performance gains of LLM vs baseline
"""

import json
import os
import pandas as pd
from typing import Dict, List
import matplotlib.pyplot as plt
import seaborn as sns


class ComparativeAnalyzer:
    """
    Analyze and compare performance between Gemini and baseline models
    """
    
    def __init__(self, results_dir: str):
        self.results_dir = results_dir
        self.gemini_data = None
        self.baseline_data = None
    
    def load_results(self):
        """Load evaluation results for both models"""
        gemini_path = os.path.join(self.results_dir, 'gemini_evaluation_results.json')
        baseline_path = os.path.join(self.results_dir, 'baseline_evaluation_results.json')
        
        with open(gemini_path, 'r') as f:
            self.gemini_data = json.load(f)
        
        with open(baseline_path, 'r') as f:
            self.baseline_data = json.load(f)
    
    def generate_comparison_report(self) -> Dict:
        """Generate comprehensive comparison report"""
        if not self.gemini_data or not self.baseline_data:
            self.load_results()
        
        gemini_metrics = self.gemini_data['metrics']
        baseline_metrics = self.baseline_data['metrics']
        
        # Overall comparison
        overall_comparison = {
            'gemini_accuracy': gemini_metrics['accuracy_percentage'],
            'baseline_accuracy': baseline_metrics['accuracy_percentage'],
            'absolute_improvement': gemini_metrics['accuracy_percentage'] - baseline_metrics['accuracy_percentage'],
            'relative_improvement': ((gemini_metrics['accuracy_percentage'] - baseline_metrics['accuracy_percentage']) / 
                                    baseline_metrics['accuracy_percentage'] * 100) if baseline_metrics['accuracy_percentage'] > 0 else 0,
            'gemini_meets_target': gemini_metrics['meets_90_percent_target'],
            'baseline_meets_target': baseline_metrics['meets_90_percent_target']
        }
        
        # Complexity comparison
        complexity_comparison = {}
        for complexity in ['simple', 'medium', 'complex']:
            if complexity in gemini_metrics['complexity_breakdown'] and complexity in baseline_metrics['complexity_breakdown']:
                gemini_acc = gemini_metrics['complexity_breakdown'][complexity]['accuracy']
                baseline_acc = baseline_metrics['complexity_breakdown'][complexity]['accuracy']
                complexity_comparison[complexity] = {
                    'gemini': gemini_acc,
                    'baseline': baseline_acc,
                    'improvement': gemini_acc - baseline_acc
                }
        
        # Category comparison
        category_comparison = {}
        all_categories = set(list(gemini_metrics['category_breakdown'].keys()) + 
                           list(baseline_metrics['category_breakdown'].keys()))
        
        for category in all_categories:
            gemini_acc = gemini_metrics['category_breakdown'].get(category, {}).get('accuracy', 0)
            baseline_acc = baseline_metrics['category_breakdown'].get(category, {}).get('accuracy', 0)
            category_comparison[category] = {
                'gemini': gemini_acc,
                'baseline': baseline_acc,
                'improvement': gemini_acc - baseline_acc
            }
        
        report = {
            'overall': overall_comparison,
            'by_complexity': complexity_comparison,
            'by_category': category_comparison
        }
        
        return report
    
    def generate_detailed_comparison_table(self) -> pd.DataFrame:
        """Generate detailed test-by-test comparison"""
        if not self.gemini_data or not self.baseline_data:
            self.load_results()
        
        gemini_results = self.gemini_data['detailed_results']
        baseline_results = self.baseline_data['detailed_results']
        
        comparison_data = []
        for g_result, b_result in zip(gemini_results, baseline_results):
            comparison_data.append({
                'Test ID': g_result['test_id'],
                'Question': g_result['question'][:50] + '...' if len(g_result['question']) > 50 else g_result['question'],
                'Complexity': g_result['complexity'],
                'Category': g_result['category'],
                'Gemini Success': '✓' if g_result['execution_success'] else '✗',
                'Baseline Success': '✓' if b_result['execution_success'] else '✗',
                'Winner': 'Gemini' if g_result['execution_success'] and not b_result['execution_success'] else 
                         'Baseline' if b_result['execution_success'] and not g_result['execution_success'] else
                         'Both' if g_result['execution_success'] and b_result['execution_success'] else 'Neither'
            })
        
        return pd.DataFrame(comparison_data)
    
    def save_comparison_report(self, report: Dict):
        """Save comparison report to JSON"""
        output_path = os.path.join(self.results_dir, 'comparative_analysis.json')
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Comparison report saved to: {output_path}")
        return output_path
    
    def save_comparison_table(self, df: pd.DataFrame):
        """Save comparison table to CSV"""
        output_path = os.path.join(self.results_dir, 'detailed_comparison.csv')
        df.to_csv(output_path, index=False)
        print(f"Detailed comparison saved to: {output_path}")
        return output_path
    
    def print_comparison_summary(self, report: Dict):
        """Print formatted comparison summary"""
        print("\\n" + "="*70)
        print("COMPARATIVE ANALYSIS: GEMINI (LLM) vs BASELINE (NON-LLM)")
        print("="*70)
        
        overall = report['overall']
        print(f"\\nOVERALL PERFORMANCE:")
        print(f"  Gemini Accuracy:    {overall['gemini_accuracy']:.2f}%")
        print(f"  Baseline Accuracy:  {overall['baseline_accuracy']:.2f}%")
        print(f"  Absolute Gain:      +{overall['absolute_improvement']:.2f} percentage points")
        print(f"  Relative Gain:      +{overall['relative_improvement']:.1f}%")
        print(f"\\n  90% Target Achievement:")
        print(f"    Gemini:   {'✓ YES' if overall['gemini_meets_target'] else '✗ NO'}")
        print(f"    Baseline: {'✓ YES' if overall['baseline_meets_target'] else '✗ NO'}")
        
        print(f"\\nPERFORMANCE BY COMPLEXITY:")
        for complexity, stats in report['by_complexity'].items():
            print(f"  {complexity.capitalize()}:")
            print(f"    Gemini:   {stats['gemini']:.1f}%")
            print(f"    Baseline: {stats['baseline']:.1f}%")
            print(f"    Gain:     +{stats['improvement']:.1f}%")
        
        print(f"\\nPERFORMANCE BY CATEGORY:")
        for category, stats in report['by_category'].items():
            print(f"  {category.capitalize()}:")
            print(f"    Gemini:   {stats['gemini']:.1f}%")
            print(f"    Baseline: {stats['baseline']:.1f}%")
            print(f"    Gain:     +{stats['improvement']:.1f}%")
        
        print("="*70)


def main():
    """Run comparative analysis"""
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    
    analyzer = ComparativeAnalyzer(results_dir)
    
    print("\\nLoading evaluation results...")
    analyzer.load_results()
    
    print("Generating comparative analysis...")
    report = analyzer.generate_comparison_report()
    
    print("Creating detailed comparison table...")
    comparison_table = analyzer.generate_detailed_comparison_table()
    
    # Save results
    analyzer.save_comparison_report(report)
    analyzer.save_comparison_table(comparison_table)
    
    # Print summary
    analyzer.print_comparison_summary(report)
    
    print(f"\\nDetailed comparison table preview:")
    print(comparison_table.to_string(index=False))


if __name__ == "__main__":
    main()
