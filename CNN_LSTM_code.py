#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import pandas as pd
import os
import glob
import keras
from scipy import misc
from PIL import Image
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import xml.etree.ElementTree as ET
from keras.layers import Dense
from keras.layers import LSTM
from keras.models import Sequential, Model
from keras.preprocessing import sequence
from keras import preprocessing, layers
from keras.utils.np_utils import to_categorical
from keras.layers.embeddings import Embedding
from keras.layers import Input, Activation, Dense
from keras.layers import LSTM, GRU
from keras.regularizers import l2
from keras.layers.core import Flatten, Dropout
from keras.layers import Conv2D, MaxPool2D, BatchNormalization #, GlobalAveragePooling1D
from keras.optimizers import SGD

print(keras.__version__)
np.random.seed(15)


# for the assignment we had 48k training data

# Start with analyzing/preprocessing the SVG files
# Loading the SVG test data and removing all unusefull data from the SVG code to make the shortest possible sequence


train_svg_dir = 'C:/Users/flori/Downloads/Python_test/train/svg'

def load_string_svg(file_dir):
    read_files = glob.glob(os.path.join(file_dir, '*.svg'))
    svg_strings = []
    
    for i in read_files:
        with open(i, 'r') as file:
            temp = file.read()
            svg_strings.append(temp)
    
    return svg_strings


def load_array_svg(svg_strings):
    svg_list = []
    
    for i in svg_strings:
        root = ET.fromstring(i)
        temp = [float(111)]
        for j in root:
            values = list(j.attrib.values())
            for h in values:
                temp.append(h)
        temp.append(float(999))
        temp = np.array(temp)
        svg_list.append(temp)
    
    svg_array = np.array(svg_list)
    
    return svg_array

train_svg_array_data = load_array_svg(np.array(load_string_svg(train_svg_dir)))
print(train_svg_array_data.shape)


# The data only has rectangles and ellipses in the PNG files, but some shapes are hidden behind others (completly hidden). 
# This means that there are more figures described in the SVG file than you can see in the corresponding PNG image.
# This part of the code is used to draw each figure in every SVG code as an numpy array and stack those on top of each other for every
# SVG code, if one figure completly disapears, the data point is left out of the data we use for this assignment.

# shapes for drawing data in arrays from svg
# create a rectangle from SVG data

def rectangle(h, w, rx, ry):
    x_cord = int(rx)
    y_cord = int(ry)
    width, height = int(w), int(h)
    base = np.zeros((64,64))
    base[x_cord:(x_cord+ width), y_cord:(y_cord+height)] += 1
    return base

#create an ellipse from SVG data

def ellipse(cx, cy, rx, ry):
    cx, rx = cx, rx  # x center, half width                                       
    cy, ry = cy, ry  # y center, half height                                      
    x = np.arange(0, 64)  # x values of interest
    y = np.arange(0, 64)[:,None]  # y values of interest, as a "column" array
    ellipse = ((x-cx)/rx)**2 + ((y-cy)/ry)**2 <= 1  # True for points inside the ellipse
    return ellipse

# replacing layers from 1 svg layer to the next one

def replace_layer(layer1, layer2):
    new_layer = []
    for i, j in zip(range(0, len(layer1)),range(0, len(layer2))):
        for h in range(0, 64):
            if layer1[i][h] < layer2[j][h]:
                new_layer.append(layer2[j][h])
            else:
                new_layer.append(layer1[i][h])

    return np.array(new_layer).reshape((64,64))
    
# finding all the data with hidden shapes

def find_crap_data(svg_data):
    new_data = []

    for e, j in enumerate(svg_data):
        data_point = j[1:-1]
        # number of figures in datapoint
        num_fig = len(data_point) / 5
        # split into parts of 5: each 5 are 1 figure
        fig_code = np.split(data_point, num_fig)
        # making a base layer
        base_layer = np.zeros((64,64))
        unique_values_in_data = [0.0]
        actualy_unique_values = []

        for i in range(0, len(fig_code)):
            # check if it is a elipse
            if fig_code[i][0][-1:] == '0':
                # add value to all values used in datapoint
                unique_values_in_data.append(float(i+1))

                new_layer = (ellipse(float(fig_code[i][0]), float(fig_code[i][1]), float(fig_code[i][3]), 
                                     float(fig_code[i][4]))/1)*(i+1)
                if i == 0:
                    next_layer = replace_layer(base_layer, new_layer)
                else:
                    next_layer = replace_layer(next_layer, new_layer)
            else:
                unique_values_in_data.append(float(i+1))
                new_layer = (rectangle(float(fig_code[i][1]), float(fig_code[i][2]), float(fig_code[i][3]), 
                                     float(fig_code[i][4]))/1)*(i+1)
                if i == 0:
                    next_layer = replace_layer(base_layer, new_layer)
                else:
                    next_layer = replace_layer(next_layer, new_layer)

            actual_unique_values = list(np.unique(next_layer))  
        
        if actual_unique_values == unique_values_in_data:
            new_data.append(e)
            
    new_array = np.asarray(new_data)
    
    return new_array   
    
 index_delete = find_crap_data(train_svg_array_data)
 train_svg_update_data = train_svg_array_data[index_delete]
    
    
# finding the distribution of lengths of sequences in the data
# 47 is the longest string, but after length 32 there aren't alot of datapoints, so we cap this at 32 so our memory might survive this.

def length_distribution(data):
    text_len, text_dis = np.unique([len(i) for i in data], return_counts=True)
    y_position = np.arange(len(text_len))
    
    plt.figure(figsize=(8,5))
    plt.bar(y_position, text_dis, align='center', alpha=0.8)
    plt.xticks(y_position, text_len)
    plt.xlabel('Length')
    plt.title('Distribution of the length of sequences in the dataset')
    plt.show()
    
length_distribution(train_svg_update_data)

maxlen = 32

# find all unique values in the data and make a dictionary of classes of those values
# also add a start and an end class in there.

def find_unique_values(data):
    all_values = []
    for i in data:
        for j in i:
            all_values.append(j)
    unique_values = np.unique(all_values)
    
    return unique_values

unique_values = find_unique_values(train_svg_array_data)
#print(unique_values)

all_values = list(unique_values)
all_values.append(float(111))
all_values.append(float(999))

all_values = all_values
unique_values_class = list(np.arange(1, 25, 1))
class_dic = dict(zip(all_values, unique_values_class))
print(class_dic)


# changing all sequence values to their respective classes

def change_to_class(data, dic = class_dic, values = all_values, unique_classes = unique_values_class):

    unique_values_class = unique_classes
    all_values = values
    class_dic = dic
    
    new_data = [] 


    for i in data:
        temp_values = []
        for j in i:
            if j in all_values: 
                new_value =  class_dic[j]
                temp_values.append(float(new_value))

        temp_array = np.array(temp_values)
        new_data.append(temp_array)
    new_data = np.array(new_data)
    return new_data
            

train_svg_class_data = change_to_class(train_svg_update_data)   


# Loading and normalizing  the PNG files 

train_png_dir = 'C:/Users/flori/Downloads/Python_test/train/png'
test_png_dir = 'C:/Users/flori/Downloads/Python_test/test/png'

def load_png(file_dir):
    read_files = glob.glob(os.path.join(file_dir, '*.png'))
    png_data = []
    for i in read_files:
        image = Image.open(i).resize((32,32))
        png_data.append(np.asarray(image))
        
    return png_data

# normalizing the data, and removing all the crap data.

train_normalized_png_data = (np.array(load_png(train_png_dir)))[index_delete]/255
test_normalized_png_data = (np.array(load_png(test_png_dir)))/255

print(len(train_normalized_png_data))
print(len(test_normalized_png_data))


# creating train/test/val data

X_train, X_val_test, y_train, y_val_test = train_test_split(train_normalized_png_data, train_svg_class_data, 
                                                  test_size=0.20, random_state=1)

X_val, X_test, y_val, y_test = train_test_split(X_val_test, y_val_test, 
                                                  test_size=0.50, random_state=1)



# Creating the sequences to feed to the Network

def predict_things(image_data, svg_data, maxlen = 32, size = 25):
    assert(len(image_data) == len(svg_data))
    
    X_svg, X_image, y_svg = [], [], []
    for image, svg in zip(image_data, svg_data):
        for i in range(len(svg)):
            in_svg, out_svg = svg[:i], svg[i]
            in_svg  = preprocessing.sequence.pad_sequences([in_svg], maxlen=maxlen, padding='post').flatten()
            out_svg = to_categorical(out_svg, num_classes = size)
            
            X_svg.append(in_svg)
            X_image.append(image)
            y_svg.append(out_svg)
            
    X_svg = np.asarray(X_svg)
    X_image = np.asarray(X_image)
    y_svg = np.asarray(y_svg)
    
    print(" {} {} {}".format(X_svg.shape, X_image.shape, y_svg.shape))
    return(X_svg, X_image, y_svg)
    
X_svg_train, X_png_train, y_svg_train = predict_things(X_train, y_train)
X_svg_val, X_png_val, y_svg_val = predict_things(X_val, y_val)
X_svg_test, X_png_test, y_svg_test = predict_things(X_test, y_test)


# The network, a 4 CNN layers and 2 LSTM layers

png_shape = (32, 32, 4)
Embed_dim = 3
maxlen = 32
class_size = 25

#Input
input_png = Input(shape=png_shape)
input_svg  = Input(shape=(maxlen,))

#ENCODING CNN: PNG to vector
#Input/Conv_layer_1
png_features  = Conv2D(32, (3,3), strides=1, padding='same', activation='relu')(input_png)
png_features  = Conv2D(64, (3,3), strides=1, padding='same',activation='relu')(png_features)
png_features  = MaxPool2D((2,2), strides=(2,2))(png_features)

png_features  = Conv2D(64, (3,3), strides=1, padding='same',activation='relu')(png_features)
png_features  = Conv2D(64, (3,3), strides=1, padding='same', activation='relu')(png_features)
png_features  = BatchNormalization()(png_features)
#Flatten 
png_features  = Flatten()(png_features)

#Dense_png_feature_output
png_features  = Dense(128, activation='relu')(png_features)
png_features  = Dropout(0.10)(png_features)

#DECODER: vector to SEQ
# LSTM_1
svg_seq   = Embedding(class_size, Embed_dim, mask_zero=True)(input_svg)
svg_seq   = LSTM(128, return_sequences=True)(svg_seq)
svg_seq   = Dropout(0.20)(svg_seq)
#LSTM_2
svg_seq   = LSTM(128, recurrent_dropout=0.05)(svg_seq)
svg_seq   = Dropout(0.20)(svg_seq)

#Connect CNN to LSTM
decoder     = layers.add([png_features, svg_seq])
decoder     = layers.Dense(256, activation='relu')(decoder)
output_class = layers.Dense(class_size, activation='softmax')(decoder)
model = Model(inputs=[input_png, input_svg], outputs=output_class)

model.compile(loss='categorical_crossentropy', optimizer='rmsprop')

model.summary()

history_model = model.fit([X_png_train, X_svg_train], y_svg_train, epochs=6,
                                         batch_size=256, validation_data=([X_png_val, X_svg_val], y_svg_val))
                                         
model.save('model4CNN_2LSTM')


# converting all the sequences from the Network back to an SVG file that can produce a PNG

class_dic = class_dic
maxlen = 32

def pred_classes(png_data, dictionary, maxlen = 32):
    start_seq = dictionary['111.0']
    predicted_sequence = []
    
    for e, i in enumerate(png_data):
        pred_start = [start_seq]
        for j in range(0, maxlen):
            seq = preprocessing.sequence.pad_sequences([pred_start], maxlen, padding = 'post').flatten()
            pred = model.predict([[i], [seq]], verbose = 0)
            pred = np.argmax(pred)
            pred_start.append(pred)
        predicted_sequence.append(pred_start)
        print('\rProcessing input: ', e+1, end='')
    
    return np.asarray(predicted_sequence)

def convert_pred_class(pred_classes_data, dictionary):
    class_dic_inv = dict([(value, key) for key, value in class_dic.items()]) 
    conv_data = []
    
    for e, j in enumerate(pred_classes_data): 
        conv_values = []
        for i in j[1:]:
            if class_dic_inv[i] != '999.0':
                conv_values.append(class_dic_inv[i])
                if len(conv_values) == 32:
                    conv_data.append(conv_values[:30])
                    break
            else:
                conv_data.append(conv_values)
#                 if len(conv_data) != e+1:
#                     return print('cannot predict: ', e-1)   # to find out if it skips data, and what??
                break
    return conv_data
    
    
def output_svg(conv_values):
    output = []
    conv_values = np.asarray(conv_values)
    lenght = 5
    for i in conv_values:
        value_ar_5 = np.split(np.asarray(i), [5,10,15,20,25,30])
        value_ar_5_only_5 = []
        for h in value_ar_5:
            if len(h) == 5:
                value_ar_5_only_5.append(np.asarray(h))
        value_ar_5_correct = np.asarray(value_ar_5_only_5) 
        perfect_svg = '<?xml version="1.0" encoding="utf-8" ?><svg baseProfile="full" height="64" version="1.1" width="64" xmlns="http://www.w3.org/2000/svg" xmlns:ev="http://www.w3.org/2001/xml-events" xmlns:xlink="http://www.w3.org/1999/xlink"><defs />'
        for j in value_ar_5_correct:
            if j[0][-1:] != '0':
                rectangle_svg = '<rect fill="'+j[0]+'" height="'+j[1]+'" width="'+j[2]+'" x="'+j[3]+'" y="'+j[4]+'" />'
                perfect_svg += rectangle_svg
            else:
                elipse_svg = '<ellipse cx="'+j[0]+'" cy="'+j[1]+'" fill="'+j[2]+'" rx="'+j[3]+'" ry="'+j[4]+'" />'
                perfect_svg += elipse_svg
        perfect_svg_out = perfect_svg+'</svg>'
        output.append(perfect_svg_out)

    return output

#results

pred_class_labels = pred_classes(X_test, class_dic)
print('length output: ', len(pred_class_labels))

svg_files_list = output_svg(converted_to_values)
print(len(svg_files_list))

y_control = output_svg(convert_pred_class(y_test, class_dic))
len(y_control)

from evaluate import CER

CER(svg_files_list, y_control)


# How do the svg/png files look? 

#------------------------------------------------
# X_val picture
get_ipython().run_line_magic('pylab', 'inline')
n = 0            # change n to see your different outputs
name_github = 'github_' + str(n) +'.png'
imgplot = plt.imshow(X_test[n])
plt.savefig(name_github)
plt.show()


#--------------------------------------------------
#strings produced by png

print(y_control[n])
print()
print(svg_files_list[n])

from cairosvg import svg2png

svg_code = svg_files_list[n]
name_output = 'output_'+ str(n) + '.png'
svg2png(bytestring=svg_code,write_to=name_output)

#-------------------------------------------------------------

## The evaluation metric used for this task was the mean Character Error Rate (CER). This code scored a 0.122 error rate on the assignment 
    

