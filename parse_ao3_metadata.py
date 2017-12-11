#!/usr/bin/python
# -*- coding:utf-8 -*-
"""after having imported the works into calibre AND imported the custom columns, run this script to populate the custom columns with the AO3 tags and data
for a calibre book folder, created from an AO3 .epub file, parse the metadata in the beginning of the work toward calibre readable metadata in the metadata.opf"""

import os, zipfile, re, codecs,sys
from bs4 import BeautifulSoup
import sqlite3

import_directory="calibre_library"

#here's a list of possible columns : tags, series_ao3, word_count, content_rating, read, status, category_relationships, fandom, genre, relationships, characters
columns_to_update=["tags","series_ao3","word_count","content_rating","read","status","category_relationships","fandom","genre","relationships","characters"] #add here all columns you want the script to update
columns_to_update=["relationships"] #add here all columns you want the script to update

custom_tags=True #Wether you want to add my custom tags, such as adding the tag "brick" if there is 10k words or more. True to add the tags, False to only keep the original tags

short_fandom={} #each character name is formatted as fandom.character, for example Avatar : The Last Airbender.Zuko This might be too verbose to your liking. Use this dictionnary to define a short name for a fandom. For example if you define short_fandom["Avatar : The Last Airbender"]="ATLA" Zuko will be named "ATLA.Zuko". No correction is performed on the long name, so be careful to type it exactly as it is. This dictionnary can also be used to put different things under the same name, for example the several "fullmetal alchemist" fandoms
short_fandom["Avatar: The Last Airbender"]="ATLA"
short_fandom["Avatar: Legend of Korra"]="LoK"
short_fandom["Fullmetal Alchemist"]="FMA"
short_fandom["Fullmetal Alchemist - All Media Types"]="FMA"
short_fandom["Fullmetal Alchemist (Anime 2003)"]="FMA"
short_fandom["Fullmetal Alchemist: Brotherhood & Manga"]="FMA"
short_fandom["Harry Potter - Rowling"]="HP"
short_fandom["Harry Potter - J. K. Rowling"]="HP"
short_fandom["Subarashiki Kono Sekai | The World Ends With You"]="TWEWY"
short_fandom["Tales of Symphonia"]="ToS"
short_fandom["Yuri!!! on Ice (Anime)"]="YoI"
short_fandom["Tsubasa: Reservoir Chronicle"]="Tsubasa"
shorten_fandom_itself=True #use the short name defined above for the metadata "fandom" itself

short_ship={} #use a shorten version of a character name in the relationship metadata. For example "HP.Draco Malfoy/Harry Potter" becomes "HP.Draco/Harry" or even "HP.Drarry". Enter only the name of the ship, without the fandom in front, like "Draco/Harry". This has no effect on the "character" metadata
short_ship["Draco Malfoy/Harry Potter"]="Draco/Harry"
short_ship["Sirius Black/Remus Lupin"]="Wolfstar"
short_ship["Christophe Giacometti/Katsuki Yuuri/Victor Nikiforov"]="Chris/Yuuri/Victor"

short_character={} #same as previously, but with only one character. For example if you have one character in ships with several other characters, you can add his name here to be shortened in all of his ships. Enter only the name of the character without the fandom, for example "Draco Malfoy" This has no effect on the "character" metadata
short_character["Christophe Giacometti"]="Chris"
short_character["Katsuki Yuuri"]="Yuuri"
short_character["Yuuri Katsuki"]="Yuuri"
short_character["Yuri Katsuki"]="Yuuri"
short_character["Victor Nikiforov"]="Victor"

brick_thresold=100000 #how many words are needed to add the tag "brick"

test_file="/home/ezi/Dropbox/save/lecture - fics/calibre_library/dance_across/After Everyone Else (2)/After Everyone Else - dance_across.epub"
#test_file="/home/ezi/Dropbox/save/lecture - fics/calibre_library/Sy_Itha/Conflict Resolution (15)/Conflict Resolution - Sy_Itha.epub"

global_genre="fiction.fanfiction" #I like to put all my fanfiction in this sub-genre. you can change the value at will
global_read_status="New" #All imported fics read status. you can set this to "New" "On it" or "Read" . mind the capital.

hierarchical_columns=["characters","relationships"] #characters and relationships can be hierarchical or not. don't add any other.


db=sqlite3.connect("calibre_library/metadata.db")
cursor=db.cursor()

#do not touch
custom_columns={}
custom_columns["word_count"]="1"
custom_columns["genre"]="2"
custom_columns["characters"]="3"
custom_columns["fandom"]="4"
custom_columns["relationships"]="5"
custom_columns["status"]="6"
custom_columns["read"]="7"
custom_columns["content_rating"]="8"
custom_columns["category_relationships"]="10"
custom_columns["series_ao3"]="12"
custom_columns["tags"]="tags" #put the non-custom columns in here, with data same as the key
#custom_columns["series"]="series"

rating_conversion={}
rating_conversion["Explicit"]="E"
rating_conversion["Mature"]="A"
rating_conversion["Teen And Up Audiences"]="T"
rating_conversion["General Audiences"]="G"
rating_conversion["Not Rated"]=""



def format_relationship(ship):
	#avoid duplicates due to different order
	#assumes that 3+ relationships have all the same separator (& or /)

	ship=re.sub(" - Relationship","",ship)
	separator=""
	if re.search("/",ship):
		separator="/"
	elif re.search("&",ship):
		separator="&"
	if separator:
		names=re.split("[/&]",ship)
		ship=[]
		for name in names:
			name=name.strip()
			name=format_character_name(name)
			if name in short_character:
				name=short_character[name]
			ship.append(name)
		ship.sort()
		ship=separator.join(ship)
	else:
		#weird formatting, do nothing
		pass
	if ship in short_ship:
		ship=short_ship[ship]
	return ship

def format_character_name(name):
	name=re.sub("\(.*?\)","",name) #delete parenthesis content, such as "Draco Malfoy (Harry Potter)"
	name=re.split("( )",name)
	#correct capitalisation
	for i,a in enumerate(name):
		if a !="'s":
			if len(a)>1:
				name[i]=a[0].upper()+a[1:]
			else:
				name[i]=a.upper()
	name="".join(name)
	name=name.strip()
	return name

def build_work_list(directory):
	list_=[]
	for root, dirs, files in os.walk(directory, topdown=False):
		for fname in files:
			if fname.endswith(".epub"):
				list_.append( os.path.join(root,fname) )
	return list_

def parse_ao3_metadata(epub_file):
	"""read and parse metadata from the AO3 header and return a dictionnary of found values
	epub_file argument must be the path+name of a .epub file inside the calibre directory. not the original .epub file"""
	
	metadata={}
	metadata["genre"]=global_genre
	metadata["read"]=global_read_status

	with zipfile.ZipFile(epub_file) as z:
		try:
			with z.open("OEBPS/preface.xhtml") as f :
				html=f.readlines()
				html="\n".join(html)
				soup=BeautifulSoup(html,"lxml")

				#work ID
				uri=soup.findAll("a")[1]["href"]
				uri=re.sub("download\.","",uri)

				#metadata
				informations = soup.findAll("div", { "class" : "meta" })[0]
				info_text=informations.getText()
		except KeyError:
			return False #not an AO3 file


		#parsing
		raw_data={}
		for data in ["Rating"]:
			try :
				raw_data[data]=re.findall(data+":\n(.*?)\n",info_text)[0]
			except IndexError:
				raw_data[data]=""
		for data in ["Fandom","Character","Relationship","Category","Additional Tags"]:
			try :
				s=re.findall(data+":\n(.*?)\n",info_text)[0]
				s=s.split(",")
				s=[x.strip() for x in s]
				raw_data[data]=s
			except IndexError:
				raw_data[data]=""

		word_count=re.findall("Words: (\d+)",info_text)[0]
		try:
			chapters=re.findall("Chapters: (.*?)\n",info_text)[0]
		except IndexError:
			chapters="1/1"

		series_match=re.findall("Series:\nPart (\d+) of\n\n(.*?)\n",info_text)
		if series_match:
			raw_data["series_n"],raw_data["series"]=series_match[0]
		else:
			raw_data["series"]=False
			raw_data["series_n"]=False


		#formatting
		metadata["content_rating"]=rating_conversion[raw_data["Rating"]]
		
		metadata["category_relationships"]=raw_data["Category"]
		metadata["word_count"]=word_count
		if raw_data["series"]:
			metadata["series_ao3"]=re.sub("[\.,']"," ",raw_data["series"])
		else:
			metadata["series_ao3"]=False
		metadata["series_number"]=raw_data["series_n"]


		if shorten_fandom_itself:
			metadata["fandom"]=[]
			for item in raw_data["Fandom"]:
				if item in short_fandom:
					metadata["fandom"].append(short_fandom[item])
				else:
					metadata["fandom"].append(item)
		else:
			metadata["fandom"]=raw_data["Fandom"]

		for column_name,column_list in {"characters": raw_data["Character"], "relationships":raw_data["Relationship"],"tags":raw_data["Additional Tags"]}.iteritems():
				
			formatted_list=[]
			for item in column_list:
				item=item.strip()
				if column_name == "characters":
					item=format_character_name(item)

				elif column_name =="relationships":
					item=format_relationship(item)

				if column_name in hierarchical_columns:
					fd=metadata["fandom"][0] #TODO hack, if there is several fandoms, just associate the characters with the first fandom
					if fd in short_fandom:
						fd=short_fandom[fd]
					fd=re.sub("\."," ",fd) #to avoid bugs with the hierarchical structure
					item=re.sub("\."," ",item)
					item=fd+"."+item
				formatted_list.append(item)
			metadata[column_name]=formatted_list


		
		chapters=chapters.strip()
		chapters=chapters.split("/")
		if chapters[1]=="?" or chapters[1]!=chapters[0]:
			metadata["status"]="Ongoing"
		else:
			metadata["status"]="Complete"


		if custom_tags==True and int(word_count)>brick_thresold:
			metadata["tags"].append("brick")
			
	
	return uri,metadata


def fetch_value_id(table_name,value_real,create_missing=False,):
	"""returns the id of a value for a custom column. with option create_missing, creates the value if it doesn't exist already ; otherwise, raise an error"""

	value_column_name="value" #name of the column where we want to find value_real
	if table_name in ["tags"]:
		value_column_name="name" #histoire de faire chier


	#print "rfffffff",[table_name,value_column_name,value_real]
	cursor.execute("SELECT id FROM "+table_name+" WHERE "+value_column_name+"= ?", (value_real,))
	rows= cursor.fetchone()
	if rows:
		value_id=str(rows[0])
	else:
		if create_missing:
			max_id=cursor.execute("SELECT MAX(id) FROM "+table_name)
			max_id=cursor.fetchone()[0]
			if max_id:
				value_id=max_id+1
			else:
				value_id=1
			#print "eeeee",[table_name,value_column_name,value_id,value_real]
			cursor.execute("INSERT INTO "+table_name+" (id, '"+value_column_name+"') VALUES (?,?)" , (value_id,value_real) )
		else:
			sys.stderr.write("error : the value "+value_real+" doesn't exist for the column "+table_name+". be sure to enter EXACTLY an existing value\n")
			raise ValueError
	return str(value_id)



def edit_calibre_database(uri,metadata):
	"""edit the metadata database of calibre
	uri must be the url of the work on AO3. like "http://archiveofourown.org/works/9290123"
	metadata must be a dictionnary produced by parse_ao3_metadata()
	"""

	#find the book id
	cursor.execute("SELECT book,val FROM identifiers WHERE val='"+uri+"'")
	rows=cursor.fetchone()
	if rows:
		id_=str(rows[0])
	else:
		sys.stderr.write("error : uri "+uri+" not found. have you first imported the work into calibre ?\n")
		raise ValueError
	#print "id:",id_


	for metadata_type in columns_to_update:
		value_real_list=metadata[metadata_type] #the real, textual values of the metadata
		column_number=custom_columns[metadata_type] #identifier of the type of metadata

		#determine table name
		column_name="custom_column_"+column_number
		if metadata_type=="tags":
			column_name="tags"
		column_name_link="books_"+column_name+"_link"
		if metadata_type=="word_count":
			column_name_link=column_name

		#determine the name of the column where the real values are in the table custom_column_N or tags
		value_column_name="value"
		if column_name=="tags":
			value_column_name="tag"


		create_missing=True
		if metadata_type in ["genre","status","read","content_rating"]:
			#create_missing=False #those have a fixed number of possible values. will return an error if we ask for a value that doesn't exist TODO remove that safeguard at the end for usability
			pass


		#fetch value id
		is_list=True
		if type(value_real_list)!=list:
			value_real_list=[value_real_list]
			is_list=False

		for value_real in value_real_list:

			if not value_real:
				continue

			if metadata_type=="word_count":
				value_id=value_real
			else:
				#print "ezrjoerzeeeee",column_name,value_real
				value_id=fetch_value_id(column_name,value_real,create_missing)


			#update the database

			if is_list :
			#if the metadata is list-like (tag-like) we don't want to replace an existing value, we want to add a new row
				#check if the specific pair of book and value already exist, create it if not
				cursor.execute("SELECT * FROM "+column_name_link+" WHERE book='"+id_+"' and "+value_column_name+"='"+value_id+"'")
				row=cursor.fetchone()
				if not row:
					cursor.execute("INSERT INTO "+column_name_link+" (book,"+value_column_name+") VALUES(?,?)",(id_,value_id))
				else:
					pass #the information is already in the db, do nothing

			else:
				#check if there is already a value for that work and metadata in the db
				cursor.execute("SELECT * FROM "+column_name_link+" WHERE book="+id_)
				rows=cursor.fetchall()

				if rows:
					#update
					if metadata_type=="series_ao3":
						cursor.execute("UPDATE "+column_name_link+" SET value = "+value_id+" , extra = "+metadata["series_number"]+" WHERE book ="+id_ )
					else:
						cursor.execute("UPDATE "+column_name_link+" SET "+value_column_name+" ="+value_id+" WHERE book ="+id_)
				else:
					#insert
					if metadata_type=="series_ao3":
						cursor.execute("INSERT INTO "+column_name_link+" (book,value,extra) VALUES(?,?,?)",(id_,value_id,metadata["series_number"]))
					else:
						cursor.execute("INSERT INTO "+column_name_link+" (book,"+value_column_name+") VALUES(?,?)",(id_,value_id))


	db.commit()


if __name__=="__main__":
	works=build_work_list(import_directory)

	short_ship2={}
	for ship in short_ship:
		ship2=format_relationship(ship)
		short_ship2[ship2]=short_ship[ship]
	short_ship=short_ship2

	for work in works:
		print "processing ",work
		data=parse_ao3_metadata(work)
		if data:
			edit_calibre_database(data[0],data[1])




