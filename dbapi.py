import pymysql


def get_connection(config,database):
    try:

        myhost = config[database]['server']
        myport = int(config[database]['port'])
        myuser = config[database]['user']
        mypasswd = config[database]['pass']
        mydb = config[database]['database']

        connection = pymysql.connect(
            host=myhost,
            port=myport,
            user=myuser,
            passwd=mypasswd,
            db=mydb,
            connect_timeout=31536000,
        )

        cursor = connection.cursor()
        cursor.execute("select database();")
        res=cursor.fetchone()

        return connection
    except ValueError as ex:
        sqlstate = ex.args[0]
        errmsg="Database connection error: %s" % sqlstate
        raise Exception(errmsg).with_traceback(ex.__traceback__) from None
    except Exception as ee:
        errmsg="unknown Database connection error"
        raise Exception(errmsg).with_traceback(ee.__traceback__) from None

def close_connection(connection):
    try:
        connection.close()
    except:
        pass