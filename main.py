import yaml
import os
from okendo_client import Okendo_api
from logger_config import *
import pandas as pd
from pandas_gbq_wrapper import pd_bigquery
import sys
from schema_sync import Save_or_convert_schema
from concurrent.futures import ThreadPoolExecutor
import time
from functions import postFunctions


path = os.path.dirname(os.path.abspath(__file__))

okendo_auth_file = os.path.join(path, "auth/okendo_auth.yaml")
with open(okendo_auth_file, "r") as file:
    auth_conf = yaml.safe_load(file)

upload_conf_file = os.path.join(path, "upload_conf.yaml")
with open(upload_conf_file, "r") as file:
    upload_conf = yaml.safe_load(file)

setup_logging(level=logging.DEBUG)
logger = logging.getLogger(__name__)



class main:

    def __init__(self):
        assert len(auth_conf) ==\
            len([item for item in auth_conf if len([k for k in item.keys() if k in ["store", "username", "password"]]) == 3]),\
                "Please include these keys in auth 'store', 'username', 'password'"
        self.auth = auth_conf
        self.source_client = Okendo_api()
        self.destination_client = pd_bigquery
        self.data = {}

    def get_last_sate(self, accountName: str) -> pd.DataFrame:

        sql_string = f"""

        SELECT MAX({upload_conf['last_state_field']}) as last_state_field FROM `{upload_conf['project_id']}.{upload_conf['dataset']}.{upload_conf['tableNameStructure'].format(accountName)}`

        """

        try:
            last_state = self.destination_client.read_bigquery(sql_string)
            last_state = pd.to_datetime(last_state.values[0], utc = True)
            assert pd.isna(last_state) == False, "Last state None error"
            return last_state
        
        except Exception as e:
            logger.info(f"{e}")
            assert "last_state_field_fallback" in upload_conf.keys(), "Please add 'last_state_field_fallback' to upload_conf"
            assert "last_state_field_fallback_format" in upload_conf.keys(), "Please add 'last_state_field_fallback_format' to upload_conf"
            last_state = pd.to_datetime(upload_conf["last_state_field_fallback"], format=upload_conf["last_state_field_fallback_format"], utc=True)
            assert pd.isna(last_state) == False, "Last state None error"
            return last_state


    def get_account_data(self, auth_item: dict):

        all_status_data = []
        
        self.source_client.set_credentials(auth_item["username"], auth_item["password"])

        last_state = self.get_last_sate(auth_item["store"])

        for status in ["approved", "pending", "rejected"]:

            data = self.source_client.get_reviews(last_state = last_state,
                                                    last_state_field = upload_conf['last_state_field'],
                                                    limit=100,
                                                    status = status)
            all_status_data.extend(data)
            

        
        all_status_data = pd.DataFrame(all_status_data)

        return all_status_data
    
    def run(self, accountName):

        #accountName = sys.argv[1]

        assert "destinationTablePatern" in upload_conf.keys(), "Please add 'destinationTablePatern' register in the upload conf"
        assert accountName in [x["store"] for x in auth_conf], f"Store {accountName} was not found in auth file"

        accountConf = next((item for item in auth_conf if item["store"] == accountName), None)
        destinationTable = upload_conf["destinationTablePatern"].format(accountName)
        logger.debug(f"Destination table {destinationTable}")

        data = self.get_account_data(accountConf)
        
        if "postFunctions" in upload_conf.keys():
            data = postFunctions.processFunctions(data, upload_conf["postFunctions"])

        data.to_csv("test_data.csv", index=False)

        data, schema = Save_or_convert_schema.process_data(data, accountName)

        #print(list(data.columns))
        #print(schema)
        
        assert type(data) == pd.DataFrame, "Fail data type"
        assert len(schema) == data.shape[1], f"Data Columns {data.shape[1]} do not match schema {len(schema)}"


        self.destination_client.upload_bigquery(data, destinationTable, schema)





if __name__ == "__main__":


    accounts = [x["store"] for x in auth_conf if x["store"] not in upload_conf["exclude_accounts"]]


    def run_account(account):

        main_instance = main()
        main_instance.run(account)


    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(run_account, accounts))

    postFunctions.cleanCache()

