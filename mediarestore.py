import logging, sys, os, datetime
import configparser as cfg
import dbapi

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




def main():
    get_source_media()

def get_source_media():
    connection = dbapi.get_connection(config, "Database")
    with connection.cursor() as cursor:
        cursor.execute("""SELECT
	m.mid,
	m.uuid,
    mfmi.field_media_image_target_id
FROM
	media m -- join media_field_data mfd on m.mid=mfd.mid
	JOIN media__field_media_image mfmi ON m.mid = mfmi.entity_id 
	AND mfmi.bundle = 'image'
WHERE
	m.mid>=100000""")
        results = cursor.fetchall()
        for result in results:
            mid=result[0]
            uuid=result[1]
            fileid=result[2]
            get_target_media_by_file_id(fileid,uuid,mid)
            pass

def get_target_media_by_file_id(fileid,source_uuid,source_mid):
    connection = dbapi.get_connection(config, "Database3")
    with connection.cursor() as cursor:
        cursor.execute(f"""SELECT
    	m.mid,
    	m.uuid,
        mfmi.field_media_image_target_id
    FROM
    	media m -- join media_field_data mfd on m.mid=mfd.mid
    	JOIN media__field_media_image mfmi ON m.mid = mfmi.entity_id 
    	AND mfmi.bundle = 'image'
    WHERE
    	mfmi.field_media_image_target_id={fileid} and m.mid>=100000""")

        results = cursor.fetchall()
        if results==None or len(results)<1:
            return

        if len(results)>1:
            logging.error(f"more than one file for source mid: {source_mid}, fileid: {fileid}")
            return

        result=results[0]
        mid=result[0]
        uuid=result[1]
        fileid=result[2]
        if(uuid!=source_uuid):
            logging.info(f"processing fileid: {fileid} - source mid: {source_mid} uuid: {source_uuid} - target mid: {mid}, uuid: {uuid}")
            update_target_uuid(mid,source_uuid,connection)

def update_target_uuid(mid,uuid,connection):
    with connection.cursor() as cursor:
        cursor.execute(f"update media set uuid='{uuid}' where mid={mid}")
        connection.commit()


if __name__ == '__main__':
    logging.basicConfig(
        level=ilog_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(f"report/mediarestore-{nowtime}.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    main()
