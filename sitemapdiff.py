import logging, sys, os, datetime
import configparser as cfg
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

SOURCE_SITEMAP_URL="https://www3.permaculture.org.uk/sitemap.xml"
TARGET_SITEMAP_URL="https://dev.permaculture.org.uk/sitemap.xml"

nowtime = datetime.datetime.now().isoformat().replace(":", "_").split(".")[0]

os.makedirs('report', exist_ok=True)

config = cfg.ConfigParser()
config.read("config.ini")
ba_user=config['AppConfig']['basic_auth_user']
ba_pass=config['AppConfig']['basic_auth_pass']


TARGET_BASE_URL=config['AppConfig']['baseurl']

log_level = config['Logging']['level']
if log_level == 'info':
    ilog_level = logging.INFO
elif log_level == 'debug':
    ilog_level = logging.DEBUG
else:
    ilog_level = logging.WARN



xml_namespace="http://www.sitemaps.org/schemas/sitemap/0.9"
def get_sitemap(uri, url_set):
    logging.info(f"Processing sitemap: {uri}")
    session = requests.Session()
    session.auth = (ba_user, ba_pass)
    resp = session.get(uri)

    xmldata=resp.content.decode("utf-8")
    root_element=ET.fromstring(xmldata)

    pars_xml_for_urls(root_element,url_set)

    for sitemap in root_element.findall('./{'+xml_namespace+'}sitemap/{'+xml_namespace+'}loc'):
        location=sitemap.text
        #"./{'+xml_namespace+'}loc")

        logging.info(f"Found nested sitemap: {location}")
        get_sitemap(location,url_set)
        pass




def pars_xml_for_urls(root_element,url_set):
    logging.info(f"Processing URLs")
    for url_element in root_element.findall('./{' + xml_namespace + '}url//{'+xml_namespace+'}loc'):
        url_str=url_element.text
        logging.debug(f"found url {url_str}")
        url_bits=urlparse(url_str)
        url_path=url_bits.path
        url_set.add(url_path)




def main():

    source_sitemap=set()
    get_sitemap(SOURCE_SITEMAP_URL,source_sitemap)

    target_sitemap=set()
    get_sitemap(TARGET_SITEMAP_URL,target_sitemap)

    diff_sitemap=source_sitemap.difference(target_sitemap)
    diff_sitemap=sorted(diff_sitemap)
    inspect_differences(diff_sitemap)


    with open(f"report/sitemap-differences-{nowtime}.csv","w") as f1, open("report/410s-map.conf","w") as f2:
        f1.write("URL\n")
        f2.write("map_hash_bucket_size 128;\n\n")
        f2.write("map $request_uri $gone_urls {\n")
        for url in diff_sitemap:
            f1.write(f"\"{url}\"\n")
            f2.write(f"\t{url} 1;\n")

        f2.write(f"\tdefault 0;\n")
        f2.write("}\n")

def inspect_differences(diff_sitemap):

        session = requests.Session()
        session.auth = (ba_user, ba_pass)
        for url in diff_sitemap:
            try:
                logging.debug(f"validating url before excluding: {url} ")
                resp = session.get(TARGET_BASE_URL + url)

                if resp.status_code!=404:
                    logging.error(f"url: {url} exists on target, excluding from 410 list")
                    diff_sitemap.remove(url)
                pass
            except Exception as e:
                logging.error(f"could not validate target url: {url}")


if __name__ == '__main__':
    logging.basicConfig(
        level=ilog_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(f"report/sitemapdiff-{nowtime}.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    main()
