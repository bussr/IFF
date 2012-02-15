#!/usr/bin/env python

""" Coded by Matthew Nebel for the CogWorks IFF experiment """

import pygame, sys, math, numpy, random, time
import picture
from pygame.locals import *
try:
    from pycogworks.cogworld import *
    from pycogworks.eyegaze import *
except:
    print "WARNING: pycogworks not installed"
import argparse

pygame.init()

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--condition', action="store", dest="condition", help='Task Condition', metavar='COND')
parser.add_argument('--port', action="store", dest="port", help='CogWorld RPC port')
parser.add_argument('--egserver', action="store", dest="egserver", help='EGServer ip or hostname', metavar='HOST')
args = parser.parse_args()

subnum = -99

cw = None
if args.port:
    cw = CogWorld('localhost',args.port,'IFF')
    ret = cw.connect()
    if (ret!=None):
        print 'CogWorld %s' % (ret)
        sys.exit()
    else:
        print 'Connected to CogWorld %s' % (cw.cwGetVersion())

# Load in variables from the config file
execfile('config.txt')

# Set condition if none is provided
if not args.condition:
    if SHOOTFIRST:
        args.condition = 'b' + str(random.randint(1, 8))
    else:
        args.condition = 'a' + str(random.randint(1, 8))
    subnum = -99

# Connect to eyegaze system
eg = None
if REALTIME_EYETRACKING:
    eg = EyeGaze()
    ret = None
    if args.egserver:
        ret = eg.connect(args.egserver)
    elif cw:
        ret = eg.connect(cw.cwGetEyetrackerIp())
    if ret != None:
        print 'EGServer %s' % (ret)
        sys.exit()
    
# INITIALIZE ALL GRAPHICAL ASSET #

# Initialize game screen
screen = pygame.display.set_mode(ASPECT)
if FULLSCREEN:
    screen = pygame.display.set_mode(ASPECT, pygame.FULLSCREEN)
    
if eg:
    if not eg.calibrate(screen):
        print "Subject failed to calibrate to eyetracker..."
        sys.exit()
    else:
        eg.data_start()

#Load in the list of backgrounds
bgs = []
bgs.append(picture.Picture("backgrounds/background.png", (0,0), 1))

# Load in the list of bodies
bodies = []
bodies.append(picture.Picture("soldiers/soldier.png", (0,0), 1))
if SOLDIERTYPES:
    bodies.append(picture.Picture("soldiers/asian_soldier.png", (0,0), 1))
    bodies.append(picture.Picture("soldiers/black_soldier.png", (0,0), 1))
    bodies.append(picture.Picture("soldiers/mustache_soldier.png", (0,0), 1))

# Load in their associated arms
arms = []
arms.append(picture.Picture("soldiers/arms.png", (0,0), 1))
arms.append(picture.Picture("soldiers/asian_arms.png", (0,0), 1))
arms.append(picture.Picture("soldiers/black_arms.png", (0,0), 1))
arms.append(picture.Picture("soldiers/mustache_arms.png", (0,0), 1))

# Load in the list of armbands
bands = []
bands.append(picture.Picture("armbands/armband_striped.png", (0,0), 1))
bands.append(picture.Picture("armbands/armband_solid.png", (0,0), 1))

# Load in the list of held pictures
held = []
held.append(picture.Picture("held/bag.png", (0,0), 1))
held.append(picture.Picture("held/bucket.png", (0,0), 1))

# Load in the list of helmets
helmets = []
helmets.append(picture.Picture("helmets/green.png", (0,0), 1))
helmets.append(picture.Picture("helmets/beige.png", (0,0), 1))

# The 'expand' function create a larger background for presented messages
def expand(surf, color = BGCOLOR):
    rect = surf.get_rect()
    newsurf = pygame.Surface((rect.width+MSGBORDER, rect.height+MSGBORDER))
    newsurf.fill(color)
    newsurf.blit(surf, (MSGBORDER/2, MSGBORDER/2))
    return newsurf

# Initialize fonts and create messages
font = pygame.font.Font(None, 45)
fcMsg = expand(font.render('Correct: was a Friend', 1, MSGCOLOR))
ecMsg = expand(font.render('Correct: was an Enemy', 1, MSGCOLOR))
fwMsg = expand(font.render('Incorrect: was an Enemy', 1, MSGCOLOR))
ewMsg = expand(font.render('Incorrect: was a Friend', 1, MSGCOLOR))
ootfMsg = expand(font.render('Out of time: was a Friend', 1, MSGCOLOR))
ooteMsg = expand(font.render('The enemy soldier shot you!', 1, MSGCOLOR))
blockMsg = expand(font.render('Block Complete!', 1, MSGCOLOR))
spaceMsg = expand(font.render('Press Space Bar to Continue', 1, MSGCOLOR))
warning1Msg = expand(font.render('You responded before any cues were shown.', 1, MSGCOLOR))
warning2Msg = expand(font.render('Please try to judge accurately based on the cues.', 1, MSGCOLOR))
warning3Msg = expand(font.render('The trial will restart in a few seconds.', 1, MSGCOLOR))

# 'Friend' and 'Enemy' messages used in the spoof
examples = []
examples.append(expand(font.render('Friend', 1, MSGCOLOR), (0, 0, 150)))
examples.append(expand(font.render('Enemy', 1, MSGCOLOR), (150, 0, 0)))

# MISCELLANIOUS INITIALIZATION #

clock=pygame.time.Clock()

# Initialize trials list
presentations = [(0,1,2), (0,2,1), (1,0,2), (1,2,0), (2,0,1), (2,1,0)]
combinations = []
for i in range(0,NUMVARIETIES):
    for j in range(0,NUMVARIETIES):
        for k in range(0,NUMVARIETIES):
            combinations.append((i,j,k))
trials = []
for presentation in presentations:
    for combination in combinations:
        trials.append((presentation[0] * NUMVARIETIES + combination[0], presentation[1] * NUMVARIETIES + combination[1], presentation[2] * NUMVARIETIES + combination[2]))

blockNum = 0

spoof = False

sleepcounter = 0

# Open output text file
if not cw:
	log = open(time.strftime("%Y_%m%d_%H%M") + '_' + str(subnum) + '_' + args.condition[0] + '_' + args.condition[1] + '.txt', 'w')

# Flag that determines whether the enemy can shoot first
shootFirst = True
if args.condition[0] == "a":
    shootFirst = False
    
# Decides which items are associated with being an enemy (1) for each slot
# THIS WILL ONLY BE RELEVANT FOR 3 SLOTS WITH 2 VARIETIES EACH
enemyPossibilities = ((0,1) , (1,0))
enemyCombinations = []
for i in range(0, SLOTS-1):
    for j in range (0, SLOTS-1):
        for k in range(0, SLOTS-1):
            enemyCombinations.append((enemyPossibilities[i], enemyPossibilities[j], enemyPossibilities[k]))
enemySet = enemyCombinations[int(args.condition[1])-1]

# Figure out which items are friend and which are enemy
enemyItems = []
friendItems = []
for i in range(SLOTS):
    for j in range(NUMVARIETIES):
        if enemySet[i][j] == 0:
            friendItems.append(i*NUMVARIETIES + j)
        else:
            enemyItems.append(i*NUMVARIETIES + j)

# DEFINE HELPER FUNCTIONS #

# Function to assist with drawing the screen
def draw_screen(bgID, soldierID, bandID, heldID, helmID):
    screen.fill((0,0,0))
    bg = bgs[bgID].image.copy()
    soldier = bodies[soldierID].image.copy()
    # Account for the initial spoof images
    if spoof:
        if bandID >= 0:
            soldier.blit(examples[bandID], (ASPECT[0] * 0.7 - examples[bandID].get_width() / 2, ASPECT[1] * 0.45 - examples[bandID].get_height() / 2))
        if heldID >= 0:
            soldier.blit(examples[heldID], (ASPECT[0] * 0.5 - examples[bandID].get_width() / 2, ASPECT[1] * 0.61 - examples[bandID].get_height() / 2))
        if helmID >= 0:
            soldier.blit(examples[helmID], (ASPECT[0] * 0.5 - examples[bandID].get_width() / 2, ASPECT[1] * 0.08 - examples[bandID].get_height() / 2))
    else:
        if bandID >= 0:
            soldier.blit(bands[bandID].image, bands[bandID].loc)
        if heldID >= 0:
            soldier.blit(held[heldID].image, held[heldID].loc)
        if helmID >= 0:
            soldier.blit(helmets[helmID].image, helmets[helmID].loc)
    soldier.blit(arms[soldierID].image, arms[soldierID].loc)
    bg.blit(soldier, bodies[soldierID].loc)
    screen.blit(bg, (0,0))
    
def calc_distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])*(p1[0]-p2[0])+(p1[1]-p2[1])*(p1[1]-p2[1]))
    
# Function to punish users for inputting an answer before any cues are displayed
def early_lockout():
    screen.fill((0,0,0))
    screen.blit(warning1Msg, (screen.get_width()/2 - warning1Msg.get_width()/2, screen.get_height()/2 - warning1Msg.get_height()/2 - MSGOFFSET))
    screen.blit(warning2Msg, (screen.get_width()/2 - warning2Msg.get_width()/2, screen.get_height()/2 - warning2Msg.get_height()/2))
    screen.blit(warning3Msg, (screen.get_width()/2 - warning3Msg.get_width()/2, screen.get_height()/2 - warning3Msg.get_height()/2 + MSGOFFSET))

    pygame.display.flip()
    pygame.time.delay(LOCKOUT)
    for event in pygame.event.get():
        continue  
    draw_screen(bgID, soldierID, trialState[ARMBAND], trialState[HELD], trialState[HELMET])
    pygame.display.flip()
    return pygame.time.get_ticks()
    
# Function to write out to either cogworld or a log file
def log_event(data):
    if cw:
        cw.cwLogInfo(data)
    else:
        logline = str(subnum) + " "
        for d in data:
            logline += (d + " ")
        logline = logline.rstrip()
        logline += "\n"
        log.write(logline)
        
def wait_for_space():
    space = False
    while not space:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if not cw:
                    log.close()
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    space = True
                elif event.key == pygame.K_ESCAPE:
                    if not cw:
                        log.close()
                    pygame.quit()
                    sys.exit(0)
                    
def wait_for_experimenter():
    numpressed = 0
    while not numpressed == 2:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if not cw:
                    log.close()
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    numpressed += 1
                elif event.key == pygame.K_p:
                    numpressed += 1
                elif event.key == pygame.K_ESCAPE:
                    if not cw:
                        log.close()
                    pygame.quit()
                    sys.exit(0)
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_q:
                    numpressed -= 1
                elif event.key == pygame.K_p:
                    numpressed -= 1
    pygame.time.delay(2000)
    
def draw_all_items(bgID, soldierID, trial):
    a = b = c = -1
    for t in trial:
        if t < NUMVARIETIES:
            a = t%NUMVARIETIES
        if t > NUMVARIETIES - 1 and t < NUMVARIETIES * 2:
            b = t%NUMVARIETIES
        elif t > NUMVARIETIES * 2 - 1:
            c = t%NUMVARIETIES
    draw_screen(bgID, soldierID, a, b, c)
    
def accept_input(key, friend):
    correctID = False
    if key == FRIENDBUTTON:
        if friend:
            screen.blit(fcMsg, (screen.get_width()/2 - fcMsg.get_width()/2, screen.get_height()/2 - fcMsg.get_height()/2))
            correctID = True
        else:
            screen.blit(fwMsg, (screen.get_width()/2 - fwMsg.get_width()/2, screen.get_height()/2 - fwMsg.get_height()/2))
    elif key == ENEMYBUTTON:
        if not friend:
            screen.blit(ecMsg, (screen.get_width()/2 - ecMsg.get_width()/2, screen.get_height()/2 - ecMsg.get_height()/2))
            correctID = True
        else:
            screen.blit(ewMsg, (screen.get_width()/2 - ewMsg.get_width()/2, screen.get_height()/2 - ewMsg.get_height()/2))
    return correctID
    
# BEGIN EXPERIMENT #

# TRAINING #

trainGroups = USE_TRAINING
trainAmbig = False
if USE_TRAINING:
    # Wait for input before starting
    screen.fill((0,0,0))
    screen.blit(spaceMsg, (screen.get_width()/2 - spaceMsg.get_width()/2, screen.get_height()/2 - spaceMsg.get_height()/2))
    pygame.display.flip()
    wait_for_space()
    
    # Initialize variables
    bgID = 0
    soldierID = 0
                
    # Show the friend and enemy cues, requiring spacebar to continue
    draw_all_items(bgID, soldierID, friendItems)
    friendSoldierMsg = expand(font.render('This the friendly soldier', 1, MSGCOLOR))
    screen.blit(friendSoldierMsg, (screen.get_width()/2 - friendSoldierMsg.get_width()/2, screen.get_height()/2 - friendSoldierMsg.get_height()/2 + 2*MSGOFFSET))
    pygame.display.flip()
    wait_for_space()
    draw_all_items(bgID, soldierID, enemyItems)
    enemySoldierMsg = expand(font.render('This is the enemy soldier', 1, MSGCOLOR))
    screen.blit(enemySoldierMsg, (screen.get_width()/2 - enemySoldierMsg.get_width()/2, screen.get_height()/2 - enemySoldierMsg.get_height()/2 + 2*MSGOFFSET))
    pygame.display.flip()
    wait_for_space()
    
    # Create a list of cues with duplicates and scramble them
    cueList = []
    for i in range(SLOTS*NUMVARIETIES):
        cueList.append(i)
        cueList.append(i)
    random.shuffle(cueList)
    # Keep track of position in the list
    iter = 0
    # Test on individual cues
    testIndiv = True
    while testIndiv:
        # Randomly pick a background and soldier image to use for this trial
        bgID = random.randint(0, len(bgs)-1)
        soldierID = random.randint(0, len(bodies)-1)
        # Figure out which piece to show
        trialItems = [-1, -1, -1]
        friend = True
        for i in range(SLOTS):
            if cueList[iter] < NUMVARIETIES * (i+1):
                trialItems[i] = cueList[iter]%NUMVARIETIES
                if enemySet[i][cueList[iter]%NUMVARIETIES] == 1:
                    friend = False
                break
        draw_screen(bgID, soldierID, trialItems[0], trialItems[1], trialItems[2])
        pygame.display.flip()
        trialRun = True
        while trialRun:
            clock.tick(FPS)
            # accept input
            if trialRun:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        if not cw:
                            log.close()
                        pygame.quit()
                        sys.exit(0)
                    elif event.type == pygame.KEYDOWN:
                        # if the escape key is pressed, close the file and exit the game
                        if event.key == pygame.K_ESCAPE:
                            if not cw:
                                log.close()
                            pygame.quit()
                            sys.exit(0)
                        # account for valid input
                        if (event.key == ENEMYBUTTON or event.key == FRIENDBUTTON) and trialRun:
                            # Figure out the results of the input and draw the appropriate message
                            correctID = accept_input(event.key, friend)
                            
                            # If the user was correct, continue on to the next item or exit if correct for all of them
                            if correctID:
                                iter += 1
                                if (iter == len(cueList)):
                                    testIndiv = False
                            else: # Otherwise reshuffle the list and start over
                                iter = 0
                                random.shuffle(cueList)
                                    
                            # Wait for the next trial
                            screen.blit(spaceMsg, (screen.get_width()/2 - spaceMsg.get_width()/2, screen.get_height()/2 - spaceMsg.get_height()/2 + 2*MSGOFFSET))
                            pygame.display.flip()
                            wait_for_space()
                            trialRun = False
else:
    spoof = USE_SPOOF

# MAIN EXPERIMENT LOOP #

# Wait for input before starting
screen.fill((0,0,0))
screen.blit(spaceMsg, (screen.get_width()/2 - spaceMsg.get_width()/2, screen.get_height()/2 - spaceMsg.get_height()/2))
pygame.display.flip()
wait_for_space()
 
while blockNum < NUMBLOCKS:
    currentTrials = []
    
    if trainGroups:
        currentTrials.append(enemyItems[:])
        currentTrials.append(enemyItems[:])
        currentTrials.append(friendItems[:])
        currentTrials.append(friendItems[:])
        for group in currentTrials:
            random.shuffle(group)
        random.shuffle(currentTrials)
        blockNum = -2
    elif trainAmbig:
        availSlots = []
        for i in range(SLOTS):
            availSlots.append(i)
        thisSet = availSlots[:]
        random.shuffle(thisSet)
        thisSet = [enemyItems[thisSet[0]], friendItems[thisSet[1]], friendItems[thisSet[2]]]
        currentTrials.append(thisSet[:])
        thisSet = availSlots[:]
        random.shuffle(thisSet)
        thisSet = [friendItems[thisSet[0]], enemyItems[thisSet[1]], enemyItems[thisSet[2]]]
        currentTrials.append(thisSet[:])
        thisSet = availSlots[:]
        random.shuffle(thisSet)
        thisSet = [enemyItems[thisSet[0]], friendItems[thisSet[1]], enemyItems[thisSet[2]]]
        currentTrials.append(thisSet[:])
        thisSet = availSlots[:]
        random.shuffle(thisSet)
        thisSet = [friendItems[thisSet[0]], enemyItems[thisSet[1]], friendItems[thisSet[2]]]
        currentTrials.append(thisSet[:])
        random.shuffle(currentTrials)
    elif spoof:
        currentTrials = [(0,2,4), (3,5,1), (5,1,2), (4,1,2), (2,1,5), (1,4,2)]
        blockNum = -1
    else:
        # Initialize list of trials for this block
        currentTrials = trials[:]
        random.shuffle(currentTrials)
        
    log_event([str(blockNum), str(pygame.time.get_ticks()), "blockstart"])

    trialNum = 0
        
    correct = 0
    shotFriend = 0
    enemyShot = 0
    helpedEnemy = 0
    
    trainFail = False
    
    for trial in currentTrials:
        # Determine friend or foe status
        friend = False
        fstatus = "enemy"
        enemySum = 0
        # If in the spoof, just add up the odd numbers
        if spoof:
            for i in range(0, len(trial)):
                enemySum += trial[i]%2
        # Otherwise go by the enemySet variable
        else:
            for i in range(0, len(trial)):
                enemySum += enemySet[trial[i]//NUMVARIETIES][trial[i]%NUMVARIETIES]
        if enemySum < (SLOTS+1)/2:
            friend = True
            fstatus = "friend"
            
        # If enemy and proper condition, calculate early end
        endtrial = ENDTIME
        endLabel = "timeout"
        if not friend and shootFirst and not spoof:
            endLabel = "shot"
            endtrial = ENDTIME - (math.exp(DISTRIBUTION*random.gauss(0, 1)) * 1000)
            while endtrial < STEPTIME + 500:
                endtrial = ENDTIME - (math.exp(DISTRIBUTION*random.gauss(0, 1)) * 1000)
        
        # Set timekeeping variables
        startTime = pygame.time.get_ticks()
        
        log_event([str(blockNum),str(trialNum),fstatus,str(startTime),'trialstart',str(endtrial)])
        
        # Randomly pick a background and soldier image to use for this trial
        bgID = random.randint(0, len(bgs)-1)
        soldierID = random.randint(0, len(bodies)-1)
        
        # Initialize the solder to be holding nothing
        trialState = [-1, -1, -1]
        trialStep = 0
        
        # Initialize screen
        draw_screen(bgID, soldierID, trialState[ARMBAND], trialState[HELD], trialState[HELMET])
        pygame.display.flip()
        
        # Flow control variable
        trialRun = True
        
        while trialRun:
            clock.tick(FPS)
            currentTime = pygame.time.get_ticks()
                        
            # If enough time has passed since the last item was presented, show the next one depending on the block and trial
            if currentTime - startTime > STEPTIME * (trialStep+1) and trialStep < TIMEOUT:
                ptype = "armband"
                pvariety = armbandTypes[trial[trialStep]%NUMVARIETIES]
                slot = 0
                if trial[trialStep] > NUMVARIETIES - 1 and trial[trialStep] < NUMVARIETIES * 2:
                    ptype = "held"
                    pvariety = heldTypes[trial[trialStep]%NUMVARIETIES]
                    slot = 1
                elif trial[trialStep] > NUMVARIETIES * 2 - 1:
                    ptype = "helmet"
                    pvariety = helmetTypes[trial[trialStep]%NUMVARIETIES]
                    slot = 2
                    
                penemy = "enemycue"
                if enemySet[trial[trialStep]//NUMVARIETIES][trial[trialStep]%NUMVARIETIES] == 0:
                    penemy = "friendcue"
                    
                log_event([str(blockNum), str(trialNum), str(trialStep), fstatus, str(currentTime), ptype, pvariety, penemy])

                trialState[slot] = trial[trialStep]%NUMVARIETIES
                trialStep+=1
                draw_screen(bgID, soldierID, trialState[ARMBAND], trialState[HELD], trialState[HELMET])
                #pygame.display.flip()
                
            # If the trial reaches a given end time and the conditions match the config, cut it off
            if not trainGroups and not trainAmbig\
            and ((shootFirst and not friend)\
                or (shootFirst and friend and SHOOTFIRSTFRIEND)\
                or (not shootFirst and not friend and NOSHOOTENEMY)\
                or (not shootFirst and friend and NOSHOOTFRIEND))\
            and currentTime - startTime > endtrial:
                log_event([str(blockNum), str(trialNum), str(trialStep), fstatus, str(currentTime), endLabel])
                trialRun = False
                # if this was a normal-length trial, increment the counter of consecutive missed trials
                if endtrial == ENDTIME:
                    sleepcounter += 1
                draw_all_items(bgID, soldierID, trial)
                # display appropriate message depending on friend or foeness
                if friend:
                    screen.blit(ootfMsg, (screen.get_width()/2 - ootfMsg.get_width()/2, screen.get_height()/2 - ootfMsg.get_height()/2))
                else:
                    screen.blit(ooteMsg, (screen.get_width()/2 - ooteMsg.get_width()/2, screen.get_height()/2 - ooteMsg.get_height()/2))
                    enemyShot += 1
                # create a pause between trials, either by a given time or by waiting for space
                if TRIALTIME and not spoof:
                    pygame.display.flip()
                    pygame.time.delay(TRIALTIME - (currentTime - startTime))
                    for event in pygame.event.get():
                        continue
                    # if enough in a row have been missed, engage sleep response
                    if sleepcounter == ASLEEP:
                        sleepcounter = 0
                        screen.fill((0,0,0))
                        notifyMsg = expand(font.render('Please contact the experimenter.', 1, MSGCOLOR))
                        screen.blit(notifyMsg, (screen.get_width()/2 - notifyMsg.get_width()/2, screen.get_height()/2 - notifyMsg.get_height()/2))
                        pygame.display.flip()
                        wait_for_experimenter()
                else:
                    screen.blit(spaceMsg, (screen.get_width()/2 - spaceMsg.get_width()/2, screen.get_height()/2 - spaceMsg.get_height()/2 + 2*MSGOFFSET))
                    pygame.display.flip()
                    wait_for_space()
                    
            if eg and eg.fix_data and eg.fix_data.eye_motion_state > 0:
                d1 = calc_distance((eg.fix_data.fix_x,eg.fix_data.fix_y), bands[trialState[ARMBAND]].loc.center)
                d2 = calc_distance((eg.fix_data.fix_x,eg.fix_data.fix_y), held[trialState[HELD]].loc.center)
                d3 = calc_distance((eg.fix_data.fix_x,eg.fix_data.fix_y), helmets[trialState[HELMET]].loc.center)
                print "armband: %.2f, held: %.2f, helmet: %.2f" % (d1,d2,d3)
                
                if DRAW_FIXATION:
                    pygame.draw.line(screen, (255, 0, 0),
                                     (eg.fix_data.fix_x - 10, eg.fix_data.fix_y),
                                     (eg.fix_data.fix_x + 10, eg.fix_data.fix_y))
                    pygame.draw.line(screen, (255, 0, 0),
                                     (eg.fix_data.fix_x, eg.fix_data.fix_y - 10),
                                     (eg.fix_data.fix_x, eg.fix_data.fix_y + 10))

            pygame.display.flip()
                    
            # Accept user input
            if trialRun:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        if not cw:
                            log.close()
                        pygame.quit()
                        sys.exit(0)
                    
                    elif event.type == pygame.KEYDOWN:
                        # if the escape key is pressed, close the file and exit the game
                        if event.key == pygame.K_ESCAPE:
                            if not cw:
                                log.close()
                            pygame.quit()
                            sys.exit(0)
                        # if valid input is detected, check if it's too early and register the user as not asleep
                        if (event.key == ENEMYBUTTON or event.key == FRIENDBUTTON):
                            # Reset sleep detection
                            sleepcounter = 0
                            # If the user responds too quickly: display warning, lockout, and reset trial
                            if trialStep == 0:
                                startTime = early_lockout()
                                log_event([str(blockNum), str(trialNum), fstatus, str(startTime), "trialstart", str(endtrial)])
                            elif trialRun:
                                # Draw the rest of the items on the soldier
                                draw_all_items(bgID, soldierID, trial)
                                # Figure out the results of the input and draw the appropriate message
                                correctID = accept_input(event.key, friend)
                                
                                # Log and keep track of results for the specific cases
                                if event.key == FRIENDBUTTON:
                                    log_event([str(blockNum), str(trialNum), str(trialStep), fstatus, str(currentTime), "friend"])
                                    if not correctID:
                                        helpedEnemy += 1
                                elif event.key == ENEMYBUTTON:
                                    log_event([str(blockNum), str(trialNum), str(trialStep), fstatus, str(currentTime), "enemy"])
                                    if not correctID:
                                        shotFriend += 1
                                        
                                if correctID:
                                    correct += 1
                                elif trainGroups or trainAmbig:
                                    trainFail = True
                                    
                                # Wait for the next trial
                                if TRIALTIME and not spoof and not trainGroups and not trainAmbig:
                                    pygame.display.flip()
                                    if correctID:
                                        pygame.time.delay(REWARDTIME)
                                    else:
                                        remainingTime = TRIALTIME - (currentTime - startTime)
                                        if remainingTime < PUNISHMENTTIME:
                                            remainingTime = PUNISHMENTTIME
                                        pygame.time.delay(remainingTime)
                                    for event in pygame.event.get():
                                        continue     
                                else:
                                    screen.blit(spaceMsg, (screen.get_width()/2 - spaceMsg.get_width()/2, screen.get_height()/2 - spaceMsg.get_height()/2 + 2*MSGOFFSET))
                                    pygame.display.flip()
                                    wait_for_space()
                                trialRun = False
                        
        if trainFail:
            break
        trialNum += 1
        
    # If doing a training block where the subject screwed up, skip feedback and just restart the trials
    if not trainFail:
        # clear screen and display feedback for block
        screen.fill((0,0,0))
        if not trainGroups and not trainAmbig:
            blockNum += 1
            friendsShotMsg = expand(font.render('Number of friends shot: ' + str(shotFriend), 1, MSGCOLOR))
            shotYouMsg = expand(font.render('Number of enemies that shot you: ' + str(enemyShot), 1, MSGCOLOR))
            letInMsg = expand(font.render('Number of enemies you let into the base: ' + str(helpedEnemy), 1, MSGCOLOR))
            correctMsg = expand(font.render('Correctly identified ' + str(correct) + ' out of ' + str(len(currentTrials)) + \
                ' for an accuracy ratio of '+ str(int(correct/float(len(currentTrials)) * 100.0)) + '%', 1, MSGCOLOR))
            screen.blit(blockMsg, (screen.get_width()/2 - blockMsg.get_width()/2, screen.get_height()/2 - blockMsg.get_height()/2 -  3 * MSGOFFSET))
            screen.blit(friendsShotMsg, (screen.get_width()/2 - friendsShotMsg.get_width()/2, screen.get_height()/2 - friendsShotMsg.get_height()/2 -  2 * MSGOFFSET))
            screen.blit(shotYouMsg, (screen.get_width()/2 - shotYouMsg.get_width()/2, screen.get_height()/2 - shotYouMsg.get_height()/2 -  MSGOFFSET))
            screen.blit(letInMsg, (screen.get_width()/2 - letInMsg.get_width()/2, screen.get_height()/2 - letInMsg.get_height()/2))
            screen.blit(correctMsg, (screen.get_width()/2 - correctMsg.get_width()/2, screen.get_height()/2 - correctMsg.get_height()/2 + MSGOFFSET))
        # manage training/spoof variables
        if trainGroups:
            trainGroups = False
            trainAmbig = True
        elif trainAmbig:
            trainAmbig = False
            spoof = USE_SPOOF
        elif spoof:
            spoof = False
        # either wait the designated amount of time or wait for the space bar
        if BLOCKPAUSE:
            pygame.display.flip()
            pygame.time.delay(BLOCKPAUSE)
        else:
            screen.blit(spaceMsg, (screen.get_width()/2 - spaceMsg.get_width()/2, screen.get_height()/2 - spaceMsg.get_height()/2 + 2 * MSGOFFSET))
            pygame.display.flip()
            wait_for_space()
if not cw:
    log.close()

screen.fill((0,0,0))
completeMsg = expand(font.render('Experiment complete!', 1, MSGCOLOR))
notifyMsg = expand(font.render('Please notify the experimenter.', 1, MSGCOLOR))
screen.blit(completeMsg, (screen.get_width()/2 - completeMsg.get_width()/2, screen.get_height()/2 - completeMsg.get_height()/2))
screen.blit(notifyMsg, (screen.get_width()/2 - notifyMsg.get_width()/2, screen.get_height()/2 - notifyMsg.get_height()/2 + MSGOFFSET))
pygame.display.flip()
wait_for_experimenter()

pygame.quit()
if eg:
    eg.data_stop()
    eg.disconnect()
