"""Defines the neural network, losss function and metrics"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

outputs_print=[]
labels_print=[]

class Net(nn.Module):
    """
    This is the standard way to define your own network in PyTorch. You typically choose the components
    (e.g. LSTMs, linear layers etc.) of your network in the __init__ function. You then apply these layers
    on the input step-by-step in the forward function. You can use torch.nn.functional to apply functions
    such as F.relu, F.sigmoid, F.softmax, F.max_pool2d. Be careful to ensure your dimensions are correct after each
    step. You are encouraged to have a look at the network in pytorch/nlp/model/net.py to get a better sense of how
    you can go about defining your own network.
    The documentation for all the various components available o you is here: http://pytorch.org/docs/master/nn.html
    """

    def __init__(self, params):
        """
        We define an convolutional network that predicts the sign from an image. The components
        required are:
        - an embedding layer: this layer maps each index in range(params.vocab_size) to a params.embedding_dim vector
        - lstm: applying the LSTM on the sequential input returns an output for each token in the sentence
        - fc: a fully connected layer that converts the LSTM output for each token to a distribution over NER tags
        Args:
            params: (Params) contains num_channels
        """
        super(Net, self).__init__()
        mult=3
        self.num_channels = params.num_channels
        
        # each of the convolution layers below have the arguments (input_channels, output_channels, filter_size,
        # stride, padding). We also include batch normalisation layers that help stabilise training.
        # For more details on how to use these layers, check out the documentation.
        self.conv1 = nn.Conv2d(3, self.num_channels, 3, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(self.num_channels)
        self.conv2 = nn.Conv2d(self.num_channels, self.num_channels*mult, 3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(self.num_channels*mult)
        self.conv3 = nn.Conv2d(self.num_channels*mult, self.num_channels*2*mult, 3, stride=1, padding=1)
        self.bn3 = nn.BatchNorm2d(self.num_channels*2*mult)
        self.conv4 = nn.Conv2d(self.num_channels, self.num_channels*2*mult, 3, stride=1, padding=1)
        self.bn4 = nn.BatchNorm2d(self.num_channels*2*mult)
        self.conv5 = nn.Conv2d(self.num_channels*2*mult, self.num_channels*3*mult, 3, stride=1, padding=1)
        self.bn5 = nn.BatchNorm2d(self.num_channels*3*mult)
        self.conv6 = nn.Conv2d(self.num_channels*mult, self.num_channels*3*mult, 3, stride=1, padding=1)
        self.bn6 = nn.BatchNorm2d(self.num_channels*3*mult)
        self.conv7 = nn.Conv2d(self.num_channels, self.num_channels*3*mult, 3, stride=1, padding=1)
        self.bn7 = nn.BatchNorm2d(self.num_channels*3*mult)
        
        # 2 fully connected layers to transform the output of the convolution layers to the final output
        self.fc1 = nn.Linear(8*8*self.num_channels*3*mult*4, self.num_channels*3*mult)
        self.fcbn1 = nn.BatchNorm1d(self.num_channels*3*mult)
        self.fc2 = nn.Linear(self.num_channels*3*mult, 11) #changing from 6 in order to fit our project        
        self.dropout_rate = params.dropout_rate

    def forward(self, s):
        """
        This function defines how we use the components of our network to operate on an input batch.
        Args:
            s: (Variable) contains a batch of images, of dimension batch_size x 3 x 64 x 64 .
        Returns:
            out: (Variable) dimension batch_size x 10 with the log probabilities for the labels of each image.
        Note: the dimensions after each step are provided
        """
        mult=3                                                  #-> batch_size x 3 x 64 x 64
        # we apply the convolution layers, followed by batch normalisation, maxpool and relu x 3
        s = self.bn1(self.conv1(s))                         # batch_size x num_channels x 64 x 64
        s = F.relu(s)                      # batch_size x num_channels x 32 x 32
        residual = s
        residual_3 = residual
        s = self.bn2(self.conv2(s))                         # batch_size x num_channels*2 x 32 x 32
        s = F.relu(F.max_pool2d(s, 2))                      # batch_size x num_channels*2 x 16 x 16
        residual_2 = s
        s = self.bn3(self.conv3(s))                         # batch_size x num_channels*4 x 16 x 16
        
        residual = self.bn4(self.conv4(residual))
        residual =F.max_pool2d(residual, 2)
        s = F.relu(F.max_pool2d(s + residual, 2))                      # batch_size x num_channels*4 x 8 x 8

        s = self.bn5(self.conv5(s))
        
        residual_2 = self.bn6(self.conv6(residual_2))
        residual_2 = F.max_pool2d(residual_2, 2)
    
        residual_3 = self.bn7(self.conv7(residual_3))
        residual_3 = F.max_pool2d(residual_3, 4)
        s = F.relu(F.max_pool2d(s + residual_2 + residual_3, 2))
        
        #print(np.shape(s))
        
        # flatten the output for each image
        s = s.view(-1, 8*8*self.num_channels*3*mult*4)             # batch_size x 8*8*num_channels*4

        # apply 2 fully connected layers with dropout
        s = F.dropout(F.relu(self.fcbn1(self.fc1(s))), 
            p=self.dropout_rate, training=self.training)    # batch_size x self.num_channels*4
        s = self.fc2(s)                                     # batch_size x 6 <-This needs to be 11!

        # apply log softmax on each image's output (this is recommended over applying softmax
        # since it is numerically more stable)
        return F.log_softmax(s, dim=1)


def loss_fn(outputs, labels):
    """
    Compute the cross entropy loss given outputs and labels.
    Args:
        outputs: (Variable) dimension batch_size x 11 - output of the model
        labels: (Variable) dimension batch_size, where each element is a value in [0, 1, 2, 3, 4, 5,..., 10]
    Returns:
        loss (Variable): cross entropy loss for all images in the batch
    Note: you may use a standard loss function from http://pytorch.org/docs/master/nn.html#loss-functions. This example
          demonstrates how you can easily define a custom loss function.
    """
    num_examples = outputs.size()[0]
    return -torch.sum(outputs[range(num_examples), labels])/num_examples


def accuracy(outputs, labels):
    """
    Compute the accuracy, given the outputs and labels for all images.
    Args:
        outputs: (np.ndarray) dimension batch_size x 6 - log softmax output of the model
        labels: (np.ndarray) dimension batch_size, where each element is a value in [0, 1, 2, 3, 4, 5,... 10]
    Returns: (float) accuracy in [0,1]
    """
    outputs = np.argmax(outputs, axis=1)
    return np.sum(outputs==labels)/float(labels.size)

#adding F1 Score, obtained from:
#https://codereview.stackexchange.com/questions/36096/implementing-f1-score
def f1_score(outputs, labels):
    outputs = np.argmax(outputs, axis=1)
    labels=set(labels)
    outputs=set(outputs)

    tp=len(labels.intersection(outputs))
    fp=len(outputs.difference(labels))
    fn=len(labels.difference(outputs))

    if tp>0:
        precision=float(tp)/(tp+fp)
        recall=float(tp)/(tp+fn)


        return 2*((precision*recall)/(precision+recall))
    else:
        return 0
    

# maintain all metrics required in this dictionary- these are used in the training and evaluation loops
metrics = {
    'accuracy': accuracy, 'f1_score' : f1_score 
    # could add more metrics such as accuracy for each token type
}
