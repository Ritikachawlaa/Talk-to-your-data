"""
Query Evaluator - Empirical Validation Framework
Objective 2: Validate query generation accuracy with 90% benchmark target
"""

import os
import json
import pandas as pd
from io import StringIO
from typing import Dict, List, Tuple, Any
import google.generativeai as genai
from dotenv import load_dotenv
import re
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.baseline_model import BaselineQueryGenerator


class QueryEvaluator:
    """
    Automated evaluation framework for query generation accuracy
    """
    
    def __init__(self, gemini_api_key: str = None):
        """Initialize evaluator with LLM and baseline models"""
        self.test_datasets_dir = os.path.join(os.path.dirname(__file__), 'test_datasets')
        self.ground_truth_path = os.path.join(os.path.dirname(__file__), 'ground_truth.json')
        self.results_dir = os.path.join(os.path.dirname(__file__), 'results')
        
        # Load ground truth
        with open(self.ground_truth_path, 'r') as f:
            self.ground_truth = json.load(f)
        
        # Initialize models
        self.baseline_generator = BaselineQueryGenerator()
        
        # Initialize Gemini
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.gemini_model = genai.GenerativeModel('models/gemini-2.5-flash')
            self.gemini_configured = True
        else:
            self.gemini_configured = False
        
        # Create results directory
        os.makedirs(self.results_dir, exist_ok=True)
    
    def load_dataset(self, dataset_name: str) -> pd.DataFrame:
        """Load a test dataset"""
        dataset_path = os.path.join(self.test_datasets_dir, dataset_name)
        return pd.read_csv(dataset_path)
    
    def get_df_info_for_ai(self, df: pd.DataFrame) -> str:
        """Generate schema information for AI (same as main app)"""
        schema_parts = []
        try:
            sample_rows = df.head(3).to_string(index=False)
        except Exception:
            sample_rows = "Could not display sample rows."
        
        for column in df.columns:
            dtype = str(df[column].dtype)
            schema_parts.append(f"- '{column}' (type: {dtype})")
        
        return "\\n".join(schema_parts) + f"\\n\\nHere are some sample rows:\\n{sample_rows}"
    
    def construct_analysis_prompt(self, schema: str, user_question: str) -> str:
        """Construct prompt for Gemini (same as main app)"""
        prompt = f"""
You are an expert Python data analyst. Your task is to write a Python script to answer a user's question about their data.

The data is available in a pandas DataFrame named `df`.

Here is the schema of the DataFrame `df`:
{schema}

User's Question: "{user_question}"

Instructions:
1. Write a Python script that uses the pandas DataFrame `df` to answer the question.
2. The script's final output MUST be a pandas DataFrame stored in a variable called `result_df`.
3. Do NOT convert the final DataFrame to a string. The `result_df` variable must hold the DataFrame object itself.
4. Do not include any print statements or any code outside of the core logic to generate the `result_df` variable.
5. Ensure the code is a single block, without any markdown formatting like ```python.
"""
        return prompt
    
    def execute_generated_code(self, code: str, df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
        """Execute generated code and return result"""
        try:
            execution_globals = {'pd': pd, 'df': df}
            execution_locals = {}
            exec(code, execution_globals, execution_locals)
            result_df = execution_locals.get('result_df')
            
            if isinstance(result_df, pd.DataFrame):
                return result_df, None
            elif result_df is not None:
                return pd.DataFrame([str(result_df)]), None
            else:
                return None, "No result_df variable produced"
        except Exception as e:
            return None, str(e)
    
    def generate_gemini_query(self, question: str, df: pd.DataFrame) -> Tuple[str, str]:
        """Generate query using Gemini LLM"""
        if not self.gemini_configured:
            return None, "Gemini not configured"
        
        try:
            schema = self.get_df_info_for_ai(df)
            prompt = self.construct_analysis_prompt(schema, question)
            response = self.gemini_model.generate_content(prompt)
            
            generated_code = response.text
            generated_code = re.sub(r'```python\\n|```', '', generated_code).strip()
            
            return generated_code, None
        except Exception as e:
            return None, str(e)
    
    def generate_baseline_query(self, question: str, df: pd.DataFrame) -> Tuple[str, str]:
        """Generate query using baseline model"""
        try:
            code = self.baseline_generator.generate_query(question, df)
            if code:
                return code, None
            else:
                return None, "Baseline could not generate query"
        except Exception as e:
            return None, str(e)
    
    def evaluate_single_query(self, test_case: Dict, model_type: str = 'gemini') -> Dict:
        """Evaluate a single test case"""
        dataset_name = test_case['dataset']
        question = test_case['query']
        
        # Load dataset
        df = self.load_dataset(dataset_name)
        
        # Generate query
        if model_type == 'gemini':
            code, gen_error = self.generate_gemini_query(question, df)
        else:
            code, gen_error = self.generate_baseline_query(question, df)
        
        result = {
            'test_id': test_case['id'],
            'question': question,
            'dataset': dataset_name,
            'complexity': test_case['complexity'],
            'category': test_case['category'],
            'model': model_type,
            'generated_code': code,
            'generation_error': gen_error,
            'execution_success': False,
            'execution_error': None,
            'result_preview': None
        }
        
        if gen_error:
            return result
        
        # Execute query
        result_df, exec_error = self.execute_generated_code(code, df)
        
        if exec_error:
            result['execution_error'] = exec_error
        else:
            result['execution_success'] = True
            result['result_preview'] = result_df.head(5).to_string() if result_df is not None else None
        
        return result
    
    def run_full_evaluation(self, model_type: str = 'gemini') -> List[Dict]:
        """Run evaluation on all test cases"""
        results = []
        test_cases = self.ground_truth['test_cases']
        
        print(f"\\nRunning evaluation for {model_type.upper()} model...")
        print(f"Total test cases: {len(test_cases)}")
        print("-" * 60)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\\nTest {i}/{len(test_cases)}: {test_case['query']}")
            result = self.evaluate_single_query(test_case, model_type)
            results.append(result)
            
            status = "✓ SUCCESS" if result['execution_success'] else "✗ FAILED"
            print(f"  Status: {status}")
            if result['generation_error']:
                print(f"  Generation Error: {result['generation_error']}")
            if result['execution_error']:
                print(f"  Execution Error: {result['execution_error']}")
        
        return results
    
    def calculate_metrics(self, results: List[Dict]) -> Dict:
        """Calculate evaluation metrics"""
        total = len(results)
        successful = sum(1 for r in results if r['execution_success'])
        failed = total - successful
        
        # By complexity
        complexity_stats = {}
        for complexity in ['simple', 'medium', 'complex']:
            complexity_results = [r for r in results if r['complexity'] == complexity]
            if complexity_results:
                complexity_success = sum(1 for r in complexity_results if r['execution_success'])
                complexity_stats[complexity] = {
                    'total': len(complexity_results),
                    'successful': complexity_success,
                    'accuracy': complexity_success / len(complexity_results) * 100
                }
        
        # By category
        category_stats = {}
        for result in results:
            category = result['category']
            if category not in category_stats:
                category_stats[category] = {'total': 0, 'successful': 0}
            category_stats[category]['total'] += 1
            if result['execution_success']:
                category_stats[category]['successful'] += 1
        
        for category in category_stats:
            stats = category_stats[category]
            stats['accuracy'] = stats['successful'] / stats['total'] * 100
        
        return {
            'total_tests': total,
            'successful': successful,
            'failed': failed,
            'accuracy_percentage': (successful / total * 100) if total > 0 else 0,
            'meets_90_percent_target': (successful / total * 100) >= 90,
            'complexity_breakdown': complexity_stats,
            'category_breakdown': category_stats
        }
    
    def save_results(self, results: List[Dict], metrics: Dict, model_type: str):
        """Save evaluation results to JSON"""
        output = {
            'model': model_type,
            'metrics': metrics,
            'detailed_results': results
        }
        
        output_path = os.path.join(self.results_dir, f'{model_type}_evaluation_results.json')
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\\nResults saved to: {output_path}")
        return output_path
    
    def print_summary(self, metrics: Dict, model_type: str):
        """Print evaluation summary"""
        print(f"\\n{'='*60}")
        print(f"{model_type.upper()} MODEL - EVALUATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total Test Cases: {metrics['total_tests']}")
        print(f"Successful: {metrics['successful']}")
        print(f"Failed: {metrics['failed']}")
        print(f"Accuracy: {metrics['accuracy_percentage']:.2f}%")
        print(f"Meets 90% Target: {'✓ YES' if metrics['meets_90_percent_target'] else '✗ NO'}")
        
        print(f"\\nBreakdown by Complexity:")
        for complexity, stats in metrics['complexity_breakdown'].items():
            print(f"  {complexity.capitalize()}: {stats['successful']}/{stats['total']} ({stats['accuracy']:.1f}%)")
        
        print(f"\\nBreakdown by Category:")
        for category, stats in metrics['category_breakdown'].items():
            print(f"  {category.capitalize()}: {stats['successful']}/{stats['total']} ({stats['accuracy']:.1f}%)")
        print(f"{'='*60}\\n")


def main():
    """Main evaluation script"""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    evaluator = QueryEvaluator(gemini_api_key=api_key)
    
    # Evaluate Gemini model
    print("\\n" + "="*60)
    print("OBJECTIVE 2: EMPIRICAL VALIDATION (90% BENCHMARK)")
    print("="*60)
    
    gemini_results = evaluator.run_full_evaluation(model_type='gemini')
    gemini_metrics = evaluator.calculate_metrics(gemini_results)
    evaluator.save_results(gemini_results, gemini_metrics, 'gemini')
    evaluator.print_summary(gemini_metrics, 'gemini')
    
    # Evaluate baseline model
    print("\\n" + "="*60)
    print("OBJECTIVE 3: COMPARATIVE ANALYSIS")
    print("="*60)
    
    baseline_results = evaluator.run_full_evaluation(model_type='baseline')
    baseline_metrics = evaluator.calculate_metrics(baseline_results)
    evaluator.save_results(baseline_results, baseline_metrics, 'baseline')
    evaluator.print_summary(baseline_metrics, 'baseline')
    
    # Comparative analysis
    print("\\n" + "="*60)
    print("COMPARATIVE ANALYSIS SUMMARY")
    print("="*60)
    improvement = gemini_metrics['accuracy_percentage'] - baseline_metrics['accuracy_percentage']
    print(f"Gemini Accuracy: {gemini_metrics['accuracy_percentage']:.2f}%")
    print(f"Baseline Accuracy: {baseline_metrics['accuracy_percentage']:.2f}%")
    print(f"Performance Gain: {improvement:.2f} percentage points")
    print(f"Relative Improvement: {(improvement / baseline_metrics['accuracy_percentage'] * 100):.1f}%")
    print("="*60)


if __name__ == "__main__":
    main()
