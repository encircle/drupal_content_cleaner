import dbapi
import logging as log

def parse_domains(config):
    connection=dbapi.get_connection(config,"Database2")


    node_table=parse_domain_access(connection)
    parse_domain_source(connection,node_table)

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

            domains=",".join(node["domains"])
            nid=node['id']
            ntitle=node['title']
            ntype=node['type']
            domain_access = node['domain-access']
            domain_source = node['domain-source']
            ntype = node['type']
            fw.write(f'"{nid}","{ntitle}","{ntype}","{domain_source}","{domain_access}","{domains}"\n')


def parse_domain_source(connection,node_table):
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