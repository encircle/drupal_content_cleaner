import os

import dbapi
import logging as log
import re
import json
import requests, shutil
import hashlib

from bs4 import BeautifulSoup
from urllib.parse import unquote,quote

from main import path_filesystem, base_url, tld, tld_re, squash_subdomains, check_links, basic_auth, basic_auth_pass, \
    basic_auth_user, scrapeexternalimages

url_timeout = (10.0, 30.0)

f = open('field_config.json')
text_content_fields = json.load(f)

def remove_prefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix):]

def parse_text_content(config, files_all):
    files_not_registered = {}

    fw_d7 = open("./report/files_in_d7_tags.csv", "w")
    fw_d7.write("entity type,entity id,field,owner,node url,fid,uri\n")
    fw_d7.flush()

    fw_ext_err = open("./report/files_external_error.csv", "w")
    fw_ext_err.write("entity type,entity id,field,owner,node url,internal,uri\n")
    fw_ext_err.flush()

    fw_url_err = open("./report/files_url_error.csv", "w")
    fw_url_err.write("entity type,entity id,field,owner,node url,internal,uri\n")
    fw_url_err.flush()

    connection = dbapi.get_connection(config, 'Database')

    for text_content_field in text_content_fields:
        field = text_content_field['field']
        entity_id_field = text_content_field['entity_id']
        entity_type = text_content_field['entity_type']
        table = text_content_field['table']
        table_rev = text_content_field['table_rev']
        # query = f"select {field},{entity_id} from {table} where entity_id=32090"

        if entity_type == "node":
            query = f"""select field.{field},field.{entity_id_field},nfd.uid,ufd.name,ufd.mail from {table} field
            join node_field_data nfd on field.{entity_id_field}=nfd.nid
            join users_field_data ufd on ufd.uid=nfd.uid  
            """
        else:
            query = f"select field.{field},field.{entity_id_field} from {table} field"  # " LIMIT 100"

        log.info(f"Parsing Field {field} in table {table}")
        connection = dbapi.get_connection(config, 'Database')
        with connection.cursor() as cursor:
            cursor.execute(query)
            records = cursor.fetchall()
        connection.close()

        for record in records:  #:= cursor.fetchone():
            has_edits = False
            content = record[0]

            if not content or len(content) < 1:
                continue
            entity_id = record[1]
            node_url = base_url + "/" + entity_type + "/" + str(entity_id)
            if entity_type == "node":
                user_name = record[3]
                user_email = record[4]
            else:
                user_name = ''
                user_email = ''

            log.info(f"Parsing entity: {entity_type} - {entity_id} - field: {field}")

            soup = BeautifulSoup(content, 'html.parser')

            for link in soup.find_all('img'):
                src = link.get('src')
                if src.startswith("data:"):
                    continue
                # log.info(f"\timage - {table}:{entity_id}=" + src)
                result = check_for_local_uri_and_reformat(src)
                if result:
                    clean_uri = result["clean_uri"]
                    if clean_uri != src:
                        log.info(f"\treplace image: {clean_uri} - {src}")
                        link['src'] = clean_uri
                        has_edits = True
                    else:
                        log.info(f"\tkeep image: {clean_uri} - {src}")

                    naked_uri = remove_prefix(clean_uri, "/sites/default/files")
                    if "?" in naked_uri:
                        naked_uri=naked_uri.split("?")[0]
                    naked_uri=unquote(naked_uri)

                    uri = "public:/" + naked_uri
                    if uri in files_all:
                        files_all[uri]["no-content"] = False
                    else:

                        if not uri.startswith("public://external-images/"):
                            files_not_registered[uri] = uri
                        check_filepath=f"{path_filesystem}{naked_uri}"
                        if not os.path.exists(check_filepath):
                            fw_ext_err.write(
                                f'"{entity_type}", "{entity_id}", "{table}", "{user_name}","{node_url}","True","{src}"\n')
                            fw_ext_err.flush()

                elif scrapeexternalimages == "True":

                    src_ext = get_external_image(src)
                    log.info(f"\texternal image: {src_ext} - {src}")
                    if src_ext == None:
                        fw_ext_err.write(
                            f'"{entity_type}", "{entity_id}", "{table}", "{user_name}","{node_url}","False","{src}"\n')
                        fw_ext_err.flush()
                    else:
                        link['src'] = src_ext
                        has_edits = True

            for link in soup.find_all('a'):
                if not 'href' in link.attrs:
                    continue
                href = link.get('href')

                result = check_for_local_uri_and_reformat(href)
                if result:
                    clean_uri = result["clean_uri"]
                    if clean_uri != href:
                        log.info(f"\treplace link: {clean_uri} - {href}")
                        link['href'] = clean_uri
                        has_edits = True
                    else:
                        log.info(f"\tkeep link: {clean_uri} - {href}")


                    if clean_uri.startswith("/sites/default/files"):

                        naked_uri = remove_prefix(clean_uri, "/sites/default/files")
                        if "?" in naked_uri:
                            naked_uri = naked_uri.split("?")[0]
                        naked_uri = unquote(naked_uri)

                        uri = "public:/" + naked_uri

                        if uri in files_all:
                            files_all[uri]["no-content"] = False
                        else:
                            if not uri.startswith("public://external-images/"):
                                files_not_registered[uri] = uri

                    check_url = f"{base_url}{clean_uri}"
                    internal_url = True
                else:
                    check_url = href
                    internal_url = False

                url_ok = get_external_link(check_url)
                if url_ok == False:
                    strsf = f'"{entity_type}","{entity_id}","{table}","{user_name}","{node_url}","{internal_url}","{check_url}"\n'
                    fw_url_err.write(strsf)
                    fw_url_err.flush()
            # find drupal 9 media entities - only test ones found
            # for link in soup.find_all('drupal-media'):
            #    log.info(f"\tmedia - {table}:{entity_id}=" + link.get('data-entity-uuid'))

            # now use regexp to find any drupal tags
            drup_tags = re.findall("\[\[(.*)\]\]", content)
            for drup_tag in drup_tags:
                try:
                    drup_tag_obj = json.loads(drup_tag)
                    fid = drup_tag_obj['fid']
                    type = drup_tag_obj['type']
                    # log.info(f"\tdrupal tag {table}:{entity_id}={type}:{fid}")
                    uri = None
                    for x, y in files_all.items():
                        if y['fid'] == int(fid):
                            uri = y['uri']
                            files_all[uri]["no-content"] = False
                            break
                    # log.info(f"\tdrupal tag {table}:{entity_id}={type}:{fid}:{uri}")

                    strsf = f'"{entity_type}","{entity_id}","{table}","{user_name}","{node_url}","{fid}","{uri}"\n'
                    fw_d7.write(strsf)
                    fw_d7.flush()
                except Exception as ex:
                    log.error(f"\tfailed drupal tag parse for {table}:{entity_id}")

            if has_edits == True:
                pretty_html = str(soup)
                pretty_html = pretty_html.replace("'", "''")

                insert_stmt = f"update {table} set {field}='{pretty_html}' where {entity_id_field}={entity_id}"
                connection = dbapi.get_connection(config, 'Database')
                with connection.cursor() as cursor2:
                    try:
                        if table_rev != "":
                            cursor2.execute(
                                f"select revision_id from {table_rev} where {entity_id_field}={entity_id} order by revision_id desc limit 1")
                            revs = cursor2.fetchone()
                            rev = revs[0]
                            insert_rev_stmt = f"update {table_rev} set {field}='{pretty_html}' where {entity_id_field}={entity_id} and revision_id={rev}"
                            cursor2.execute(insert_rev_stmt)

                        cursor2.execute(insert_stmt)

                        connection.commit()
                        pass
                    except Exception as ex:
                        log.error(f"failed to update content:{entity_type}:{entity_id} field {table}")
                connection.close()
    log.info("finished content sweep, cleaning up.")

    fw_url_err.close()
    fw_d7.close()
    fw_ext_err.close()

    with open("./report/files_not_registered_content.csv", "w") as fw:
        fw.write("filepath\n")
        for record in files_not_registered:
            if record.startswith("public://sites/default/files/"):
                fw.write(f'"{record}"\n')


def check_for_local_uri_and_reformat(uri):
    result = {
        "subdomain": None,
        "clean_uri": None
    }


    # ignore mailto: links
    if uri.startswith("mailto:") or "@" in uri:
        return None

    if uri.startswith("/"):
        result["clean_uri"] = uri
        return result

    # look for permaculture links
    if not tld in uri:
        return None

    # find subdomains
    match = re.search(f"^(?:https*://)(\w+)\.{tld_re}(.*)", uri)
    if match:
        subdomain = match.group(1)
        relurl = match.group(2)
        if subdomain == "www":
            # log.info(f"main - {relurl}")
            pass

        else:
            if squash_subdomains == "True":
                # log.info(f"subdomain - {subdomain}:{relurl}")
                result["subdomain"] = subdomain
            else:
                return None

        result["clean_uri"] = relurl
        return result
    # check for root domain links
    else:

        match = re.search(f"^(?:https*://){tld_re}(.*)", uri)
        if match:
            result["clean_uri"] = match.group(1)
            return result

    return None


def get_external_image(url):
    try:

        path_bits = url.split("/")
        filename = path_bits[-1]
        urlpath = "/".join(path_bits[:-1])
        md5path = md5_str(urlpath)

        if "?" in filename:
            fparts=filename.partition("?")

            fnameparts=fparts[0].rpartition(".")

            filename=""+fnameparts[0]+"-"+md5_str(fparts[2])+"."+fnameparts[2]
            pass

        filename=unquote(filename)

        basedir = path_filesystem + "/external-images/" + md5path + "/"
        os.makedirs(basedir, exist_ok=True)
        localpath = basedir + filename;
        if os.path.isfile(localpath):
            return "/sites/default/files/external-images/" + md5path + "/" + filename

        res = requests.get(url, stream=True, timeout=url_timeout)
        if res.status_code == 200:
            with open(localpath, 'wb') as f:
                shutil.copyfileobj(res.raw, f)
            return "/sites/default/files/external-images/" + md5path + "/" + filename
        else:
            pass
    except Exception as ex:
        log.error(f"failed to download image:{url}")
    return None


def get_external_link(url):
    if check_links != "True":
        return True
    try:

        if url.startswith("mailto:") or url.startswith('#'):
            return True
        session = requests.Session()
        if basic_auth == "True" and tld in url:
            session.auth = (basic_auth_user, basic_auth_pass)
        res = session.get(url, stream=True, timeout=url_timeout)
        if res.status_code == 200:
            return True
        else:
            pass
    except Exception as ex:
        log.error(f"failed to download link:{url}")
    return False


def md5_str(str):
    m = hashlib.md5()
    m.update(str.encode('utf-8'))
    return m.hexdigest()
