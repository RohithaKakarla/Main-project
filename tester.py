
import torch
import cv2
import numpy as np

import torch.nn as nn
import torch.nn.functional as F
from .SUMNet_bn import SUMNet
import SimpleITK as sitk
import matplotlib.pyplot as plt
import pandas as pd
from glob import glob
from torchvision import transforms

def load_itk_image(filename):
    itkimage = sitk.ReadImage(filename)
    numpyImage = sitk.GetArrayFromImage(itkimage)

    numpyOrigin = np.array(list(reversed(itkimage.GetOrigin())))
    numpySpacing = np.array(list(reversed(itkimage.GetSpacing())))
    return numpyImage, numpyOrigin, numpySpacing

def get_filename(case):
    global file_list
    for f in file_list:
        if case in f:
            return(f)



def segment_function(luna_subset_path,result_path,img_file,seg_model_loadPath):

    itk_img = sitk.ReadImage(img_file)
    img_tensor = torch.from_numpy(sitk.GetArrayFromImage(itk_img)).unsqueeze(1).float()


    netS = SUMNet(in_ch=1,out_ch=2)
    netS.load_state_dict(torch.load(seg_model_loadPath+'sumnet_cpu.pt'))

    apply_norm = transforms.Normalize([-460.466],[444.421])
    N = int(img_tensor.shape[0]/5)

    print("Its running")
    for sliceNum in range(N,img_tensor.shape[0]-N):
        img_slice = img_tensor[sliceNum]
        mid_mean = img_slice[:,100:400,100:400].mean()
        img_slice[img_slice==img_slice.min()] = mid_mean
        img_slice[img_slice==img_slice.max()] = mid_mean
        img_slice_norm = apply_norm(img_slice).unsqueeze(0)
        print("data is being prepared")

        out = F.softmax(netS(img_slice_norm),dim=1)
        out_np = np.asarray(out[0,1].squeeze(0).detach().cpu().numpy()*255,dtype=np.uint8)

        ret, thresh = cv2.threshold(out_np,0,1,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        connectivity = 4
        output = cv2.connectedComponentsWithStats(thresh, connectivity, cv2.CV_32S)
        stats = output[2]
        temp = stats[1:, cv2.CC_STAT_AREA]
        print("entering a loop bro")
        if len(temp)>0:
            largest_label = 1 + np.argmax(temp)
            areas = stats[1:, cv2.CC_STAT_AREA]
            max_area = np.max(areas)
            if max_area>150:
                print('Slice:',sliceNum+1)
                out_mask = np.zeros((512,512))
                idx = np.where(output[1]==largest_label)
                out_mask[idx] = 1
                plt.figure(figsize=[15,5])
                plt.subplot(131)
                plt.imshow(img_slice.squeeze(0).squeeze(0).numpy(),cmap='gray')
                plt.title('Original image')
                plt.subplot(132)
                plt.imshow(out[0,1].squeeze(0).detach().numpy(),cmap='gray')
                plt.title('Segmented regions')
                plt.subplot(133)
                plt.imshow(out_mask,cmap='gray')
                plt.title('Detected largest nodule')
                plt.savefig(result_path+'slice_'+str(sliceNum+1)+'.png')
                plt.close()
