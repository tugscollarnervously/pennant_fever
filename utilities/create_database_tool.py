import psycopg2

# Connect to the PostgreSQL server (but not a specific database yet)
conn = psycopg2.connect("dbname=postgres user=postgres password=bacon host=localhost")

# Open a cursor to perform database operations
conn.autocommit = True
cursor = conn.cursor()

# Create the database
cursor.execute('CREATE DATABASE pennant_race;')

print("Database pennant_race created successfully!")

# Close the cursor and connection
cursor.close()
conn.close()
