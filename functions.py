import pandas as pd
from translate import googleTranslate
from google.oauth2 import service_account
import yaml
import os
import yake

path = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(path, "upload_conf.yaml"), "r") as file:
    upload_conf = yaml.safe_load(file)

path = os.path.dirname(os.path.abspath(__file__))
assert "service_account_path" in upload_conf.keys(), "'service_account_path' was not found in upload_conf"

class postFunctions:

    googleTranslate = None
    yakeExtract = None

    @classmethod
    def cleanCache(cls):
        if cls.googleTranslate != None:
            cls.googleTranslate.cleanCache()

    @classmethod
    def processFunctions(cls, data: pd.DataFrame, conf_item) -> pd.DataFrame:
        assert type(conf_item) == list, "postFunctions upload_config section should be a list"
        assert len([x for x in conf_item if len(x.keys()) == 1]) == len(conf_item), "Only one function name per dictionary within list"
        assert len([x for x in conf_item if next(iter(x.keys())) in ("copy", "translate", "extract_keywords")]) == len(conf_item), "Suported functons - copy, translate, extractKeywords"

        for item in conf_item:
            if next(iter(item.keys())) == "copy":
                data = cls.copyField(data, item["copy"]["sourceField"], item["copy"]["targetField"])
            if next(iter(item.keys())) == 'translate':
                data = cls.translateText(data, item["translate"]["sourceField"], item["translate"]["targetField"])
            if next(iter(item.keys())) == 'extract_keywords':
                data = cls.extractKeywords(data, item["extract_keywords"]["sourceField"], item["extract_keywords"]["targetField"])

        return data


    @classmethod
    def copyField(cls, data: pd.DataFrame, sourceField: str, targetField: str) -> pd.DataFrame:

        #assert sourceField in list(data.columns), f"{sourceField} was not found in dataframe"

        if sourceField in list(data.columns):
            data[targetField] = data[sourceField]
        else:
            data[targetField] = pd.NA

        return data
    
    @classmethod
    def translateText(cls, data: pd.DataFrame, sourceField: str, targetField: str) -> pd.DataFrame:

        if cls.googleTranslate == None:
            credentials = service_account.Credentials.from_service_account_file(
                    path + upload_conf['service_account_path']
                    )
            cls.googleTranslate = googleTranslate(credentials)

        assert targetField not in list(data.columns), f"{targetField} is a duplicate name of other column. Please choose another"
        
        data[targetField] = data[sourceField].map(lambda x: cls.googleTranslate.translateText(x))

        return data
    
    @classmethod
    def extractKeywords(cls, data: pd.DataFrame, sourceField: str, targetField: str) -> pd.DataFrame:

        if cls.yakeExtract == None:
            cls.yakeExtract = yake.KeywordExtractor()


        def processReview(text: str) -> list:

            keywords = cls.yakeExtract.extract_keywords(text)

            keyword_dicts = [
                {
                    "keyword": kw,
                    "score": score
                }
                for kw, score in keywords
            ]

            keyword_dicts.sort(key=lambda d: d['score'], reverse=True)

            return keyword_dicts
        

        data[targetField] = data[sourceField].map(lambda x: processReview(x))

        return data



        







