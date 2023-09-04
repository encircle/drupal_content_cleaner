import filecmp, os
import json

og_dir="/var/encircle/docker/permaculture/drupal/sites/default/files"
target_dir="/var/encircle/docker/live-permaculture/drupal/site/web/sites/default/files"

#og_dir="/var/encircle/docker/pca-stage/drupal/site/test1"
#target_dir="/var/encircle/docker/pca-stage/drupal/site/test2"

ignore_dirs_raw=[]
with open("./ignore_dirs.json") as iff:
    ignore_dirs_raw=json.load(iff)

ignore_dirs=[]
for idir in ignore_dirs_raw:
    stripper=og_dir+"/"+idir.removeprefix("public://").strip("/")
    ignore_dirs.append(stripper)

missing_files=[]
ignoring_files=[]

def walk_cmp(cmp: filecmp.dircmp):
    for id in ignore_dirs:
        if id==cmp.left:
            return
    for left_only in cmp.left_only:
        left_only_abs=cmp.left+"/"+left_only
        if os.path.isdir(left_only_abs):
            continue
        if left_only_abs.endswith(".jpg") or left_only_abs.endswith(".jpeg") or left_only_abs.endswith(".png") or left_only_abs.endswith(".gif") or left_only_abs.endswith(".JPG"):
            right_target_abs= cmp.right + "/" + left_only
            missing_files.append("cp '"+left_only_abs+"' '"+right_target_abs+"'")
        else:
            ignoring_files.append(left_only_abs)

    if cmp.subdirs:
        for subdirname,subdirobj in cmp.subdirs.items():
            walk_cmp(subdirobj)




cmp=filecmp.dircmp(og_dir,target_dir)
cmp.report_full_closure()

walk_cmp(cmp)

with open("restore_files.sh","w") as f:
    for line in missing_files:
       f.write(line)
       f.write("\n")

with open("missing_files_ignored.log","w") as f:
    for line in ignoring_files:
       f.write(line)
       f.write("\n")


pass