from google.cloud import translate_v2 as translate
from langdetect import detect
import string
import re
import logging
import os
import json
import threading

logger = logging.getLogger(__name__)

#Cache
path = os.path.dirname(os.path.abspath(__file__))
translate_cache_fileName = 'translation_cache.json'
translate_cache_fileName_fullPath = os.path.join(path, translate_cache_fileName)


if os.path.exists(translate_cache_fileName_fullPath):
    with open(translate_cache_fileName_fullPath, 'r') as f:
        translation_cache = json.load(f)
else:
    translation_cache = {}

cache_lock = threading.Lock()


class googleTranslate:

    def __init__(self, credentials):
        self.client = translate.Client(credentials=credentials)
        self.cleanPunctuation = str.maketrans('', '', string.punctuation)
        self.emoji_pattern = re.compile(
                "[" 
                "\U0001F600-\U0001F64F"  # emoticons
                "\U0001F300-\U0001F5FF"  # symbols & pictographs
                "\U0001F680-\U0001F6FF"  # transport & map symbols
                "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                "\U00002700-\U000027BF"  # Dingbats
                "\U000024C2-\U0001F251" 
                "]+", flags=re.UNICODE)

    def isEnglish(self, text:str) -> bool:

        try:
            if text == None or text == "" or len(text.strip()) == 1:
                return None
            elif self.emoji_pattern.sub(r'', text.translate(self.cleanPunctuation).strip()) == "":
                return None
            elif detect(text) == "en":
                return True
            else:
                return False
            
        except Exception as e:
            logger.debug(e)
            return None
            


    def translateText(self, text: str, target_language='en') -> str:

        with cache_lock:
        
            #Check cache
            if text in translation_cache.keys():
                return translation_cache[text]
            
            if self.isEnglish(text) == False:
                translatedText = self.client.translate(text, target_language=target_language)

                #Write to cache
                translation_cache[text] = translatedText['translatedText']
                
                with open(translate_cache_fileName_fullPath, 'w') as f:
                    json.dump(translation_cache, f, ensure_ascii=False, indent=2)

                return translatedText['translatedText']
            return text


    def cleanCache(self):
        with cache_lock:
            with open(translate_cache_fileName_fullPath, 'w') as f:
                json.dump({}, f)