#!/usr/bin/python
# -*- coding:utf-8 -*-
"""after having imported the works into calibre AND imported the custom columns, run this script to populate the custom columns with the AO3 tags and data
for a calibre book folder, created from an AO3 .epub file, parse the metadata in the beginning of the work toward calibre readable metadata in the metadata.opf"""

import os, zipfile, re, codecs
from bs4 import BeautifulSoup
import sqlite3

custom_tags=True #Wether you want to add my custom tags, such as adding the tag "brick" if there is 10k words or more. True to add the tags, False to only keep the original tags

short_fandom={} #each character name is formatted as fandom.character, for example Avatar : The Last Airbender.Zuko This might be too verbose to your liking. Use this dictionnary to define a short name for a fandom. For example if you define short_fandom["Avatar : The Last Airbender"]="ATLA" Zuko will be named "ATLA.Zuko". No correction is performed on the long name, so be careful to type it exactly as it is. This has no effect on the metadata "fandom"
short_fandom["Avatar: The Last Airbender"]="ATLA" #example
short_fandom["The Legend of Korra"]="LoK"

brick_thresold=10000 #how many words are needed to add the tag "brick"

test_file="/home/ezi/Dropbox/save/lecture - fics/calibre_library/Sy_Itha/Conflict Resolution (15)/Conflict Resolution - Sy_Itha.epub"
#must be the file already imported into calibre, with the column already created, but with empty values
test_metadata_file="/home/ezi/Dropbox/save/lecture - fics/calibre_library/Sy_Itha/Conflict Resolution (15)/metadata.opf"



#read and parse metadata from the AO3 header
metadata={}
metadata["genre"]="fiction.fanfiction" #I like to put all my fanfiction in this sub-genre. you can change the value at will
metadata["read"]="New" #All fics read status will be "new". you can change this to "On it" or "Read" if you prefer. mind the capital.

with zipfile.ZipFile(test_file) as z:
	with z.open("OEBPS/preface.xhtml") as f :
		html=f.readlines()
		html="\n".join(html)
		soup=BeautifulSoup(html,"lxml")

		#work ID
		uri=soup.findAll("a")[1]["href"]
		uri=re.sub("download\.","",uri)

		#metadata
		informations = soup.findAll("div", { "class" : "meta" })[0]
		title=soup.findAll("h1")[0].getText() #used to find the work in the library
		info_text=informations.getText()


		#parsing
		rating=re.findall("Rating:\n(.*?)\n",info_text)[0]
		fandom=re.findall("Fandom:\n(.*?)\n",info_text)[0]
		characters=re.findall("Character:\n(.*?)\n",info_text)[0]
		characters=characters.split(",")
		tags=re.findall("Additional Tags:\n(.*?)\n",info_text)[0]
		tags=tags.split(",")
		word_count=re.findall("Words: (\d+)",info_text)[0]
		chapters=re.findall("Chapters: (.*?)\n",info_text)[0]
		#series informations
		#pairings
		#bonus tags (brick,polyamory)

		#formatting
		if rating=="Not Rated":
			metadata["content_rating"]=""

		metadata["fandom"]=fandom
		formatted_characters=[]
		for chara in characters:
			fd=metadata["fandom"]
			if fd in short_fandom:
				fd=short_fandom[fd]
			fd=re.sub("\."," ",fd) #to avoid bugs with the hierarchical structure
			chara=chara.strip()
			chara=chara.title()
			chara=re.sub("\."," ",chara) #to avoid bugs with the hierarchical structure
			chara=fd+"."+chara
			if False:
				chara="&quot;"+chara+"&quot;"
			formatted_characters.append(chara)
		#formatted_characters=",".join(formatted_characters)
		#formatted_characters="["+formatted_characters+"]"
		metadata["characters"]=formatted_characters
		
		chapters=chapters.strip()
		chapters=chapters.split("/")
		if chapters[1]=="?" or chapters[1]!=chapters[0]:
			metadata["status"]="ongoing"
		else:
			metadata["status"]="completed"

		metadata["tags"]=[]
		for tag in tags:
			tag=tag.strip()
			metadata["tags"].append(tag)

		if custom_tags==True and int(word_count)>brick_thresold:
			metadata["tags"].append("brick")
		metadata["word_count"]=word_count
		

		#print metadata




#edit the calibre metadata file (metadata.opf
if False:
	with codecs.open(test_metadata_file,"r","utf-8") as fin, codecs.open(test_metadata_file+"_new","w","utf-8") as fout:
			for l in fin:
				match=re.match('\s+<meta name="calibre:user_metadata:#(.*?)"',l)
				if match:
					
					#get the type and value of the metadata
					data_type=match.group(1)
					try:
						data_value=metadata[data_type]
					except KeyError:
						data_value=""


					match2=re.search("&quot;#value#&quot;:(.*?), &quot;category_sort&quot;:",l)
					if match2:
						l_modified=l[:match2.start(1)]+data_value+l[match2.end(1):]
						if data_type in["characters","read"]:
							fout.write(l_modified)
						else:
							fout.write(l)
					else:
						fout.write(l)


				else: #not a line we need to change
					fout.write(l)


#edit the database

db=sqlite3.connect("calibre_library/metadata.db")
cursor=db.cursor()

#find the book id
cursor.execute("SELECT book,val FROM identifiers WHERE type='uri'")
rows=cursor.fetchall()
for r in rows:
	if r[1]==uri:
		id_=str(r[0])

#find the value id

cursor.execute("SELECT * FROM books_custom_column_6_link WHERE id="+id_)
rows=cursor.fetchall()
if rows:
	#update
	print rows
	pass
else:
	#insert
	print "fioefh"
	cursor.execute("INSERT INTO books_custom_column_6_link (book,value) VALUES(?,?)",(id_,1))


db.commit()


