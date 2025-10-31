import pandas as pd
from django.core.management.base import BaseCommand
from query_app.models import Sale

# This class MUST be named 'Command'
class Command(BaseCommand):
    help = 'Populates the database with sales data from sales_data.csv'

    def handle(self, *args, **kwargs):
        # Clear existing data
        self.stdout.write('Clearing existing sales data...')
        Sale.objects.all().delete()

        # Read the CSV file
        try:
            # Assumes sales_data.csv is in the root directory
            df = pd.read_csv('sales_data.csv', parse_dates=['Date'])
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('sales_data.csv not found! Make sure it is in the main project directory.'))
            return

        self.stdout.write('Loading new data from sales_data.csv...')
        
        sales_to_create = []
        for _, row in df.iterrows():
            sales_to_create.append(
                Sale(
                    date=row['Date'],
                    product=row['Product'],
                    category=row['Category'],
                    price=row['Price'],
                    quantity=row['Quantity'],
                    salesperson=row['Salesperson'],
                    region=row['Region']
                )
            )
        
        Sale.objects.bulk_create(sales_to_create)

        self.stdout.write(self.style.SUCCESS(f'Successfully populated the database with {len(sales_to_create)} records.'))

