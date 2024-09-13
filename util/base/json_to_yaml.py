import json
import yaml
import sys

def json_to_yaml(input_file, output_file: str):

    with open(input_file, 'r') as f:
        json_data = json.load(f)

    with open(output_file, 'w') as f:
        yaml.dump(json_data, f, default_flow_style=False)

    print(f"Converted {input_file} to {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: json_to_yaml.py <input.json> <output.yaml>")
        sys.exit(1)
    json_to_yaml(sys.argv[1], sys.argv[2])