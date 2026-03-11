import sys
import csv

REQUIRED_COLUMNS = ["protein", "mutation", "reference_accession", "effect", "source_publication"]

def validate_attachment(file_path):
    errors = []

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            reader = csv.reader(file, delimiter="\t")

            # Read the header
            header = next(reader, None)
            if not header:
                errors.append("❌ Error: File is empty or has no header.")
            else:
                # Check for missing columns
                missing_cols = [col for col in REQUIRED_COLUMNS if col not in header]
                if missing_cols:
                    errors.append(f"❌ Missing required columns: {', '.join(missing_cols)}")
                
                # Get column indices (only if header is valid)
                col_indices = {col: header.index(col) for col in REQUIRED_COLUMNS if col in header}

                # Validate each row
                for i, row in enumerate(reader, start=2):  # Start at line 2 (after header)
                    if len(row) < len(header):  
                        errors.append(f"❌ Incomplete row at line {i}.")
                        continue  # Move to next row

                    # Check for missing values in required fields
                    missing_values = [col for col in REQUIRED_COLUMNS if col in col_indices and not row[col_indices[col]].strip()]
                    if missing_values:
                        errors.append(f"❌ Missing values in required fields at line {i}: {', '.join(missing_values)}")

    except Exception as e:
        errors.append(f"❌ Error processing attachment: {str(e)}")

    # Write results to file
    with open("validation_result.txt", "w") as f:
        if errors:
            for error in errors:
                print(error)
                f.write(error + "\n")
        else:
            message = "✅ Attachment format is correct!"
            print(message)
            f.write(message)

if __name__ == "__main__":
    validate_attachment(sys.argv[1])
