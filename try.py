import pandas as pd

# Example API data
api_data = [
    {"StudentID": 1, "Name": "Alice", "Marks": 85},
    {"StudentID": 2, "Name": "Bob", "Marks": 90},
    {"StudentID": 3, "Name": "Charlie", "Marks": 78}
]

# Save to CSV
df = pd.DataFrame(api_data)
df.to_csv("student_marks.csv", index=False)
print("CSV saved.")
