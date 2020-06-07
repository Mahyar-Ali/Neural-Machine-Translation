# Neural-Machine-Translation
A Seq2Seq model for Neural Machine Translation with Attention for trasnslating
any lanuguage.  
--------------------------------------------------------------------------
Model Architecture:-

Model: "encoder"
_________________________________________________________________
Layer (type)                 Output Shape              Param #   
=================================================================
embedding (Embedding)        multiple                  3327744   
_________________________________________________________________
gru (GRU)                    multiple                  3938304   
=================================================================
Total params: 7,266,048
Trainable params: 7,266,048
Non-trainable params: 0
_________________________________________________________________

Model: "decoder"
_________________________________________________________________
Layer (type)                 Output Shape              Param #   
=================================================================
embedding_1 (Embedding)      multiple                  1745152   
_________________________________________________________________
gru_1 (GRU)                  multiple                  7084032   
_________________________________________________________________
dense_3 (Dense)              multiple                  6987425   
_________________________________________________________________
bahdanau_attention_1 (Bahdan multiple                  2100225   
=================================================================
Total params: 17,916,834
Trainable params: 17,916,834
Non-trainable params: 0
_________________________________________________________________

-------------------------------------------------------------------------------

For this example the model was trained for only ten epochs on the spa-eng dataset
(50,000 examples). Still, the model managed to achieve very good results. This 
model can be considered as a blueprint and can be used to translate between any
language.

--------------------------------------------------------------------------------

Author : m.mahyar.ali 
