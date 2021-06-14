/**
 * This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
 * If a copy of the MPL was not distributed with this file, You can obtain one at 
 * http://mozilla.org/MPL/2.0/.
 */

/**
 * DbToHtml.groovy
 *
 * This script connects to a running database, inspects the tables, and generates an
 * HTML file that can be used to conveniently browse the structure of the tables.
 *
 * Usage: groovy DbToHtml.groovy /path/to/configFile
 *
 * The configFile is a java properties file containing the database connection details,
 * path to output file, and title for the HTML page.  For example:
 *
 * Sample configFile
 * -----------------
 * db_url = "jdbc:mysql://localhost/dbname"
 * db_username = "username"
 * db_password = "password"
 * output_file = "/path/to/data-model.html"
 * title = "My Data Model"
 * favicon = "https://example.com/favicon.ico
 *
 * If the db_password is not provided in config, you will be prompted for the password.
 */
@GrabConfig( systemClassLoader=true )
@Grab('org.postgresql:postgresql:42.2.18')

import groovy.sql.*

def config = new ConfigSlurper().parse(new File(args[0]).toURL())

def DB_URL = config.db_url
def DB_USERNAME = config.db_username ?: 'root'
def DB_PASSWORD = config.db_password ?: System.console().readPassword("$DB_USERNAME's password:").toString()
def OUTPUT_FILE = config.output_file ?: 'db.html'
def TITLE = config.title ?: 'Data Model Browser'
def FAVICON = config.favicon ?: 'data:image/x-icon;base64,AAABAAEAEBAAAAAAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAAAAAAAAAAAAAAAAAAAAAAAD///8B////Af///wH///8BFajwERWo8FsVqPCfFajwuxWo8LkVqPCXFajwTRWo8Av///8B////Af///wH///8B////Af///wH///8B////ARWo74EVqPD/Fajw/xWo8P8VqPD/Fajw/xWo8P0VqO9j////Af///wH///8B////Af///wH///8B////Af///wERqvWVFajw/xWo8P8VqPD3Fajw+RWo8P8VqO//Ean5d////wH///8B////Af///wH///8B////Af///wH///8BEKz2kxSo8cUVqPBVFajwKRWo8CsVqPBjE6jz1RSo83f///8B////Af///wH///8BpldbC6ZXW2mnVlqBsVFQh0SOwVcMrfkL////Af///wH///8B////ARCo+xdNnnxjjpIAfYSTAH2EkwBf////AaZXW1WmV1v/pldb/6lVWMehW2EF////Af///wH///8B////Af///wH///8BWZthF4uSAOOEkwD/hJMA94STADGmV1ubpldb/6ZXW/+mV1tL////Af///wH///8B////Af///wH///8B////Af///wGGkwBxhJMA/4STAP+EkwB1pldbuaZXW/+mV1vvpldbI////wH///8B////Af///wH///8B////Af///wH///8BhJMAO4STAP+EkwD/hJMAmaZXW7umV1v/pldb7aZXWyH///8B////Af///wH///8B////Af///wH///8B////AYSTADeEkwD/hJMA/4STAJumV1ujpldb/6ZXW/+mV1s/////Af///wH///8B////Af///wH///8B////Af///wGEkwBjhJMA/4STAP+EkwB9pldbYaZXW/+mV1v/qFdZtaZXWwP///8B////Af///wH///8B////Af///wGAkQ8LhZQA0YSTAP+EkwD/hJMAPaZXWxOmV1uPp1daobRWTJ9SYLpF////Af///wH///8B////Af///wEaYf8DVHx8WZCYAKuEkwCphJMAh4STAAf///8B////Af///wH///8BIWXzlyBl9KMiZfIxImXyGSJl8hkiZfI9HGP8sz5yq3f///8B////Af///wH///8B////Af///wH///8B////AR1m+J8iZfL/ImXy+yJl8tsiZfLdImXy/yJl8f8dYvx1////Af///wH///8B////Af///wH///8B////Af///wEjZfGRImXy/yJl8v8iZfL/ImXy/yJl8v8iZfL/ImXxb////wH///8B////Af///wH///8B////Af///wH///8BImXyHSJl8m8iZfKtImXyyyJl8skiZfKpImXyaSJl8hf///8B////Af///wH///8BAAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//w%3D%3D'

class Table {
  String name
  def columns = []
}

class Column {
  Boolean key
  Boolean required
  String name
  String type
  Integer size
  String fkTable = null
  String fkColumn = null
  Boolean isFk() { fkTable != null }
}

// Pretty names for java.sql.Types
knownDataTypes = [
    (java.sql.Types.ARRAY)    : "array",
    (java.sql.Types.BIGINT)   : "bigint",
    (java.sql.Types.BINARY)   : "binary",
    (java.sql.Types.BIT)      : "bit",
    (java.sql.Types.BLOB)     : "blob",
    (java.sql.Types.BOOLEAN)  : "boolean",
    (java.sql.Types.CHAR)     : "char",
    (java.sql.Types.CLOB)     : "clob",
    (java.sql.Types.DATALINK) : "datalink",
    (java.sql.Types.DATE)     : "date",
    (java.sql.Types.DECIMAL)  : "decimal",
    (java.sql.Types.DISTINCT) : "distinct",
    (java.sql.Types.DOUBLE)   : "double",
    (java.sql.Types.FLOAT)    : "float",
    (java.sql.Types.INTEGER)  : "integer",
    (java.sql.Types.JAVA_OBJECT) : "java object",
    (java.sql.Types.LONGNVARCHAR) : "long n varchar",
    (java.sql.Types.LONGVARBINARY) : "long varbinary",
    (java.sql.Types.LONGVARCHAR) : "long varchar",
    (java.sql.Types.NCHAR)    : "n char",
    (java.sql.Types.NCLOB)    : "n clob",
    (java.sql.Types.NULL)     : "null",
    (java.sql.Types.NUMERIC)  : "numeric",
    (java.sql.Types.NVARCHAR) : "n varchar",
    (java.sql.Types.OTHER)    : "other",
    (java.sql.Types.REAL)     : "real",
    (java.sql.Types.REF)      : "ref",
    (java.sql.Types.ROWID)    : "row id",
    (java.sql.Types.SMALLINT) : "smallint",
    (java.sql.Types.SQLXML)   : "xml",
    (java.sql.Types.STRUCT)   : "struct",
    (java.sql.Types.TIME)     : "time",
    (java.sql.Types.TIMESTAMP): "timestamp",
    (java.sql.Types.TINYINT)  : "tinyint",
    (java.sql.Types.VARBINARY): "varbinary",
    (java.sql.Types.VARCHAR)  : "varchar"
  ]

String dataType(type) {
  (knownDataTypes[type] ?: "*** unknown ***")
}

// Scan database to build model of tables and columns
def sql = Sql.newInstance(DB_URL, DB_USERNAME, DB_PASSWORD, 'org.postgresql.Driver')
tables = []
meta = sql.connection.metaData
metaTables = meta.getTables(null, null, "%", "TABLE")
new GroovyResultSetExtension(metaTables).eachRow {
  table = new Table()
  table.name = it.table_name
  keys = []
  metaKeys = meta.getPrimaryKeys(null, null, it.table_name)
  new GroovyResultSetExtension(metaKeys).eachRow {
    keys << it.column_name
  }
  fks = [:]
  metaFks = meta.getImportedKeys(null, null, it.table_name)
  new GroovyResultSetExtension(metaFks).eachRow {
    fks[it.fkcolumn_name] = [
      'table' : it.pktable_name,
      'column' : it.pkcolumn_name
    ]
  }
  metaColumns = meta.getColumns(null, null, it.table_name, "%")
  new GroovyResultSetExtension(metaColumns).eachRow {
    column = new Column()
    column.key = keys.contains(it.column_name)
    column.name = it.column_name
    column.type = dataType(it.data_type)
    column.size = it.column_size
    column.required = (it.is_nullable == 'NO')
    if (fks[column.name]) {
      column.fkTable = fks[column.name].table
      column.fkColumn = fks[column.name].column
    }
    table.columns << column
  }
  tables << table
}

// Write our output to file system
def out = new File(OUTPUT_FILE)
out.write('') // truncate file

out << "<!DOCTYPE html>\n<html>\n"
out << """<head>
<title>$TITLE</title>
<link href="$FAVICON" rel="icon" type="image/x-icon" />
<style type="text/css">
<!--
body {
    font-family: arial;
}
.title, .form {
  display: table;
  padding: 10px;
  margin-left: auto;
  margin-right: auto;
}
.title {
  font-weight: bold;
}
#q {
  width: 300px;
  font-size: 16px;
}
.share {
  visibility: hidden;
  display: inline-block;
  margin-left: 10px;
}
.share a img {
  vertical-align: -40%;
}
.match-counts {
  visibility: hidden;
  display: block;
  margin-left: 10px;
  font-size: 75%;
  font-style: italic;
  color: #AAA;
}
.help-control {
  position: absolute;
  top: 10px;
  right: 10px;
}
.help {
  display: none;
  width: 80%;
  margin-left: auto;
  margin-right: auto;
  border: thick solid black;
  border-radius: 10px;
  padding: 10px;
  background-color: lightgray;
}
.help table {
  margin: 10px;
  border-collapse: collapse;
}
.help table, .help th, .help td {
  border: 1px solid black;
  padding: 5px;
}
.help td:first-child {
  font-family: monospace;
}
.tip {
  text-align: center;
  font-style: italic;
  font-size: 0.8em;
}
.tip:before {
  content: 'TIP: ';
}
.table {
  display: table;
    margin-top: 1em;
    border: thin solid #CCC;
    border-radius: 10px;
    margin-left: auto;
    margin-right: auto;
    box-shadow: 2px 2px #AAA;
}
.table-name {
    font-weight: bold;
    text-align: center;
    background-color: #DDD;
    padding: 2px;
    border-radius: 10px 10px 0px 0px;
}
.column {
  padding: 2px 4px 2px 4px;
}
.match {
  background-color: yellow;
}
.column-name, .column-type {
  display: inline-block;
}
.column-name {
  min-width: 250px;
  overflow-x: hidden;
  padding-left: 20px;
  white-space: nowrap;
}
.column-type {
  min-width: 200px;
  overflow-x: hidden;
  white-space: nowrap;
  padding-right: 20px;
}
.column.primary-key > .column-name {
  background-image: url("data:image/svg+xml;utf8,<svg version='1.2' baseProfile='tiny' width='215.9mm' height='279.4mm' viewBox='0 0 21590 27940' preserveAspectRatio='xMidYMid' fill-rule='evenodd' stroke-width='28.222' stroke-linejoin='round' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink' xml:space='preserve'><g visibility='visible' id='key'><g><path fill='rgb(255,255,0)' stroke='rgb(0,0,0)' id='Drawing_1_0' transform='scale(0.1)' stroke-width='150' stroke-linejoin='round' d='M 2194,3159 C 2193,3159 2193,3159 2193,3159 L 2132,3157 C 2131,3157 2130,3157 2129,3157 L 2071,3152 C 2070,3152 2069,3151 2067,3151 L 2011,3142 C 2010,3142 2009,3142 2007,3142 L 1952,3129 C 1951,3129 1950,3128 1949,3128 L 1894,3111 C 1893,3111 1892,3111 1891,3110 L 1837,3090 C 1836,3089 1835,3089 1834,3088 L 1781,3064 C 1780,3063 1779,3063 1778,3062 L 1725,3034 C 1725,3034 1724,3033 1724,3033 1724,3033 1723,3033 1723,3032 L 1671,3001 C 1670,3000 1670,3000 1669,2999 L 1621,2965 C 1620,2964 1619,2964 1618,2963 L 1574,2927 C 1573,2926 1572,2925 1571,2925 L 1530,2886 C 1529,2885 1528,2884 1527,2883 L 1488,2842 C 1488,2841 1487,2840 1486,2839 L 1450,2795 C 1449,2794 1449,2793 1448,2792 L 1414,2744 C 1413,2743 1413,2743 1412,2742 L 1381,2690 C 1380,2690 1380,2689 1380,2689 1380,2689 1379,2688 1379,2688 L 1351,2635 C 1350,2634 1350,2633 1349,2632 L 1325,2579 C 1324,2578 1324,2577 1323,2576 L 1303,2522 C 1302,2521 1302,2520 1302,2519 L 1285,2464 C 1285,2463 1284,2462 1284,2461 L 1271,2406 C 1271,2404 1271,2403 1271,2402 L 1262,2346 C 1262,2344 1261,2343 1261,2342 L 1256,2284 C 1256,2283 1256,2282 1256,2281 L 1254,2220 C 1254,2220 1254,2220 1254,2219 1254,2218 1254,2218 1254,2218 L 1256,2157 C 1256,2156 1256,2155 1256,2154 L 1261,2096 C 1261,2095 1262,2094 1262,2092 L 1271,2036 C 1271,2035 1271,2034 1271,2032 L 1284,1977 C 1284,1976 1285,1975 1285,1974 L 1302,1919 C 1302,1918 1302,1917 1303,1916 L 1323,1862 C 1324,1861 1324,1860 1325,1859 L 1349,1806 C 1350,1805 1350,1804 1351,1803 L 1379,1750 C 1379,1750 1380,1749 1380,1749 1380,1749 1380,1748 1381,1748 L 1412,1696 C 1413,1695 1413,1695 1414,1694 L 1448,1646 C 1449,1645 1449,1644 1450,1643 L 1486,1599 C 1487,1598 1488,1597 1488,1596 L 1527,1555 C 1528,1554 1529,1553 1530,1552 L 1571,1513 C 1572,1513 1573,1512 1574,1511 L 1618,1475 C 1619,1474 1620,1474 1621,1473 L 1669,1439 C 1670,1438 1670,1438 1671,1437 L 1723,1406 C 1723,1405 1724,1405 1724,1405 1724,1405 1725,1404 1725,1404 L 1778,1376 C 1779,1375 1780,1375 1781,1374 L 1834,1350 C 1835,1349 1836,1349 1837,1348 L 1891,1328 C 1892,1327 1893,1327 1894,1327 L 1949,1310 C 1950,1310 1951,1309 1952,1309 L 2007,1296 C 2009,1296 2010,1296 2011,1296 L 2067,1287 C 2069,1287 2070,1286 2071,1286 L 2129,1281 C 2130,1281 2131,1281 2132,1281 L 2193,1279 C 2193,1279 2193,1279 2194,1279 2195,1279 2195,1279 2195,1279 L 2256,1281 C 2257,1281 2258,1281 2259,1281 L 2317,1286 C 2318,1286 2319,1287 2321,1287 L 2377,1296 C 2378,1296 2379,1296 2381,1296 L 2436,1309 C 2437,1309 2438,1310 2439,1310 L 2494,1327 C 2495,1327 2496,1327 2497,1328 L 2551,1348 C 2552,1349 2553,1349 2554,1350 L 2607,1374 C 2608,1375 2609,1375 2610,1376 L 2663,1404 C 2663,1404 2664,1405 2664,1405 2664,1405 2665,1405 2665,1406 L 2717,1437 C 2718,1438 2718,1438 2719,1439 L 2767,1473 C 2768,1474 2769,1474 2770,1475 L 2814,1511 C 2815,1512 2816,1513 2817,1513 L 2858,1552 C 2859,1553 2860,1554 2861,1555 L 2900,1596 C 2900,1597 2901,1598 2902,1599 L 2938,1643 C 2939,1644 2939,1645 2940,1646 L 2974,1694 C 2975,1695 2975,1695 2976,1696 L 3007,1748 C 3008,1748 3008,1749 3008,1749 3008,1749 3009,1750 3009,1750 L 3037,1803 C 3038,1804 3038,1805 3039,1806 L 3063,1859 C 3064,1860 3064,1861 3065,1862 L 3084,1914 4349,1914 5115,1914 5122,1914 C 5131,1914 5139,1916 5148,1921 5156,1926 5161,1931 5166,1939 5171,1948 5173,1956 5173,1965 L 5173,3108 C 5173,3117 5171,3125 5166,3134 5161,3142 5156,3147 5148,3152 5139,3157 5131,3159 5122,3159 L 4349,3159 C 4340,3159 4332,3157 4324,3152 4315,3147 4310,3142 4305,3134 4300,3125 4298,3117 4298,3108 L 4298,2524 3084,2524 3065,2576 C 3064,2577 3064,2578 3063,2579 L 3039,2632 C 3038,2633 3038,2634 3037,2635 L 3009,2688 C 3009,2688 3008,2689 3008,2689 3008,2689 3008,2690 3007,2690 L 2976,2742 C 2975,2743 2975,2743 2974,2744 L 2940,2792 C 2939,2793 2939,2794 2938,2795 L 2902,2839 C 2901,2840 2900,2841 2900,2842 L 2861,2883 C 2860,2884 2859,2885 2858,2886 L 2817,2925 C 2816,2925 2815,2926 2814,2927 L 2770,2963 C 2769,2964 2768,2964 2767,2965 L 2719,2999 C 2718,3000 2718,3000 2717,3001 L 2665,3032 C 2665,3033 2664,3033 2664,3033 2664,3033 2663,3034 2663,3034 L 2610,3062 C 2609,3063 2608,3063 2607,3064 L 2554,3088 C 2553,3089 2552,3089 2551,3090 L 2497,3110 C 2496,3111 2495,3111 2494,3111 L 2439,3128 C 2438,3128 2437,3129 2436,3129 L 2381,3142 C 2379,3142 2378,3142 2377,3142 L 2321,3151 C 2319,3151 2318,3152 2317,3152 L 2259,3157 C 2258,3157 2257,3157 2256,3157 L 2195,3159 C 2195,3159 2195,3159 2194,3159 Z'/></g></g></svg>");
  background-repeat: no-repeat;
  background-position: -4px 0px;
}
.column.required > .column-name:after {
  content: "*";
  font-weight: bold;
  color: red;
}
-->
</style>
<script>
<!--
"""

// Embed JQuery so our HTML file doesn't need any additional files or internet connection
out << new URL("https://ajax.googleapis.com/ajax/libs/jquery/2.1.1/jquery.min.js").text

out << """
-->
</script>
</head>
<body>"""

// Generate search form and help panel
out << """
<h1>$TITLE</h1>
<div class="form">
  <input id="q" type="search" placeholder="search (or type 'help')" />
  <div class="share">
    <a title="Copy link to share your search"><img src="data:image/svg+xml;utf8,<svg version='1.1' id='Layer_1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink' x='0px' y='0px' width='25' height='25' xml:space='preserve'><g transform='scale(0.3) translate(-5,-5)'><path d='M68.1,28.3c-2.4-2.5-5.6-3.9-9.1-4c-3.7-0.1-7.1,1.5-9.7,4.1l-6,6c1.4-0.3,2.9-0.3,4.3-0.1c0.7,0.1,1.3,0.2,2,0.4 c0,0,0,0,0,0c0.8,0.3,1.7,0.1,2.3-0.5l1.6-1.6c1.2-1.2,2.8-2.1,4.6-2.2c2.3-0.2,4.4,0.7,5.9,2.5c2.4,2.8,2,7-0.6,9.6l-8,8 c-0.8,0.8-1.9,1.4-3,1.8c-0.6,0.2-1.1,0.2-1.7,0.3l-0.2,0c-0.5,0-0.9,0-1.4-0.1c-1.3-0.3-2.5-0.9-3.5-1.9c-0.8-0.8-1.4-1.9-1.8-3 c-0.3,0.2-0.6,0.4-0.9,0.7l-1.6,1.6c-1.4,1.4-1.4,3.6-0.1,4.9c0,0,0,0,0,0c1.1,1.1,2.3,1.9,3.6,2.5c0.5,0.3,1.1,0.5,1.8,0.7 c0.7,0.2,1.3,0.4,2,0.4c0.6,0.1,1.2,0.1,1.8,0.1c2.1,0,4.2-0.5,6.1-1.5c1-0.5,1.9-1.2,2.6-1.9c0.2-0.1,0.3-0.3,0.5-0.4l7.9-7.9 C72.6,41.7,73,33.5,68.1,28.3z'/><path d='M48.7,61.8c-0.7-0.1-1.3-0.2-2-0.4c0,0,0,0,0,0c-1-0.3-2.1-0.1-2.9,0.7l-1.5,1.5c-1.2,1.2-2.8,2-4.5,2.2 c-2.1,0.2-4.1-0.5-5.5-2c-1.5-1.5-2.2-3.5-2-5.5c0.1-1.7,1-3.3,2.2-4.5l8-8c0.8-0.8,1.9-1.4,3-1.8c0.5-0.2,1.1-0.2,1.7-0.3l0.3,0 c0.5,0,0.9,0,1.4,0.1c1.3,0.3,2.5,0.9,3.5,1.9c0.8,0.8,1.4,1.9,1.7,3c0.3-0.2,0.6-0.4,0.8-0.7l1.6-1.6c1.3-1.3,1.4-3.6,0.1-4.9 c0,0,0,0,0,0c-1.1-1.1-2.3-1.9-3.6-2.5c-0.5-0.3-1.1-0.5-1.8-0.7c-0.7-0.2-1.3-0.4-2-0.4c-2.7-0.4-5.5,0.1-7.9,1.4 c-1,0.5-1.9,1.2-2.6,1.8c-0.2,0.1-0.3,0.2-0.5,0.4l-7.9,7.9c-5,5-5.4,13.2-0.5,18.3c2.4,2.5,5.6,3.9,9.1,4c3.7,0.1,7.1-1.5,9.7-4.1 l5.8-5.8c-0.7,0.1-1.3,0.2-2,0.2C49.9,61.9,49.3,61.9,48.7,61.8z'/></g></svg>" /></a>
  </div>
  <div class="match-counts">&nbsp;</div>
</div>
<div class="help">
Search by table name, column name, or datatype.  By default, the search will be for
table name.  Add a period (or start with a period) to search by column name.  Add a 
colon (or start with a colon) to search by datatype. Basic 
<a href="http://www.regular-expressions.info/" target="_blank">regular expressions</a>
are supported.  Want to run this locally?  Just save this file locally and open it with your
browser; no internet required.  Adding "#query" to the end of the URL will automatically 
perform that search when the page is loaded, so you can share links to specific searches.
<table>
  <tr><th>Example</th><th>Search for...</th></tr>
  <tr><td>foobar</td><td>table names containing "foobar"</td></tr>
  <tr><td>.foobar</td><td>column names containing "foobar"</td></tr>
  <tr><td>:int</td><td>columns with datatype containing "int"</td></tr>
  <tr><td>:concept.concept_id</td><td>columns that are a foreign key to concept.concept_id</td></tr>
  <tr><td>foobar.baz</td><td>column names containing "baz" within tables with names containing "foobar"</td></tr>
  <tr><td>^foo\$</td><td>table with exact name "foo"</td></tr>
  <tr><td>.^bar\$</td><td>columns with exact name "bar"</td></tr>
  <tr><td>:^int\$</td><td>columns with exact datatype "int"</td></tr>
  <tr><td>^foo.*bar\$</td><td>tables with names starting with "foo" and ending with "bar"</td></tr>
  <tr><td>foo.*bar.^baz:varchar</td><td>column names starting with "baz" and datatype containing "varchar" within tables containing "foo" followed by "bar"</td></tr>
</table>
<div class="tip">hotkeys: "/" jumps to search box, "?" toggle help. Click on help to dismiss.</div>
</div>
"""

// Render our data model as divs
tables.each {
  out << """<div class="table" id="$it.name">\n"""
  out << """<div class="table-name">$it.name</div>\n"""
  it.columns.each {
    def columnClass = "column"
    if (it.key) columnClass += " primary-key"
    if (it.required) columnClass += " required"
    def type
    def columnTypeClass = "column-type"
    if (it.isFk()) {
      type = "${it.fkTable}.${it.fkColumn}"
      columnTypeClass += " fk"
    } else {
      type = it.type
      if (it.size != null) type += " ($it.size)"
    }
    out << """<div class="$columnClass"><div class="column-name">$it.name</div>"""
    out << """<div class="$columnTypeClass">$type</div></div>\n"""
  }
  out << "</div>\n"
}

// Generate scripts to define the tool's behavior
out << """
<script>
<!--
var j = jQuery.noConflict();
j(document).ready(function() {
  // Jump to foreign key
  var scrollToFk = function() {
    var fk = j(this).text();
    var fkTable = fk.split('.')[0];
    j('#q').val('');
    j('.table').show();
    j('html,body').animate({scrollTop: j('#'+fkTable).offset().top},'slow');
  }
  // Add foreign key links
  j('.column-type.fk').each(function() {
    var fk = j(this).text();
    var link = j('<a href="#">' + fk + '</a>');
    link.click(scrollToFk);
    j(this).html(link);
  });
  // Select all when focusing in search box
  j('#q').focus(function() {
    j(this).select();
    // Work around Chrome's little problem
    j(this).mouseup(function() {
      // Prevent further mouseup intervention
      j(this).unbind("mouseup");
      return false;
    });
  });
  function clearQuery() {
    j('#q').val('');
    j('.share').css('visibility', 'hidden');
    j('.table').show();
    displayMatchCounts(j('.table').size(), null);
  }
  function hideMatchCounts() {
    j('.match-counts').css('visibility', 'hidden');
  }
  function displayMatchCounts(tables, columns) {
    var matchCounts = '';
    if (tables) {
      matchCounts += tables + ' table' + (tables > 1 ? 's' : '');
    }
    if (columns) {
      if (matchCounts != '') matchCounts += ', ';
      matchCounts += columns + ' column' + (columns > 1 ? 's' : '');
    }
    if (matchCounts == '') matchCounts = '&nbsp;'; // keeps height stable
    j('.match-counts').html(matchCounts).css('visibility', 'visible');
  }
  // Handle searches
  function search(q) {
    j('.column').removeClass('match');
    if (q != null && q.length > 0) {
      // Show help if user type 'help'
      if (/^(help|\\?)\$/i.test(q)) {
        clearQuery();
        j('.help').fadeToggle(500);
        return true;
      }
      j('.share > a').attr('href', window.location.href.split(/#/)[0] + '#' + encodeURIComponent(q));
      j('.share').css('visibility', 'visible');
      // Queries are in the form [table].[column]:[type]
      var searchPattern = /^(.*?)(\\.(?!\\*)(.*?))?(:(.*))?\$/i;
      var query = searchPattern.exec(q);
      var tableQuery;
      var columnQuery;
      var typeQuery;
      if (query) {
        tableQuery = query[1] ? new RegExp(query[1], 'i') : null;
        columnQuery = query[3] ? new RegExp(query[3], 'i') : null;
        typeQuery = query[5] ? new RegExp(query[5].replace(/([\\(\\)])/g, '\\\\\$1'), 'i') : null;
      } else {
        tableQuery = new RegExp('.*'), columnQuery = null, typeQuery = null;
      }
      var numTables = 0, numColumns = 0;
      j('.table').each(function() {
        var matchingTable = !tableQuery || tableQuery.test(j(this).find('.table-name').text());
        var matchingColumn = false;
        var potentialNumColumns = 0;
        if (columnQuery || typeQuery) {
          // Scan columns for those that match by name and type
          j(this).find('.column').each(function() {
            if ((!columnQuery || columnQuery.test(j(this).find('.column-name').text()))
              && (!typeQuery || typeQuery.test(j(this).find('.column-type').text()))) {
              j(this).addClass('match');
              matchingColumn = true;
              potentialNumColumns++;
            }
          });
        }
        if ((!tableQuery || matchingTable) && (!(columnQuery || typeQuery) || matchingColumn)) {
          j(this).show();
          numTables++;
          if (matchingColumn) numColumns += potentialNumColumns;
        } else {
          j(this).hide();
        }
      });
      displayMatchCounts(numTables, numColumns);
    } else {
      j('.share').css('visibility', 'hidden');
      displayMatchCounts(j('.table').size(), null);
      j('.table').show();
    }
  }
  // Fires on keydown but after input value updated
  j('#q').on('input', function() {
    search(j(this).val());
  });
  // Focus on search box
  j('#q').focus().keypress(function(event) {
    event.stopPropagation();
  });
  // Let forward slash jump to search box
  j('body').keypress(function(event) {
    if (event.which == 47) {
      event.preventDefault();
      j('#q').focus();
    } else if (event.which == 63) {
      event.preventDefault();
      j('.help').fadeToggle(500);
    }
  });
  // Hide help when clicked
  j('.help').click(function() {
    if (/^help\$/i.test(j('#q').val())) {
      clearQuery();
    }
    j(this).fadeToggle(500);
    j('#q').focus();
  });
  // On first load, if URL contains query, load it
  function init() {
    var match = /^.*?#(.+)\$/.exec(window.location.href);
    if (match) {
      var queryFromUrl = decodeURIComponent(match[1]);
      j('#q').val(queryFromUrl);
      search(queryFromUrl);
    } else {
      displayMatchCounts(j('.table').size(), null);
    }
  }
  init();
});
-->
</script>
</body>
</html>"""
