import nrrd
import scipy
import random
import numpy as np
from glob import glob
import matplotlib.pyplot as plt
from skimage.transform import resize


__author__ = 'elmalakis'


class DataLoader():

    def __init__(self, batch_sz = 16, sample_type = 'fly'):
        """
        :param batch_sz: int - size of the batch
        :param sampletype: string - 'fly' or 'fish'
        """
        self.batch_sz = batch_sz

        self.imgs = []
        self.masks = []
        self.img_template = None
        self.mask_template = None

        self.imgs_test = []
        self.masks_test = []

        if sample_type is 'fly':
            self.imgs, self.masks, self.img_template, self.mask_template, self.imgs_test, self.masks_test, self.n_batches = self.prepare_fly_data(batch_sz)
        elif sample_type is 'fish':
            self.imgs, self.masks, self.img_template, self.mask_template, self.imgs_test, self.masks_test, self.n_batches = self.prepare_fish_data(batch_sz)
        else:
            raise ValueError('Data of type %s is not available'%(sample_type))



    def prepare_fish_data(self, batch_sz):

        self.batch_sz = batch_sz
        self.n_gpus = 1
        self.crop_sz = (40, 40, 40)  # the image shape is 1227,1996,40, and sometimes 1170, 1996,43
        self.mask_sz = (40, 40, 40)

        imgs = []
        masks = []
        img_template = None
        mask_template = None

        imgs_test = []
        masks_test = []

        template_shape = (1166, 1996, 40) # most of the images have this size

        filepath = '/nrs/scicompsoft/elmalakis/GAN_Registration_Data/fishdata/data/for_salma/preprocess_to_4/'
        img_pp = [filepath +'subject_1_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_2_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_3_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_4_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_5_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_6_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_7_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_8_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_9_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_10_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_11_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_12_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_13_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_14_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_15_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_16_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_17_anat_stack_regiprep_pp.nii.gz',
                  filepath + 'subject_18_anat_stack_regiprep_pp.nii.gz'
                  ]

        mask_pp = [filepath + 'subject_1_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_2_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_3_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_4_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_5_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_6_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_7_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_8_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_9_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_10_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_11_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_12_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_13_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_14_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_15_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_16_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_17_anat_stack_regiprep_mask.nii.gz',
                   filepath + 'subject_18_anat_stack_regiprep_mask.nii.gz'
                  ]

        print('----- loading data file -----')
        for i in range(len(img_pp)):
            # images normalize
            curr_img, meta_dict = self._read_nifti(img_pp[i])
            curr_img = np.float32(curr_img)
            curr_img = (curr_img - np.mean(curr_img))/ np.std(curr_img)
            # masks 1: interesting value, 0: not interesting value
            curr_mask, meta_dict = self._read_nifti(mask_pp[i])
            curr_mask = np.float32(curr_mask)

            # resize
            if curr_img.shape != template_shape:
                curr_img = resize(curr_img, template_shape, anti_aliasing=True)
                curr_mask = resize(curr_mask, template_shape, anti_aliasing=True)

            masks.append(curr_mask)
            imgs.append(curr_img)

        # template is subject 4
        img_template = self.imgs.pop(3)
        mask_template = self.masks.pop(3)

        # test is subject 16, 17, 18 after popping subject 4 the indices are 14, 15, 16 (Indices start at 0)
        imgs_test.append(self.imgs.pop(16))
        imgs_test.append(self.imgs.pop(15))
        imgs_test.append(self.imgs.pop(14))

        masks_test.append(self.masks.pop(16))
        masks_test.append(self.masks.pop(15))
        masks_test.append(self.masks.pop(14))

        n_batches = int( (len(self.imgs) * template_shape[0] / self.crop_sz[0] )  / self.batch_sz)

        return imgs, masks, img_template, mask_template, imgs_test, masks_test, n_batches


    def prepare_fly_data(self, batch_sz):
        self.batch_sz = batch_sz
        self.n_gpus = 1
        self.crop_sz = (64, 64, 64)
        self.mask_sz = (64, 64, 64)

        imgs = []
        masks = []
        img_template = None
        mask_template = None

        imgs_test = []
        masks_test = []


        filepath = '/nrs/scicompsoft/elmalakis/GAN_Registration_Data/flydata/forSalma/lo_res/preprocessed/'
        img_pp = [filepath + '20161102_32_C1_Scope_1_C1_down_result_normalized.nrrd',
                  filepath + '20161102_32_C3_Scope_4_C1_down_result_normalized.nrrd',
                  filepath + '20161102_32_D1_Scope_1_C1_down_result_normalized.nrrd',
                  filepath + '20161102_32_D2_Scope_1_C1_down_result_normalized.nrrd',
                  filepath + '20161102_32_E1_Scope_1_C1_down_result_normalized.nrrd',
                  filepath + '20161102_32_E3_Scope_4_C1_down_result_normalized.nrrd',
                  filepath + '20161220_31_I1_Scope_2_C1_down_result_normalized.nrrd',
                  filepath + '20161220_31_I2_Scope_6_C1_down_result_normalized.nrrd',
                  filepath + '20161220_31_I3_Scope_6_C1_down_result_normalized.nrrd',
                  filepath + '20161220_32_C1_Scope_3_C1_down_result_normalized.nrrd',
                  filepath + '20161220_32_C3_Scope_3_C1_down_result_normalized.nrrd',
                  filepath + '20170223_32_A2_Scope_3_C1_down_result_normalized.nrrd',
                  filepath + '20170223_32_A3_Scope_3_C1_down_result_normalized.nrrd',
                  filepath + '20170223_32_A6_Scope_2_C1_down_result_normalized.nrrd',
                  filepath + '20170223_32_E1_Scope_3_C1_down_result_normalized.nrrd',
                  filepath + '20170223_32_E2_Scope_3_C1_down_result_normalized.nrrd',
                  filepath + '20170223_32_E3_Scope_3_C1_down_result_normalized.nrrd',
                  filepath + '20170301_31_B1_Scope_1_C1_down_result_normalized.nrrd',
                  filepath + '20170301_31_B3_Scope_1_C1_down_result_normalized.nrrd',
                  filepath + '20170301_31_B5_Scope_1_C1_down_result_normalized.nrrd'
                  ]

        mask_pp = [filepath + '20161102_32_C1_Scope_1_C1_down_result_mask.nrrd',
                   filepath + '20161102_32_C3_Scope_4_C1_down_result_mask.nrrd',
                   filepath + '20161102_32_D1_Scope_1_C1_down_result_mask.nrrd',
                   filepath + '20161102_32_D2_Scope_1_C1_down_result_mask.nrrd',
                   filepath + '20161102_32_E1_Scope_1_C1_down_result_mask.nrrd',
                   filepath + '20161102_32_E3_Scope_4_C1_down_result_mask.nrrd',
                   filepath + '20161220_31_I1_Scope_2_C1_down_result_mask.nrrd',
                   filepath + '20161220_31_I2_Scope_6_C1_down_result_mask.nrrd',
                   filepath + '20161220_31_I3_Scope_6_C1_down_result_mask.nrrd',
                   filepath + '20161220_32_C1_Scope_3_C1_down_result_mask.nrrd',
                   filepath + '20161220_32_C3_Scope_3_C1_down_result_mask.nrrd',
                   filepath + '20170223_32_A2_Scope_3_C1_down_result_mask.nrrd',
                   filepath + '20170223_32_A3_Scope_3_C1_down_result_mask.nrrd',
                   filepath + '20170223_32_A6_Scope_2_C1_down_result_mask.nrrd',
                   filepath + '20170223_32_E1_Scope_3_C1_down_result_mask.nrrd',
                   filepath + '20170223_32_E2_Scope_3_C1_down_result_mask.nrrd',
                   filepath + '20170223_32_E3_Scope_3_C1_down_result_mask.nrrd',
                   filepath + '20170301_31_B1_Scope_1_C1_down_result_mask.nrrd',
                   filepath + '20170301_31_B3_Scope_1_C1_down_result_mask.nrrd',
                   filepath + '20170301_31_B5_Scope_1_C1_down_result_mask.nrrd'

                   ]

        print('----- loading data file -----')
        for i in range(len(img_pp)):
            # images normalize
            curr_img, img_header = nrrd.read(img_pp[i])
            curr_img = np.float32(curr_img)
            curr_img = (curr_img - np.mean(curr_img)) / np.std(curr_img)
            # masks 1: interesting value, 0: not interesting value
            curr_mask, mask_header = nrrd.read(mask_pp[i])
            curr_mask = np.float32(curr_mask)

            masks.append(curr_mask)
            imgs.append(curr_img)

        # template
        img_template, templ_header = nrrd.read(filepath + 'JRC2018_lo_normalized.nrrd')
        img_template = np.float32(img_template)
        img_template = (img_template - np.mean(img_template)) / np.std(img_template)
        mask_template, templ_header = nrrd.read(filepath + 'JRC2018_lo_mask.nrrd')

        # TODO: save test images
        # test is subject 16, 17, 18 after popping subject 4 the indices are 14, 15, 16 (Indices start at 0)
        # imgs_test.append(self.imgs.pop(16))
        # imgs_test.append(self.imgs.pop(15))
        # imgs_test.append(self.imgs.pop(14))
        #
        # masks_test.append(self.masks.pop(16))
        # masks_test.append(self.masks.pop(15))
        # masks_test.append(self.masks.pop(14))

        n_batches = int((len(imgs) * img_template.shape[0] / self.crop_sz[0]) / self.batch_sz)

        return imgs, masks, img_template, mask_template, imgs_test, masks_test, n_batches


    def get_template(self):
        return self.img_template

    def load_data(self, batch_size=1, is_testing=False, is_validation=False):
        #idxs = []
        #test_images = []
        #test_masks = []

        #for batch in range(batch_size):

        idx = None
        test_image = None
        test_mask = None
        if is_testing:
             #use batch_size=1 for now
            idx, test_image = random.choice(list(enumerate(self.imgs_test)))
            test_mask = self.masks_test[idx]
            #idxs.append(idx)
            #test_images.append(test_image)
            #test_masks.append(test_mask)

        elif is_validation:
            idx, test_image = random.choice(list(enumerate(self.imgs)))
            test_mask = self.masks[idx]

        return idx, test_image, test_mask


    def load_batch(self, sample_type = 'fly'):

        for i in range(self.n_batches - 1):
            #print('----- loading a batch -----')
            batch_img = np.zeros((self.batch_sz, self.crop_sz[0], self.crop_sz[1], self.crop_sz[2], 1), dtype='float32')
            batch_mask = np.zeros((self.batch_sz, self.mask_sz[0], self.mask_sz[1], self.mask_sz[2], 1), dtype='float32')

            batch_img_template = np.zeros((self.batch_sz, self.crop_sz[0], self.crop_sz[1], self.crop_sz[2], 1), dtype='float32')
            batch_mask_template = np.zeros((self.batch_sz, self.mask_sz[0], self.mask_sz[1], self.mask_sz[2], 1), dtype='float32')

            # randomly crop an image from imgs list
            idx = np.random.randint(0, len(self.imgs))
            img_for_crop = self.imgs[idx]
            mask_for_crop = self.masks[idx]

            num_crop = 0
            while num_crop < self.batch_sz:
                x = np.random.randint(0, img_for_crop.shape[0] - self.crop_sz[0])
                y = np.random.randint(0, img_for_crop.shape[1] - self.crop_sz[1])
                if sample_type is 'fish': z = 0 # take the whole dimension of Z
                else: z = np.random.randint(0, img_for_crop.shape[2] - self.crop_sz[2])
                # crop in the x-y dimension only and use the all the slices
                cropped_img = img_for_crop[x:x+self.crop_sz[0], y:y+self.crop_sz[1], z:z+self.crop_sz[2]]
                cropped_img_template = self.img_template[x:x + self.crop_sz[0], y:y + self.crop_sz[1], z:z+self.crop_sz[2]]
                cropped_mask = mask_for_crop[x:x + self.crop_sz[0], y:y + self.crop_sz[1], z:z+self.crop_sz[2]]
                cropped_mask_template = self.mask_template[x:x + self.crop_sz[0], y:y + self.crop_sz[1], z:z+self.crop_sz[2]]
                # if include the random crop in training
                is_include = False
                num_vox = len(cropped_mask[cropped_mask == 1])

                accept_prob = np.random.random()
                if num_vox > 500 and accept_prob > 0.98:
                    is_include = True

                if is_include:
                    #print('include this batch %d' %(num_crop))
                    batch_img[num_crop,:,:,:,0] = cropped_img
                    batch_mask[num_crop,:,:,:,0] = cropped_mask

                    # filter the image with the mask
                    batch_img = batch_img * batch_mask

                    batch_img_template[num_crop,:,:,:,0] = cropped_img_template
                    batch_mask_template[num_crop,:,:,:,0] = cropped_mask_template

                    # filter the template with the mask
                    batch_img_template = batch_img_template * batch_mask_template

                    num_crop += 1

            # TODO: data augmentation if needed

            yield batch_img, batch_img_template


    def _read_nifti(self,path, meta_dict={}):
        import nibabel as nib
        image = nib.load(path)
        image_data = image.get_data().squeeze()
        new_meta_dict = dict(image.header)
        meta_dict = {**new_meta_dict, **meta_dict}
        return image_data, meta_dict

    def _write_nifti(self,path, image_data, meta_dict={}):
        #    image_data = _standardize_axis_order(image_data, 'nii') # possibly a bad idea
        import nibabel as nib
        image = nib.Nifti1Image(image_data, None)
        for key in meta_dict.keys():
            if key in image.header.keys():
                image.header[key] = meta_dict[key]
        nib.save(image, path)


if __name__ == '__main__':
    dataloader = DataLoader()
    dataloader.load_batch()