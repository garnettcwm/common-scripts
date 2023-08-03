import os

def read_keywords_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        keywords = [line.strip() for line in file.readlines()]
    return keywords

def search_keyword_in_directory(keywords, directory):
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        return []

    found_lines = []

    for root, _, files in os.walk(directory):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if not os.path.isfile(file_path):
                continue

            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                for line_number, line in enumerate(lines, start=1):
                    for keyword in keywords:
                        if keyword in line:
                            # found_lines.append(f"{file_path}:{line_number}: {line.strip()}")
                            found_lines.append(f"{line.strip()}")
                            break

    return found_lines

if __name__ == "__main__":
    keyword_file_path = input("Enter the file path containing keywords (one per line): ")
    search_directory = input("Enter the directory path to search: ")

    keywords = read_keywords_from_file(keyword_file_path)
    if not keywords:
        print("Error: Could not read keywords from the specified file.")
    else:
        result = search_keyword_in_directory(keywords, search_directory)
        if result:
            print("Lines containing the keywords:")
            for line_info in result:
                print(line_info)
        else:
            print("Keywords not found in any of the files.")

# predixy-openeuler22-arm64:1.0.5-2.1.5
# /Users/chenwenming10/workspace/garnettcwm/common-scripts/diff/0-extra-image.csv
# /Users/chenwenming10/workspace/garnettcwm/common-scripts/test/image