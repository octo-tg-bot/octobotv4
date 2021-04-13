import json
import os
from glob import glob

from babel.messages.pofile import read_po
import requests

BASE_ARGS = {"api_token": os.environ["POEDITOR_TOKEN"],
             "id": os.environ["POEDITOR_ID"], }


def create_poeditor_catalog(catalog, endpoint):
    catalog_poeditor = []
    for message in catalog:
        msgid = message if isinstance(message, str) else message.id
        msgext = {}
        if not isinstance(message, str):
            msgext["translation"] = {"content": message.string}
            if not endpoint == "translations":
                msgext["reference"] = ""
                msgext["tags"] = []
                for location in message.locations:
                    msgext["reference"] += f"{location[0]}#{location[1]} "
                    msgext["tags"].append(location[0])
        if msgid != '':
            catalog_poeditor.append({
                "term": msgid,
                **msgext
            })
    return catalog_poeditor


def send_poeditor_catalog(endpoint, action, catalog, extra_args={}):
    print(f"Uploading catalog to {endpoint}/{action}, args: {extra_args}")
    if not catalog:
        print("Nothing to send...")
        return
    catalog = json.dumps(create_poeditor_catalog(catalog, endpoint))
    r = requests.post(f"https://api.poeditor.com/v2/{endpoint}/{action}",
                      data={"data": catalog,
                            **BASE_ARGS,
                            **extra_args})
    r.raise_for_status()
    if r.json()["response"]["message"] != "OK":
        raise Exception(r.json()["response"]["message"])
    print("Result:", r.json()["result"])


def main():
    catalog_template = read_po(open('base.pot', encoding="utf-8"), domain="messages", ignore_obsolete=False)
    send_poeditor_catalog("terms", "add", catalog=catalog_template)
    for language in glob("*/LC_MESSAGES/*.po"):
        catalog = read_po(open(language, encoding="utf-8"), domain="messages", ignore_obsolete=False)
        langcode = catalog.locale.language
        send_poeditor_catalog("translations", "add", catalog=catalog,
                              extra_args={"language": langcode})
        send_poeditor_catalog("translations", "delete", catalog=catalog.obsolete, extra_args={"language": langcode})
        send_poeditor_catalog("terms", "delete", catalog=catalog.obsolete)
    send_poeditor_catalog("terms", "delete", catalog=catalog_template.obsolete)


if __name__ == '__main__':
    main()