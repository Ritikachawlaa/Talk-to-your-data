from django.db import models

class Sale(models.Model):
    date = models.DateTimeField()
    product = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    salesperson = models.CharField(max_length=100)
    region = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.product} sale on {self.date.strftime('%Y-%m-%d')}"
