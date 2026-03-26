import os,shutil
path = "./asset/"
class fmt_parser(object):
    def parse_vb0(self,filename,location):
        # print(filename.replace(".ib",""))
        for root, dir, files in os.walk(path):
            for file in files:
                if os.path.splitext(file)[1] == ".txt" and "vb0" in os.path.splitext(file)[0]:
                    if filename in file:
                        exfmtname = file.split('-')[0] + ".fmt"
                        linenum = 0

                        f = open(root+"/"+file)
                        exfmt = open(location+"/"+exfmtname,"w")
                        shutil.copy(os.path.join(root,"hash.json"),os.path.join(location,"hash.json"))
                        for line in map(str.strip,f):
                            if line.startswith('element['):
                                exfmt.write(line+"\n")
                                linenum = 7
                                continue
                            if linenum == 0:
                                continue
                            exfmt.write("  "+line+"\n")
                            linenum = linenum -1
                        return 

# fmt_parser().parse_vb0()