import pandas as pd


df = pd.read_csv("sales.csv")


print("Dados:")
print(df.head())


df["revenue"] = df["price"] * df["quantity"]


top_products = df.groupby("product")["revenue"].sum().sort_values(ascending=False)

print("\nTop produtos por receita:")
print(top_products)


region_sales = df.groupby("region")["revenue"].sum()

print("\nVendas por região:")
print(region_sales)

import sqlite3

# criar conexão com banco
conn = sqlite3.connect("sales.db")

# salvar dados no banco
df.to_sql("sales", conn, if_exists="replace", index=False)

# consulta SQL
query = """
SELECT product, SUM(revenue) as total_revenue
FROM sales
GROUP BY product
ORDER BY total_revenue DESC
"""

result = pd.read_sql(query, conn)

print("\nTop produtos (SQL):")
print(result)