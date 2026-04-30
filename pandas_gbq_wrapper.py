import pandas_gbq
import logging
from google.oauth2 import service_account
import os
import pandas as pd
import yaml

path = os.path.dirname(os.path.abspath(__file__))
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = path + '/auth/service_account.json'
credentials = service_account.Credentials.from_service_account_file(
  path + '/auth/service_account.json'
)

with open(path + "/upload_conf.yaml", "r") as file:
    upload_conf = yaml.safe_load(file)


class pd_bigquery:

    @staticmethod
    def read_bigquery(query_sql: str):

        return pandas_gbq.read_gbq(query_sql,
                                project_id = upload_conf["project_id"],
                                credentials=credentials)
    
    
    @staticmethod
    def upload_bigquery(df: pd.DataFrame, destinationTable: str, table_schema: list = None):
        
        return pandas_gbq.to_gbq(df,
                                destination_table = upload_conf["dataset"] + "." + destinationTable,
                                project_id = upload_conf["project_id"],
                                credentials = credentials,
                                if_exists = "append",
                                table_schema = table_schema)

