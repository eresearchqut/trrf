Database Model Generation
=========================

About
-----

DB analysis helps in getting an overview of the databases, for documenting, better DB admin and troubleshooting.

Existing database reports
-------------------------
(subject to change with instances)

->folder *schemaspy/report* contains the DB report generated locally in DEV environment by SchemaSpy .
->folder *dbtohtml contains* a list of tables in DBs 

Note: reportingdb contains no schema in the local instance, thus no/empty reports generated

Tools used
----------

**dbtohtml:**

https://github.com/bmamlin/dbtohtml

**SchemaSpy** (for ER model and other DB analysis):

http://schemaspy.org/



Usage
------------

Note: portnumbers should be edited wherever needed

**dbtohtml:**


Clone the repo at https://github.com/bmamlin/dbtohtml.

Use JDBC driver for postgreSQL in DbToHtml.groovy file, via GRAB annotation.
Configure the DB connection attributes in *.properties* file.

Sample configFile.properties file:

    *db_url = "jdbc:postgresql://localhost:49584/"*

    *db_username = "webapp"*

    *db_password = "webapp"*

    *output_file = "./dbtohtml/TRRFmodel.html"*

    *title = "TRRF Data Model"*


After making neccessary changes to DbToHtml.groovy(edited file can be found in docs/database/schemaspy) and .properties file, run the following command:

    *groovy DbToHtml.groovy configFile.properties*



**SchemaSpy:**


Refer the instructions at https://schemaspy.readthedocs.io/en/latest/ or http://schemaspy.org/ 
Get latest JDBC JAR for your DB, and download SchemaSpy JAR file

Run the following command:
    
    *java -jar schemaspy-6.1.0.jar -t pgsql -s public -db webapp -u webapp -p webapp -host localhost -port 49002 -o /tmp -dp postgresqlJDBC.jar*

You can find usage details of the above command in the SchemaSpy Docs.

A set of webpages are generated in the *tmp* folder, index.html can be opened to access the report. ER diagrams generated as sample for this application are stored in *./schemaspy* folder. 