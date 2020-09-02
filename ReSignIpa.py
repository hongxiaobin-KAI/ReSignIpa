# -*- coding: utf-8 -*-1
import optparse
import os
import sys
import getpass
import re
import base64

#桌面路径
desktopPath = "/Users/" + getpass.getuser() + "/Desktop/"
#桌面上存放ipa和mobilepro的文件夹      如果需要改文件夹名，只需要改reipa，其他参数不需要修改
ipaForderPath = desktopPath + "reipa"
#ipa名
ipaName = ''
#provision名
provisionName = ''
#查找provision里面的证书名字
caName = ''

def lookingForIpaAndProvisionName():
	files = os.listdir(ipaForderPath)
	print("files:",files)

	for file in files:
		filePath = ipaForderPath + "/" + file
		name = os.path.splitext(file)[0]
		suffix = os.path.splitext(file)[1]

		global ipaName
		global provisionName

		if suffix == '.ipa':
			ipaName = name
		elif suffix == '.mobileprovision':
			provisionName = name
	return

def checkIpaAndProvisionName():
	if len(ipaName) > 0 and len(provisionName) > 0: 
		print("ipa name :",ipaName)
		print("mobileprovision name:",provisionName)

		return True
	else :
		print("unable to find ipa or mobileprovision")

	return False

def lookingForCaName():
	provisionPath = ipaForderPath + "/" + provisionName + ".mobileprovision"

	info = parseMobileprovision(provisionPath)

	print("mobileprovision info: ",info)

	global caName
	if len(info["cer"]) :
		caName = info["cer"]
	else :
		caTypeStr = 'iPhone Distribution: '
		if info["type"] == "development" :
			caTypeStr = 'iPhone Developer: '

		caName = caTypeStr + info["teamName"] + " (" + info["team"] + ")"

	print("ca name : ",caName)
	return

def parseMobileprovision(filePath):
    reader = open(filePath, "rb")
    readContent = reader.read()
    reader.close()

    if sys.version_info[0] >= 3:
    	readContent = readContent.decode('ISO-8859-1')

    cerRegularStr = re.compile("<key>DeveloperCertificates</key>[\s\r\n]*<array>[\s\r\n]*<data>(.*)</data>[\s\r\n]*</array>", re.M | re.S)
    cerStrList = cerRegularStr.findall(readContent)
    cer = cerStrList[0]

    uuidRegularStr = re.compile(r"<key>UUID</key>[\s\r\n]*<string>([0-9a-f-]+)</string>",re.M | re.S)
    uuidStrList = uuidRegularStr.findall(readContent)
    uuid = uuidStrList[0]

    nameRegularStr = re.compile("<key>Name</key>[\s\r\n]*<string>(.*?)</string>",re.M | re.S)
    nameStrList = nameRegularStr.findall(readContent)
    name = nameStrList[0]
    
    idRegularStr = re.compile(r"<key>application-identifier</key>[\s\r\n]*<string>([^\.]+)\.(.*?)</string>")
    idStrList = idRegularStr.findall(readContent)
    teamId, idStr = idStrList[0]

    teamNameRegularStr = re.compile("<key>TeamName</key>[\s\r\n]*<string>(.*?)</string>",re.M | re.S)
    teamNameStrList = teamNameRegularStr.findall(readContent)
    teamName = teamNameStrList[0]

    base = base64.b64decode(cer)
    if sys.version_info[0] >= 3:
    	base = base.decode('ISO-8859-1')
    
    cerTeamRegularStr = re.compile("iPhone[\w\s\r\n]+\:[\w\s\r\n]+\(\w+\)",re.M | re.S)
    cerTeam = cerTeamRegularStr.findall(base)
    
    typeStr = ""
    if readContent.find("ProvisionsAllDevices") >= 0:
        typeStr = "enterprise"
    elif readContent.find("ProvisionedDevices") >= 0:
        if readContent.find("Entitlements") >= 0:
            if readContent.find("production") >= 0:
                typeStr = "ad-hoc"
            else:
                typeStr = "development"
    else :
        typeStr = "app-store"

    info = {
        "type" : typeStr,
        "uuid" : uuid,
        "team" : teamId,
        "teamName" : teamName,
        "id"   : idStr,
        "name" : name,
        "cer"  : cerTeam[0],
    }
    del readContent
    return info

def reloadCodeSignature():
	os.system('rm -rf %s/Payload'%(ipaForderPath))
	os.system('rm -rf %s/Symbols'%(ipaForderPath))
	os.system('rm -rf %s/reload%s.ipa'%(ipaForderPath, ipaName))

	os.system('cd %s; unzip %s.ipa'%(ipaForderPath, ipaName))

	payloadPath = ipaForderPath + "/Payload" 

	files = os.listdir(payloadPath)
	fileName = files[0]

	if len(fileName) > 0:
		appPath = payloadPath + "/" + fileName
		os.system('rm -rf %s/_CodeSignature/'%(appPath))

		frameworksPath = appPath + "/Frameworks"
		frameworkFiles = os.listdir(frameworksPath)
		for frameworkName in frameworkFiles:
			os.system('rm -rf %s/%s/_CodeSignature/'%(frameworksPath, frameworkName))
			os.system('codesign -f -s "%s" %s/%s/'%(caName, frameworksPath, frameworkName))


		os.system('cp %s/%s.mobileprovision  %s/embedded.mobileprovision'%(ipaForderPath, provisionName, appPath))

		os.system('cd %s;security cms -D -i %s.mobileprovision > embedded.plist'%(ipaForderPath, provisionName))

		os.system('cd %s;/usr/libexec/PlistBuddy -x -c "Print:Entitlements" embedded.plist > entitlements.plist'%(ipaForderPath))

		os.system('cd %s;codesign -f -s "%s" --no-strict --entitlements=entitlements.plist %s'%(ipaForderPath, caName, appPath))

		os.system('codesign -vv -d %s'%(appPath))

		os.system('cd %s;zip -r reload%s.ipa Payload'%(ipaForderPath, ipaName))

	else :
		print("unzip ipa error")



def main():
	
	lookingForIpaAndProvisionName()

	if (checkIpaAndProvisionName()) :

		lookingForCaName()

		reloadCodeSignature()



main()