import numpy
import refextract
import argparse
import requests
import Levenshtein
import hist
import os


## Get REFS from file - refextract (crossref)
def get_refs_from_file_refextract(filename, reference_search_mode="year_n_symbols"):
    
    ref_info=refextract.extract_references_from_file(filename, reference_search_mode=reference_search_mode)

    return ref_info

## given a raw reference string, extract doi information
def find_doi_from_raw(raw_string):

    splits_1=raw_string.split(" ")

    for s in splits_1:
        splits_2=s.split(",")

        for s2 in splits_2:
            if(len(s2)>7):
                if(s2[:4]=="doi:"):
                    print "DOI in first letters"
                    return s2[4:]
                if(s2[:3]=="10." and s2[7]=="/"):
                    return s2

    return None

## given a raw string, extract arxiv information
def find_arxiv_from_raw(raw_string):

    splits_1=raw_string.split(" ")

    for s in splits_1:
        splits_2=s.split(",")

        for s2 in splits_2:
            if(len(s2)>8):
                s2low=s2.lower()
                
                ## if last item is a ".", remove it
                if(s2low[-1]=="."):
                    s2low=s2low[:-1]

                ## typical situation: arXiv:XXXX, commma is separator
                if(s2low[:6]=="arxiv:"):
                    arxiv_string=s2low[6:]
                    return arxiv_string

                ## new identifier after 2007 xxxx.xxxx(x)
                if(s2low[4]=="."):
                    if(s2low[:4].isdigit() and s2low[5:].isdigit()):
                        return s2low

                ## old identifier before 2007 YY(VAR)/xxxxxxx (7 digits after /
                if(len(s2low)>7):
                    if(s2low[-8]=="/"):
                        if(s2low[-7:].idigit()):
                            return s2low

    return None


## crossref api to extract reference information from certain info strings or raw string
def return_crossref_info(author_list=None, title=None, year=None, doi=None, raw=None, rows=3):

    req_string="https://api.crossref.org/works?"
    select_string="select=title,DOI,author,published-print,published-online,reference,link,publisher,volume,short-container-title,page,references-count&sort=score&"
    #select_string="sort=score&"

    if(raw is not None):
        
        req_string+="query=%s"%raw.replace(" ", "+")+"&"#"&rows=3&"+"query.author="+author_list[0].replace(" ", "+")+"&"+select_string
        #items=requests.get(req_string).json()["message"]["items"]
        
        #return items

    if(author_list is not None):
        if(len(author_list)==1):
            req_string+="query.author="+author_list[0].replace(" ", "+")+"&"
        else:   
            req_string+="+".join([a.replace(" ", "") for a in author_list])+"&"

    if(title!=None):
        req_string+="query.title=%s&" % title.replace(" ", "+")

    filter_str=""
    filter_list=[]

    if(year!=None):
        if(type(year)==list):
            year=year[0]
            
        
        filter_list.append("until-pub-date:%d" % (int(year)+1))
        filter_list.append("from-pub-date:%d" % (int(year)-1))
        
    if(doi!=None):
        filter_list.append("doi:%s" % doi)

    if(len(filter_list)>0):
        filter_str="filter="+",".join(filter_list)+"&"
        req_string+=filter_str


    
    req_string+=select_string

    req_string+="rows=%d" % rows

    print "------------"
    print "CROSSREF GET -> ", req_string
    print " --------------- "
    print "RAW ", raw

  
    items=requests.get(req_string).json()

    #print items
    
    return items["message"]["items"]


def return_semantic_scholoar_info(search_str):

    req_string="api.semanticscholar.org/v1/paper/%s" % search_str

    res=requests.get(req_string).json()

    print res

def calc_relative_levensthein(str1, str2):

    return float(Levenshtein.distance(str1, str2))/(0.5*(float(len(str1)+len(str2))))
def crossmatch_refextract_refs(refs1, refs2, filename):


    def check_item_with_existing_list(new_item, new_item_index, check_list):
        found=False
        matched_this_ind=False
        for ind, check_item in enumerate(check_list):
            match_distance=calc_relative_levensthein(new_item["raw_ref"][0], check_item["raw_ref"][0])

            if(match_distance<0.3 or ((match_distance < 0.6) and (new_item_index == 0))):
                found=True
                matched_this_ind=True
                if(len(new_item.keys())>len(check_item.keys())):

                    check_list[ind]=new_item
                    
                    break
        return found, matched_this_ind
                ## either replace the match or do nothing
    ## three lists
    trailing_list_1=[]
    trailing_list_2=[]
    matched_list=[]

    ## crossmatches references based on reference similarity

    rel_distances=[]
    for ind1, r1 in enumerate(refs1):
        matched_this_ind=False
        for ind2, r2 in enumerate(refs2):
            relative_distance=calc_relative_levensthein(r1["raw_ref"][0], r2["raw_ref"][0])
            rel_distances.append(relative_distance)


            if(relative_distance < 0.3 or ( (relative_distance < 0.6) and (ind1 == 0))):
                found=False

                found,matched_this_ind=check_item_with_existing_list(r1, ind1, matched_list)
                
                if(found==False):
                    ## ok append r1 as a new match
                    
                    matched_list.append(r1)
                    matched_this_ind=True
                    break
        if(not matched_this_ind):
            found, matched_this_ind=check_item_with_existing_list(r1, -1, trailing_list_1)
            if(not found):
                trailing_list_1.append(r1)

    ## now the other way around
    rel_distances=[]
    for ind2, r2 in enumerate(refs2):
        matched_this_ind=False
        for ind1, r1 in enumerate(refs1):
            relative_distance=calc_relative_levensthein(r2["raw_ref"][0], r1["raw_ref"][0])
            rel_distances.append(relative_distance)
            if(relative_distance < 0.3 or ( (relative_distance < 0.6) and (ind2 == 0))):
                found=False
                found, matched_this_ind=check_item_with_existing_list(r1, ind2, matched_list)
                if(found==False):
                    ## ok append r2 as a new match
                    
                    matched_list.append(r2)
                    matched_this_ind=True
                    break
        if(not matched_this_ind):
            found, matched_this_ind=check_item_with_existing_list(r2, -1, trailing_list_2)
            if(not found):
                trailing_list_2.append(r2)
    ## check if trailing 1 are strict subsets of trailing 2 .. if so .. take the subset
    new_trailing_list_1=[]
    new_trailing_list_2=[]

    """
    for tr1 in trailing_list_1:
        found_subset=False
        for tr2 in trailing_list_2:
            if(tr1["raw_ref"][0] in tr2["raw_ref"][0]):
                print "tr1 subset of tr2 ...  "
                print " TR1 "
                for k in tr1.keys():
                    print k, " : ", tr1[k]

                print "TR 2 "
                for k in tr2.keys():
                    print k, " : ", tr2[k]
                found_subset=True
                matched_list.append(tr1)
                break
        if(found_subset==False):
            new_trailing_list_1.append(tr1)
    
    for tr2 in trailing_list_2:
        found_subset=False
        for tr1 in trailing_list_1:
            if(tr2["raw_ref"][0] in tr1["raw_ref"][0]):
                print tr2["raw_ref"][0]
                print " found in ... "
                found_subset=True
                matched_list.append(tr2)
                print tr1["raw_ref"][0]
                break
        if(found_subset==False):
            new_trailing_list_2.append(tr2)
    """

    print "matches ..", len(matched_list), matched_list
    print "trailing 1 / 2 lens ", len(new_trailing_list_1), len(new_trailing_list_2)
    print trailing_list_2

    #h=hist.hist("r", r=rel_distances)
    #h.plot(save_as="rel_distances_%s.png" % os.path.basename(filename),title="%d smaller 0.2 " % ((numpy.array(rel_distances)<0.2).sum()))

    return matched_list,trailing_list_1, trailing_list_2
                

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("fname")
    parser.add_argument("-search_mode", default="standard")

    arguments= parser.parse_args()

    search_mode="standard"
    if(arguments.search_mode=="multi"):
        search_mode="year_n_symbols"

    refs1=get_refs_from_file_refextract(arguments.fname, reference_search_mode="standard")
    refs2=get_refs_from_file_refextract(arguments.fname, reference_search_mode="year_n_symbols")
    
    matches, trailing1, trailing2=crossmatch_refextract_refs(refs1, refs2, arguments.fname)

    ## TODO - do the same with inverse year logic to catch papers which start with the year


    n_definite=0
    for r in refs:
        author_list=None
        title=None
        year=None

        raw_string=r["raw_ref"][0].replace("&", "")

        doi_str=find_doi_from_raw(raw_string)

        if(doi_str!=None):
            res=return_crossref_info(doi=doi_str)

            if(len(res)==1):
                print "yes sucessful! ", doi_str
                n_definite+=1

                continue
        arxiv_str=find_arxiv_from_raw(raw_string)
        if(arxiv_str!=None):
            if(arxiv_str!=None):
                print "yes sucessful! ", arxiv_str
                n_definite+=1

                if(arxiv_str[-1]=="."):
                    print "RAW : ", raw_string

                continue


                

        if(r.has_key("author")):
            author_list=r["author"]

        if(r.has_key("year")):
            year=r["year"]

        res=return_crossref_info(year=year, author_list=author_list, title=title, raw=raw_string)

        print "LEN RESULT LIST : ", len(res)
        if(len(res)>0):
            for ind_r, rr in enumerate(res):
                print "-----------------"
                print ind_r

                
                if(rr.has_key("short-container-title")):
                    print rr["short-container-title"]
                if(rr.has_key("published-print")):
                    print res[ind_r]["published-print"]
                elif(rr.has_key("published-online")):
                    print res[ind_r]["published-online"]
                else:
                    print "no publication date!!! weird"

                if(rr.has_key("published-print") and rr.has_key("published-online")):
                    print "PUBLISHED BOTH ONLINE and PRINT! ", res[ind_r]["published-print"], res[ind_r]["published-online"]
                if(rr.has_key("volume")):
                    print "vol .. ", rr["volume"]

                if(rr.has_key("page")):
                    print "page .. ", rr["page"]
                if(rr.has_key("title")):
                    print "title .. ", rr["title"]
                print "ref count .. ", rr["references-count"]
                print "-----------------"

                break
         



    print " num refs .. ", len(refs)
    print "NDEFINITE resolved ", n_definite





