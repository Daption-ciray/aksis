import pandas as pd

# Reading the CSV file that we got from cloud, i write it just for sake of testing
file_path = 'student_marks.csv'  # Replace with the actual file path
data = pd.read_csv(file_path)

# getting the ID's of stored lessons
lesson_ids=data["ID"].tolist()

#get the json data which is data=response.json()["Data"]

"""
    Checks for new records in the raw data and returns a list of new records.

    Args:
        existing_ids (list): List of IDs already stored (from the CSV file).
        raw_data (list): JSON data containing new records.

    Returns:
        list: A list of new records if any, or an empty list.
"""
def check_new_record(existing_ids,raw_data):
    results=list()
    new_results=list()
    for key in raw_data :
            items=key["Items"]
            for item in items:
                exam_ID=item["SinavID"]
                lesson_name=item["DersAdi"]
                exam_date=item["SinavTarihiString"]
                exam_mark=item["Notu"]
                percantage=item["EtkiOrani"]

                results.append({"ID":exam_ID,"Lesson":lesson_name,"Date":exam_date,"Mark":exam_mark,"Percantage":percantage})

    for result in result:
         if result["ID"] not in existing_ids:
            new_results.append(result)

    return new_results  
         
    