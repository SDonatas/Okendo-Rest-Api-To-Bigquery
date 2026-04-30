import pandas_gbq
import logging
from google.oauth2 import service_account
import os
import yaml

path = os.path.dirname(os.path.abspath(__file__))
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = path + '/auth/service_account.json'
credentials = service_account.Credentials.from_service_account_file(
  path + '/auth/service_account.json'
)
logger = logging.getLogger(__name__)

with open(path + "/upload_conf.yaml", "r") as file:
    upload_conf = yaml.safe_load(file)


class bigquery:
    
    def __init__(self):
        pass
        #self.client = bigquery.Client()
        self.delete_ids_batch_staging = ""

    def get_schema(self, tableName) -> dict:

        sql = """
                SELECT * FROM {} LIMIT 1
                """.format(tableName)

        resp = pandas_gbq.read_gbq(sql, project_id=google_project_id, credentials=credentials)

        return resp

    def delete_ids_batch_commit_staging(self):

        assert len(self.delete_ids_batch_staging) > 0, "Staging batch delete is empty"

        self.delete_ids_batch_staging = "BEGIN " + self.delete_ids_batch_staging + " END"

        print(self.delete_ids_batch_staging)
        resp = pandas_gbq.read_gbq(self.delete_ids_batch_staging, project_id=google_project_id, credentials=credentials, max_results = 1)
        print('Deleted records from delete_ids_batch_staging')
        self.delete_ids_batch_staging = ""


    def delete_ids_batch(self, tableName: str, keyName: str, ids: list, table_name_query_window: str, second_keyName: str, second_ids: list, staging = False):
        
        if second_keyName != None:
            assert len(ids) == len(second_ids), "Two deletion id lists ({} and {}) do not match".format(keyName, second_keyName)
        
        increment_size = 1000
        x = 0
        second_keyName_query = ""

        ids = ["'" + str(z) + "'" for z in ids]
        ids_split = []
        
        second_ids = ["timestamp('" + str(z) + "')" for z in second_ids]
        second_ids_split = []

        run_rounds = math.ceil(len(ids) / increment_size)

        for x in range(0, run_rounds):
            ids_split.append(ids[x * increment_size:(x * increment_size) + increment_size])
            second_ids_split.append(second_ids[x * increment_size:(x * increment_size) + increment_size])

        #Perform Test
        assert len(ids) == sum([len(x) for x in ids_split]), "Primary ids batch split did not match"
        assert len(second_ids) == sum([len(x) for x in second_ids_split]), "Secondary ids batch split did not match"
        
        delete_sql_string = ""

        for count, delete_range in enumerate(ids_split):
            
            if second_keyName != None:
                second_keyName_query = " AND {} IN ({})".format(second_keyName, ", ".join(second_ids_split[count]))
            else:
                second_keyName_query = ""

            sql = """
                    DELETE `{}`
                    WHERE {} IN ({})
                    """.format(tableName, keyName, ", ".join(delete_range)) + second_keyName_query + table_name_query_window + ";"
            
            delete_sql_string = sql

            if staging == False:
                delete_sql_string = "BEGIN " + delete_sql_string + " END"
                print(delete_sql_string)
                resp = pandas_gbq.read_gbq(delete_sql_string, project_id=google_project_id, credentials=credentials, max_results = 1)
                print('Deleted records from {} using unique key {}'.format(tableName, keyName))
            else:
                self.delete_ids_batch_staging += delete_sql_string
        

    def delete_ids(self, tableName: str, keyName: str, ids: list):
        
        ids = ["'" + str(x) + "'" for x in ids]

        sql = """
                DELETE `{}`
                WHERE {} IN ({})
                """.format(tableName, keyName, ", ".join(ids))
        
        print(sql)

        resp = pandas_gbq.read_gbq(sql, project_id=google_project_id, credentials=credentials, max_results = 1)
        print('Deleted records from {} using unique key {}'.format(tableName, keyName))

    
    def delete_ids_manual(self, tableName: str, keyName: str, ids: list):
        
        ids = ["'" + str(x) + "'" for x in ids]

        sql = """
                DELETE `{}`
                WHERE {} IN ({})
                """.format(tableName, keyName, ", ".join(ids))
        
        print(sql)

        while True:
            input_resp = input("Please type 'deleted' to confirm you have executed SQL query above")
            if input_resp == 'deleted':
                break

        #resp = pandas_gbq.read_gbq(sql, project_id=google_project_id, credentials=credentials)
        print('Manually deleted records from {} using unique key {}'.format(tableName, keyName))


    def query(self, query_sql) -> pd.DataFrame:

        logger.info("Querying bigquery...")
        resp = pandas_gbq.read_gbq(query_sql, project_id=upload_conf["project_id"], credentials=credentials)
        return resp

    def upload_data(self, df, destination_table, schema, if_exists = 'append'):

        try:

            if schema == None:
                resp = pandas_gbq.to_gbq(df,
                                        destination_table = dataset + "." + destination_table,
                                        project_id=google_project_id,
                                        credentials=credentials,
                                        if_exists = if_exists)
            
                print("Uploaded to {}. Without Schema".format(dataset + "." + destination_table))

            else:
                resp = pandas_gbq.to_gbq(df,
                                        destination_table = dataset + "." + destination_table,
                                        project_id=google_project_id,
                                        credentials=credentials,
                                        if_exists = if_exists,
                                        table_schema = schema)
            
                print("Uploaded to {}. With Schema".format(dataset + "." + destination_table))

        except Exception as e:
            print(e)
            print("Destination Table: {}".format(dataset + "." + destination_table))
            print("Schema: {}".format(json.dumps(schema)))
            print("Data Details: {}".format(df.dtypes))