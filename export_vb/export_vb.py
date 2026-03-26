import binascii,os
from distutils.dir_util import copy_tree
import parse_ini,parse_fmt
import pprint
asset_path = "./asset/"
mod_path = "./mods/"
output_path = "./output/"

class Custom_mod(object):
    # ib_files = []

    def __init__(self,modfolder):      

        self.mod_name = modfolder
        self.mod_ini = parse_ini.ini_parser(modfolder)
        self.vb , self.ib_files = self.mod_ini.collect_self_fmt()
        self.totalstr = self.mod_ini.totalstr
        self.complete_export()
    
    def export_fmt(self):
        for ibs in self.ib_files:
            outputpwd = self.ib_files[ibs]['location'].replace(mod_path,output_path)
            print(f"[DEBUG] parse_vb0 호출: 이름={ibs.replace('.ib','')}, 경로={outputpwd}")
            parse_fmt.fmt_parser().parse_vb0(ibs.replace(".ib",""),outputpwd)
            print(f"[DEBUG] parse_vb0 호출 완료")
            ibfile = os.path.join(outputpwd,ibs.replace(".ib",".fmt"))
            if os.path.exists(ibfile):
                with open(ibfile,"r") as exfmt:
                    f = exfmt.readlines()
                with open(ibfile,"w") as fmt:
                    fmt.writelines("stride: "+str(self.mod_ini.searchStride(ibs.replace(".ib",""))))
                    fmt.writelines("\ntopology: trianglelist\nformat: "+self.ib_files[ibs]['format']+"\n")
                    fmt.writelines(f)
            else:
                print("Loding Error : "+ ibs)
    def export_vbs(self):
        for ibs in self.ib_files:
            location = backup_mod_folder(self.ib_files[ibs]['location'])
            filename = self.ib_files[ibs]['filename'].replace(".ib",".vb")
            filepwd = os.path.join(location,filename)
            with open(filepwd, "wb") as b:
                b.write(self.mod_ini.searchVB(ibs.replace(".ib","")))
            # with open(filepwd, "wb") as b:
            #    data = self.mod_ini.searchVB(ibs.replace(".ib",""))
            #    if isinstance(data, str):
            #        data = data.encode()
            #    b.write(data)

    def complete_export(self):
        self.export_vbs()
        self.export_fmt()
        print(f"[{self.mod_name}]\t Complete")
    

def backup_mod_folder(path):
    location = path.replace(mod_path,output_path)
    folder_exists(location)
    copy_tree(path, location)
    return location

def folder_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
    
def check_mod_folder():
    for (root, directories, files) in os.walk(mod_path):
        
        for file in files:
            if os.path.splitext(file)[1] == ".ini":
                if (file != "merged.ini"):
                    file_path = os.path.join(root, file)
                    # print(file_path + "is Found")
                    Custom_mod(file_path)
                    # ini_parser(file_path).parse_ini()
                    next

check_mod_folder()

