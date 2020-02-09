import numpy as np
from keras.models import model_from_yaml
import cv2
import math

# load YAML and create model
yaml_file = open('model1.yaml', 'r')
loaded_model_yaml = yaml_file.read()
yaml_file.close()
loaded_model = model_from_yaml(loaded_model_yaml)
# load weights into new model
loaded_model.load_weights("model1.h5")
print("Loaded model from disk")


cap = cv2.VideoCapture(0)
good = []

while(True):
    # Capture frame-by-frame
    ret, frame = cap.read()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


    # ret2, thresh = cv2.threshold(gray, 127, 255, 0)
    # image, contours = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    #
    # cnt = contours[0]
    # ctr = np.array(cnt).reshape((-1, 1, 2)).astype(np.int32)
    # img = cv2.drawContours(frame, [ctr], -1, 255, -1)


    # #converts to white and black
    # (thresh, im_bw) = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    # thresh = 127
    # im_bw = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)[1]

    ret, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    # dilation
    kernel = np.ones((1, 1), np.uint8)
    img_dilation = cv2.dilate(thresh, kernel, iterations=1)
    # cv2.imshow('dilated', img_dilation)

    # find contours - cv2.findCountours() function changed from OpenCV3 to OpenCV4: now it have only two parameters instead of 3
    cv2MajorVersion = cv2.__version__.split(".")[0]
    # check for contours on thresh
    if int(cv2MajorVersion) == 4:
        ctrs, hier = cv2.findContours(img_dilation.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    else:
        im2, ctrs, hier = cv2.findContours(img_dilation.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # sort contours
    sorted_ctrs = sorted(ctrs, key=lambda ctr: cv2.boundingRect(ctr)[0])

    line = {} #lines of images

    for i, ctr in enumerate(sorted_ctrs):
        # Get bounding box
        x, y, w, h = cv2.boundingRect(ctr)

        if (w < 10 and h < 10) or (w > 45 and h > 45):  # small speck, doesn't matter
            continue

        if abs(w - h) > 15: #get rid of barcodeS
            continue

        # Getting ROI
        roi = frame[y:y + h, x:x + w]

        found = False #found a line this box is on

        for key in line.keys(): #every previous line
            if abs(key - y) <= 2: #on the line
                arr = line[key]
                arr.append([x, y, w, h]) #add to array
                line[key] = arr #update
                found = True #now found

        if not found:
            line[y] = [] #create new key and value

        # show ROI
        #cv2.imshow('segment no:'+str(i),roi)
        frame = cv2.rectangle(frame,(x,y),( x + w, y + h ),(0,255,0),2)
        #cv2.waitKey(0)

    good = []

    for key in line.keys():
        if len(line[key]) >= 13: #should be 13, but just in case

            arr = line[key]

            good.append(arr)

            for val in arr:
                x = val[0]
                y = val[1]
                w = val[2]
                h = val[3]

                #frame = cv2.rectangle(frame,(x,y),( x + w, y + h ),(0,255,0),2)

    if len(good) > 0:
        break

    # Display the resulting frame
    cv2.imshow('frame',frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

for arr in good:
    for val in arr:
        x = val[0] - 2
        y = val[1] - 2
        w = val[2] + 2
        h = val[3] + 2

        roi = frame[y:y + h, x:x + w]
        resized = cv2.resize(roi, (28, 28))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        gray = gray.reshape((1, 1, 28, 28)).astype("float32") / 255
        result = loaded_model.predict(gray)
        result = result[0]
        max_char = np.where(result == np.amax(result))

        print(max_char)

        cv2.imshow('frame', resized)
        cv2.waitKey(0)

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()