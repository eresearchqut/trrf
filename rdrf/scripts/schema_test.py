from report.schema.schema import create_dynamic_schema
import json


def get_results(schema, query):
    result = schema.execute(query)
    if result.errors:
        print(f"Error: {query}")
        print("--------------------------------------------------------------")
        print(result.errors)
    else:
        print(f"Success: {query}")
        print("--------------------------------------------------------------")
        print(json.dumps(result.data, indent=4))
    print("--------------------------------------------------------------")
    print()


def run():
    schema = create_dynamic_schema()
    # print(schema)

    # get_results(schema, "{ patients { givenNames } }")

    # get_results(schema, "{ patients { givenNames, test } }")

    get_results(schema, """
{
  patients {
    familyName,
    givenNames,
    id
    clinicalData {
      History {
        NewbornAndInfancyHistory {
          ANGNewbornInfancyReside {
            ResideNewborn,
            ResideInfancy
          },
          ANGNewbornHistory {
            ANGHOWFEDINFANCY
          }
        }
      }
      Sleep {
        Sleep {
          key,
          data {
            ANGBEHDEVSLEEPGENERAL {
              ANGBEHDEVGOODSLEEP2
            }
          }
        }
      }
    }
  }
}
    """)
