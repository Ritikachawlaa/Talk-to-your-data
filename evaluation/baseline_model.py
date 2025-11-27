"""
Baseline Query Generator (Non-LLM Approach)
Template-based and rule-based query generation for comparative analysis
"""

import pandas as pd
import re
from typing import Dict, Any, Optional


class BaselineQueryGenerator:
    """
    Simple template-based query generator without LLM.
    Uses keyword matching and predefined templates.
    """
    
    def __init__(self):
        self.templates = self._initialize_templates()
        
    def _initialize_templates(self) -> Dict[str, Any]:
        """Initialize query templates and patterns"""
        return {
            'total': {
                'keywords': ['total', 'sum', 'overall'],
                'template': 'df["{col}"].sum()'
            },
            'count': {
                'keywords': ['how many', 'count', 'number of'],
                'template': 'len(df)'
            },
            'average': {
                'keywords': ['average', 'mean', 'avg'],
                'template': 'df["{col}"].mean()'
            },
            'max': {
                'keywords': ['maximum', 'max', 'highest', 'largest', 'most'],
                'template': 'df.loc[df["{col}"].idxmax()]'
            },
            'min': {
                'keywords': ['minimum', 'min', 'lowest', 'smallest', 'least'],
                'template': 'df.loc[df["{col}"].idxmin()]'
            },
            'filter': {
                'keywords': ['show', 'list', 'display', 'get', 'find'],
                'template': 'df[df["{col}"] {op} {val}]'
            },
            'groupby': {
                'keywords': ['by', 'per', 'each', 'group'],
                'template': 'df.groupby("{col}").size()'
            }
        }
    
    def generate_query(self, question: str, df: pd.DataFrame) -> Optional[str]:
        """
        Generate pandas code based on question using templates
        
        Args:
            question: Natural language question
            df: DataFrame to query
            
        Returns:
            Generated pandas code or None if unable to generate
        """
        question_lower = question.lower()
        
        # Detect query type
        query_type = self._detect_query_type(question_lower)
        if not query_type:
            return None
            
        # Extract relevant columns
        columns = self._extract_columns(question_lower, df)
        if not columns:
            return None
            
        # Generate code based on type
        code = self._generate_code(query_type, columns, question_lower, df)
        
        return code
    
    def _detect_query_type(self, question: str) -> Optional[str]:
        """Detect the type of query based on keywords"""
        for query_type, config in self.templates.items():
            for keyword in config['keywords']:
                if keyword in question:
                    return query_type
        return None
    
    def _extract_columns(self, question: str, df: pd.DataFrame) -> list:
        """Extract relevant column names from question"""
        columns = []
        
        # Simple word matching with column names
        for col in df.columns:
            col_lower = col.lower()
            # Check if column name appears in question
            if col_lower in question or col_lower.replace('_', ' ') in question:
                columns.append(col)
        
        return columns
    
    def _generate_code(self, query_type: str, columns: list, question: str, df: pd.DataFrame) -> str:
        """Generate pandas code based on query type and columns"""
        
        if query_type == 'total':
            return self._generate_total_code(columns, df)
        elif query_type == 'count':
            return self._generate_count_code(columns, question, df)
        elif query_type == 'average':
            return self._generate_average_code(columns, df)
        elif query_type == 'max':
            return self._generate_max_code(columns, df)
        elif query_type == 'min':
            return self._generate_min_code(columns, df)
        elif query_type == 'filter':
            return self._generate_filter_code(columns, question, df)
        elif query_type == 'groupby':
            return self._generate_groupby_code(columns, question, df)
        
        return "result_df = df.head()"
    
    def _generate_total_code(self, columns: list, df: pd.DataFrame) -> str:
        """Generate code for total/sum queries"""
        # Look for numeric columns
        numeric_cols = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]
        
        if not numeric_cols:
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if len(numeric_cols) == 1:
            return f"result_df = pd.DataFrame([{{'Total': df['{numeric_cols[0]}'].sum()}}])"
        elif len(numeric_cols) >= 2:
            # Assume revenue calculation (price * quantity pattern)
            return f"result_df = pd.DataFrame([{{'Total Revenue': (df['{numeric_cols[0]}'] * df['{numeric_cols[1]}'].fillna(1)).sum()}}])"
        
        return "result_df = df.sum().to_frame().T"
    
    def _generate_count_code(self, columns: list, question: str, df: pd.DataFrame) -> str:
        """Generate code for count queries"""
        if 'department' in question or 'category' in question or 'region' in question:
            group_col = next((col for col in columns if col.lower() in ['department', 'category', 'region']), None)
            if group_col:
                return f"result_df = df.groupby('{group_col}').size().reset_index(name='Count')"
        
        if columns and 'transaction' in question:
            return f"result_df = pd.DataFrame([{{'Count': len(df)}}])"
        
        return "result_df = pd.DataFrame([{'Count': len(df)}])"
    
    def _generate_average_code(self, columns: list, df: pd.DataFrame) -> str:
        """Generate code for average queries"""
        numeric_cols = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]
        
        if not numeric_cols:
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if numeric_cols:
            col = numeric_cols[0]
            return f"result_df = pd.DataFrame([{{'Average {col}': df['{col}'].mean()}}])"
        
        return "result_df = df.mean().to_frame().T"
    
    def _generate_max_code(self, columns: list, df: pd.DataFrame) -> str:
        """Generate code for max/highest queries"""
        numeric_cols = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]
        
        if numeric_cols:
            col = numeric_cols[0]
            return f"result_df = df.nlargest(1, '{col}')"
        
        return "result_df = df.head(1)"
    
    def _generate_min_code(self, columns: list, df: pd.DataFrame) -> str:
        """Generate code for min/lowest queries"""
        numeric_cols = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]
        
        if numeric_cols:
            col = numeric_cols[0]
            return f"result_df = df.nsmallest(1, '{col}')"
        
        return "result_df = df.head(1)"
    
    def _generate_filter_code(self, columns: list, question: str, df: pd.DataFrame) -> str:
        """Generate code for filtering queries"""
        # Extract comparison operators and values
        if 'greater than' in question or '>' in question:
            match = re.search(r'(\d+)', question)
            if match and columns:
                value = match.group(1)
                col = columns[0]
                return f"result_df = df[df['{col}'] > {value}]"
        
        if 'less than' in question or '<' in question:
            match = re.search(r'(\d+)', question)
            if match and columns:
                value = match.group(1)
                col = columns[0]
                return f"result_df = df[df['{col}'] < {value}]"
        
        # Filter by specific value
        if 'completed' in question:
            return "result_df = df[df['status'] == 'Completed']"
        elif 'failed' in question:
            return "result_df = df[df['status'] == 'Failed']"
        elif 'engineering' in question:
            return "result_df = df[df['department'] == 'Engineering']"
        elif 'electronics' in question:
            return "result_df = df[df['category'] == 'Electronics']"
        
        return "result_df = df.head(10)"
    
    def _generate_groupby_code(self, columns: list, question: str, df: pd.DataFrame) -> str:
        """Generate code for groupby queries"""
        # Find grouping column
        group_cols = ['department', 'category', 'region', 'payment_method', 'salesperson']
        group_col = next((col for col in columns if col.lower() in group_cols), None)
        
        if not group_col:
            group_col = columns[0] if columns else df.columns[0]
        
        # Determine aggregation
        if 'average' in question or 'mean' in question:
            numeric_cols = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]
            if numeric_cols:
                agg_col = numeric_cols[0]
                return f"result_df = df.groupby('{group_col}')['{agg_col}'].mean().reset_index()"
        
        if 'total' in question or 'sum' in question:
            numeric_cols = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]
            if numeric_cols:
                agg_col = numeric_cols[0]
                return f"result_df = df.groupby('{group_col}')['{agg_col}'].sum().reset_index()"
        
        # Default to count
        return f"result_df = df.groupby('{group_col}').size().reset_index(name='Count')"
