import logging as log
import os, sys, datetime, json
import configparser as cfg
import dbapi
import content_crawler
import domain_parser


f = open('ignore_dirs.json')
ignore_dirs = json.load(f)


os.makedirs('report',exist_ok=True)



config = cfg.ConfigParser()
config.read("config.ini")
log_level = config['Logging']['level']
if log_level == 'info':
    ilog_level = log.INFO
elif log_level == 'debug':
    ilog_level = log.DEBUG
else:
    ilog_level = log.WARN

d7_tag_mode=config['AppConfig']['d7_tag_mode']
path_filesystem=config['AppConfig']['basedir']

base_url=config['AppConfig']['baseurl']

tld=config['AppConfig']['tld']
tld_re=tld.replace('.','\\.')

scrapeexternalimages=config['AppConfig']['scrapeexternalimages']

squash_subdomains=config['AppConfig']['squash_subdomains']
check_links=config['AppConfig']['check_links']

delete_unreferenced_files=config['AppConfig']['delete_unreferenced_files']

basic_auth=config['AppConfig']['basic_auth']
basic_auth_user=config['AppConfig']['basic_auth_user']
basic_auth_pass=config['AppConfig']['basic_auth_pass']

nowtime=datetime.datetime.now().isoformat().replace(":","_").split(".")[0]
log.basicConfig( format='%(levelname)s:%(message)s', level=ilog_level, handlers=[
            log.FileHandler(f"report/debug-{nowtime}.log"),
            log.StreamHandler(sys.stdout)
        ])


def remove_prefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix):]

def list_real_files():
    file_table= {};
    for (dirpath, dirnames, filenames) in os.walk(path_filesystem):
        for filename in filenames:
                if filename==".htaccess":
                    continue
                fullfile = "/".join([dirpath, filename])
                relfile="public:/"+remove_prefix(fullfile,path_filesystem)

                #check if file is in exclusion table.
                ignore=False
                for x in ignore_dirs:
                    if relfile.startswith(x):
                        ignore=True
                        break

                if ignore==True:
                    continue
                file_table[relfile]=fullfile

    file_list=sorted(file_table.keys(),key=str.casefold)


    if False:
        with open("./report/files_real_all.csv", "w") as fw:
            fw.write("filepath\n")
            for filepath in file_list:
                fw.write(f"{filepath}\n")

    return file_table

def get_db_unused_files(files_all):
    connection=dbapi.get_connection(config,'Database')
    with connection.cursor() as cursor:
        # Read a single record
        sql = """select fm.uri from file_managed as fm
left join file_usage as fu on fm.fid=fu.fid
where fu.count is null or fu.count<1 
order by fm.uri"""

        cursor.execute(sql)
        result = cursor.fetchall()
        #with open("./report/files_registered_unused_by_entities.csv", "w") as fw:
        #    fw.write("filepath\n")
        for record in result:
            uri=record[0]
            #fw.write(f'"{uri}",\n')
            if uri in files_all:
                all_record=files_all[uri]
                all_record["no-entity"]=True


def get_db_all_files():
    connection=dbapi.get_connection(config,'Database')
    files_all={}
    with connection.cursor() as cursor:
        # Read a single record
        sql = """select fm.fid,fm.uri from file_managed as fm order by fm.uri"""

        cursor.execute(sql)
        result = cursor.fetchall()
        #with open("./report/files_registered_all.csv", "w") as fw:
        #    fw.write("filepath\n")
        for record in result:
            #fw.write(f'"{record[0]}"\n')
            files_all[record[1]]={
                "uri":record[1],
                "fid":record[0],
                "no-entity":False,
                "no-content":True
            }
        return files_all

def compare_real_and_registered_files(files_real,files_all):

    files_not_registered={}

    file_real_keys= sorted(files_real.keys(),key=str.casefold)
    for file_real in file_real_keys:
        if file_real in files_all:
            continue

        files_not_registered[file_real]=files_real[file_real]


    with open("./report/files_not_registered.csv", "w") as fw:
        fw.write("filepath\n")
        for uri,path in files_not_registered.items():
            fw.write(f'"{uri}","{path}"\n')

    files_not_present={}

    file_all_keys = sorted(files_all.keys(), key=str.casefold)
    for file_all in file_all_keys:
        # check if file is in exclusion table.
        ignore = False
        for x in ignore_dirs:
            if file_all.startswith(x):
                ignore = True
                break

        if ignore == True:
            continue
        if file_all in files_real:
            continue

        files_not_present[file_all] = files_all[file_all]

    with open("./report/files_not_present.csv", "w") as fw:
        fw.write("filepath\n")
        for uri in files_not_present.keys():
            fw.write(f'"{uri}"\n')

    return (files_not_registered,files_not_present)

def main():
    os.makedirs("./report", exist_ok=True);
    if d7_tag_mode=="True":
        domain_parser.parse_domains(config)


    files_real=list_real_files()
    files_all=get_db_all_files()
    compare_real_and_registered_files(files_real, files_all)

    get_db_unused_files(files_all)


    content_crawler.parse_text_content(config,files_all)

    log.info("processing unreferenced files")
    connection = dbapi.get_connection(config, 'Database')
    with connection.cursor() as cursor:
        # Read a single record

        #with open("./report/files_registered_unused.sh","w") as fwb:
        #fwb.write("#!/bin/sh\n")
        with open("./report/files_registered_unused.csv", "w") as fw:
            fw.write("filepath\n")
            for x,y in files_all.items():

                ignore=False
                for z in ignore_dirs:
                    if x.startswith(z):
                        ignore=True
                        break

                if ignore==True:
                    continue

                fid=y['fid']
                uri=y['uri']
                noent=y["no-entity"]
                nocontent=y["no-content"]
                xx=x.removeprefix("public://")
                if noent and nocontent:
                    if delete_unreferenced_files=="True":
                        log.info(f" \tdelete file: {uri}")
                        sql1 = f"delete from file_managed where fid={fid}"
                        sql2= f"delete from file_usage where fid={fid} and module='file'"
                        try:
                            cursor.execute(sql1)
                            cursor.execute(sql2)
                            connection.commit()
                        except Exception as ex:
                            log.error(f"failed to delete file from db: {uri}")

                        try:
                            os.remove(path_filesystem+""+uri.removeprefix("public:/"))
                        except Exception as ex:
                            log.error(f"failed to delete file from filesystem: {uri}")

                    fw.write(f'"{x}"\n')
                    #fwb.write(f'rm "{path_filesystem}/{xx}"\n')
    connection.close()



# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()


