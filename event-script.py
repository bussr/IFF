inname = raw_input("File name: ")
infile = open(inname)
outname = "R_" + inname
outfile = open(outname, 'w')

outfile.write("block# trial# trialStartTime friendStatus presented responseTime responseCorrect\n")

currentline = infile.readline()
currentline.rstrip()    
linelist = currentline.split()

blocknum = 0
presented = ''

while(currentline):
    if linelist[0] == 'blockStart':
        blocknum = linelist[2]
        
    elif linelist[0] == 'trialStart':
        outfile.write(blocknum + " " + linelist[2] + " " + linelist[1] + " " + linelist[3] + " ")
        
    elif linelist[0] == 'present':
        presented = presented + linelist[2]
        
    elif linelist[0] == 'identify':
        outfile.write(presented + " " + linelist[1] + " " + linelist[3] + "\n")
        presented = ''
        
    elif linelist[0] == 'timeout':
        outfile.write(presented + " " + linelist[1] + " " + linelist[2] + "\n")
        presented = ''
        
    currentline = infile.readline()
    currentline.rstrip()    
    linelist = currentline.split()
    
infile.close()
outfile.close()