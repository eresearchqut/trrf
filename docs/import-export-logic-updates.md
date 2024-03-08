# Import/Export Logic Updates

When making changes to models that are specific to the registry's definition, it's essential to ensure that the import/export logic is updated accordingly.
This ensures that new fields or models are appropriately extracted and handled during data import/export processes.

## Updating Import/Export Logic

After making relevant changes to the models, it's crucial to update the import/export logic to accommodate these changes. This includes:

1. **Identification of Changes**: Identify the specific changes made to the models and determine how they affect the import/export process.

2. **Modification of Logic**: Modify the import/export logic as necessary to incorporate the new fields or models and handle any changes in data structure or format.

3. **Testing**: Thoroughly test the updated import/export logic to ensure that it functions correctly and accurately handles the new data fields or models.

## Adding Migration to migrations_list.py

Once the import/export logic has been updated, it's important to document the changes by adding the name of the new migration to [migrations_list.py](./rdrf/rdrf/services/io/defs/migrations_list.py).
