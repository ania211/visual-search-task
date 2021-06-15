#!/usr/bin/env python
# -*- coding: latin-1 -*-
import sys
import atexit
import codecs
import csv
import os
import random
from os.path import join
from statistics import mean

import yaml
from psychopy import visual, event, logging, gui, core

from misc.screen_misc import get_screen_res, get_frame_rate
from itertools import combinations_with_replacement, product


@atexit.register
def save_beh_results():
    """
    Save results of experiment. Decorated with @atexit in order to make sure, that intermediate
    results will be saved even if interpreter will broke.
    """
    with open(join('results', PART_ID + '_' + str(random.choice(range(100, 1000))) + '_beh.csv'), 'w', encoding='utf-8') as beh_file:
        beh_writer = csv.writer(beh_file)
        beh_writer.writerows(RESULTS)
    logging.flush()


def show_image(win, file_name, size, key='f7'):
    """
    Show instructions in a form of an image.
    """
    image = visual.ImageStim(win=win, image=file_name,
                             interpolate=True, size=size)
    image.draw()
    win.flip()
    clicked = event.waitKeys(keyList=[key, 'return', 'space'])
    if clicked == [key]:
        logging.critical(
            'Experiment finished by user! {} pressed.'.format(key[0]))
        exit(0)
    win.flip()


def read_text_from_file(file_name, insert=''):
    """
    Method that read message from text file, and optionally add some
    dynamically generated info.
    :param file_name: Name of file to read
    :param insert:
    :return: message
    """
    if not isinstance(file_name, str):
        logging.error('Problem with file reading, filename must be a string')
        raise TypeError('file_name must be a string')
    msg = list()
    with codecs.open(file_name, encoding='utf-8', mode='r') as data_file:
        for line in data_file:
            if not line.startswith('#'):  # if not commented line
                if line.startswith('<--insert-->'):
                    if insert:
                        msg.append(insert)
                else:
                    msg.append(line)
    return ''.join(msg)


def check_exit(key='f7'):
    """
    Check (during procedure) if experimentator doesn't want to terminate.
    """
    stop = event.getKeys(keyList=[key])
    if stop:
        abort_with_error(
            'Experiment finished by user! {} pressed.'.format(key))


def show_info(win, file_name, insert=''):
    """
    Clear way to show info message into screen.
    :param win:
    :return:
    """
    msg = read_text_from_file(file_name, insert=insert)
    msg = visual.TextStim(win, color='black', text=msg,
                          height=20, wrapWidth=SCREEN_RES['width'])
    msg.draw()
    win.flip()
    key = event.waitKeys(keyList=['f7', 'return', 'space', 'left', 'right'])
    if key == ['f7']:
        abort_with_error(
            'Experiment finished by user on info screen! F7 pressed.')
    win.flip()


def abort_with_error(err):
    """
    Call if an error occured.
    """
    logging.critical(err)
    raise Exception(err)


# GLOBALS

RESULTS = list()  # list in which data will be colected
RESULTS.append(['PART_ID', 'Block number',  'Trial_no', 'Session type', 'Correctness', 'Target present', 'Reaction time','Target position']) # ... Results header

def main():
    global PART_ID  # PART_ID is used in case of error on @atexit, that's why it must be global

    # === Dialog popup ===
    info={'IDENTYFIKATOR': '', u'P\u0141EC': ['M', "K"], 'WIEK': '20'}
    dictDlg=gui.DlgFromDict(
        dictionary=info, title='Experiment title, fill by your name!')
    if not dictDlg.OK:
        abort_with_error('Info dialog terminated.')

    clock=core.Clock()
    # load config, all params are there
    conf=yaml.load(open('config.yaml', encoding='utf-8'))

    # === Scene init ===
    win=visual.Window(list(SCREEN_RES.values()), fullscr=False, monitor='testMonitor', units='pix',
                                       screen=0, color=conf['BACKGROUND_COLOR'])
    event.Mouse(visible=False, newPos=None, win=win)  # Make mouse invisible
    FRAME_RATE=get_frame_rate(win)

    # check if a detected frame rate is consistent with a frame rate for witch experiment was designed
    # important only if milisecond precision design is used
    if FRAME_RATE != conf['FRAME_RATE']:
        dlg=gui.Dlg(title="Critical error")
        dlg.addText(
            'Wrong no of frames detected: {}. Experiment terminated.'.format(FRAME_RATE))
        dlg.show()
        return None

    PART_ID=info['IDENTYFIKATOR'] + info[u'P\u0141EC'] + info['WIEK']
    logging.LogFile(join('results', PART_ID + '.log'),
                    level=logging.INFO)  # errors logging
    logging.info('FRAME RATE: {}'.format(FRAME_RATE))
    logging.info('SCREEN RES: {}'.format(SCREEN_RES.values()))

    # === Prepare stimulus here ===
    # create fix cross before matrix
    fix_cross = visual.TextStim(win, text='+', height=100, color=conf['FIX_CROSS_COLOR'])
    # === Training ===

    show_info(win, join('.', 'messages', 'hello.txt'))
    show_info(win, join('.', 'messages', 'before_training.txt'))
    
    # === Start pre-trial  stuff (Fixation cross etc.)===
    # display fix crox before matrix
    for _ in range(conf['FIX_CROSS_TIME']):
        fix_cross.draw()
        win.flip()
    
    # reset number of trials
    trial_no = 1
    
    # start training sessions
    for _ in range(conf['TRAINING_SESSIONS']):
        corr, target_present, rt, taget_position = run_trial(win, conf, clock)
        RESULTS.append([PART_ID, 0, trial_no, 'Training', corr, target_present, rt, taget_position])
        trial_no += 1
    
    win.flip()
    # white screen after tranining sessions
    core.wait(0.8)
    
    # === Experiment ===

    show_info(win, join('.', 'messages', 'before_experiment.txt'))
    
    for block_no in range(conf['NO_BLOCKS']):
        # show fix cross
        for _ in range(conf['FIX_CROSS_TIME']):
            fix_cross.draw()
            win.flip()
        
        # reset number of trials
        trial_no = 1    
        for _ in range(conf['EXPERIMENT_SESSIONS']):
            corr, target_present, rt, taget_position = run_trial(win, conf, clock)
            RESULTS.append([PART_ID, block_no, trial_no, 'Experiment', corr, target_present, rt, taget_position])
            trial_no += 1
        
        # don't show a white screen after the last experiment trial
        if block_no < conf['NO_BLOCKS'] - 1:
            win.flip()
            # show white screen after a finished session
            core.wait(0.8)
            # show a break image to relax a user
            show_image(win, os.path.join('.', 'images', 'break.jpg'),
                   size=(SCREEN_RES['width'], SCREEN_RES['height']))

        # === Cleaning time ===
    save_beh_results()
    logging.flush()
    show_info(win, join('.', 'messages', 'end.txt'))
    win.close()


def create_matrix(win, conf):
    """
    Method generates a matrix with distractors and a target. Target generated at a fixed random rate.
    :param win: Name of file to read
    :param conf:
    :return: matrix (generated matrix), target_present, taget_position
    """
    
    w, h = conf['MATRIX_SIZE'], conf['MATRIX_SIZE']
    # specify a number of distractors
    distractors_num = conf['DISTRACTOR_NUM']
    # check if target is present in the matrix - at a given probability
    # if a target is present then the number of distractors is incremented by 1
    target_present = random.randint(1,100) <= conf['TARGET_PROBABILITY']
    if target_present:
        distractors_num = distractors_num + 1
    
    distractor_position_index = 0
    # generate positions in the matrix that contain a distractor
    distractor_positions = random.sample(range(w*h), distractors_num)
    
    matrix = [[0 for x in range(w)] for y in range(h)] 
    taget_position = [-1,-1]
    for i in range(h):
        for j in range(w):
            if distractor_position_index in distractor_positions:
                # if this is a position (i,j) where a target is present
                # if a target is present then it's always at 0 position in distractor_positions array
                if target_present and distractor_position_index == distractor_positions[0]:
                    matrix[i][j] = visual.TextStim(win, text='A', height=conf['TARGET_SIZE'], color=conf['TARGET_COLOR'])
                    taget_position = [i,j]
                else:
                    # target is not present so the position contains a distractor
                    # distracotrs appear for certain probababilities, an orange A is the most common distracotor
                    distractor_type = random.randint(0,9)
                    if distractor_type <= 5:
                        matrix[i][j] = visual.TextStim(win, text='A', height=conf['DISTRACTOR_SIZE'], color=conf['DISTRACTOR_COLOR'])
                    elif distractor_type <= 7:
                        matrix[i][j] = visual.TextStim(win, text='A', ori=180, height=conf['DISTRACTOR_SIZE'], color=conf['DISTRACTOR_COLOR'])
                    else:
                        matrix[i][j] = visual.TextStim(win, text='A', ori=180, height=conf['DISTRACTOR_SIZE'], color=conf['TARGET_COLOR'])
            else:
                # if a position in matrix contains no distractor then the empty/white space is rendered
                matrix[i][j] = visual.TextStim(win, text='', height=conf['DISTRACTOR_SIZE'])
                
            distractor_position_index += 1
            
    return matrix, target_present, taget_position
    
def run_trial(win, conf, clock):
    """
    Prepare and present single trial of procedure.
    Input (params) should consist all data need for presenting stimuli.
    If some stimulus (eg. text, label, button) will be presented across many trials.
    Should be prepared outside this function and passed for .draw() or .setAutoDraw().

    All behavioral data (reaction time, answer, etc. should be returned from this function)
    """

    # === Prepare trial-related stimulus ===
    matrix, target_present, taget_position = create_matrix(win, conf)
    
    # === Start trial ===
    # This part is time-crucial. All stims must be already prepared.
    # Only .draw() .flip() and reaction related stuff goes there.
    event.clearEvents()
    # make sure, that clock will be reset exactly when stimuli will be drawn
    win.callOnFlip(clock.reset)
        
    for _ in range(conf['STIM_TIME']):  # present stimuli
        reaction=event.getKeys(keyList=list(
            conf['REACTION_KEYS']), timeStamped=clock)
        if reaction:  # break if any button was pressed
            break   
        for i in range(len(matrix)):
            for j in range(len(matrix[i])):
                matrix[i][j] .pos = ((j-2) * matrix[i][j].height, (2-i) * matrix[i][j].height)
                matrix[i][j] .draw()
        win.flip()

    # === Trial ended, prepare data for send  ===
    if reaction:
        if target_present:
            corr = True
            rt=reaction[0][1]
        else:
            corr = False
            rt = reaction[0][1]
    else:
        if target_present:
            corr = False
            rt=-1
        else:
            corr = True
            rt=-1

    return corr, target_present, rt, taget_position  # return all data collected during trial

if __name__ == '__main__':
    PART_ID=''
    SCREEN_RES=get_screen_res()
    main()
