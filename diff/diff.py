import csv

def compare_csv(file1, file2):
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        csv_reader1 = csv.reader(f1)
        csv_reader2 = csv.reader(f2)

        rows_file1 = set()
        rows_file2 = set()

        for row in csv_reader1:
            rows_file1.add(row[0])  # 假设每行只有一个大字符串

        for row in csv_reader2:
            rows_file2.add(row[0])  # 假设每行只有一个大字符串

        diff_rows = rows_file1 - rows_file2

        for row in diff_rows:
            print(row)

# 用法示例
file1 = './26-image.csv'
file2 = './doc-v23-image.csv'
compare_csv(file1, file2)