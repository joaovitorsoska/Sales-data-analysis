import pandas as pd
import random
from datetime import datetime, timedelta

products = ["Laptop", "Mouse", "Keyboard", "Monitor", "Headset"]
categories = ["Electronics", "Accessories"]
regions = ["South", "Southeast", "North", "Northeast"]

data = []

start_date = datetime(2024, 1, 1)

for i in range(500):
    date = start_date + timedelta(days=random.randint(0, 365))
    product = random.choice(products)
    category = random.choice(categories)
    price = random.randint(50, 5000)
    quantity = random.randint(1, 5)
    region = random.choice(regions)

    data.append([date, product, category, price, quantity, region])

df = pd.DataFrame(data, columns=["date", "product", "category", "price", "quantity", "region"])

df.to_csv("sales.csv", index=False)

print("Dataset criado com sucesso!")
