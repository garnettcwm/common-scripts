import csv
import os


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
    current_directory = os.getcwd()
    print(current_directory)

    script_directory = os.path.dirname(os.path.abspath(__file__))
    # 物料相对于当前py文件的位置
    relative_path = os.path.join('../test/materials')
    # 获取物料的目录路径
    materials_absolute_path = os.path.abspath(os.path.join(script_directory, relative_path))
    print(materials_absolute_path)

    csv_file = os.path.abspath(os.path.join(materials_absolute_path, "diff/jdpan-image.csv"))
    duplicates = check_duplicate_file_names(csv_file)

    if duplicates:
        print("Duplicate file names found:")
        for file_name in duplicates:
            print(file_name)
    else:
        print("No duplicate file names found.")