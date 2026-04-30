import requests
import pandas as pd
import logging
from typing import Iterator

logger = logging.getLogger(__name__)

class Okendo_api:

    def __init__(self):
        self.client = requests.Session()
        self.client.headers.update({'Accept': 'application/json'})

    def set_credentials(self, username: str, password: str):
        self.client.auth = (username, password)

    def get_reviews(self, last_state = None, last_state_field = None, **params) -> Iterator[dict]:
        assert last_state != None and last_state_field != None, "Please populate 'last_state' and 'last_state_field' value"
        base_url = "https://api.okendo.io"
        url = "/enterprise/reviews"
        assert self.client.auth not in (None, "", (), []), "Please set_credentials first"
        data = []

        while url != None:
            response = self.client.get(base_url + url, params=params)
            response = response.json()

            if "nextUrl" in response.keys() and response["nextUrl"] not in ("", None):
                url = response["nextUrl"]
            else:
                url = None


            if "reviews" in response.keys():
                if last_state == None:
                    for item in response["reviews"]:
                        yield item
                else:
                    for item in response["reviews"]:
                        #logger.debug(f"date field: {item[last_state_field]}, last_state: {last_state}")
                        if pd.to_datetime(item[last_state_field], utc=True) >= last_state:
                            yield item
                        else:
                            url = None
                            break
