
When making changes to models that are specific to the **registry's definition**, it's essential to ensure that the import/export logic is updated accordingly.
This ensures that new fields or models are appropriately extracted and handled during data import/export processes.

## Rules to Update Import/Export Logic

1. **Models**
- Do Import/Export: Models that are explicitly defined within the registry. These models represent the core data structures of the system.
- Do Not Import/Export: Models contain sensitive data like clinical information, patient records, or user data.

2. **Fields**
- Do Import/Export:

  - Human-readable, unique primary key strings.
  - All other fields that contribute to the definition of the registry data. 
- Do Not Import/Export:

  - Generated or implicit primary keys.
  - Automatic fields related to auditing, such as creation timestamps or user information.

3. **Order**
- Import Order: Dependent models come first during import. This ensures that the necessary structure is established before importing dependent models.
- Record Order: Within each model, records should be sorted by their human-readable alphanumeric primary key.

4. **Validation**
- New models should call the `full_clean` method to ensure complete validation is run over the model instance. Any subsequent errors should be handled appropriately.

## Adding New Migration to migrations_considered_for_import_export.py

Once the import/export logic has been updated, it's important to document the changes by adding the name of the new migration to [migrations_considered_for_import_export.py](../rdrf/rdrf/services/io/defs/migrations_considered_for_import_export.py).
