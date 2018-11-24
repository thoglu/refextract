#! /usr/bin/python

import getopt, re, urllib,numpy, argparse, os, shutil, subprocess,commands, glob

import urllib2, gzip

def get_bibitems(text_chunk):
    print "asd"

def obtain_src_n_return_refs(arxiv_id):
    rnd=numpy.random.uniform()
    tmp_path="temp_%.10f"%rnd
    os.makedirs(tmp_path)
    print ".. generated tmpdir ", tmp_path
    

    print "retrieving src for ", arxiv_id
    dest_filename=os.path.join(tmp_path, arxiv_id.split("/")[-1])


    headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
           'Accept-Language': 'en-US,en;q=0.5',
           'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0'}

    req = urllib2.Request('https://arxiv.org/e-print/' + arxiv_id, headers=headers)
    
    response=urllib2.urlopen(req)

    encoding="standard"
    if "gzip" in response.info().get('Content-Encoding'):
        encoding="gzip"
        dest_filename=dest_filename
    
        result=urllib.urlretrieve('https://arxiv.org/e-print/' + arxiv_id, dest_filename+".gz")
        commands.getstatusoutput("gunzip %s" % (dest_filename+".gz"))
    else:
        result=urllib.urlretrieve('https://arxiv.org/e-print/' + arxiv_id, dest_filename)

    #ok_flag=commands.getstatusoutput("gzip -t %s && echo ok || echo bad" % dest_filename)[1]

    #if(ok_flag=="ok"):
    
    res=commands.getstatusoutput("tar -xzf %s -C %s" % (dest_filename, tmp_path))
    if(len(res[1])>0):
        print "tar extract failed (no tar.gz) .. try tar .."
        res=commands.getstatusoutput("tar -xf %s -C %s" % (dest_filename, tmp_path))
        
    is_texfile=True
    fname=dest_filename

    if(len(res[1])==0):
        print " we got a tar file"
        bbl_files=glob.glob(os.path.join(tmp_path, "*.bbl"))
        if(len(bbl_files)==1):
            fname=bbl_files[0]
            is_texfile=False
        else:
            tex_files=glob.glob(os.path.join(tmp_path, "*.tex"))
            for ind, tex_file in enumerate(tex_files):
                f=open(tex_file, "r")
                block=f.read()
                f.close()
                if("bibitem" in block):
                    fname=tex_files[ind]
                    break

    else:
        print "it was a normal tex file.."
        

    print "IDENTIFY FILE ", fname
    print "TEX FILE: ", is_texfile

    f=open(fname, "r")
    block=f.readlines()
    f.close()

    if(not os.path.exists("tex_bbl_files")):
        os.makedirs("tex_bbl_files")

    commands.getstatusoutput("cp %s tex_bbl_files/%s.txt" % (fname, arxiv_id))
    
    shutil.rmtree(tmp_path)

    return block

def count_refs_amstex(block):

    bibitems=[]

    began_comment=False
    cur_block=[]
    found_ref_section=False
    running_block=False


    for l in block:

        if(l[:5]=="\\Refs" ) :
            found_ref_section=True
       
        if(found_ref_section):
            if("egin{comment}" in l):
                began_comment=True
            if("end{comment}" in l):
                began_comment=False

         
            if(not began_comment):
                

                if("\\ref" in l):
                    running_block=True
                    continue

                if(running_block):
                    if("\\endref" in l):
                        bibitems.append(cur_block)
                        running_block=False
                        cur_block=[]
                    else:

                        if(l[0]!="%"):
                            
                            cur_block.append(l)
        
  
    return bibitems

    

def count_refs(block):

    bibitems=[]

    began_comment=False
    cur_block=[]
    found_ref_section=False
    running_block=False

    

    for l in block:

        if(("begin{thebibliography}" in l.lower()) or ("begin{references" in l.lower())):
            found_ref_section=True
        #else:
        #    print "not found ..", l.lower()

        if(found_ref_section):
            if("egin{comment}" in l):
                began_comment=True
            if("end{comment}" in l):
                began_comment=False

         
            if(not began_comment):
                

                if("bibitem" in l):
                    if(l[0]=="%"):

                        if(running_block):
                            bibitems.append(cur_block)
                            cur_block=[]
                            running_block=False
                    else:
                        if(running_block):
                            bibitems.append(cur_block)
                            cur_block=[]
                        cur_block.append(l)
                        running_block=True
                else:
                    if( ("end{thebibliography" in l.lower()) or ("end{references" in l.lower())):
                        if(running_block):
                            bibitems.append(cur_block)
                            break
                    else:
                        if(running_block):
                            cur_block.append(l)

                    
    if(len(bibitems)==0):
        ## try amstex
        bibitems=count_refs_amstex(block)

    withdrawn=False
    if(len(bibitems)==0):
        for l in block:
            if("submission has been withdrawn" in l):
                ## OK HAs BEEN WITHDRAWN
                withdrawn=True



    return bibitems, withdrawn



if(__name__=="__main__"):


    parser=argparse.ArgumentParser()

    parser.add_argument("-id", default="0806.0043")
    parser.add_argument("-range", default="")

    arguments=parser.parse_args()

    if(arguments.range!=""):
        for r in numpy.arange(1, 200):
            new_id="0806.%.4d" % r
            block=obtain_src_n_return_refs(new_id)  
            bibitems, withdrawn=count_refs(block)
            if(not withdrawn):
                print r, " ... num refs .. ", len(bibitems)

                if(len(bibitems)<1):
                    print "HM?"
                    exit(-1)