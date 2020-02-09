from tkinter import *
import cv2
import pyzbar.pyzbar as pyzbar
from lxml import html
import requests
import numpy as np
import mysql.connector
import datetime
from tkinter import *

# pip install pillow
from PIL import Image, ImageTk

main_window = 0
data_window = 0

row = 0 #what row of the database we are showing
item_data = 0 #text on screen

#sql code

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  passwd="password",
  auth_plugin='mysql_native_password',
  database="Code211"
)

mycursor = mydb.cursor()

# mycursor.execute("CREATE TABLE items (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), quantity VARCHAR(255), last VARCHAR(255))")

def add_to_db(title):
    #check if already exists
    title = str(title)
    title = title.replace("'", "")
    sql = "SELECT * FROM items where name = '" + title + "'"

    mycursor.execute(sql)

    result = mycursor.fetchall()
    print(result)
    if result: #found
        row = result[0]
        quantity = row[2]
        quantity = int(quantity)
        quantity += 1
        quantity = str(quantity)

        mycursor.execute('''UPDATE items SET quantity = %s WHERE name = %s''', (quantity, title))
        mydb.commit()

    else: #didnt find
        time = str(datetime.datetime.now())

        sql = '''INSERT INTO items (name, quantity, last) VALUES (%s, %s, %s)'''
        val = (title, "1", time)
        mycursor.execute(sql, val)

        mydb.commit()

        print(mycursor.rowcount, "created new record")

def clamp(val, min, max):
    if val >= max:
        return max
    elif val <= min:
        return min
    return val

def get_from_db():

    global row

    mycursor.execute("SELECT * FROM items")

    myresult = mycursor.fetchall()

    number = len(myresult)

    max_row = int(number / 5)

    row = clamp(row, 0, max_row)

    # print("row ", row)

    start = int(row * 5)
    end = int(row * 5 + 5)

    # print(str(start) + " " + str(end))

    text = ""

    for x in range(start, clamp(int(end), 0, int(number))):
        value = myresult[x]

        title = value[1]
        quantity = value[2]
        date = value[3]

        text += title + "\nQuantity: " + quantity + "\nLast Entered: " + date + "\n\n"

    return text



#barcode code

def decode(im): #decodes a barcode
    # Find barcodes and QR codes
    decodedObjects = pyzbar.decode(im)
    return decodedObjects

def getTitle(decodedObjects):
    for obj in decodedObjects:
        data = str(obj.data)
        upc = data[2:len(data) - 1]
        print(upc)

        page = requests.get('https://www.upcitemdb.com/upc/' + upc)
        tree = html.fromstring(page.content)

        # This will create a list of buyers:
        title = tree.xpath('//b/text()')

        if len(title) > 0:
            return title[0]
    return ""

# Display barcode and QR code location
def display(im, decodedObjects):
    # Loop over all decoded objects
    for decodedObject in decodedObjects:
        points = decodedObject.polygon

        # If the points do not form a quad, find convex hull
        if len(points) > 4:
            hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
            hull = list(map(tuple, np.squeeze(hull)))
        else:
            hull = points

        # Number of points in the convex hull
        n = len(hull)

        # Draw the convext hull
        for j in range(0, n):
            cv2.line(im, hull[j], hull[(j + 1) % n], (255, 0, 0), 3)

    # Display results
    cv2.imshow("Add Items", im)

def showNumbers(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


    et, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
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

    line = {}  # lines of images

    for i, ctr in enumerate(sorted_ctrs):
        # Get bounding box
        x, y, w, h = cv2.boundingRect(ctr)

        if (w < 2 and h < 2) or (w > 45 and h > 45):  # small speck, doesn't matter
            continue

        if abs(w - h) > 15:  # get rid of barcodeS
            continue

        # Getting ROI
        roi = frame[y:y + h, x:x + w]

        found = False  # found a line this box is on

        for key in line.keys():  # every previous line
            if abs(key - y) <= 2:  # on the line
                arr = line[key]
                arr.append([x, y, w, h])  # add to array
                line[key] = arr  # update
                found = True  # now found

        if not found:
            line[y] = []  # create new key and value

        # show ROI
        # cv2.imshow('segment no:'+str(i),roi)
        # frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # cv2.waitKey(0)

    for key in line.keys():
        if len(line[key]) >= 11:  # should be 13, but just in case

            arr = line[key]

            for val in arr:
                x = val[0]
                y = val[1]
                w = val[2]
                h = val[3]

                frame = cv2.rectangle(frame,(x,y),( x + w, y + h ),(0,255,0),2)

    return frame

def camera():
    cap = cv2.VideoCapture(0)
    show_boxes = False
    while (True):
        # Capture frame-by-frame
        ret, frame = cap.read()

        # Display the resulting frame
        #cv2.imshow('frame', frame)

        decoded = decode(frame)


        if show_boxes:
            frame = showNumbers(frame)
            frame = cv2.putText(frame, 'Showing Bounding Boxes', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2,
                                cv2.LINE_AA)
            frame = cv2.putText(frame, 'click s to switch mode', (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0),
                                1,
                                cv2.LINE_AA)
            frame = cv2.putText(frame, 'click q to quit', (10, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1,
                                cv2.LINE_AA)
            display(frame, decoded)
        else:
            frame = cv2.putText(frame, 'Scanning Barcodes', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
            frame = cv2.putText(frame, 'click s to switch mode', (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0),
                                1,
                                cv2.LINE_AA)
            frame = cv2.putText(frame, 'click q to quit', (10, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1,
                                cv2.LINE_AA)
            title = getTitle(decoded)

            if title != "":
                add_to_db(title)
                break
            cv2.imshow('frame', frame)

        if cv2.waitKey(1) & 0xFF == ord('s'):
            show_boxes = not show_boxes
            cv2.destroyAllWindows()

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # When everything done, release the capture
    cap.release()
    cv2.destroyAllWindows()

#show data

def showNext():
    global row
    row += 1
    item_data["text"] = get_from_db()

def showBack():
    global row
    row -= 1
    item_data["text"] = get_from_db()

def goBack():
    global data_window

    data_window.destroy()

    showMain()

def showDatabase():
    global data_window, item_data, row

    main_window.destroy()

    data_window = Tk()

    title = Label(data_window, text="Item Scanner App", fg='black', font=("ms sans serif", 32))
    title.place(x=85, y=25)

    item_data = Label(data_window, text=get_from_db(), fg='black', font=("Helvetica", 8))
    item_data.place(x=65, y=125)

    nextBtn = Button(data_window, text="Next", fg='black', command=showNext , font=("Helvetica", 15))
    nextBtn.place(x=225, y=450)

    backBtn = Button(data_window, text="Back", fg='black', command=showBack , font=("Helvetica", 15))
    backBtn.place(x=150, y=450)

    exitBtn = Button(data_window, text="Exit", fg='black', command=goBack , font=("Helvetica", 15))
    exitBtn.place(x=300, y=450)

    data_window.title('View Items')
    data_window.geometry('500x500')
    data_window.configure(bg='#83ECC4')
    data_window.mainloop()

#tkinter code
def showMain():
    global main_window
    main_window = Tk()

    title = Label(main_window, text="Item Scanner App", fg='black', font=("ms sans serif", 32))
    title.place(x=85, y=25)

    by = Label(main_window, text="created by: Ashay Parikh", fg='black', font=("ms sans serif", 16))
    by.place(x=115, y=100)

    load = Image.open("scanner6.jpg")
    render = ImageTk.PhotoImage(load)
    img = Label(main_window, image=render, height = 150, width = 150)
    img.image = render
    img.place(x=150, y=150)

    cameraBtn = Button(main_window, text="Add Item", fg='black', command=camera, font=("ms sans serif", 16))
    cameraBtn.place(x=185, y=325)

    viewBtn = Button(main_window, text="View Items", fg='black', command=showDatabase, font=("ms sans serif", 16))
    viewBtn.place(x=185, y=400)

    main_window.title('Menu')
    main_window.geometry('500x500')
    main_window.configure(bg='#83ECC4')
    main_window.mainloop()

showMain()