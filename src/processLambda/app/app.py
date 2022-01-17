import boto3
import os
import subprocess
import shlex
from boto3.dynamodb.conditions import Key
from datetime import datetime

SOURCE_BUCKET = os.environ['MEDIA_CAPTURE_BUCKET']
SOURCE_PREFIX = 'captures'
s3 = boto3.client('s3')

def process_files(objs_keys, MEETING_ID, file_type):        
    now = datetime.today()
    print(MEETING_ID)
    with open('/tmp/' + file_type +'_list.txt', 'w') as f:
        for k in objs_keys:
            print(k)
            basename = os.path.splitext(k)[0]
            print("basename:"+basename)
            ffmpeg_cmd = "ffmpeg -i /tmp/" + k + " -bsf:v h264_mp4toannexb -f mpegts -framerate 15 -c copy /tmp/" + basename + "-" + file_type + ".ts -y"
            command1 = shlex.split(ffmpeg_cmd)
            p1 = subprocess.run(command1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            f.write(f'file \'/tmp/{basename}-{file_type}.ts\'\n')

    ffmpeg_cmd = "ffmpeg -f concat -safe 0 -i /tmp/" + file_type + "_list.txt  -c copy /tmp/"+file_type+".mp4 -y"
    command1 = shlex.split(ffmpeg_cmd)
    p1 = subprocess.run(command1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    s3.upload_file('/tmp/'+file_type+'.mp4', SOURCE_BUCKET, MEETING_ID + '/'+now.strftime("%Y%m%d%H%M%S%f")+'.mp4')
    processedUrl = s3.generate_presigned_url('get_object', Params={'Bucket': SOURCE_BUCKET, 'Key': MEETING_ID + '/processed'+file_type+'.mp4' })
    
    return processedUrl
    
    
def handler(event, context):
    #This demo is limited in scope to give a starting point for how to process 
    #produced audio files and should include error checking and more robust logic 
    #for production use. Large meetings and/or long duration may lead to incomplete 
    #recordings in this demo.    
    print(event)
    MEETING_ID = event.get('detail').get('externalMeetingId')
    print(MEETING_ID)

    audioPrefix = SOURCE_PREFIX + '/' + MEETING_ID + '/audio'
    videoPrefix = SOURCE_PREFIX + '/' + MEETING_ID + '/video'
    print("audioPrefix:" + audioPrefix)
    
    audioList = s3.list_objects_v2(
        Bucket=SOURCE_BUCKET,
        Delimiter='string',
        MaxKeys=1000,
        Prefix=audioPrefix
    )
    audioObjects = audioList.get('Contents', [])
    print(audioObjects)
    
    videoList = s3.list_objects_v2(
        Bucket=SOURCE_BUCKET,
        Delimiter='string',
        MaxKeys=1000,
        Prefix=videoPrefix
    )
    videoObjects = videoList.get('Contents', [])
    print(videoObjects)
    
    if videoObjects:
        file_list=[]
        file_type = 'video'
        for object in videoObjects:
            path, filename = os.path.split(object['Key'])
            s3.download_file(SOURCE_BUCKET, object['Key'], '/tmp/' + filename)
            file_list.append(filename)
    
        objs_keys = list(filter(lambda x : 'mp4' in x, file_list))
        print(objs_keys)
        process_files(objs_keys, MEETING_ID, file_type)
    else:
        print("No videos")
        
    file_list=[]
    file_type = 'audio'
    for object in audioObjects:
        path, filename = os.path.split(object['Key'])
        s3.download_file(SOURCE_BUCKET, object['Key'], '/tmp/' + filename)
        file_list.append(filename)
    if audioObjects:
        objs_keys = filter(lambda x : 'mp4' in x, file_list)        
        process_files(objs_keys, MEETING_ID, file_type)
        # delete object after processing the audio files
        for object in audioObjects:
            s3.delete_object(SOURCE_BUCKET, object['Key'])
    else:
        print("No Audio")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST'            
        }
    }
