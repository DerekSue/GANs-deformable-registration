from __future__ import print_function, division

from tensorflow.contrib.image import dense_image_warp
import keras.backend as K

from keras.datasets import mnist

from keras.layers import BatchNormalization, Activation, MaxPooling3D, Cropping3D
from keras.layers import Input, Dense, Reshape, Flatten, Dropout, Concatenate, concatenate
from keras.layers import Lambda

from keras.layers.advanced_activations import LeakyReLU, ReLU
from keras.layers.convolutional import UpSampling3D, Conv3D

from keras.optimizers import RMSprop, Adam

from keras.models import Model
from keras.utils import to_categorical

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
import scipy
import sys



class GANImageRegistration:
    def __init__(self):
        self.crop_size_g = (64, 64, 64)
        self.crop_size_d = (24, 24, 24)
        self.channels = 1
        self.input_shape_g = self.crop_size_g + (self.channels,)
        self.input_shape_d = self.crop_size_d + (self.channels,)

        # Number of filters in the first layer of G and D
        self.gf = 64
        self.df = 64

        optimizer = Adam(0.0002, 0.5)

        # Build and compile the discriminator
        self.discriminator = self.build_discriminator()
        self.discriminator.compile(loss='binary_crossentropy',
            optimizer=optimizer,
            metrics=['accuracy'])


        # Build the generator
        self.generator = self.build_generator()

        # Input images
        img_S = Input(shape=self.input_shape_g) # subject image S
        img_T = Input(shape=self.input_shape_g) # template image T
        img_R = Input(shape=self.input_shape_d) # reference image R

        # By conditioning on T generate a warped transformation of S
        phi = self.generator([img_S, img_T])

        # warp the subject image
        warped_S = Lambda(self.warp)(img_S, phi)

        # Use Python partial to provide loss function with additional deformable field argument
        partial_gp_loss = partial(self.gradient_penalty_loss,
                          phi=phi)
        partial_gp_loss.__name__ = 'gradient_penalty' # Keras requires function names

        # For the combined model we will only train the generator
        self.discriminator.trainable = False

        # Discriminators determines validity of translated images / condition pairs
        valid = self.discriminator([warped_S, img_R])

        self.combined = Model(inputs=[img_S, img_T], outputs=valid)
        self.combined.compile(loss=self.partial_gp_loss,
                              #loss_weights=[1, 100],
                              optimizer=optimizer)


    """
    Generator Network
    """
    def build_generator(self):
        """U-Net Generator"""
        def g_layer(input_tensor,
                        n_filters,
                        kernel_size=(3, 3, 3),
                        batch_normalization=True,
                        scale=True,
                        padding='valid',
                        use_bias=False):
            """
            3D convolutional layer (+ batch normalization) followed by ReLu activation
            """
            layer = Conv3D(filters=n_filters,
                           kernel_size=kernel_size,
                           padding=padding,
                           use_bias=use_bias)(input_tensor)
            if batch_normalization:
                layer = BatchNormalization()(layer)
            layer = Activation('relu')(layer)

            return layer


        input_shape = self.input_shape_g
        inputs_S = Input(shape=input_shape)  # 64x64x64
        inputs_T = Input(shape=input_shape)  # 64x64x64

        # Concatenate subject image and template image by channels to produce input
        combined_imgs = Concatenate(axis=-1)([inputs_S, inputs_T])

        # down-sampling
        down1 = g_layer(input_tensor=combined_imgs, n_filters=self.gf, padding='valid')  # 62x62x62
        down1 = g_layer(input_tensor=down1, n_filters=self.gf, padding='valid')  # 60x60x60
        pool1 = MaxPooling3D(pool_size=(2, 2, 2))(down1)  # 30x30x30

        down2 = g_layer(input_tensor=pool1, n_filters=2 * self.gf, padding='valid')  # 28x28x28
        down2 = g_layer(input_tensor=down2, n_filters=2 * self.gf, padding='valid')  # 26x26x26
        pool2 = MaxPooling3D(pool_size=(2, 2, 2))(down2)  # 13x13x13

        center = g_layer(input_tensor=pool2, n_filters=4 * self.gf, padding='valid')  # 11x11x11
        center = g_layer(input_tensor=center, n_filters=4 * self.gf, padding='valid')  # 9x9x9

        # up-sampling
        up2 = concatenate(
            [Cropping3D(((4, 4), (4, 4), (4, 4)))(down2), UpSampling3D(size=(2, 2, 2))(center)])  # 18x18x18
        up2 = g_layer(input_tensor=up2, n_filters=2 * self.gf, padding='valid')  # 16x16x16
        up2 = g_layer(input_tensor=up2, n_filters=2 * self.gf, padding='valid')  # 14x14x14

        up1 = concatenate(
            [Cropping3D(((16, 16), (16, 16), (16, 16)))(down1), UpSampling3D(size=(2, 2, 2))(up2)])  # 28x28x28
        up1 = g_layer(input_tensor=up1, n_filters=self.gf, padding='valid')  # 26x26x26
        up1 = g_layer(input_tensor=up1, n_filters=self.gf, padding='valid')  # 24x24x24

        # ToDo: check if the activation function 'sigmoid' is the right one or leave it to be linear; originally sigmoid
        phi = Conv3D(filters=1, kernel_size=(1, 1, 1), use_bias=False)(up1)  # 24x24x24

        model = Model(inputs=combined_imgs, outputs=phi)

        return model

    """
    Descriminator Network
    """
    def build_discriminator(self):

        def d_layer(layer_input, filters, f_size=3, bn=True):
            """Discriminator layer"""
            d = Conv3D(filters, kernel_size=f_size, strides=1, padding='same')(layer_input)
            d = ReLU()(d)
            if bn:
                d = BatchNormalization()(d)
            return d

        img_A = Input(shape=self.input_shape_d) #24x24x24
        img_B = Input(shape=self.input_shape_d) #24x24x24

        # Concatenate image and conditioning image by channels to produce input
        combined_imgs = Concatenate(axis=-1)([img_A, img_B])

        d1 = d_layer(combined_imgs, self.df, bn=False) #24x24x24
        d2 = d_layer(d1, self.df*2)                    #24x24x24
        pool = MaxPooling3D(pool_size=(2, 2, 2))(d2)   #12x12x12

        d3 = d_layer(pool, self.df*4)                  #12x12x12
        d4 = d_layer(d3, self.df*8)                    #12x12x12
        pool = MaxPooling3D(pool_size=(2, 2, 2))(d4)   #6x6x6

        d4 = d_layer(pool, self.df*8)                  #6x6x6

        # ToDo: check if the activation function 'sigmoid' is the right one or leave it to be linear; originally linear
        # ToDo: Use FC layer at the end like specified in the paper
        validity = Conv3D(1, kernel_size=4, strides=1, padding='same', activation='sigmoid')(d4) #6x6x6
        #validity = Dense(1, activation='sigmoid')(d4)

        return Model([img_A, img_B], validity)


    """
    Deformable transformation layer
    """
    def deformable_transformation_layer(self, deformable_field, subject_image):
        # TODO: trilinear interpolation
        return subject_image


    """
    Define losses
    """
    # def discriminator_loss(self,y_true,y_pred):
    #     if y_true == 0: #fake (negative case: images are not well registered)
    #         score = K.log(y_pred)
    #     else: # real (positive case: well registered images)
    #         score = K.log(1-y_pred)
    #     return score

    def gradient_penalty_loss(self, y_true, y_pred, phi):
        """
        Computes gradient penalty on phi to ensure smoothness
        """
        if y_true == 0:
            lr = -K.log(1-y_pred) # negative sign because the loss should be a positive value
        else:
            lr = 0  # no loss in the other case because the y_true in all the generation case should be 0
        #  Get the numerical gradient of phi by putting variables as 1
        x = K.variable([1])
        gradients = K.gradients(phi, x)[0] #FIXME: grandients return None: need to implement the numerical gradient
        # compute the euclidean norm by squaring ...
        gradients_sqr = K.square(gradients)
        #   ... summing over the rows ...
        gradients_sqr_sum = K.sum(gradients_sqr,
                                  axis=np.arange(1, len(gradients_sqr.shape)))
        #   ... and sqrt
        gradient_l2_norm = K.sqrt(gradients_sqr_sum)
        # compute lambda * (1 - ||grad||)^2 still for each single sample
        gradient_penalty = K.square(1 - gradient_l2_norm)
        # return the mean as loss over all the batch samples
        return K.mean(gradient_penalty)


    def registration_loss(self, y_true, y_pred):
        if y_true == 0:
            lr = -K.log(1-y_pred)  # negative because the loss has to be positive vaue
        else:
            lr = 0  # no loss in the other case because the y_true in all the generation case should be 0

        # smoothness term
        reg_lambda = 1
        lreg = reg_lambda * 1 #TODO add lreg (np.gradient) which is the gradient loss
        score = lr + lreg

        return score


    # Wrapper over dense_image_warp function in tensor flow to use in Lambda layer in Keras
    def warp(self,img, flow):
        # deformable_field (flow) 24x24x24
        # subject_image (img) 64x64x64
        # return should be warped image 24x24x24 #fixme
        # This use bilinear interpolation --> not intended for 3D image
        warped_image = dense_image_warp(image=img, flow=flow)

        return warped_image