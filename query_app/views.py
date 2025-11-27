import os
import pandas as pd
import google.generativeai as genai
from django.shortcuts import render
from django.http import HttpResponse
from dotenv import load_dotenv
from io import StringIO, BytesIO
import re
import json
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import base64

# --- AI Configuration ---
load_dotenv()
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    GEMINI_CONFIGURED = True
except Exception as e:
    print(f"Warning: Gemini API not configured. {e}")
    GEMINI_CONFIGURED = False

# --- Helper Functions ---

def get_df_info_for_ai(df):
    """Analyzes a DataFrame and returns a string summary for the AI."""
    schema_parts = []
    try:
        sample_rows = df.head(3).to_string(index=False)
    except Exception:
        sample_rows = "Could not display sample rows."
    
    for column in df.columns:
        dtype = str(df[column].dtype)
        schema_parts.append(f"- '{column}' (type: {dtype})")
        
    return "\n".join(schema_parts) + f"\n\nHere are some sample rows:\n{sample_rows}"

def generate_suggested_questions(schema):
    """Uses the AI to generate suggested questions based on the data schema."""
    if not GEMINI_CONFIGURED:
        return []
    
    prompt = f"""
    Based on the following schema for a pandas DataFrame, please generate 3 interesting and diverse analytical questions that a user could ask.
    
    Schema:
    {schema}

    Return the questions as a JSON list of strings. For example: ["Question 1?", "Question 2?", "Question 3?"]
    """
    try:
        response = model.generate_content(prompt)
        suggestions_text = response.text.strip()
        # A more robust way to find the JSON list
        match = re.search(r'\[.*\]', suggestions_text, re.DOTALL)
        if match:
            suggestions_list = json.loads(match.group(0))
            return suggestions_list
        return ["What is the total count of records?", "Can you show the first 5 rows?"] # Fallback
    except Exception as e:
        print(f"Could not generate suggested questions: {e}")
        return ["What is the total count of records?", "Can you show the first 5 rows?"]

def construct_analysis_prompt(schema, user_question):
    """Constructs the detailed prompt for the AI to generate analysis code."""
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

def execute_generated_code(code, df):
    """Safely executes the AI-generated Python code and returns the resulting DataFrame."""
    try:
        execution_globals = {'pd': pd, 'df': df}
        execution_locals = {}
        exec(code, execution_globals, execution_locals)
        result_df = execution_locals.get('result_df')
        if isinstance(result_df, pd.DataFrame):
            return result_df, None
        elif result_df is not None:
             # If the result is not a dataframe, convert it to one
            return pd.DataFrame([str(result_df)]), None
        else:
            return None, "Error: No `result_df` variable (DataFrame) was produced by the executed code."
            
    except Exception as e:
        return None, f"Error executing generated code: {str(e)}"

def should_generate_chart(result_df, query_text):
    """Determine if a chart should be generated based on the result and query"""
    if result_df is None or len(result_df) == 0:
        return False
    
    # Keywords that suggest visualization
    viz_keywords = ['show', 'compare', 'trend', 'distribution', 'by', 'per', 'top', 'bottom']
    query_lower = query_text.lower()
    
    # Check if query suggests visualization
    has_viz_keyword = any(keyword in query_lower for keyword in viz_keywords)
    
    # Check if result is suitable for charting
    is_suitable = len(result_df) > 1 and len(result_df) < 100  # Not too small or too large
    
    return has_viz_keyword and is_suitable

def generate_chart(result_df, query_text):
    """Generate an appropriate chart based on the result DataFrame"""
    try:
        # Set style
        sns.set_style("whitegrid")
        plt.figure(figsize=(10, 6))
        
        # Determine chart type based on data
        numeric_cols = result_df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = result_df.select_dtypes(include=['object']).columns.tolist()
        
        if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
            # Bar chart for categorical vs numeric
            x_col = categorical_cols[0]
            y_col = numeric_cols[0]
            
            # Limit to top 15 items for readability
            plot_df = result_df.nlargest(15, y_col) if len(result_df) > 15 else result_df
            
            plt.bar(range(len(plot_df)), plot_df[y_col], color='#4f46e5')
            plt.xticks(range(len(plot_df)), plot_df[x_col], rotation=45, ha='right')
            plt.xlabel(x_col.replace('_', ' ').title())
            plt.ylabel(y_col.replace('_', ' ').title())
            plt.title(f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}")
            
        elif len(numeric_cols) >= 2:
            # Scatter plot for two numeric columns
            plt.scatter(result_df[numeric_cols[0]], result_df[numeric_cols[1]], 
                       color='#4f46e5', alpha=0.6, s=100)
            plt.xlabel(numeric_cols[0].replace('_', ' ').title())
            plt.ylabel(numeric_cols[1].replace('_', ' ').title())
            plt.title(f"{numeric_cols[1].replace('_', ' ').title()} vs {numeric_cols[0].replace('_', ' ').title()}")
            
        elif len(numeric_cols) == 1:
            # Histogram for single numeric column
            plt.hist(result_df[numeric_cols[0]], bins=20, color='#4f46e5', alpha=0.7, edgecolor='black')
            plt.xlabel(numeric_cols[0].replace('_', ' ').title())
            plt.ylabel('Frequency')
            plt.title(f"Distribution of {numeric_cols[0].replace('_', ' ').title()}")
            
        else:
            # Default: just show first column as bar chart
            first_col = result_df.columns[0]
            plt.bar(range(len(result_df)), result_df[first_col], color='#4f46e5')
            plt.xlabel('Index')
            plt.ylabel(first_col.replace('_', ' ').title())
            plt.title(f"{first_col.replace('_', ' ').title()}")
        
        plt.tight_layout()
        
        # Save to base64 string
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
        
        return image_base64
        
    except Exception as e:
        print(f"Error generating chart: {e}")
        plt.close()
        return None

def generate_sql_command(schema, user_question, df):
    """Generate SQL command equivalent to the pandas operation"""
    if not GEMINI_CONFIGURED:
        return None
    
    try:
        # Assume table name based on common convention
        table_name = "data_table"
        
        prompt = f"""
You are an expert SQL developer. Convert the following natural language question into a SQL query.

The data is in a table named '{table_name}' with the following schema:
{schema}

User's Question: "{user_question}"

Instructions:
1. Write a SQL query that answers the user's question
2. Use standard SQL syntax (compatible with SQLite/PostgreSQL/MySQL)
3. Return ONLY the SQL query, no explanations
4. Do not include any markdown formatting like ```sql
5. Make the query clean and readable
"""
        
        response = model.generate_content(prompt)
        sql_query = response.text.strip()
        
        # Clean up any markdown formatting
        sql_query = re.sub(r'```sql\n|```', '', sql_query).strip()
        
        return sql_query
        
    except Exception as e:
        print(f"Error generating SQL: {e}")
        return None

# --- Django Views ---

def index(request):
    """Main view to handle user interaction and analysis."""
    context = {
        'query_history': request.session.get('query_history', [])
    }

    if not GEMINI_CONFIGURED:
        context['error'] = "AI model is not configured. Please ensure your GEMINI_API_KEY is set in a .env file."
        return render(request, 'query_app/index.html', context)

    if request.method == 'POST':
        query_text = request.POST.get('query', '').strip()
        uploaded_file = request.FILES.get('csv_file')
        
        if uploaded_file:
            try:
                csv_data = uploaded_file.read().decode('utf-8')
                request.session['csv_data'] = csv_data
                request.session['file_name'] = uploaded_file.name
                # Clear previous results when a new file is uploaded
                request.session['csv_export_data'] = ''
            except Exception as e:
                context['error'] = f"Error reading the uploaded file: {e}"
                return render(request, 'query_app/index.html', context)

        csv_data_from_session = request.session.get('csv_data')
        if csv_data_from_session:
            try:
                df = pd.read_csv(StringIO(csv_data_from_session))
                schema = get_df_info_for_ai(df)
                context['file_name'] = request.session.get('file_name')
                
                if uploaded_file and not query_text:
                     context['suggested_questions'] = generate_suggested_questions(schema)

                if query_text:
                    context['query_text'] = query_text
                    
                    history = request.session.get('query_history', [])
                    if query_text not in history:
                        history.insert(0, query_text)
                    request.session['query_history'] = history[:10]
                    context['query_history'] = request.session['query_history']

                    prompt = construct_analysis_prompt(schema, query_text)
                    response = model.generate_content(prompt)
                    
                    generated_code = response.text
                    generated_code = re.sub(r'```python\\n|```', '', generated_code).strip()
                    
                    # Generate SQL command
                    sql_command = generate_sql_command(schema, query_text, df)
                    if sql_command:
                        context['sql_command'] = sql_command
                    
                    result_df, error = execute_generated_code(generated_code, df)
                    
                    if error:
                        context['error'] = error
                    else:
                        # For display
                        context['result'] = result_df.to_string(index=False)
                        # For export
                        request.session['csv_export_data'] = result_df.to_csv(index=False)
                        
                        # Generate chart if appropriate
                        if should_generate_chart(result_df, query_text):
                            chart_image = generate_chart(result_df, query_text)
                            if chart_image:
                                context['chart_image'] = chart_image
                    
                    context['generated_code'] = generated_code

            except Exception as e:
                context['error'] = f"An error occurred during analysis: {e}"
        
        elif query_text:
             context['error'] = "Please upload a CSV file before asking a question."

    return render(request, 'query_app/index.html', context)

def download_csv(request):
    """Handles the CSV file download."""
    csv_data = request.session.get('csv_export_data', None)
    if csv_data:
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="query_result.csv"'
        return response
    else:
        return HttpResponse("No data available to download.", status=404)


# --- Evaluation Views (Research Objectives 2 & 3) ---

def evaluation_dashboard(request):
    """Display evaluation dashboard"""
    context = {}
    
    # Check if results exist
    results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'evaluation', 'results')
    gemini_results_path = os.path.join(results_dir, 'gemini_evaluation_results.json')
    baseline_results_path = os.path.join(results_dir, 'baseline_evaluation_results.json')
    
    if os.path.exists(gemini_results_path) and os.path.exists(baseline_results_path):
        with open(gemini_results_path, 'r') as f:
            gemini_data = json.load(f)
        with open(baseline_results_path, 'r') as f:
            baseline_data = json.load(f)
        
        context['results'] = True
        context['gemini_accuracy'] = round(gemini_data['metrics']['accuracy_percentage'], 2)
        context['baseline_accuracy'] = round(baseline_data['metrics']['accuracy_percentage'], 2)
        context['improvement'] = round(context['gemini_accuracy'] - context['baseline_accuracy'], 2)
        context['meets_target'] = gemini_data['metrics']['meets_90_percent_target']
        context['total_tests'] = gemini_data['metrics']['total_tests']
        context['gemini_successful'] = gemini_data['metrics']['successful']
        context['baseline_successful'] = baseline_data['metrics']['successful']
    
    return render(request, 'query_app/evaluation_dashboard.html', context)


def run_evaluation(request):
    """Run the full evaluation suite"""
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from evaluation.evaluator import QueryEvaluator
    
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        evaluator = QueryEvaluator(gemini_api_key=api_key)
        
        # Run evaluations
        gemini_results = evaluator.run_full_evaluation(model_type='gemini')
        gemini_metrics = evaluator.calculate_metrics(gemini_results)
        evaluator.save_results(gemini_results, gemini_metrics, 'gemini')
        
        baseline_results = evaluator.run_full_evaluation(model_type='baseline')
        baseline_metrics = evaluator.calculate_metrics(baseline_results)
        evaluator.save_results(baseline_results, baseline_metrics, 'baseline')
        
        # Generate comparative analysis
        from evaluation.comparative_analysis import ComparativeAnalyzer
        results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'evaluation', 'results')
        analyzer = ComparativeAnalyzer(results_dir)
        report = analyzer.generate_comparison_report()
        comparison_table = analyzer.generate_detailed_comparison_table()
        analyzer.save_comparison_report(report)
        analyzer.save_comparison_table(comparison_table)
        
        return HttpResponse("Evaluation completed successfully! <a href='/evaluation/'>View Results</a>")
    except Exception as e:
        return HttpResponse(f"Error running evaluation: {str(e)}", status=500)


def download_evaluation_results(request):
    """Download evaluation results as JSON"""
    results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'evaluation', 'results')
    comparison_path = os.path.join(results_dir, 'comparative_analysis.json')
    
    if os.path.exists(comparison_path):
        with open(comparison_path, 'r') as f:
            data = f.read()
        response = HttpResponse(data, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="evaluation_results.json"'
        return response
    else:
        return HttpResponse("No evaluation results found. Please run evaluation first.", status=404)


def download_comparison_csv(request):
    """Download detailed comparison as CSV"""
    results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'evaluation', 'results')
    csv_path = os.path.join(results_dir, 'detailed_comparison.csv')
    
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            data = f.read()
        response = HttpResponse(data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="detailed_comparison.csv"'
        return response
    else:
        return HttpResponse("No comparison data found. Please run evaluation first.", status=404)

