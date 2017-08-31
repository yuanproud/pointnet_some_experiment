# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-
"""
Created on Wed Aug 16 14:31:29 2017

@author: nvlab
"""

import tensorflow as tf
import numpy as np
import math
import sys
import os
import random
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, '../utils'))
import tf_util
from transform_nets import input_transform_net, feature_transform_net

def placeholder_inputs(batch_size, num_point):
    pointclouds_pl = tf.placeholder(tf.float32, shape=(batch_size, num_point, 3))
    labels_pl = tf.placeholder(tf.int32, shape=(batch_size))
    return pointclouds_pl, labels_pl


def get_model(point_cloud, is_training, bn_decay=None):
    """ Classification PointNet, input is BxNx3, output Bx40 """
    batch_size = point_cloud.get_shape()[0].value
    num_point = point_cloud.get_shape()[1].value
    end_points = {}
    
    var1 = tf.random_normal([32,1024,1,64], mean=0.0, stddev=1.0, dtype=tf.float32)
    var1 = tf.contrib.layers.fully_connected(var1, 64, activation_fn=tf.nn.relu)
    var1 = tf.contrib.layers.fully_connected(var1, 64, activation_fn=tf.nn.relu)

    with tf.variable_scope('transform_net1') as sc:
        transform = input_transform_net(point_cloud, is_training, bn_decay, K=3)
        #transform.shape = (32,3,3)
    point_cloud_transformed = tf.matmul(point_cloud, transform)
    #input_image = tf.expand_dims(point_cloud_transformed, -1)
    
    rotate_matric_ = rotate(k = 3)
    input_image_rotate = tf.matmul(point_cloud_transformed, rotate_matric_)
    input_image_rotate = tf.expand_dims(input_image_rotate, -1)
    
    net = tf_util.conv2d(input_image_rotate, 64, [1,3],
                         padding='VALID', stride=[1,1],
                         bn=True, is_training=is_training,
                         scope='conv1', bn_decay=bn_decay)
    
    net = tf.concat(3, [net, var1])
    net = tf_util.conv2d(net, 64, [1,1],
                         padding='VALID', stride=[1,1],
                         bn=True, is_training=is_training,
                         scope='conv2', bn_decay=bn_decay)
    #print(net.shape)                     
    with tf.variable_scope('transform_net2') as sc:
        transform = feature_transform_net(net, is_training, bn_decay, K=64)
    end_points['transform'] = transform
    net_transformed = tf.matmul(tf.squeeze(net), transform)
    net_transformed = tf.expand_dims(net_transformed, [2])

    #net = tf.add(net, var2)
    net = tf_util.conv2d(net_transformed, 64, [1,1],
                         padding='VALID', stride=[1,1],
                         bn=True, is_training=is_training,
                         scope='conv3', bn_decay=bn_decay)
                         
    #net = tf.add(net, var3)
    net = tf_util.conv2d(net, 128, [1,1],
                         padding='VALID', stride=[1,1],
                         bn=True, is_training=is_training,
                         scope='conv4', bn_decay=bn_decay)
                         
    #net = tf.add(net, var4)
    net = tf_util.conv2d(net, 1024, [1,1],
                         padding='VALID', stride=[1,1],
                         bn=True, is_training=is_training,
                         scope='conv5', bn_decay=bn_decay)
    #print(net.shape)

    # Symmetric function: max pooling
    net = tf_util.max_pool2d(net, [num_point,1],
                             padding='VALID', scope='maxpool')

    net = tf.reshape(net, [batch_size, -1])
    net = tf_util.fully_connected(net, 512, bn=True, is_training=is_training,
                                  scope='fc1', bn_decay=bn_decay)
    net = tf_util.dropout(net, keep_prob=0.7, is_training=is_training,
                          scope='dp1')
    net = tf_util.fully_connected(net, 256, bn=True, is_training=is_training,
                                  scope='fc2', bn_decay=bn_decay)
    net = tf_util.dropout(net, keep_prob=0.7, is_training=is_training,
                          scope='dp2')
    net = tf_util.fully_connected(net, 40, activation_fn=None, scope='fc3')

    return net, end_points


def get_loss(pred, label, end_points, reg_weight=0.001):
    """ pred: B*NUM_CLASSES,
        label: B, """
    loss = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=pred, labels=label)
    classify_loss = tf.reduce_mean(loss)
    
    #loss2 = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=pred2, labels=label)
    #classify_loss2 = tf.reduce_mean(loss2)
    
    tf.summary.scalar('classify loss', classify_loss)
    #tf.summary.scalar('classify loss2', classify_loss2)

    # Enforce the transformation as orthogonal matrix
    transform = end_points['transform'] # BxKxK
    K = transform.get_shape()[1].value
    mat_diff = tf.matmul(transform, tf.transpose(transform, perm=[0,2,1]))
    mat_diff -= tf.constant(np.eye(K), dtype=tf.float32)
    mat_diff_loss = tf.nn.l2_loss(mat_diff) 
    tf.summary.scalar('mat loss', mat_diff_loss)

    return classify_loss + mat_diff_loss * reg_weight

def rotate(k):
    q = random.uniform(0, 2*math.pi)
    rotate_matric = np.array([[1,0,0],[0,math.cos(q),-1*math.sin(q)],[0,math.sin(q),math.cos(q)]])
    rotate_matric_ = rotate_matric[np.newaxis, ...]    
    for i in range(1,6):
        rotate_matric_ = np.concatenate((rotate_matric_,rotate_matric_),0)        
    rotate_matric_ = rotate_matric_.astype(np.float32)
       
    return rotate_matric_
    
if __name__=='__main__':
    with tf.Graph().as_default():
        inputs = tf.zeros((32,1024,3))
        outputs = get_model(inputs, tf.constant(True))
        print(outputs)

"""
Created on Sun Aug 27 17:09:11 2017

@author: nvlab
"""

