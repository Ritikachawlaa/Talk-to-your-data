import os
import pandas as pd
import google.generativeai as genai
from django.shortcuts import render
from django.http import HttpResponse
from dotenv import load_dotenv
from io import StringIO
import re
import json

# --- AI Configuration ---
load_dotenv()
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro')
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
                    generated_code = re.sub(r'```python\n|```', '', generated_code).strip()
                    
                    result_df, error = execute_generated_code(generated_code, df)
                    
                    if error:
                        context['error'] = error
                    else:
                        # For display
                        context['result'] = result_df.to_string(index=False)
                        # For export
                        request.session['csv_export_data'] = result_df.to_csv(index=False)
                    
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

