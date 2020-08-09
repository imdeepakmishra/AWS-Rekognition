import os
from app import app
import csv
import boto3
import urllib.request
import mysql.connector
from flask import Flask, flash, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
from pprint import pprint
from opencage.geocoder import OpenCageGeocode
from GPSPhoto import gpsphoto

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

# MySQL-Connector
mydb = mysql.connector.connect(host="127.0.0.1",user='root',password='root',database='world',port=3306)

# Geo-Location (OpenCage)
key = 'XXXXXXXXXXXXXXXXXXXXXXXX'
geocoder = OpenCageGeocode(key)

# AWS-Credentials
with open('aws-credentials.csv','r') as input:
    next(input)
    reader=csv.reader(input)
    for line in reader:
        access_key_id =line[2]
        secret_access_key=line[3]

def compare_faces(sourceFile, targetFile, location):
	client = boto3.client('rekognition')
	imageSource = open(sourceFile, 'rb')
	imageTarget = open(targetFile, 'rb')
	response = client.compare_faces(SimilarityThreshold=80,
                                    SourceImage={'Bytes': imageSource.read()},
                                    TargetImage={'Bytes': imageTarget.read()})

	# print(response['FaceMatches'].['Similarity'])
	for faceMatch in response['FaceMatches']:
		position = faceMatch['Face']['BoundingBox']
		similarity = str(faceMatch['Similarity'])
	imageSource.close()
	imageTarget.close()
	if(len(response['FaceMatches']) == 1):
		return [len(response['FaceMatches']),str(round(faceMatch['Similarity']))];
	else:
		return len(response['FaceMatches']);

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
	
@app.route('/')
def upload_form():
	return render_template('upload.html')

@app.route('/', methods=['POST'])
def upload_image():
	if 'files[]' not in request.files:
		flash('No file part')
		return redirect(request.url)
	files = request.files.getlist('files[]')
	file_names = []
	for file in files:
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file_names.append(filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
		else:
			flash('Allowed image types are -> png, jpg, jpeg, gif')
			return redirect(request.url)
	data = gpsphoto.getGPSData('./static/uploads/'+(file_names[0]))
	results = geocoder.reverse_geocode(data['Latitude'], data['Longitude'])
	location =  (results[0]['formatted'])
	source_file = ('./static/uploads/'+(file_names[0]))
	target_file = ('./static/uploads/'+(file_names[1]))
	
	face_matches = compare_faces(source_file, target_file, location)
	if(str(face_matches) == str(0)):
		cur=mydb.cursor()
		s="""INSERT INTO aws_test (address,similarity,type) VALUES (%s,%s,%s)"""
		b1=(location, 'N/A', 'Unmatched')
		cur.execute(s, b1)
		mydb.commit()
		return render_template('results.html',file_name_0 = file_names[0], file_name_1 = file_names[1], filenames=file_names,result = face_matches, location = location)
	else:
		cur=mydb.cursor()
		s="""INSERT INTO aws_test (address,similarity,type) VALUES (%s,%s,%s)"""
		b1=(location,face_matches[1],'Matched')
		cur.execute(s, b1)
		mydb.commit()
		return render_template('results.html',file_name_0 = file_names[0], file_name_1 = file_names[1],filenames=file_names, result1= face_matches[0],result2= face_matches[1], location = location)

@app.route('/display/<filename>')
def display_image(filename):
	#print('display_image filename: ' + filename)
	return redirect(url_for('static', filename='uploads/' + filename), code=301)

if __name__ == "__main__":
	app.run()