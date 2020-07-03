#!/usr/bin/env python

from argparse import ArgumentParser
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import DictCursor

TABLE_QUERY_COLUMNS = [
    "table_schema", "table_name", "column_name",
    "ordinal_position", "column_default", "is_nullable",
    "data_type", "character_maximum_length", "character_octet_length",
    "numeric_precision", "numeric_precision_radix", "numeric_scale",
    "datetime_precision", "interval_type", "interval_precision",
    "domain_catalog", "domain_schema", "domain_name",
    "udt_schema", "udt_name", "maximum_cardinality",
    "dtd_identifier", "is_updatable"
]

SEQUENCE_QUERY_COLUMNS = [
    "sequence_schema", "sequence_name", "numeric_scale",
    "start_value", "minimum_value", "increment",
    "cycle_option"
]

parser = ArgumentParser(
    description="Diff the table and sequence schemas of two postgres databases",
    add_help=True
)
parser.add_argument("old_url", type=str, help="postgresql://username:password@host:port/database")
parser.add_argument("new_url", type=str, help="postgresql://username:password@host:port/database")
parser.add_argument("--full-schemas", type=str, nargs="+", choices=("tables", "sequences"))


def create_cursor(server):
    result = urlparse(server)
    username = result.username
    password = result.password
    hostname = result.hostname
    port = result.port
    database = result.path[1:]
    return psycopg2.connect(
        database=database,
        user=username,
        password=password,
        host=hostname,
        port=port
    ).cursor(cursor_factory=DictCursor)


def get_table_names(cursor):
    cursor.execute("""SELECT table_name FROM information_schema.tables
                      WHERE table_schema = 'public'""")
    return [t[0] for t in cursor.fetchall()]


def get_sequence_names(cursor):
    cursor.execute("""SELECT sequence_name FROM information_schema.sequences
                      WHERE sequence_schema = 'public'""")
    return [t[0] for t in cursor.fetchall()]


def get_table_schema(cursor, table):
    cursor.execute(f"""SELECT {",".join(TABLE_QUERY_COLUMNS)}
                        FROM information_schema.columns
                        WHERE table_name = '{table}'
    """)
    return cursor.fetchall()


def get_sequence_schema(cursor, sequence):
    cursor.execute(f"""SELECT {",".join(SEQUENCE_QUERY_COLUMNS)}
                        FROM information_schema.sequences
                        WHERE sequence_name = '{sequence}'
    """)
    return cursor.fetchall()


def diff_dict_rows(old_rows, new_rows, name):
    if len(old_rows) != len(new_rows):
        print(f"ERROR: {name} Schemas don't have the same number of rows")
        print(f"old - {len(old_rows)}")
        print(f"new - {len(new_rows)}")
        print()
        return

    for old_dict, new_dict in zip(old_rows, new_rows):
        old_keys = set(old_dict.keys())
        new_keys = set(new_dict.keys())

        if old_keys != new_keys:
            old_diff = old_keys.difference(new_keys)
            if len(old_diff) > 0:
                print(f"WARNING: Columns missing from new {name} schema:")
                print(old_diff)
                print()

            new_diff = new_keys.difference(old_keys)
            if len(new_diff) > 0:
                print(f"WARNING: Columns missing from old {name} schema:")
                print(new_diff)
                print()

        shared_columns = old_keys.intersection(new_keys)

        for column in shared_columns:
            if old_dict[column] != new_dict[column]:
                print(f"WARNING: Column {column} doesn't match for {name} schema:")
                print(f"old - {old_dict[column]}")
                print(f"new - {new_dict[column]}")
                print()


def diff_names(old_cur, new_cur, schema_name, name_func):
    old_names = set(name_func(old_cur))
    new_names = set(name_func(new_cur))

    if len(old_names.symmetric_difference(new_names)) > 0:
        print(f"WARNING: The list of database {schema_name}s is different:")
        print(f"old extras - {list(old_names.difference(new_names))}")
        print(f"new extras - {list(new_names.difference(old_names))}")
        print()


def diff_table_names(old_cur, new_cur):
    return diff_names(old_cur, new_cur, 'table', get_table_names)


def diff_sequence_names(old_cur, new_cur):
    return diff_names(old_cur, new_cur, 'sequence', get_sequence_names)


def diff_schemas(old_cur, new_cur, schema_name, name_func, schema_func):
    old_names = set(name_func(old_cur))
    new_names = set(name_func(new_cur))

    names = old_names.intersection(new_names)

    for name in names:
        old_schema = schema_func(old_cur, name)
        new_schema = schema_func(new_cur, name)

        diff_dict_rows(old_schema, new_schema, name)


def diff_table_schemas(old_cur, new_cur):
    return diff_schemas(old_cur, new_cur, 'table', get_table_names, get_table_schema)


def diff_sequence_schemas(old_cur, new_cur):
    return diff_schemas(old_cur, new_cur, 'sequence', get_sequence_names, get_sequence_schema)


def main():
    args = parser.parse_args()

    if args.full_schemas:
        if "tables" in args.full_schemas:
            global TABLE_QUERY_COLUMNS
            TABLE_QUERY_COLUMNS = "*"
        if "sequences" in args.full_schemas:
            global SEQUENCE_QUERY_COLUMNS
            SEQUENCE_QUERY_COLUMNS = "*"

    old_cur = create_cursor(args.old_url)
    new_cur = create_cursor(args.new_url)

    diff_table_names(old_cur, new_cur)
    diff_table_schemas(old_cur, new_cur)

    diff_sequence_names(old_cur, new_cur)
    diff_sequence_schemas(old_cur, new_cur)


if __name__ == "__main__":
    main()
