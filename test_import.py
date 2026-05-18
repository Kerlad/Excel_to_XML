from importers.xlsx_importer import load_xlsx

records, error_details, error_rows, error_messages = load_xlsx('test_workers_with_errors.xlsx')
print(f'Records: {len(records)}, Errors: {len(error_details)}, Error rows: {error_rows}')
for e in error_details:
    print(f'  Row {e["row"]}: {e["field"]} - {e["message"]}')