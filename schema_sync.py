import yaml
import pandas as pd
import numpy as np
import os
import logging
import json

path = os.path.dirname(os.path.abspath(__file__))
upload_conf_file = os.path.join(path, "upload_conf.yaml")

with open(upload_conf_file, "r") as file:
    upload_conf = yaml.safe_load(file)

logger = logging.getLogger(__name__)

class Save_or_convert_schema:

    @classmethod
    def check_if_schema_exists(cls, accountName):
        if "schema" in upload_conf.keys()\
            and type(upload_conf["schema"]) == dict\
            and accountName in upload_conf["schema"].keys()\
            and type(upload_conf["schema"][accountName]) == list\
            and len(upload_conf["schema"][accountName]) > 0:


            return (True, upload_conf["schema"][accountName])
        
        else:
            return (False, [])
        
    @classmethod
    def convert_schema(cls, data, schema):

        data_columns = list(data.columns)

        schema_columns = [x['name'] for x in schema]

        missing_columns = [x for x in schema_columns if x not in data_columns]

        for col in missing_columns:
            data[col] = np.nan

        data = data[schema_columns]

        assert len(schema) == len(list(data.columns)), "Schema coversion failed"

        return data
    
    @classmethod
    def convert_schema_types(cls, data, schema):

        def convert_string_objects(value):

            if type(value) in (dict, list, tuple):
                return json.dumps(value)
            
            elif value == None or pd.isna(value) == True:
                return value
                
            else:
                return str(value)

        for item in schema:

            if item['type'] == "STRING":

                data[item["name"]] = data[item["name"]].map(lambda x: convert_string_objects(x))
                data[item["name"]] = data[item["name"]].astype("string")
            
            elif item["type"] == "INTEGER":

                data[item["name"]] = data[item["name"]].astype("int")

            elif item['type'] == "FLOAT":

                data[item["name"]] = data[item["name"]].astype("float")

            elif item["type"] in ("BOOL", "BOOLEAN"):

                data[item["name"]] = data[item["name"]].astype("boolean")

            elif item["type"] in ("TIMESTAMP", "DATETIME"):

                data[item["name"]] = pd.to_datetime(data[item["name"]], errors="coerce")


        return data

    
    
    @classmethod
    def create_and_save_schema(cls, data, accountName):
        
        columns = list(data.columns)

        if "schema" not in upload_conf.keys():
            upload_conf["schema"] = {}
        elif type(upload_conf["schema"]) != dict:
            upload_conf["schema"] = {}

        
        if accountName not in upload_conf["schema"].keys():
            upload_conf["schema"][accountName] = None

        schema = cls.generate_bq_schema_types(columns)

        upload_conf["schema"][accountName] = schema

        with open(upload_conf_file, "w") as file:
            yaml.safe_dump(upload_conf, file)

        return schema



    @classmethod
    def generate_bq_schema_types(cls, columns: list) -> list:

        schema = []
        
        for col in columns:
            if any(x in col.lower() for x in ["create", "update", "published"]):
                schema.append({"name": col, "type": "TIMESTAMP"})
            else:
                schema.append({"name": col, "type": "STRING"})

        return schema

    
    @classmethod
    def process_data(cls, data, accountName):

        check_schema, schema = cls.check_if_schema_exists(accountName)

        if check_schema == True:
            logger.debug("Schema Found")
            data = cls.convert_schema(data, schema)
        else:
            logger.debug("Schema Not Found")
            schema = cls.create_and_save_schema(data, accountName)
            data = cls.convert_schema(data, schema)

        assert len(schema) == len(list(data.columns)), "Dataframe does not match schema"

        #print(data.columns)

        data = cls.convert_schema_types(data, schema)

        return (data, schema)

        



    

