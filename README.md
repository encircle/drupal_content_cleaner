# Drupal Content Cleaner

**WARNING** this will make irreversible changes to your Drupal instance. Please, please take a back up of your Drupal database and your  `sites/default/files` directory.
You have been forwarned! No express warranty is implied - Encircle are not liable for any damage done.

## Overview



## Install
run the bash script  `./install.sh`
This will create the Python3 virtualenv (requires python3, pip and virtualenv). 

It will also create the config file config.ini

## Configure
Three files control the behaviour of the script

### File: config.ini
```
#Drupal MySQL Database connection
[Database]
server=localhost
database=www_drupal
port=3306
user=root
pass=pass

#Not currently plumbed in
# - this is a mysql db connection to a Drupal 7 instance with the domains module installed
# this is used to look at all node content and determine what nodes belong to domains other than the main domain
[Database2] 
server=localhost
database=www_drupal
port=3308
user=root
pass=pass


# the main app config
[AppConfig]

# url of the site to clean/audit
baseurl=https://www.somesite.org.uk

# local file path to drupal root directory for this instance
basedir=/path_to_localdrupal_installation

#top level domain that the site is ar
tld=somesite.org.uk

# if True - any links in the site that point to a subdomain will be converted to a relative link
# - Note www subdomain links will always be converted whether this value is True or False 
squash_subdomains=True

# check any links found in content - to make sure they are valid
check_links=True

#any external images in <img> tags in text content, will be downloaded to [DRUAPL_ROOT]/sites/default/files/external-images
# to an md5 hased path under this directory and `<img src=` attributes will be updated accordingly
scrapeexternalimages=True

#basic auth credentials for the site - if basic_auth=True
basic_auth=False
basic_auth_user=admin
basic_auth_pass=admin


[Logging]
level=info #standard python logger levels for run log gile
```
### File: field_config.json 

An array of fields to clean/audit textual content. All other fields are ignored
```
[
    {
        "table": "node__body",
        "table_rev": "node_revision__body",
        "field": "body_value",
        "entity_id": "entity_id",
        "entity_type": "node"
    },
]
    
```


`entity_type` can be `node` or `taxonomy` or `user` 

`table` is the database table for this field

`table_rev` is the database table for this fields revision history.

if `table_rev` is an empty string e.g. "" - don't attempt to update latest revision of content

`field` is the database column for the textual field value in the table

`entity_id` is the primary key in the database table. Should refer to the node or taxonomy id that the row in question belongs to.



### File: ignore_dirs.json

An array of directory paths (in `[DRUPAL_ROOT]/sites/default/files` to ignore.
Default file contains the usual suspects.
```
[
    "public://civicrm/",
    "public://javascript/",
    "public://external-images/",
    "public://css/",
    "public://js/",
    "public://php/",
    "public://styles/",
    "public://media-icons/generic",
    "public://video_embed_field_thumbnails",
    "public://oembed_thumbnails"
]
```


## Run
Run the bash script `run.sh`.
Go have a cup of tea whilst all your wonderful Drupal content is audited and cleaned.

## Outputs
Check out the `reports` directory for the run and audit logs

### Run Log File: reports/debug-{some-timestamp).log
This is the scripts main log.

### Audit Log File: reports/files_external_error.csv
Spreadsheet that lists all external image file references in content that cannot be downloaded 

### Audit Log File: reports/files_in_d7_tags.csv
Spreadsheet that lists any entities that contain the old Drupal 7 media entities tags

### Audit Log File: reports/files_not_present.csv
Spreadsheet that lists all files registered in Drupal that do not exist on the file syste,

### Audit Log File: reports/files_not_registered.csv
Spreadsheet that lists all files in `[DRUPAL_ROOT]/sites/default/files` that are not registered in Drupal.

Note that the `ignore_dirs.json` config file applies here.

### Audit Log File: reports/files_not_registered_content.csv
Spreadsheet that lists all the files in `[DRUPAL_ROOT]/sites/default/files` that are referenced in text field content but not registered in Drupal.

### Audit Log File: reports/files_registered_unused.csv
Spreadsheet that lists all the files in `[DRUPAL_ROOT]/sites/default/files` that are registered in Drupal but are not reference anywhere on the site. i.e. in textual content, or in any other fields.

Note that the `ignore_dirs.json` config file applies here.

### Audit Log File: reports/files_url_error.csv
Spreadsheet that lists all external hyperlinks that are no longer valid
