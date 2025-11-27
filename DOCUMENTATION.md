# Talk to Your Data - Technical Documentation

## 📚 Complete Developer Documentation

This document provides comprehensive technical documentation for developers working with the "Talk to Your Data" application.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Core Components](#core-components)
3. [API Reference](#api-reference)
4. [Database Schema](#database-schema)
5. [Frontend Guide](#frontend-guide)
6. [Backend Guide](#backend-guide)
7. [AI Integration](#ai-integration)
8. [Configuration](#configuration)
9. [Development Workflow](#development-workflow)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Development Environment Setup

#### Prerequisites
```bash
# Python 3.8+
python --version

# pip
pip --version

# Git
git --version
```

#### Installation Steps

1. **Clone and Setup**
```bash
git clone <repository-url>
cd talk_to_your_data
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Environment Configuration**
```bash
# Create .env file
echo "GEMINI_API_KEY=your_key_here" > .env
```

3. **Database Setup**
```bash
python manage.py makemigrations
python manage.py migrate
```

4. **Run Development Server**
```bash
python manage.py runserver
```

---

## Core Components

### 1. Views Module (`query_app/views.py`)

#### Main View Function

```python
def index(request):
    """
    Main view handling both GET and POST requests.
    
    GET: Displays the main interface
    POST: Processes file uploads and queries
    
    Returns:
        HttpResponse: Rendered template with context
    """
```

**Context Variables Passed to Template**:
- `file_name`: Name of uploaded CSV
- `query_text`: User's natural language query
- `result`: Query results as string
- `generated_code`: Python/pandas code
- `sql_command`: SQL query
- `chart_image`: Base64 encoded chart
- `error`: Error message if any
- `query_history`: List of previous queries
- `suggested_questions`: AI-generated suggestions

#### Code Generation Function

```python
def generate_code(schema: str, question: str) -> str:
    """
    Generate Python/pandas code using Gemini API.
    
    Args:
        schema (str): CSV schema description
        question (str): Natural language question
        
    Returns:
        str: Generated Python code
        
    Raises:
        Exception: If API call fails
    """
```

**Prompt Template**:
```python
prompt = f"""You are a data analyst. Given this CSV schema:
{schema}

Write Python pandas code to answer: {question}

Requirements:
- Use 'df' as the DataFrame variable
- Store result in 'result_df'
- Return ONLY code, no explanations
"""
```

#### SQL Generation Function

```python
def generate_sql_command(schema: str, user_question: str, df: pd.DataFrame) -> str:
    """
    Generate SQL query equivalent to pandas operation.
    
    Args:
        schema (str): Database schema
        user_question (str): Natural language query
        df (pd.DataFrame): Source DataFrame
        
    Returns:
        str: SQL query string
    """
```

#### Code Execution Function

```python
def execute_generated_code(code: str, df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """
    Execute generated code in isolated environment.
    
    Args:
        code (str): Python code to execute
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        tuple: (result_df, error_message)
        - result_df: Resulting DataFrame or None
        - error_message: Error string or None
    """
```

**Execution Environment**:
```python
execution_globals = {'pd': pd, 'df': df}
execution_locals = {}
exec(code, execution_globals, execution_locals)
result_df = execution_locals.get('result_df')
```

#### Chart Generation Functions

```python
def should_generate_chart(result_df: pd.DataFrame, query_text: str) -> bool:
    """
    Determine if chart should be generated.
    
    Args:
        result_df: Query result DataFrame
        query_text: User's query
        
    Returns:
        bool: True if chart should be generated
    """
```

**Decision Criteria**:
- Query contains visualization keywords
- Result has 1-100 rows
- Data is suitable for charting

```python
def generate_chart(result_df: pd.DataFrame, query_text: str) -> str:
    """
    Generate chart visualization.
    
    Args:
        result_df: Data to visualize
        query_text: Query for context
        
    Returns:
        str: Base64 encoded PNG image
    """
```

**Chart Types**:
1. **Bar Chart**: Categorical + Numeric columns
2. **Scatter Plot**: Two numeric columns
3. **Histogram**: Single numeric column

#### CSV Download Function

```python
def download_csv(request):
    """
    Handle CSV file download.
    
    Returns:
        HttpResponse: CSV file or 404
    """
```

---

### 2. Models Module (`query_app/models.py`)

#### DatasetUpload Model

```python
class DatasetUpload(models.Model):
    """
    Stores metadata about uploaded CSV files.
    """
    file_name = models.CharField(max_length=255)
    upload_date = models.DateTimeField(default=timezone.now)
    row_count = models.IntegerField(null=True, blank=True)
    column_count = models.IntegerField(null=True, blank=True)
    columns = models.TextField()  # JSON format
    
    def __str__(self):
        return f"{self.file_name} ({self.upload_date})"
```

**Usage Example**:
```python
dataset = DatasetUpload.objects.create(
    file_name='sales.csv',
    row_count=1000,
    column_count=5,
    columns=json.dumps(['id', 'product', 'price', 'quantity', 'date'])
)
```

#### QueryHistory Model

```python
class QueryHistory(models.Model):
    """
    Stores query execution history and results.
    """
    dataset = models.ForeignKey(DatasetUpload, on_delete=models.CASCADE)
    query_text = models.TextField()
    query_date = models.DateTimeField(default=timezone.now)
    python_code = models.TextField(blank=True)
    sql_command = models.TextField(blank=True)
    result_data = models.TextField(blank=True)
    has_chart = models.BooleanField(default=False)
    chart_image = models.TextField(blank=True)
    execution_success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    execution_time_ms = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-query_date']
```

**Usage Example**:
```python
query = QueryHistory.objects.create(
    dataset=dataset,
    query_text="What is the total revenue?",
    python_code="result_df = df['revenue'].sum()",
    sql_command="SELECT SUM(revenue) FROM data_table",
    result_data="15000",
    execution_success=True
)
```

---

### 3. URL Configuration

#### App URLs (`query_app/urls.py`)

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('download/', views.download_csv, name='download_csv'),
]
```

#### Project URLs (`talk_to_your_data/urls.py`)

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('query_app.urls')),
]
```

---

## API Reference

### Gemini API Integration

#### Configuration

```python
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
```

#### Model Initialization

```python
model = genai.GenerativeModel('gemini-2.0-flash-exp')
```

#### API Call Pattern

```python
try:
    response = model.generate_content(prompt)
    code = response.text.strip()
    # Clean markdown formatting
    code = code.replace('```python', '').replace('```', '').strip()
    return code
except Exception as e:
    print(f"Error: {e}")
    return None
```

#### Rate Limits
- **Requests per minute**: 60 (free tier)
- **Requests per day**: 1500 (free tier)
- **Token limit**: Varies by model

---

## Database Schema

### Entity Relationship Diagram

```
DatasetUpload (1) ----< (N) QueryHistory
```

### Table Structures

#### `query_app_datasetupload`
```sql
CREATE TABLE query_app_datasetupload (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name VARCHAR(255) NOT NULL,
    upload_date DATETIME NOT NULL,
    row_count INTEGER,
    column_count INTEGER,
    columns TEXT NOT NULL
);
```

#### `query_app_queryhistory`
```sql
CREATE TABLE query_app_queryhistory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL,
    query_text TEXT NOT NULL,
    query_date DATETIME NOT NULL,
    python_code TEXT,
    sql_command TEXT,
    result_data TEXT,
    has_chart BOOLEAN NOT NULL DEFAULT 0,
    chart_image TEXT,
    execution_success BOOLEAN NOT NULL DEFAULT 1,
    error_message TEXT,
    execution_time_ms INTEGER,
    FOREIGN KEY (dataset_id) REFERENCES query_app_datasetupload(id)
);
```

---

## Frontend Guide

### HTML Structure

#### Template Hierarchy

```html
<!DOCTYPE html>
<html>
<head>
    <!-- Meta tags, title, CSS -->
</head>
<body>
    <aside class="sidebar">
        <!-- Query history -->
    </aside>
    <main class="main-content">
        <div class="container">
            <header><!-- Title --></header>
            <form><!-- Upload & Query --></form>
            <section><!-- Suggestions --></section>
            <section><!-- Results with tabs --></section>
        </div>
    </main>
    <script><!-- JavaScript --></script>
</body>
</html>
```

### CSS Architecture

#### CSS Variables

```css
:root {
    --primary-text: #1f2937;
    --secondary-text: #6b7280;
    --accent-color: #4f46e5;
    --accent-hover: #4338ca;
    --border-color: #e5e7eb;
    --card-bg: #ffffff;
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}
```

#### Component Classes

**Tabs**:
```css
.tabs { /* Tab container */ }
.tab-btn { /* Tab button */ }
.tab-btn.active { /* Active tab */ }
.tab-content { /* Tab content */ }
.tab-content.active { /* Active content */ }
```

**Code Blocks**:
```css
.code-header { /* Header with copy button */ }
.copy-btn { /* Copy button */ }
.copy-btn.copied { /* Copied state */ }
.code-block { /* Code display */ }
```

### JavaScript Functions

#### Tab Switching

```javascript
function switchTab(tabName, clickedButton) {
    // Remove active class from all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Add active class to selected tab
    document.getElementById(tabName + '-tab').classList.add('active');
    clickedButton.classList.add('active');
}
```

#### Copy to Clipboard

```javascript
function copyToClipboard(elementId, button) {
    const element = document.getElementById(elementId);
    const text = element.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        // Show feedback
        const originalText = button.textContent;
        button.textContent = '✅ Copied!';
        button.classList.add('copied');
        
        // Reset after 2 seconds
        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard');
    });
}
```

---

## Backend Guide

### Session Management

#### Storing Data

```python
# Store CSV data
request.session['csv_data'] = csv_content
request.session['file_name'] = file.name

# Store query results
request.session['csv_export_data'] = result_df.to_csv(index=False)
```

#### Retrieving Data

```python
# Get CSV data
csv_data = request.session.get('csv_data')
file_name = request.session.get('file_name')

# Get query history
query_history = request.session.get('query_history', [])
```

### Error Handling

#### Try-Except Pattern

```python
try:
    # Risky operation
    result = execute_code(code, df)
except Exception as e:
    # Log error
    print(f"Error: {str(e)}")
    # Return user-friendly message
    context['error'] = "An error occurred processing your query."
```

### Data Processing

#### CSV to DataFrame

```python
from io import StringIO
import pandas as pd

csv_data = request.session.get('csv_data')
df = pd.read_csv(StringIO(csv_data))
```

#### Schema Extraction

```python
schema = f"Columns: {', '.join(df.columns)}\n"
schema += f"Data types:\n"
for col in df.columns:
    schema += f"- {col}: {df[col].dtype}\n"
schema += f"\nFirst few rows:\n{df.head(3).to_string()}"
```

---

## AI Integration

### Prompt Engineering

#### Code Generation Prompt

```python
prompt = f"""You are a data analyst. Given this CSV schema:
{schema}

Write Python pandas code to answer: {question}

Requirements:
1. Use 'df' as the DataFrame variable name
2. Store the final result in a variable called 'result_df'
3. Return ONLY the code, no explanations or markdown
4. Handle potential errors gracefully
5. Keep code concise and efficient

Example:
result_df = df.groupby('category')['sales'].sum()
"""
```

#### SQL Generation Prompt

```python
prompt = f"""Given this database schema:
{schema}

User question: {user_question}

Generate ONLY the SQL query that would answer this question.
Return ONLY the SQL code, no explanations, no markdown formatting.
Assume the table name is 'data_table'.
"""
```

### Response Processing

```python
def clean_code_response(response_text: str) -> str:
    """Remove markdown formatting from API response."""
    code = response_text.strip()
    code = code.replace('```python', '')
    code = code.replace('```sql', '')
    code = code.replace('```', '')
    return code.strip()
```

---

## Configuration

### Django Settings

#### Key Settings

```python
# settings.py

# Security
SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Session
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 24 hours

# File Upload
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
```

### Environment Variables

```env
# Required
GEMINI_API_KEY=your_api_key_here

# Optional
DEBUG=True
SECRET_KEY=your_secret_key
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

---

## Development Workflow

### Adding New Features

1. **Create Branch**
```bash
git checkout -b feature/new-feature
```

2. **Make Changes**
```bash
# Edit files
# Test locally
python manage.py runserver
```

3. **Run Tests**
```bash
python manage.py test
```

4. **Commit Changes**
```bash
git add .
git commit -m "Add new feature"
```

5. **Push and Create PR**
```bash
git push origin feature/new-feature
```

### Database Migrations

```bash
# Create migrations
python manage.py makemigrations

# View SQL
python manage.py sqlmigrate query_app 0001

# Apply migrations
python manage.py migrate

# Rollback
python manage.py migrate query_app 0001
```

---

## Troubleshooting

### Common Issues

#### 1. Gemini API Errors

**Problem**: `API key not found`
```python
# Solution
# Check .env file exists
# Verify GEMINI_API_KEY is set
load_dotenv()
print(os.getenv('GEMINI_API_KEY'))  # Should not be None
```

#### 2. DataFrame Execution Errors

**Problem**: `result_df not found`
```python
# Solution
# Ensure generated code creates result_df
# Check execution_locals for result_df
result_df = execution_locals.get('result_df')
if result_df is None:
    # Handle missing result
```

#### 3. Chart Generation Fails

**Problem**: Charts not displaying
```python
# Solution
# Check matplotlib backend
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

# Verify base64 encoding
import base64
from io import BytesIO
buffer = BytesIO()
plt.savefig(buffer, format='png')
image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
```

#### 4. Session Data Lost

**Problem**: Data disappears between requests
```python
# Solution
# Ensure session is saved
request.session.modified = True

# Check session middleware
# MIDDLEWARE should include:
# 'django.contrib.sessions.middleware.SessionMiddleware'
```

---

## Best Practices

### Code Quality

1. **Follow PEP 8**
```bash
pip install flake8
flake8 query_app/
```

2. **Type Hints**
```python
def generate_code(schema: str, question: str) -> str:
    pass
```

3. **Docstrings**
```python
def function_name(param: type) -> return_type:
    """
    Brief description.
    
    Args:
        param: Description
        
    Returns:
        Description
    """
```

### Security

1. **Never commit secrets**
```bash
# Add to .gitignore
.env
*.pyc
__pycache__/
db.sqlite3
```

2. **Validate user input**
```python
if not file.name.endswith('.csv'):
    return HttpResponse("Only CSV files allowed", status=400)
```

3. **Sanitize code execution**
```python
# Limited globals
execution_globals = {'pd': pd, 'df': df}
# No __builtins__ access
```

---

## Performance Optimization

### Caching

```python
from django.core.cache import cache

# Cache query results
cache_key = f"query_{hash(query_text)}"
result = cache.get(cache_key)
if result is None:
    result = execute_query(query_text)
    cache.set(cache_key, result, 300)  # 5 minutes
```

### Database Optimization

```python
# Use select_related for foreign keys
queries = QueryHistory.objects.select_related('dataset').all()

# Use only() to limit fields
queries = QueryHistory.objects.only('query_text', 'query_date')
```

---

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set up static files serving
- [ ] Configure HTTPS
- [ ] Set up logging
- [ ] Configure email backend
- [ ] Set up monitoring
- [ ] Configure backups

### Example Production Settings

```python
# Production settings
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'dbname',
        'USER': 'dbuser',
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## Additional Resources

### Documentation Links
- [Django Documentation](https://docs.djangoproject.com/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Matplotlib Documentation](https://matplotlib.org/stable/contents.html)

### Useful Commands

```bash
# Django
python manage.py shell          # Interactive shell
python manage.py dbshell         # Database shell
python manage.py showmigrations  # Show migrations
python manage.py createsuperuser # Create admin user

# Development
pip freeze > requirements.txt    # Update dependencies
python manage.py check           # Check for issues
python manage.py test --verbose  # Run tests with output
```

---

This documentation is maintained by the development team. For questions or updates, please open an issue or submit a pull request.
