import csv
import os


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

if __name__ == "__main__":
    script_directory = os.path.dirname(os.path.abspath(__file__))
    # 物料相对于当前py文件的位置
    materials_relative_path = os.path.join('../test/materials')
    # 获取物料的目录路径
    materials_absolute_path = os.path.abspath(os.path.join(script_directory, materials_relative_path))
    # 用法示例
    file1 = os.path.abspath(os.path.join(materials_absolute_path, "diff/doc-v38-charts-0731.csv"))
    file2 = os.path.abspath(os.path.join(materials_absolute_path, "diff/jdpan-chart.csv"))
    compare_csv(file1, file2)