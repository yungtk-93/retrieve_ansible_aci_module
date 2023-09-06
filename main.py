import paramiko
import re
import yaml
import json5
from stat import S_ISDIR, S_ISREG

def connect_ssh(host, username, password):
    ssh = paramiko.client.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, password=password)
    return ssh

def disconnect_ssh(ssh):
    ssh.close()

def retrieve_aci_modules(yaml):
    aci_regex = re.compile(".*?aci+.*")
    aci_tasks = []
    for item in yaml:
        if "tasks" in item:
            tasks = item['tasks']
            for task in tasks:
                task_keys = list(task.keys())
                for key in task_keys:
                    if aci_regex.search(key)!=None:
                        if key == 'aci_rest': 
                            rest_content = json5.loads(task['aci_rest']['content'])
                            key+=' | '+task['aci_rest']['path']+' | '+list(rest_content.keys())[0]
                        aci_tasks.append(key)
    if len(aci_tasks)>0:
        return aci_tasks
    return False
                

if __name__ == '__main__':
    host = "ansible-mfg-dev.intel.com"
    username = "XXXXX"
    password = "XXXXX"

    target_dir_path = "/ANSIBLE_DEVELOPMENT/MFG/ACI/factory_build"
    target_filename_regex = re.compile("^phase(\d)_+.*")

    #connect to ssh
    ssh = connect_ssh(host, username, password)
    sftp = ssh.open_sftp()
    entry_dict = sftp.listdir_attr(target_dir_path)

    #initialize data dictionary
    data = {}

    for entry in entry_dict:
        #check item is folder and match folder name regex
        if S_ISDIR(entry.st_mode) and target_filename_regex.search(entry.filename)!=None: 
            dir_path = target_dir_path+"/"+entry.filename
            child_dict = sftp.listdir_attr(dir_path)
            for child in child_dict:
                #check is yaml file
                if S_ISREG(child.st_mode) and (child.filename.endswith('.yml') or child.filename.endswith('.yaml')):
                    child_file_path = dir_path+"/"+child.filename
                    remote_file = sftp.open(child_file_path)
                    yaml_content = yaml.load(remote_file, Loader=yaml.Loader)
                    aci_modules_result = retrieve_aci_modules(yaml_content)
                    
                    if isinstance(aci_modules_result, list):
                        # data[entry.filename] = aci_modules_result
                        if entry.filename not in data:
                            data[entry.filename] = []
                        data[entry.filename].extend(aci_modules_result)

                    remote_file.close()

    if data:
        data = dict(sorted(data.items())) #sort by key ascending
        file = open("aci_module_list.txt", "a")
        for phase, modules in data.items():
            file.write(phase+"\n")
            for module in modules:
                file.write(module+"\n")
            file.write("\n")
        file.close()
    disconnect_ssh(ssh)