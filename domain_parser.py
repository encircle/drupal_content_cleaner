import time
import dbapi
import logging as log



def get_domain_taxonomy_ids(config):

    taxonomy_ids={}
    connection = dbapi.get_connection(config, "Database")
    with connection.cursor() as cursor:
        cursor.execute("select tid,name from taxonomy_term_field_data where vid='domain'")
        result = cursor.fetchall()
        for record in result:
            key=record[1].lower().replace(" ","")
            taxonomy_ids[key]={"tid":record[0],"name":record[1]}
    return taxonomy_ids
def get_target_nodes(config):
    existing_nodes=set()
    connection = dbapi.get_connection(config, "Database")
    with connection.cursor() as cursor:

        cursor.execute("select nid from node")
        result = cursor.fetchall()
        for record in result:
            existing_nodes.add(record[0])
    return existing_nodes


def parse_domains(config):

    existing_nodes=get_target_nodes(config)
    taxonomy_ids=get_domain_taxonomy_ids(config)
    connection=dbapi.get_connection(config,"Database2")


    node_table=parse_domain_access(connection)
    parse_domain_source(connection,node_table,config)

    del_keys = []
    for key, node in node_table.items():
        domains = node["domains"]
        if "www.permaculture.org.uk" in domains:
            del_keys.append(key)

    for key in del_keys:
        node_table.pop(key)

    with open("./report/node_domain_list.csv", "w") as fw:
        fw.write("node id,node title,node type,domain source,domain access,domains\n")
        for key, node in node_table.items():
            nid=node['id']
            if not nid in existing_nodes:
                continue
            domains=",".join(node["domains"])
            mydomains=list(node["domains"].keys())
            process_node_domains(nid,mydomains,taxonomy_ids,config)
            ntitle=node['title']
            ntype=node['type']
            domain_access = node['domain-access']
            domain_source = node['domain-source']
            ntype = node['type']
            fw.write(f'"{nid}","{ntitle}","{ntype}","{domain_source}","{domain_access}","{domains}"\n')


def process_node_domains(nid,domains,taxonomy_ids,config):
    domainkeys=[]

    connection = dbapi.get_connection(config, "Database")

    for dom in domains:
        domainkeys.append(dom.split(".",1)[0])

    for dom in domainkeys:
        if dom in taxonomy_ids:
            tax_id=taxonomy_ids[dom]['tid']

            try:

                with connection.cursor() as cursor:
                    cursor.execute(f"select count(*) from taxonomy_index where tid={tax_id} and nid={nid}")
                    result=cursor.fetchall()
                    if(result[0][0]<1):
                        log.info(f"adding nid:{nid} to taxonomy:{dom} - id:{tax_id}")
                        cursor.execute(f"insert into taxonomy_index (nid,tid,status,sticky,created) values({nid},{tax_id},1,0,{int(time.time())})")
                        connection.commit()
                    else:
                        log.info(f"nid: {nid} already in taxonomy:{dom} - id:{tax_id}")



            except Exception as ex:
                log.error(f"failed to add node: {nid} to domain: {dom}")
        else:
            #log.info(f"nondom nid:{nid} for taxonomy:{dom}")
            pass




def parse_domain_source(connection,node_table,config):
    with connection.cursor() as cursor:
        query = f"""select n.nid,n.title,n.type,dom.* from node n
    join domain_source dom_src on n.nid=dom_src.nid
    join domain dom on dom_src.domain_id=dom.domain_id
    where dom_src.domain_id>=0
            """
        cursor.execute(query)
        while record := cursor.fetchone():
            log.info(record)
            nid=record[0]
            ntitle=record[1]
            ntype=record[2]
            ndomainid=record[3]
            ndomain=record[4]

            if nid in node_table:
                node = node_table[nid]
                node["domain-source"]=True
            else:
                node = {
                    "domains": {},
                    "domain-source": True,
                    "domain-access": False
                }
                node_table[nid] = node

            node["id"] = nid
            node["title"] = ntitle.replace("\"","\"\"")
            node["type"] = ntype
            node["domains"][ndomain] = ndomainid





def parse_domain_access(connection):
    node_table={}

    with connection.cursor() as cursor:
        query = f"""select n.nid,n.title,n.type,dom.* from node n
join domain_access dom_acc on n.nid=dom_acc.nid and dom_acc.realm='domain_id'
join domain dom on dom_acc.gid=dom.domain_id
order by n.nid
            """
        cursor.execute(query)
        while record := cursor.fetchone():
            #log.info(record)
            nid=record[0]
            ntitle=record[1]
            ntype=record[2]
            ndomainid = record[3]
            ndomain=record[4]

            if nid in node_table:
                node=node_table[nid]
            else:
                node={
                    "domains":{},
                    "domain-source":False,
                    "domain-access":True
                }
                node_table[nid]=node

            node["id"]=nid
            node["title"] = ntitle.replace("\"","\"\"")
            node["type"] = ntype
            node["domains"][ndomain]=ndomainid



    return node_table