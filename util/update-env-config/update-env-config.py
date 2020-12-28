import cfnresponse
import os
import boto3
import json
from io import BytesIO
from urllib.request import urlopen
import zipfile
from pathlib import Path
def handler(event, context):
    print (str(event))
    responseData = {}
    try: 
        if (event['RequestType'] == 'Create') or (event['RequestType'] == 'Update'):
            UserPoolId = event['ResourceProperties']['UserPoolId']
            CognitoRegion = event['ResourceProperties']['CognitoRegion']
            SourceUrl = event['ResourceProperties']['SourceUrl']
            EdgeFunctionArn = event['ResourceProperties']['EdgeFunctionArn']   
            # SourceUrl = 'https://mingtong-update-config.s3.amazonaws.com/upload-test.zip'
            print("get jwks value")
            jwksUrl = 'https://cognito-idp.' + CognitoRegion + '.amazonaws.com/' + UserPoolId + '/.well-known/jwks.json'
            with urlopen(jwksUrl) as httpresponse:
                jwks = str( httpresponse.read() )
            jwks = jwks.replace('b\'{', '{')
            jwks = jwks.replace('}\'', '}')
            print(jwks)
            print("unzip source Zip to local directory")
            baseDir = '/tmp/mingtong/updateConfig/'
            print("baseDir=" + baseDir)
            with urlopen(SourceUrl) as zipresp:
              with zipfile.ZipFile(BytesIO(zipresp.read())) as zfile:
                zfile.extractall(baseDir)
            print("read app.js")
            indexjs = Path(baseDir + 'app.js').read_text()
            # indexjs = indexjs.replace('##JWKS##', jwks)
            indexjs = indexjs.replace('##USERPOOLID##', UserPoolId)
            print("save app.js back to disk")
            with open(baseDir + 'app.js',"w") as w:
                w.write(indexjs)
            print("zip up the directory")
            zipHandle = zipfile.ZipFile('/tmp/edge-auth.zip', 'w', compression = zipfile.ZIP_DEFLATED)
            addDirToZip(zipHandle, baseDir, baseDir)
            zipHandle.close()
            with open('/tmp/edge-auth.zip', 'rb') as file_data:
                bytes_content = file_data.read()
            lambdaClient = boto3.client('lambda')            
            lambdaClient.update_function_code(
                FunctionName=EdgeFunctionArn,
                ZipFile=bytes_content)            
            # print("upload to S3")
            # s3 = boto3.resource('s3')
            # s3.meta.client.upload_file('/tmp/edge-auth.zip', 'mingtong-update-config', 'upload-test-replace.zip', ExtraArgs={'ACL': 'public-read'} )
            responseData['Status'] = 'SUCCESS'
            cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "CustomResourcePhysicalID")
            print ('SUCCESS')
        else:
            print("SUCCESS - operation not Create or Update, ResponseData=" + str(responseData))
            cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "CustomResourcePhysicalID")
    except Exception as e:
        responseData['Error'] = str(e)
        cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "CustomResourcePhysicalID") 
        print("FAILED ERROR: " + responseData['Error'])
def addDirToZip(zipHandle, path, basePath=""):
    basePath = basePath.rstrip("\\/") + ""
    basePath = basePath.rstrip("\\/")
    for root, dirs, files in os.walk(path):
        zipHandle.write(os.path.join(root, "."))
        for file in files:
            filePath = os.path.join(root, file)
            inZipPath = filePath.replace(basePath, "", 1).lstrip("\\/")
            zipHandle.write(filePath, inZipPath)