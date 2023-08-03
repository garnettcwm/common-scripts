import csv

def check_duplicate_file_names(csv_file):
    file_names = set()
    duplicate_names = set()

    with open(csv_file, 'r', newline='', encoding='utf-8') as file:
        csv_reader = csv.reader(file, delimiter=' ')
        for row in csv_reader:
            if len(row) >= 2:
                file_name = row[1].strip()
                #print(file_name)
                if file_name in file_names:
                    duplicate_names.add(file_name)
                else:
                    file_names.add(file_name)

    return duplicate_names

if __name__ == "__main__":
    csv_file = "/Users/chenwenming10/workspace/garnettcwm/common-scripts/diff/jdpan-image.csv"  # Replace with the path to your CSV file
    duplicates = check_duplicate_file_names(csv_file)

    if duplicates:
        print("Duplicate file names found:")
        for file_name in duplicates:
            print(file_name)
    else:
        print("No duplicate file names found.")