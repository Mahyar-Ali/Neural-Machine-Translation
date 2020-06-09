# -*- coding: utf-8 -*-
"""Copy of Neural Machine Translation.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/github/Mahyar-Ali/Neural-Machine-Translation/blob/master/Neural_Machine_Translation.ipynb
"""

#Importing all the dependencies
import tensorflow as tf

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from sklearn.model_selection import train_test_split

import unicodedata
import re
import numpy as np
import os
import io
import time

#Downloading and Extracting the dataset
path_to_zip = tf.keras.utils.get_file(
    'spa-eng.zip', origin='http://storage.googleapis.com/download.tensorflow.org/data/spa-eng.zip',
    extract=True)

path_to_file = os.path.dirname(path_to_zip)+"/spa-eng/spa.txt"

#Make sure that you have the preprocees.py file which contain some helper functions
#Download the file from https://github.com/Mahyar-Ali/Neural-Machine-Translation/blob/master/preprocess.py
import preprocess

#We will be using the first 50000 examples from the dataset
num_examples=50000
#Using the preprocess module to preprocess the data
input_tensor, target_tensor, inp_lang, targ_lang = preprocess.load_dataset(path_to_file,num_examples)
max_length_targ, max_length_inp = target_tensor.shape[1], input_tensor.shape[1]

# Creating training and validation sets using an 80-20 split
input_tensor_train, input_tensor_val, target_tensor_train, target_tensor_val = train_test_split(input_tensor, target_tensor, test_size=0.2)

# Show length
print(len(input_tensor_train), len(target_tensor_train), len(input_tensor_val), len(target_tensor_val))

#This function is to just display how the data is encoded
def convert(lang, tensor):
  for t in tensor:
    if t!=0:
      print ("%d ----> %s" % (t, lang.index_word[t]))

print ("Input Language; index to word mapping")
convert(inp_lang, input_tensor_train[0])
print ()
print ("Target Language; index to word mapping")
convert(targ_lang, target_tensor_train[0])

#Size of buffer while shuffling the data
BUFFER_SIZE = len(input_tensor_train)

BATCH_SIZE = 64
steps_per_epoch = len(input_tensor_train)//BATCH_SIZE

#size of the embedding layer
embedding_dim = 256
#No. of hidden units in the GRU
units = 1024

#Size of the Vocabulary at encoder (i.e., Spanish)
vocab_inp_size = len(inp_lang.word_index)+1
#Size of the Vocabulary at Decoder (i.e., English)
vocab_tar_size = len(targ_lang.word_index)+1

#Creating a Tensorflow Dataset Object
dataset = tf.data.Dataset.from_tensor_slices((input_tensor_train, target_tensor_train)).shuffle(BUFFER_SIZE)
dataset = dataset.batch(BATCH_SIZE, drop_remainder=True)

example_input_batch, example_target_batch = next(iter(dataset))
example_input_batch.shape, example_target_batch.shape

#Creating a Custom Layer
class Encoder(tf.keras.Model):
  def __init__(self,vocab_size,embedding_dim,enc_units,batch_sz):
    super(Encoder,self).__init__()
    '''
    vocab_size : Size of the Vocabulary
    embedding_dim : Size of the Embedding layer
    enc_units : No. of Hidden Units in the GRU
    batch_sz : Batch Size
    '''
    self.enc_units = enc_units
    self.batch_sz = batch_sz
    #Embedding Layer
    self.embedding = tf.keras.layers.Embedding(vocab_size,embedding_dim)
    #GRU
    self.gru = tf.keras.layers.GRU(self.enc_units,
                                   return_sequences=True,
                                   return_state=True,
                                   recurrent_initializer='glorot_uniform')

  #Function that will create the model with the layers 
  def call(self,inp,hidden):
      '''
      inp: input to the model.i.e., vectorized form of the spanish sentence
      hidden: intial hidden_state of the gru.
      '''
      x = self.embedding(inp)
      output,state = self.gru(x,initial_state=hidden)
      return output,state

#Function to initialize the initial hidden state of the gru
  def initialize_hidden_state(self):
    return tf.zeros([self.batch_sz,self.enc_units])

encoder = Encoder(vocab_inp_size, embedding_dim, units, BATCH_SIZE)

sample_hidden = encoder.initialize_hidden_state()
sample_output, sample_hidden = encoder(example_input_batch, sample_hidden)
print ('Encoder output shape: (batch size, sequence length, units) {}'.format(sample_output.shape))
print ('Encoder Hidden state shape: (batch size, units) {}'.format(sample_hidden.shape))

#Creating a Custom Layer
class BahdanauAttention(tf.keras.layers.Layer):
  def __init__(self,units):
    super(BahdanauAttention,self).__init__()
    '''
    units: Number of hidden Units , represented as "h_u" in the article
    '''
    self.units = units
    self.W1 = tf.keras.layers.Dense(self.units)
    self.W2 = tf.keras.layers.Dense(self.units)
    self.V = tf.keras.layers.Dense(1)

   #Function that will create the model with the layers 
  def call(self,query,values):
    '''
    query : The hidden state of the GRUs "refer to B"
    values: The output of the GRUs "refer to A"
    '''
    #To ccnvert the query from 2-D to 3-D
    query_with_time_axis = tf.expand_dims(query,1)
    
    #Implementation of STEP-1
    '''Both query and Values are passed into a dense layer with units "h_u"
    and,added together,after that a tanh activation is applied and finally
    the result is passed into a dense layer with one neuron. ''' 
    score = self.V(tf.keras.activations.tanh(
                                        self.W1(query_with_time_axis)+
                                        self.W2(values)
                                  ))
    #Implementaion of STEP-2
    attention_weights = tf.keras.activations.softmax(score,1)

    #Implementation of STEP-3 
    context_vector =  attention_weights*values
    context_vector = tf.reduce_sum(context_vector,1)

    return context_vector,attention_weights

attention_layer = BahdanauAttention(10)
attention_result,attention_weights = attention_layer(sample_hidden,sample_output)

print("Attention result shape: (batch size, units) {}".format(attention_result.shape))
print("Attention weights shape: (batch_size, sequence_length, 1) {}".format(attention_weights.shape))

#Creating a Custom Layer
class Decoder(tf.keras.Model):
  def __init__(self,vocab_size,embedding_dim,dec_units,batch_sz):
    super(Decoder,self).__init__()
    '''
    vocab_size : Size of vocabulary for the resulting sentence (i.e.,English)
    embedding_dim : Size of the Embedding layer
    enc_units : No. of Hidden Units in the GRU
    batch_sz : Batch Size
    '''
    self.dec_units = dec_units
    self.batch_sz = batch_sz
    #Embedding layer
    self.embedding = tf.keras.layers.Embedding(vocab_size,embedding_dim)
    #GRU
    self.gru =              tf.keras.layers.GRU(dec_units,
                                               return_sequences=True,
                                               return_state=True,
                                               recurrent_initializer='glorot_uniform')
    #Dense Layer
    self.fc = tf.keras.layers.Dense(vocab_size)
    #An Instance of attention layer 
    self.attention = BahdanauAttention(self.dec_units)
  #Function that will create the model with the layers 
  def call(self,x,hidden,enc_output):
    '''
    x :Input to the decoder
    hidden: Hidden state of the GRU
    enc_output: Output from the encoder layer (not attention layer)
    '''

    '''I combined the attention layer with the decoder layer.So that the attention 
    is calculated at the decoder.'''
    #Calculate attention vector
    context_vector,attention_weights = self.attention(hidden,enc_output)

    #Embedding Layer
    x = self.embedding(x)

    #Concating the attention vector with x
    x = tf.concat([tf.expand_dims(context_vector,1),x],axis=-1)

    output,state = self.gru(x)

    #just Reshaaping the output i.e., (Batch_Size,Vocab_Dims)
    output = tf.reshape(output,(-1,output.shape[2]))
    #Passing it through a Dense layer
    x = self.fc(output)
    return x,state,attention_weights

decoder = Decoder(vocab_tar_size, embedding_dim, units, BATCH_SIZE)
sample_decoder_output,_,_ = decoder(tf.random.uniform((BATCH_SIZE, 1)),
                                      sample_hidden, sample_output)

print ('Decoder output shape: (batch_size, vocab size) {}'.format(sample_decoder_output.shape))

#creating the optimizer Object
optimizer= tf.keras.optimizers.Adam()

#Creating the Loss Object
loss_object= tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True,reduction='none')

'''We will be taking bulks of data from the dataset while training
This function just uses the Loss Object to deal with a bulk of
data,and calculate loss for the whole bulk'''
def loss_function(real,pred):
  mask = tf.math.logical_not(tf.math.equal(real,0))
  loss_ = loss_object(real,pred)

  mask = tf.cast(mask,dtype=loss_.dtype)
  loss_ *= mask

  return tf.reduce_mean(loss_)

#Path where the checkpoint is to be stored
checkpoint_dir = './training_checkpoints'

#To store the index of the checkpoint
checkpoint_prefix = os.path.join(checkpoint_dir,'ckpt')

#Checkpoint Object that will store the state of each layer
checkpoint = tf.train.Checkpoint(optimizer=optimizer,
                                 encoder=encoder,
                                 decoder=decoder)
# we combined the Attention layer with the decoder layer so we don't
#have to save it explicitly.

def train_step(inp,targ,enc_hidden):
  loss=0
  with tf.GradientTape() as tape:
    #Step-4
    enc_output,enc_hidden = encoder(inp,enc_hidden)
    dec_hidden = enc_hidden

    #Step-7
    dec_input = tf.expand_dims([targ_lang.word_index['<start>']]*BATCH_SIZE,1)
    #We have to concatenate the decoder input with the attention vector
    #So we have to convert it into 2-D by expanding Dims.

    for t in range(1,targ.shape[1]):
      predictions,dec_hidden,_ = decoder(dec_input,dec_hidden,enc_output)

      #Increment the loss,targ[:,t] means we are calculating loss for the 
      #t'th word in all batches at the same time.(BULK!)
      loss += loss_function(targ[:,t],predictions)

      #We have to concatenate the decoder input with the attention vector
      #So we have to convert it into 2-D by expanding Dims.
      dec_input = tf.expand_dims(targ[:,t],1)

  batch_loss = (loss / int(targ.shape[1]))

  #Get all the trainable variables
  variables = encoder.trainable_variables + decoder.trainable_variables
  #Calculate Derivative
  gradients = tape.gradient(loss, variables)
  #Apply the gradients
  optimizer.apply_gradients(zip(gradients, variables))

  return batch_loss

EPOCH=10
for epoch in range(EPOCH):
  #To calculate time taken for each epoch
  start = time.time()
  enc_hidden = encoder.initialize_hidden_state()
  total_loss = 0
  #Taking batches of data
  for (batch,(inp,targ)) in enumerate(dataset.take(steps_per_epoch)):
    batch_loss = train_step(inp, targ, enc_hidden)
    total_loss += batch_loss
    #Printing stats after 100 batches
    if batch % 100 == 0:
      print('Epoch {} Batch {} Loss {:.4f}'.format(epoch + 1,
                                                   batch,
                                                   batch_loss.numpy()))
  # saving (checkpoint) the model every 2 epochs
  if (epoch + 1) % 2 == 0:
    checkpoint.save(file_prefix = checkpoint_prefix)
  #Printing some stats.
  print('Epoch {} Loss {:.4f}'.format(epoch + 1,
                                      total_loss / steps_per_epoch))
  print('Time taken for 1 epoch {} sec\n'.format(time.time() - start))

#Function that translates a given sentence
def evaluate(sentence):
  #This is to store the attention vector for plotting.Ignore this
  attention_plot = np.zeros((max_length_targ, max_length_inp))

  #Preprocessing the sentence.Steps 2,3 and 4
  sentence = preprocess.preprocess_sentence(sentence)
  inputs = [inp_lang.word_index[i] for i in sentence.split(' ')]
  inputs = tf.keras.preprocessing.sequence.pad_sequences([inputs],
                                                         maxlen=max_length_inp,
                                                          padding='post')
  #Step 4
  inputs = tf.convert_to_tensor(inputs)

  #creating a string to store the translated sentence
  result = ''

  #Step 5
  hidden = [tf.zeros((1, units))]
  enc_out, enc_hidden = encoder(inputs, hidden)
  dec_hidden = enc_hidden

  #Step 6
  dec_input = tf.expand_dims([targ_lang.word_index['<start>']], 0)

  #Step 7
  for t in range(max_length_targ):
    predictions, dec_hidden, attention_weights = decoder(dec_input,
                                                         dec_hidden,
                                                         enc_out)

    # storing the attention weights to plot later on.Ignore it
    attention_weights = tf.reshape(attention_weights, (-1, ))
    attention_plot[t] = attention_weights.numpy()

    #Step 8
    predicted_id = tf.argmax(predictions[0]).numpy()

    result += targ_lang.index_word[predicted_id] + ' '

    if targ_lang.index_word[predicted_id] == '<end>':
      return result, sentence, attention_plot

    # the predicted ID is fed back into the model
    dec_input = tf.expand_dims([predicted_id], 0)

  #Return the Original Sentence,Translated Sentence and the history of attention weights
  return result, sentence, attention_plot

sentence = u'hace mucho frio aqui.'
translation,_,_ = evaluate(sentence)
print(translation)

"""# Visualizing Some Results."""

# function for plotting the attention weights
def plot_attention(attention, sentence, predicted_sentence):
  fig = plt.figure(figsize=(10,10))
  ax = fig.add_subplot(1, 1, 1)
  ax.matshow(attention, cmap='viridis')

  fontdict = {'fontsize': 14}

  ax.set_xticklabels([''] + sentence, fontdict=fontdict, rotation=90)
  ax.set_yticklabels([''] + predicted_sentence, fontdict=fontdict)

  ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
  ax.yaxis.set_major_locator(ticker.MultipleLocator(1))

  plt.show()

def translate(sentence):
  result, sentence, attention_plot = evaluate(sentence)

  print('Input: %s' % (sentence))
  print('Predicted translation: {}'.format(result))

  attention_plot = attention_plot[:len(result.split(' ')), :len(sentence.split(' '))]
  plot_attention(attention_plot, sentence.split(' '), result.split(' '))

checkpoint.restore(tf.train.latest_checkpoint(checkpoint_dir))

translate(u'hace mucho frio aqui.')

translate(u'¿todavia estan en casa?')